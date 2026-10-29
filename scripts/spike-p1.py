#!/usr/bin/env python3
"""Ensayo P1 manual autorizado. No es un adaptador de envío seguro para producción.

Exige confirmación humana de prompt vacío, Claude inactivo y broadcast apagado.
Un directorio de ensayo existente impide repetir el envío, incluso si fue incierto.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import time
import zlib


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=10).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split-submit', action='store_true',
                        help='Ensayo supervisado: texto y un retorno en llamadas separadas')
    parser.add_argument('--session', required=True)
    parser.add_argument('--tty', required=True)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--trial', required=True, help='Directorio nuevo dentro del repositorio')
    parser.add_argument('--confirmed-empty-idle-broadcast-off', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    trial = Path(args.trial).resolve()
    if not trial.is_relative_to(root) or trial == root:
        parser.error('El ensayo debe quedar dentro del repositorio')

    def validate():
        sessions = json.loads(run('it2', 'session', 'list', '--json'))
        matches = [s for s in sessions if s['id'] == args.session]
        if len(matches) != 1:
            raise RuntimeError('Panel ausente o ambiguo')
        tty = matches[0]['tty'].replace('\\/', '/').removeprefix('/dev/')
        processes = run('ps', '-axo', 'pid=,tty=,comm=')
        found = any(len(f := line.split(None, 2)) == 3 and
                    f[0] == str(args.pid) and f[1] == args.tty and
                    Path(f[2]).name == 'claude' for line in processes.splitlines())
        if tty != args.tty or not found:
            raise RuntimeError('Cambió la asociación panel/TTY/proceso')

    validate()
    os.umask(0o077)
    trial.mkdir(mode=0o700)  # Nunca reutilizar un ensayo ni reintentar un envío.
    palette = [('rojo', (230, 35, 40)), ('verde', (30, 180, 65)),
               ('azul', (30, 75, 230)), ('amarillo', (245, 205, 25))]
    secrets.SystemRandom().shuffle(palette)
    pixels = bytearray([255] * (480 * 240 * 3))
    for i, (_, color) in enumerate(palette):
        for y in range(70, 170):
            for x in range(20 + i * 120, 100 + i * 120):
                pos = (y * 480 + x) * 3
                pixels[pos:pos + 3] = bytes(color)
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    raw = b''.join(b'\x00' + pixels[y * 1440:(y + 1) * 1440] for y in range(240))
    image = trial / 'visual sample.png'
    image.write_bytes(b'\x89PNG\r\n\x1a\n' +
                     chunk(b'IHDR', struct.pack('!2I5B', 480, 240, 8, 2, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
    (trial / 'expected.json').write_text(json.dumps([name for name, _ in palette]))
    message = (f'Prueba visual autorizada: lee como imagen únicamente el archivo local '
               f'{json.dumps(str(image))}. No leas otros archivos ni ejecutes comandos. '
               'Indica cuántas figuras de color hay, su forma y sus colores de izquierda '
               'a derecha. Si no puedes ver la imagen, dilo; no deduzcas su contenido por el nombre.')
    (trial / 'message.txt').write_text(message)
    validate()
    receipt = trial / 'receipt.json'
    receipt.write_text(json.dumps({'state': 'attempting', 'session': args.session}))
    try:
        if args.split_submit:
            run('it2', 'session', 'send', message, '--session', args.session)
            receipt.write_text(json.dumps({'state': 'text_written', 'session': args.session}))
            time.sleep(2)
            validate()  # Identidad solamente; no demuestra editor vacío ni ausencia de diálogos.
            run('it2', 'session', 'send', '\r', '--session', args.session)
        else:
            run('it2', 'session', 'send', message + '\r', '--session', args.session)
    except Exception:
        receipt.write_text(json.dumps({'state': 'uncertain', 'session': args.session}))
        raise  # No reintentar.
    receipt.write_text(json.dumps({'state': 'submitted', 'session': args.session}))
    print('submitted: escritura aceptada por iTerm2; interpretación visual pendiente.')


if __name__ == '__main__':
    main()
