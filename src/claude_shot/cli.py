import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

from . import __version__
from .core import (IMAGE_NAME, MAX_IMAGES, ROOT, RUNTIME, ShotError, append_image,
                   discard_images, discover, image_paths, message, operation, receipt,
                   revalidate, runtime, target_lock)
from .iterm_adapter import send


WARNING = ('Enter envía la imagen a Claude. El destino debe estar inactivo, sin menús y con el prompt vacío.\n'
           'No escribas en el destino durante el envío. Ctrl+C cancela antes de enviar.')


def target_label(target):
    return f'{target.tab_title or "Sin título"} · {target.tty} · PID {target.pid} · panel {target.session_id}'


def choose(targets, session_id):
    if session_id:
        matches = [t for t in targets if t.session_id == session_id]
        if len(matches) != 1:
            raise ShotError('ID no disponible como Claude local en primer plano.')
        return matches[0]
    if not targets:
        raise ShotError('No hay paneles con un único Claude local en primer plano. SSH/tmux no soportados.')
    for i, target in enumerate(targets, 1):
        print(f'{i}. {target_label(target)}')
    while True:
        value = input('Destino (número de lista, PID o ID completo; vacío cancela): ').strip()
        if not value:
            return None
        matches = {t for t in targets if t.session_id == value}
        if value.isdecimal():
            number = int(value)
            matches.update(t for t in targets if t.pid == number)
            if 1 <= number <= len(targets):
                matches.add(targets[number - 1])
        if len(matches) == 1:
            return matches.pop()
        if matches:
            print('Selección ambigua entre número de lista y PID. Usa el ID completo del panel.')
        else:
            print('No coincide con un destino de la lista. Usa, por ejemplo, 1 para la primera fila.')


def cleanup(hours):
    if hours < 24:
        raise ShotError('La retención mínima de este prototipo es 24 horas.')
    count = 0
    for op in (runtime() / 'operations').iterdir():
        info = op.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            continue
        try:
            fd = os.open(op / 'receipt.json', os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd) as stream:
                rec_info = os.fstat(stream.fileno())
                if not stat.S_ISREG(rec_info.st_mode) or rec_info.st_size > 4096:
                    continue
                state = json.load(stream)['state']
            if state not in ('submitted', 'uncertain', 'cancelled', 'failed'):
                continue
            if time.time() - rec_info.st_mtime < hours * 3600:
                continue
            files = list(op.iterdir())
            if any((p.name not in ('receipt.json', 'capture.png', 'attempted', 'images.json')
                    and not IMAGE_NAME.fullmatch(p.name)) or p.is_symlink() or not p.is_file() for p in files):
                continue
            for path in files:
                path.unlink()
            op.rmdir()
            count += 1
        except (OSError, ValueError, KeyError):
            continue
    print(f'Operaciones eliminadas: {count}. No hay limpieza periódica automática.')


