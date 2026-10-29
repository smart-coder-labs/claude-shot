#!/usr/bin/env python3
"""Prueba real de solo lectura: SDK + CLI coexistentes. No enviar ni capturar."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from claude_shot.core import discover
from claude_shot.iterm_adapter import with_connection


async def check(connection):
    import iterm2
    app = await iterm2.async_get_app(connection)
    targets = discover()  # Consulta CLI con credenciales independientes.
    for target in targets:
        if app.get_session_by_id(target.session_id) is None:
            raise RuntimeError('Inventario cambiado durante la consulta')
    print(f'SDK + CLI: OK. Claude locales coincidentes: {len(targets)}. Sin envío ni captura.')


if __name__ == '__main__':
    try:
        with_connection(check)
    except Exception:
        print('Comprobación de solo lectura fallida. Revisa autorización/API de iTerm2.', file=sys.stderr)
        raise SystemExit(1)
