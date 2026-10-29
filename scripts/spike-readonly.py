#!/usr/bin/env python3
"""Inventario de solo lectura. No envía texto, captura pantallas ni conecta SSH."""
import importlib.util
import json
import subprocess


def probe(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        print(f"$ {' '.join(args)}\nexit={result.returncode}")
        if args == ('it2', 'session', 'list', '--json'):
            if result.returncode == 0:
                data = json.loads(result.stdout)
                print(f"Enumeración OK; tipo={type(data).__name__}; paneles={len(data)}")
            else:
                print('Enumeración fallida; salida omitida por privacidad.')
        else:
            print(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"No disponible: {type(exc).__name__}")


if __name__ == '__main__':
    probe('sw_vers')
    probe('python3', '--version')
    probe('claude', '--version')
    probe('/usr/libexec/PlistBuddy', '-c', 'Print :CFBundleShortVersionString',
          '/Applications/iTerm.app/Contents/Info.plist')
    print('Módulo Python iterm2:', bool(importlib.util.find_spec('iterm2')))
    probe('it2', 'session', 'list', '--json')