def workflow(args):
    if not sys.stdin.isatty():
        raise ShotError('El envío requiere confirmación interactiva; no se admite --yes ni stdin canalizado.')
    targets = discover()
    target = choose(targets, args.session)
    if target is None:
        print('Cancelado; sin cambios en la terminal.')
        return
    sources = args.image if args.command == 'send' else [None] * getattr(args, 'count', 1)
    if isinstance(sources, str):
        sources = [sources]  # Compatibilidad con invocaciones internas antiguas.
    if not 1 <= len(sources) <= MAX_IMAGES:
        raise ShotError('El lote requiere entre 1 y 6 capturas.')
    op = operation()
    print(f'Operación: {op.name}')
    try:
        for index, value in enumerate(sources, 1):
            source = Path(value).absolute() if value is not None else op / 'capture.png'
            if value is None:
                print(f'Captura {index}/{len(sources)}: selecciona región; Esc cancela el lote sin enviar.')
                try:
                    captured = subprocess.run(['/usr/sbin/screencapture', '-i', '-s', '-t', 'png', str(source)],
                                              capture_output=True, timeout=180)
                except subprocess.TimeoutExpired:
                    discard_images(op)
                    receipt(op, 'cancelled')
                    raise ShotError('Captura cancelada por tiempo; sin envío.') from None
                if captured.returncode or not source.exists() or source.stat().st_size == 0:
                    discard_images(op)
                    receipt(op, 'cancelled')
                    print('Captura cancelada o permiso no disponible; sin envío.')
                    return
                os.chmod(source, 0o600)
            append_image(source, op)
            if value is None:
                source.unlink()
        images = image_paths(op)
        message(images, args.text or '')  # Valida --text antes de mostrarlo en terminal.
        print(f'Destino: {target_label(target)}')
        print(f'Imágenes: {len(images)}')
        for image in images:
            print(f'  {image}')
        print(WARNING)
        if args.text is not None:
            print(f'Texto predefinido: {args.text}')
        text = input('Texto opcional (una línea; Enter envía): ')
        if not text and args.text is not None:
            text = args.text
        prompt = message(images, text)
        with target_lock(target):
            revalidate(target)
            send(target, prompt, op)
        print('SUBMITTED: iTerm2 aceptó texto y Enter. Verifica la respuesta en Claude; no se afirma éxito visual.')
    except (KeyboardInterrupt, EOFError):
        state = json.loads((op / 'receipt.json').read_text())['state']
        if state == 'preparing':
            discard_images(op)
            receipt(op, 'cancelled')
            print('Cancelado; terminal intacta.')
            return
        raise  # Si comenzó escritura, conservar el estado incierto del adaptador.
    except BaseException:
        # El adaptador marca uncertain antes de propagar cualquier error de entrega.
        state = json.loads((op / 'receipt.json').read_text())['state']
        if state == 'preparing':
            receipt(op, 'failed')
        print(f'Operación {op.name}: revisa el panel y el recibo. No reintentes a ciegas.', file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description='Claude Shot local: lectura por ruta y disponibilidad confirmada por ti.')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    sub.add_parser('desktop', help='Puente JSON para la app nativa; no usar manualmente para enviar')
    listing = sub.add_parser('sessions')
    listing.add_argument('--json', action='store_true')
    clean = sub.add_parser('cleanup')
    clean.add_argument('--older-than-hours', type=int, default=24)
    for name in ('send', 'capture'):
        action = sub.add_parser(name)
        if name == 'send':
            action.add_argument('--image', required=True, action='append', help='PNG; repetir para enviar un lote')
        else:
            action.add_argument('--count', type=int, choices=range(1, MAX_IMAGES + 1), default=1,
                                help='Cantidad de regiones a capturar antes de enviar (1–6)')
        action.add_argument('--session', help='ID explícito; omitir abre selector interactivo')
        action.add_argument('--text', help='Texto opcional de una sola línea')
    args = parser.parse_args()
    if args.command == 'desktop':
        from .desktop import main as desktop_main
        return desktop_main()
    try:
        if args.command == 'doctor':
            import importlib.metadata
            print('Claude Shot', __version__, '· Python', sys.version.split()[0])
            print('Repositorio:', ROOT)
            print('SDK iterm2:', importlib.metadata.version('iterm2'))
            print('Confirmación humana de estado: obligatoria. SSH/tmux: no soportados.')
            print('Este diagnóstico no conecta al SDK, no pide permisos ni captura.')
        elif args.command == 'sessions':
            targets = discover()
            if args.json:
                print(json.dumps([dict(asdict(t), state='unknown', transport='local') for t in targets], indent=2))
            else:
                for target in targets:
                    print(f'{target_label(target)} · estado unknown')
                if not targets:
                    print('Sin Claude local en primer plano.')
        elif args.command == 'cleanup':
            cleanup(args.older_than_hours)
        else:
            workflow(args)
    except (ShotError, OSError, ValueError, subprocess.SubprocessError) as exc:
        # No imprimir detalles de errores externos que puedan contener el mensaje.
        detail = str(exc) if isinstance(exc, ShotError) else 'Falló una operación local; revisa permisos y recibo.'
        print('Error: ' + detail, file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('Interrumpido. Si comenzó la escritura, resultado incierto: comprueba el panel antes de actuar.', file=sys.stderr)
        return 130
    except Exception:
        print('Error del SDK o del controlador. Comprueba el recibo y el panel; no reintentes automáticamente.', file=sys.stderr)
        return 1
    return 0
