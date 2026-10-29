"""API oficial de iTerm2; sin fallback al panel activo ni broadcast."""
import asyncio
from .core import ShotError, receipt, revalidate


def with_connection(callback):
    """El runner oficial cancela su dispatcher antes de cerrar el websocket.

    Capturamos fallos del callback hasta que el SDK termine su limpieza para
    evitar que su runner imprima traceback y haga sys.exit durante la entrega.
    """
    import iterm2
    results, failures = [], []

    async def wrapped(connection):
        try:
            results.append(await callback(connection))
        except BaseException as exc:
            failures.append(exc)

    iterm2.run_until_complete(wrapped, retry=False)
    if failures:
        raise failures[0]
    if not results:
        raise ShotError('El SDK terminó sin completar la operación; no se reintenta.')
    return results[0]


def send(target, text, op, delay=2.0):
    import iterm2
    attempted = False

    async def deliver(connection):
        nonlocal attempted
        app = await asyncio.wait_for(iterm2.async_get_app(connection), timeout=10)
        revalidate(target)
        session = app.get_session_by_id(target.session_id)
        if session is None:
            raise ShotError('El panel ya no existe en la API de iTerm2.')
        receipt(op, 'writing_text')
        attempted = True
        await asyncio.wait_for(session.async_send_text(text, suppress_broadcast=True), timeout=10)
        receipt(op, 'text_written')
        await asyncio.sleep(delay)
        # Solo identidad y primer plano; disponibilidad confirmada por el humano.
        revalidate(target)
        await asyncio.wait_for(app.async_refresh(), timeout=10)
        session = app.get_session_by_id(target.session_id)
        if session is None:
            raise ShotError('El panel se cerró después de insertar el texto.')
        receipt(op, 'submitting')
        await asyncio.wait_for(session.async_send_text('\r', suppress_broadcast=True), timeout=10)
        receipt(op, 'submitted')  # Acuse iTerm2, NO confirmación de Claude.

    try:
        with_connection(deliver)
    except BaseException:
        receipt(op, 'uncertain' if attempted else 'failed')
        raise
