# Aceptación de app mínima — pendiente

Compilación/firma y tests del controlador comprobados. El registro real de ⌘⌃7 devolvió código 0 en la versión anterior; no demuestra el nuevo flujo de captura directa. No se automatizan capturas ni envíos para comprobar esta checklist.

## Arranque y atajo

- [ ] App aparece solo en barra de menús, sin ventana inicial ni Dock; no captura al arrancar.
- [ ] Menú muestra registro ⌘⌃7 activo o código de error, sin que las consultas de sesiones lo oculten.
- [ ] ⌘⌃7 abre directamente selección de región desde otra aplicación, sin elegir sesión primero.
- [ ] Esc durante selección cancela sin popup ni imagen enviada.
- [ ] Una segunda pulsación durante selección no muestra la app sobre la captura.
- [ ] Captura pendiente: repetir atajo o + añade al lote en orden, sin sobrescribir ni perder texto (máximo 6).
- [ ] Esc al añadir captura conserva las previas y vuelve al popup; números × eliminan la imagen correcta.
- [ ] Quitar la última imagen cancela el lote y deshabilita envío; Esc en popup elimina todas.
- [ ] Límite de 6 imágenes/60 MiB se informa sin perder las anteriores.
- [ ] Menú permite mostrar popup, elegir PNG, ver archivo en Finder, desactivar atajo y salir.
- [ ] Desactivar libera atajo; reiniciar lo registra otra vez. Conflictos se informan sin cambiar otros atajos.

## Popup posterior

- [ ] Después de capturar aparece popup flotante pequeño con selector de sesión y texto enfocado, sin vista previa grande.
- [ ] Sesiones se actualizan después de capturar; títulos iguales se distinguen por TTY/PID. SSH no aparece.
- [ ] Sin Claude local se conserva imagen y permite actualizar tras abrir uno; Enter no envía sin destino.
- [ ] Renombrar pestaña solo cambia etiqueta. Panel/proceso cerrado no se sustituye automáticamente por otro destino.
- [ ] Esc descarta imagen y oculta popup sin modificar terminal.
- [ ] Permisos denegados o error de captura se informan sin envío; decidir permisos manualmente.
- [ ] Retina y varios monitores producen la región correcta sin incluir el popup.

## Envío autorizado por Enter/avión

- [ ] Claude local inactivo, sin menús y prompt vacío: Enter envía una sola vez a la conversación elegida y oculta popup.
- [ ] Botón avión equivalente, sin duplicar por doble clic/Enter.
- [ ] Comprobar interpretación real, no solo recibo `submitted`.
- [ ] Dos capturas con contenido visual distinto: Enter genera un único mensaje y Claude interpreta ambas en ese mismo turno, manteniendo conversación.
- [ ] Quitar una imagen del medio respeta orden y no envía el archivo eliminado.
- [ ] Texto vacío usa descripción por defecto; multilínea/controles se rechazan con error visible.
- [ ] Error previo a escritura conserva captura para corregir selección/texto; sin reintento automático.
- [ ] Entrega incierta conserva archivos y no ofrece reenviar esa operación. Comprobar Claude antes de nueva captura.
- [ ] Durante envío no se sale normalmente ni inicia otra captura. Cierre forzado se trata como incierto.

No probar borradores o diálogos mediante envío accidental: el estado de Claude sigue siendo responsabilidad del usuario, no P3 automático.
