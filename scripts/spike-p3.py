#!/usr/bin/env python3
"""Observador P3: sin envío a terminal, sin captura, sin registro de contenido."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.spike-runtime'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PermissionRequest',
          'PostToolUse', 'PostToolUseFailure', 'Notification', 'Stop', 'StopFailure',
          'SubagentStart', 'SubagentStop', 'SessionEnd')
NOTIFICATIONS = {'idle_prompt', 'permission_prompt', 'elicitation_dialog',
                 'elicitation_url_dialog', 'agent_needs_input', 'agent_completed'}
LABELS = ('idle-empty', 'draft', 'draft-multiline', 'menu', 'permission', 'busy',
          'typing-race', 'finished')
LIMIT = 1024 * 1024


class DiagnosticError(Exception):
    """Mensaje fijo seguro para el usuario, sin payloads de hooks."""


def private_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Directorio no privado, ajeno o enlace')


def checked_run(name):
    if not name.startswith('p3-') or not all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
        raise ValueError('Identificador de ensayo inválido')
    private_directory(RUNTIME)
    run = RUNTIME / name
    private_directory(run)
    return run


def safe_record(payload):
    if not isinstance(payload, dict) or payload.get('hook_event_name') not in EVENTS:
        raise ValueError('Evento no admitido')
    record = {'kind': 'hook', 'event': payload['hook_event_name']}
    sid = payload.get('session_id')
    if isinstance(sid, str) and len(sid) <= 256:
        record['session_fingerprint'] = hashlib.sha256(sid.encode()).hexdigest()[:16]
    if record['event'] == 'Notification':
        notification = payload.get('notification_type')
        record['notification_type'] = notification if notification in NOTIFICATIONS else 'other'
    if record['event'] == 'SessionEnd':
        reason = payload.get('reason')
        allowed = ('clear', 'resume', 'logout', 'prompt_input_exit', 'other')
        record['reason'] = reason if isinstance(reason, str) and reason in allowed else 'other'
    # Nunca conservar prompt, message, tool_input/output, rutas ni last_assistant_message.
    return record


def append_record(run, record):
    record = dict(record, observed_at=datetime.now(timezone.utc).isoformat(),
                  monotonic_ns=time.monotonic_ns())
    data = (json.dumps(record, ensure_ascii=True) + '\n').encode()
    fd = os.open(run / 'events.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Log inseguro')
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, data)
    finally:
        os.close(fd)


def prepare():
    os.umask(0o077)
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    private_directory(RUNTIME)
    name = 'p3-' + secrets.token_hex(6)
    run = RUNTIME / name
    run.mkdir(mode=0o700)
    command = shlex.join([sys.executable, '-B', str(Path(__file__).resolve()), 'hook', '--run', name])
    hooks = {event: [{'hooks': [{'type': 'command', 'command': command, 'timeout': 5}]}]
             for event in EVENTS}
    (run / 'settings.json').write_text(json.dumps({'hooks': hooks}, indent=2) + '\n')
    append_record(run, {'kind': 'prepared'})
    print(name)
    print('Ejecutar manualmente en un panel local nuevo; no incluye prompt ni resume:')
    print(shlex.join([sys.executable, '-B', str(Path(__file__).resolve()), 'launch', '--run', name]))


def launch(name):
    run = checked_run(name)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise DiagnosticError('Se requiere un panel de terminal interactivo para lanzar Claude.')
    # No reutilizar el registro para otra conversación.
    try:
        fd = os.open(run / 'launched', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        raise DiagnosticError('Este ensayo ya tiene un intento de arranque. Ejecuta prepare y usa el nuevo ID; no borres launched.') from None
    os.close(fd)
    os.chdir(ROOT)
    args = ['claude', '--setting-sources', '', '--settings', str(run / 'settings.json'),
            '--permission-mode', 'manual', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}']
    try:
        os.execvp(args[0], args)  # Conserva TTY; no proxy PTY, no prompt ni envío.
    except OSError:
        raise DiagnosticError('No se pudo ejecutar Claude. Comprueba command -v claude y prepara un ensayo nuevo.') from None


def status_report(run):
    path = run / 'events.jsonl'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        text = stream.read(4 * LIMIT + 1)
    if len(text) > 4 * LIMIT:
        raise ValueError('Log demasiado grande para este diagnóstico')
    rows = [json.loads(line) for line in text.splitlines()]
    print(json.dumps({'state': 'unknown', 'safe_to_submit': False,
                      'reason': 'Los eventos no prueban borrador vacío ni envío condicional atómico',
                      'records': rows}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('prepare')
    for name in ('hook', 'status', 'launch', 'mark'):
        sub = subs.add_parser(name)
        sub.add_argument('--run', required=True)
        if name == 'mark':
            sub.add_argument('label', choices=LABELS)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
        return
    run = checked_run(args.run)
    if args.command == 'hook':
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Entrada demasiado grande')
        append_record(run, safe_record(json.loads(raw)))
        # Sin stdout ni decisiones de hooks: puramente observacional.
    elif args.command == 'status':
        status_report(run)
    elif args.command == 'mark':
        append_record(run, {'kind': 'human_label', 'label': args.label})
    else:
        launch(args.run)


if __name__ == '__main__':
    try:
        main()
    except DiagnosticError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, TypeError):
        # No volcar excepciones que puedan contener el payload o rutas sensibles.
        print('Diagnóstico P3 no disponible; sin decisión ni permiso de envío.', file=sys.stderr)
        sys.exit(1)
