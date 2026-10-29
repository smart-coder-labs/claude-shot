#!/usr/bin/env python3
"""Comprueba enlaces/activos locales de documentación sin acceder a la red."""
from pathlib import Path
import re
import struct
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / 'README.md', ROOT / 'CONTRIBUTING.md', ROOT / 'IMPLEMENTATION_PLAN.md']
FILES += list((ROOT / 'docs').glob('*.md'))
FILES += list((ROOT / 'tests/manual').glob('*.md'))
FILES += list((ROOT / '.github/assets').glob('*.md'))
errors = []
for path in FILES:
    text = path.read_text()
    refs = re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', text)
    refs += re.findall(r'(?:src|href)="([^"]+)"', text)
    for ref in refs:
        parsed = urlsplit(ref)
        if parsed.scheme or ref.startswith('#') or not parsed.path:
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(ROOT) or not target.exists():
            errors.append(f'{path.relative_to(ROOT)}: enlace local ausente: {ref}')
for image in (ROOT / '.github/assets').glob('*.svg'):
    try:
        ET.parse(image)
    except ET.ParseError:
        errors.append('SVG inválido: ' + image.name)
for image in (ROOT / '.github/assets').glob('*.png'):
    data = image.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) < 24:
        errors.append('PNG inválido: ' + image.name)
    else:
        width, height = struct.unpack('!II', data[16:24])
        if not width or not height:
            errors.append('PNG vacío: ' + image.name)
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print(f'Documentación: {len(FILES)} archivos, enlaces y activos locales OK.')
