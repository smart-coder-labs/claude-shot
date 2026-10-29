#!/usr/bin/env python3
"""Actualiza descripción/topics por API oficial, sin guardar ni imprimir tokens."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://api.github.com/repos/smart-coder-labs/claude-shot'


def credential():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/usr/bin/false')
    result = subprocess.run(['git', '-c', 'credential.interactive=false', 'credential', 'fill'],
                            input='protocol=https\nhost=github.com\n\n', capture_output=True,
                            text=True, timeout=10, env=env)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    token = values.get('password')
    if not token or '\n' in token or '\r' in token:
        raise RuntimeError('No hay credencial GitHub HTTPS disponible sin interacción.')
    return token


def request(token, method, suffix='', payload=None):
    # Token por stdin de curl, nunca en argv, archivos o logs. Verificación TLS normal.
    config = 'header = ' + json.dumps('Authorization: Bearer ' + token) + '\n'
    config += 'header = "Accept: application/vnd.github+json"\n'
    config += 'header = "X-GitHub-Api-Version: 2022-11-28"\n'
    args = ['curl', '-sS', '--max-time', '25', '--config', '-', '--request', method,
            '--write-out', '\n%{http_code}', BASE + suffix]
    if payload is not None:
        args += ['--header', 'Content-Type: application/json', '--data-binary', json.dumps(payload)]
    result = subprocess.run(args, input=config, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Falló conexión HTTPS con GitHub; no se modificó TLS ni se imprime la credencial.')
    body, _, code = result.stdout.rpartition('\n')
    if not code.startswith('2'):
        raise RuntimeError('GitHub respondió HTTP ' + code + '; revisa permisos del repositorio.')
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Autoriza cambiar descripción y topics remotos')
    args = parser.parse_args()
    desired = json.loads((ROOT / '.github/repository-metadata.json').read_text())
    if not args.apply:
        print(json.dumps(desired, indent=2))
        return
    token = credential()
    request(token, 'PATCH', payload={'description': desired['description']})
    request(token, 'PUT', '/topics', {'names': desired['topics']})
    actual = request(token, 'GET')
    if actual.get('description') != desired['description'] or set(actual.get('topics', [])) != set(desired['topics']):
        raise RuntimeError('No se confirmó toda la metadata remota.')
    print('Descripción y topics de GitHub actualizados y verificados.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'No se pudo completar la actualización remota.')
        raise SystemExit(1)
