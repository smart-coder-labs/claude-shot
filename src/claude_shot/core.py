import binascii
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import struct
import subprocess
import zlib
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / '.claude-shot'
MAX_IMAGE = 20 * 1024 * 1024


class ShotError(Exception):
    pass


@dataclass(frozen=True)
class Target:
    session_id: str
    tty: str
    pid: int
    started: str
    # Etiquetas cambiantes, nunca identidad ni condición de revalidación.
    tab_title: str = field(default='', compare=False)
    tab_id: str = field(default='', compare=False)


def display_title(value):
    if not isinstance(value, str):
        return ''
    return ' '.join(''.join(c for c in value if not unicodedata.category(c).startswith('C')).split())[:120]


def command(*args):
    try:
        # El SDK consume una cookie de un solo uso y la deja en os.environ.
        # No prestarla al CLI it2: debe autenticar su conexión independiente.
        env = os.environ.copy()
        if args and args[0] == 'it2':
            env.pop('ITERM2_COOKIE', None)
            env.pop('ITERM2_KEY', None)
        return subprocess.run(args, capture_output=True, text=True, check=True, timeout=10, env=env).stdout
    except (OSError, subprocess.SubprocessError):
        raise ShotError('No se pudo consultar iTerm2 o los procesos locales.') from None


def discover():
    panels = json.loads(command('it2', 'session', 'list', '--json', '--format', r'\(tab.title)'))
    processes = []
    for line in command('ps', '-axo', 'pid=,pgid=,tpgid=,tty=,lstart=,comm=').splitlines():
        fields = line.split(None, 9)
        if len(fields) == 10:
            pid, pgid, tpgid, tty, *rest = fields
            started = ' '.join(rest[:5])
            executable = rest[5]
            if Path(executable).name == 'claude' and pgid == tpgid:
                processes.append((tty, int(pid), started))
    targets = []
    for panel in panels:
        if panel.get('is_tmux'):
            continue
        tty = panel.get('tty', '').replace('\\/', '/').removeprefix('/dev/')
        candidates = [p for p in processes if p[0] == tty]
        if len(candidates) == 1:
            _, pid, started = candidates[0]
            title = display_title(panel.get('formatted')) or display_title(panel.get('title')) or display_title(panel.get('name'))
            targets.append(Target(panel['id'], tty, pid, started, title, str(panel.get('tab_id', ''))))
    return targets


def revalidate(target):
    if target not in discover():
        raise ShotError('El destino cambió, se cerró o Claude dejó de estar en primer plano. No se enviará Enter.')


def ensure_private(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ShotError('Directorio de trabajo inseguro; no se cambian sus permisos automáticamente.')


def runtime():
    ensure_private(RUNTIME)
    for name in ('operations', 'locks'):
        ensure_private(RUNTIME / name)
    return RUNTIME


def atomic_json(path, data):
    temp = path.with_name('.' + path.name + '-' + secrets.token_hex(8))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def operation():
    path = runtime() / 'operations' / secrets.token_hex(16)
    path.mkdir(mode=0o700)
    receipt(path, 'preparing')
    return path


def receipt(path, state):
    # Sin prompt, ruta de origen, ID de conversación ni contenido de imagen.
    atomic_json(path / 'receipt.json', {'state': state, 'updated_at': datetime.now(timezone.utc).isoformat()})


def read_image(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_IMAGE:
            raise ShotError('Se requiere un PNG regular de hasta 20 MiB, sin enlace final.')
        data = stream.read(MAX_IMAGE + 1)
    validate_png(data)
    return data


def validate_png(data):
    if len(data) > MAX_IMAGE or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ShotError('Imagen no PNG o demasiado grande.')
    pos, width, height, rowbytes = 8, 0, 0, 0
    packed = bytearray()
    ended = False
    while pos + 12 <= len(data):
        length = struct.unpack('!I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(data):
            raise ShotError('PNG truncado.')
        payload = data[pos + 8:pos + 8 + length]
        checksum = struct.unpack('!I', data[end - 4:end])[0]
        if binascii.crc32(kind + payload) != checksum:
            raise ShotError('CRC de PNG inválido.')
        if pos == 8 and kind != b'IHDR':
            raise ShotError('PNG sin cabecera inicial.')
        if kind == b'IHDR':
            if width or length != 13:
                raise ShotError('Cabecera PNG inválida.')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('!2I5B', payload)
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            if not channels or depth != 8 or compression or filtering or interlace:
                raise ShotError('Por ahora se requiere PNG de 8 bits, no entrelazado.')
            if not width or not height or width * height > 40_000_000:
                raise ShotError('Dimensiones PNG no permitidas.')
            rowbytes = width * channels
        elif kind == b'IDAT':
            packed.extend(payload)
        elif kind == b'IEND':
            if length or end != len(data):
                raise ShotError('Final PNG inválido.')
            ended = True
            break
        pos = end
    if not ended or not packed or not width:
        raise ShotError('PNG incompleto.')
    expected = height * (rowbytes + 1)
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, expected + 1)
    except zlib.error:
        raise ShotError('Datos PNG inválidos.') from None
    if len(raw) != expected or not decoder.eof or decoder.unused_data:
        raise ShotError('Datos de píxeles PNG incompletos o excesivos.')
    if any(raw[y * (rowbytes + 1)] > 4 for y in range(height)):
        raise ShotError('Filtros PNG inválidos.')


def stage_image(source, op):
    data = read_image(source)
    path = op / 'image.png'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    return path


def message(image, text):
    if len(text) > 8000:
        raise ShotError('Texto demasiado largo (máximo 8000 caracteres).')
    # No enviar saltos ni secuencias de control al terminal; multilínea pendiente.
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 or c in '\u2028\u2029' for c in str(image) + text):
        raise ShotError('Este prototipo solo admite texto de una línea, sin caracteres de control.')
    reference = json.dumps(str(image), ensure_ascii=True)
    return reference + ' ' + (text if text else 'Describe lo que ves.')


@contextmanager
def target_lock(target):
    import hashlib
    key = hashlib.sha256(target.session_id.encode()).hexdigest()
    path = runtime() / 'locks' / key
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ShotError('Archivo de bloqueo inseguro.')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ShotError('Otra operación usa este panel.') from None
        yield
    finally:
        os.close(fd)
