#!/usr/bin/env python3
"""Sign with an explicitly configured local identity, otherwise ad-hoc.

Does not create certificates, access private-key contents, change trust or reset TCC.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / '.local-signing' / 'identity.json'


def validate(config):
    if not isinstance(config, dict):
        raise ValueError('Configuración de firma inválida.')
    identity, keychain = config.get('identity'), config.get('keychain')
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-fA-F]{40}', identity):
        raise ValueError('Se requiere la huella SHA-1 completa del certificado (40 hex).')
    if not isinstance(keychain, str) or not Path(keychain).is_absolute() or not Path(keychain).is_file():
        raise ValueError('El llavero debe ser un archivo existente con ruta absoluta.')
    result = subprocess.run(['/usr/bin/security', 'find-identity', '-v', '-p', 'codesigning', keychain],
                            check=True, capture_output=True, text=True, timeout=30)
    identities = re.findall(r'^\s*\d+\) ([0-9A-Fa-f]{40}) ', result.stdout, re.MULTILINE)
    if identity.upper() not in [value.upper() for value in identities]:
        raise ValueError('El certificado configurado no es una identidad de firma válida en ese llavero. '
                         'No se sustituirá por firma ad-hoc.')
    return {'identity': identity.upper(), 'keychain': keychain}


def configure(identity, keychain):
    config = validate({'identity': identity, 'keychain': keychain})
    if CONFIG.parent.is_symlink() or CONFIG.is_symlink():
        raise ValueError('La configuración local no admite enlaces simbólicos.')
    CONFIG.parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(CONFIG.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix='.identity-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(config, stream)
            stream.write('\n')
        os.replace(name, CONFIG)
    finally:
        Path(name).unlink(missing_ok=True)
    print('Firma estable configurada solo para este checkout; no se ha modificado el llavero.')


def settings():
    if CONFIG.is_symlink() or CONFIG.parent.is_symlink():
        raise ValueError('La configuración local no admite enlaces simbólicos.')
    return validate(json.loads(CONFIG.read_text())) if CONFIG.exists() else None


def sign(app):
    command = ['/usr/bin/codesign', '--force', '--timestamp=none']
    config = settings()
    if config is not None:
        command += ['--sign', config['identity'], '--keychain', config['keychain']]
        print('Firma: certificado local estable (sin notarización).', flush=True)
    else:
        command += ['--sign', '-']
        print('Firma: ad-hoc; los permisos de macOS pueden cambiar tras recompilar.', flush=True)
    subprocess.run(command + [str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', nargs='?', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--configure', metavar='CERT_SHA1')
    mode.add_argument('--check', action='store_true', help='Validar configuración sin firmar ni cambiar llavero')
    parser.add_argument('--keychain', type=lambda value: str(Path(value).expanduser().absolute()))
    args = parser.parse_args(argv)
    if args.check:
        if args.app or args.keychain:
            parser.error('--check no admite app ni --keychain')
    elif args.configure:
        if args.app or not args.keychain:
            parser.error('--configure requiere --keychain y no admite app')
    elif not args.app or args.keychain:
        parser.error('indica la app o usa --configure CERT_SHA1 --keychain RUTA')
    try:
        if args.check:
            configured = settings()
            print('Configuración de firma local válida.' if configured else 'Sin configuración local; se usará firma ad-hoc.')
        elif args.configure:
            configure(args.configure, args.keychain)
        else:
            sign(args.app)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Firma fallida: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
