"""Puente JSON para la app nativa. Una petición por proceso, nunca shell libre."""
from contextlib import redirect_stdout
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from .core import (MAX_BATCH, MAX_IMAGES, ShotError, Target, append_image, atomic_json,
                   discard_images, discover, image_paths, message, operation, read_image,
                   receipt, revalidate, runtime, target_lock)
from .iterm_adapter import send


class DesktopError(ShotError):
    pass


def get_operation(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise DesktopError('Identificador de operación inválido.')
    path = runtime() / 'operations' / identifier
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise DesktopError('Operación no privada o no disponible.')
    return path


def operation_state(path):
    fd = os.open(path / 'receipt.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise DesktopError('Recibo no privado o no regular.')
        data = stream.read(4097)
    if len(data) > 4096:
        raise DesktopError('Recibo inválido.')
    return json.loads(data)['state']


def checked_target(data):
    if not isinstance(data, dict):
        raise DesktopError('Selecciona una sesión local.')
    required = ('session_id', 'tty', 'pid', 'started')
    if any(key not in data for key in required):
        raise DesktopError('Identidad de destino incompleta.')
    if type(data['pid']) is not int or data['pid'] <= 0:
        raise DesktopError('PID inválido.')
    if any(not isinstance(data[key], str) or not 0 < len(data[key]) <= 256
           for key in ('session_id', 'tty', 'started')):
        raise DesktopError('Identidad de destino inválida.')
    return Target(**{key: data[key] for key in required})


def cancel(op):
    with target_lock(Target('operation:' + op.name, '', 0, '')):
        return _cancel(op)


def _cancel(op):
    if operation_state(op) != 'preparing' or (op / 'attempted').exists():
        raise DesktopError('La escritura pudo comenzar; no se cancela ni elimina la imagen.')
    discard_images(op)
    receipt(op, 'cancelled')
    return {'state': 'cancelled', 'operation': op.name}


def batch_reply(op, state='prepared'):
    paths = image_paths(op)
    return {'state': state, 'operation': op.name, 'image_paths': list(map(str, paths)),
            'image_path': str(paths[-1]) if paths else None, 'count': len(paths), 'max_images': MAX_IMAGES}


def prepare(request):
    existing = request.get('operation') is not None
    op = get_operation(request['operation']) if existing else operation()
    with target_lock(Target('operation:' + op.name, '', 0, '')):
        if operation_state(op) != 'preparing' or (op / 'attempted').exists():
            raise DesktopError('El lote ya se intentó; no se puede modificar.')
        if len(image_paths(op)) >= MAX_IMAGES:
            raise DesktopError('Máximo 6 capturas por mensaje.')
        source = None
        try:
            if request['action'] == 'capture':
                source = op / 'capture.png'
                try:
                    result = subprocess.run(['/usr/sbin/screencapture', '-i', '-s', '-t', 'png', str(source)],
                                            capture_output=True, timeout=180)
                except subprocess.TimeoutExpired:
                    source.unlink(missing_ok=True)
                    return batch_reply(op, 'capture_cancelled') if image_paths(op) else _cancel(op)
                if result.returncode or not source.exists() or source.stat().st_size == 0:
                    source.unlink(missing_ok=True)
                    return batch_reply(op, 'capture_cancelled') if image_paths(op) else _cancel(op)
                os.chmod(source, 0o600)
            else:
                value = request.get('path')
                if not isinstance(value, str) or not value:
                    raise DesktopError('Elige un PNG local.')
                source = Path(value).absolute()
            append_image(source, op)
            if request['action'] == 'capture':
                source.unlink()
            return batch_reply(op)
        except Exception:
            if request['action'] == 'capture' and source is not None:
                source.unlink(missing_ok=True)
            if not existing:
                discard_images(op)
                receipt(op, 'failed')
            raise


def remove(request):
    op = get_operation(request.get('operation'))
    with target_lock(Target('operation:' + op.name, '', 0, '')):
        if operation_state(op) != 'preparing' or (op / 'attempted').exists():
            raise DesktopError('No se puede modificar un lote intentado.')
        paths = image_paths(op)
        index = request.get('index')
        if type(index) is not int or not 0 <= index < len(paths):
            raise DesktopError('Índice de captura inválido.')
        removed = paths.pop(index)
        atomic_json(op / 'images.json', [p.name for p in paths])
        removed.unlink()
        return batch_reply(op) if paths else _cancel(op)


def submit(request):
    op = get_operation(request.get('operation'))
    with target_lock(Target('operation:' + op.name, '', 0, '')):
        return _submit(request, op)


def _submit(request, op):
    if operation_state(op) != 'preparing':
        raise DesktopError('Esta operación ya terminó o se intentó. Prepara otra imagen; no reintentes a ciegas.')
    target = checked_target(request.get('target'))
    text = request.get('text', '')
    if not isinstance(text, str):
        raise DesktopError('Texto inválido.')
    images = image_paths(op)
    total = sum(len(read_image(image)) for image in images)
    if total > MAX_BATCH:
        raise DesktopError('El lote supera 60 MiB.')
    prompt = message(images, text)
    with target_lock(target):
        revalidate(target)
        # Exclusión por operación aunque dos peticiones elijan paneles distintos.
        try:
            fd = os.open(op / 'attempted', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            raise DesktopError('La operación ya se intentó; comprueba el panel antes de preparar otra.') from None
        os.close(fd)
        try:
            send(target, prompt, op)
        except BaseException:
            if operation_state(op) == 'preparing':
                receipt(op, 'failed')
            raise
    return {'state': 'submitted', 'operation': op.name}


def handle(request):
    if not isinstance(request, dict):
        raise DesktopError('Petición JSON inválida.')
    action = request.get('action')
    if action == 'sessions':
        return {'sessions': [asdict(t) for t in discover()]}
    if action in ('prepare', 'capture'):
        return prepare(request)
    if action == 'send':
        return submit(request)
    if action == 'cancel':
        return cancel(get_operation(request.get('operation')))
    if action == 'remove':
        return remove(request)
    raise DesktopError('Operación no permitida.')


def main():
    request = None
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise DesktopError('Petición demasiado grande.')
        request = json.loads(raw)
        # Cualquier aviso del SDK va a stderr; stdout es exclusivamente JSON.
        with redirect_stdout(sys.stderr):
            result = handle(request)
        response = dict(ok=True, **result)
    except Exception as exc:
        response = {'ok': False, 'error': str(exc) if isinstance(exc, ShotError)
                    else 'Falló el controlador local. Comprueba permisos y el panel; no reintentes a ciegas.'}
        if isinstance(request, dict) and request.get('action') in ('send', 'prepare', 'capture', 'remove') and request.get('operation'):
            response['state'] = 'unknown'
            try:
                op = get_operation(request.get('operation'))
                state = operation_state(op)
                if state == 'preparing' and (op / 'attempted').exists():
                    state = 'uncertain'
                response.update(state=state, operation=op.name)
                if state == 'preparing' and request.get('action') != 'send':
                    response.update(batch_reply(op, state))
            except Exception:
                pass
    print(json.dumps(response))
    return 0 if response['ok'] else 1
