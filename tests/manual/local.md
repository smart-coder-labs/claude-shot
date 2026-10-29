# Aceptación manual local — pendiente

Solo realizar con consentimiento del usuario y paneles desechables. No activar broadcast sobre sesiones de trabajo para probar aislamiento.

- [ ] Dos paneles locales Claude: `sessions --json` encuentra ambos por proceso y TTY, independientemente de títulos.
- [ ] Un panel SSH con título Claude no aparece como destino local.
- [ ] Un Claude suspendido o en segundo plano no aparece como destino.
- [ ] Vacío en selector o Ctrl+C en campo de texto no cambia el terminal ni conecta al SDK.
- [ ] La lista muestra el título de pestaña solo como etiqueta; renombrarla no invalida identidad.
- [ ] Enter en el campo de texto envía sin confirmación extra, incluso vacío; con --text usa el texto predefinido.
- [x] El usuario confirmó envío de imagen sintética e interpretación correcta con el controlador SDK (UX anterior ENVIAR).
- [ ] Revalidar esa entrega con la nueva UX de Enter en el campo de texto.
- [ ] Verificar que el panel no enfocado recibe, sin modificar otros paneles.
- [ ] En paneles de prueba inocuos, comprobar aislamiento con broadcast habilitado: el SDK debe suprimirlo. Requiere autorización adicional; no ejecutar sobre trabajo real.
- [ ] Cerrar panel seleccionado antes de confirmar: rechazo sin fallback al activo.
- [ ] SDK sin autorización/API apagada: error claro, sin habilitar servicios automáticamente.
- [ ] Captura nativa cancelada: no envío ni artefactos de imagen restantes.
- [x] El usuario confirmó que la captura funciona (UX anterior con confirmaciones adicionales).
- [ ] Captura sin pregunta previa, permisos denegados, Retina y múltiples monitores: comprobar imagen localmente antes de Enter en el campo de texto.
- [ ] Imagen con espacios y Unicode en la ruta de origen se copia y lee.
- [ ] Texto Unicode de una línea funciona; multilínea y controles se rechazan antes de escribir.
- [ ] Interrupción tras primera escritura: resultado incierto, sin reintentos ni borrado del borrador.
- [ ] Dos invocaciones simultáneas para el mismo panel: exclusión entre operaciones.
- [ ] Artefactos privados, recibos sin prompts, limpieza explícita después de retención y consumo.

**No probar borradores, permisos o menús mediante envío destructivo.** No hay protección automática de esos estados. El requisito actual es confirmación humana y riesgo explícitamente aceptado; no marcarlo como P3 resuelto.

Resultados de esta checklist se registran en `docs/spike-results.md`, diferenciando controlador nuevo y arneses antiguos.
