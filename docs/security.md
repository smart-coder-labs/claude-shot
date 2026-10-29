# Seguridad del prototipo local

## Modelo acordado

P3 automático no está resuelto. La disponibilidad comprobada por el usuario es un cambio de alcance aceptado, no una detección técnica. A petición del usuario, pulsar Enter en el campo de texto autoriza el envío (también con texto vacío); no se solicita `ENVIAR` ni confirmación previa de captura. Ctrl+C antes de la escritura cancela y elimina la copia. No enviar a una sesión de trabajo importante sin entender que un borrador, diálogo o carrera puede alterar el resultado.

## Protecciones implementadas

- Descubrimiento por ID iTerm2/TTY y proceso local `claude` en grupo de primer plano. No por títulos, OCR, foco o coordenadas.
- Revalidación de ID, TTY, PID y hora de arranque antes de escribir y antes de Enter. No es una comprobación atómica: subsiste una carrera entre consulta y escritura.
- SDK oficial, `suppress_broadcast=True` en texto y Enter, sin fallback al panel activo ni reintentos.
- Exclusión por panel entre instancias de esta herramienta mediante `flock`. No excluye teclado, otras apps ni otros emisores.
- Texto de una línea sin controles C0/C1, DEL o separadores de línea Unicode. No interpolación del texto en shell; argumentos de procesos mediante listas. Imagen referenciada mediante ruta JSON entre comillas.
- Copia de PNG limitada en tamaño/dimensiones, firma/chunks/CRC y datos descomprimidos comprobados; no se acepta enlace simbólico final o archivo no regular.
- Artefactos privados dentro del repositorio, sin contenido de prompts en recibos. Git ignora `.claude-shot`, `.venv` y `.spike-runtime`.

## Limitaciones

No hay acuse de consumo de imagen, recepción o respuesta del modelo. Un acuse iTerm2 es `submitted`, no `confirmed`. Cualquier excepción después de intentar la primera escritura marca `uncertain`, incluso si pudiera no haberse entregado nada. No reintentar sin inspección humana.

La autorización del SDK puede requerir interacción con iTerm2/macOS; nunca se aceptan permisos automáticamente. No se ejecuta `defaults write` ni se cambia configuración de Claude. Invocar `capture` y seleccionar destino abre directamente la captura; Enter en el campo de texto autoriza su transmisión. Puede incluir secretos que el usuario debe revisar antes de ese Enter.

No se garantiza seguridad frente a un proceso malicioso del mismo usuario que altere directorios antecesores, archivos o el proceso destino. PID+hora de arranque reducen reutilización accidental, no constituyen identidad criptográfica del ejecutable. No se inspeccionan los argumentos sensibles del proceso.

La sesión Claude puede leer otras cosas, pedir permisos o ejecutar herramientas según su propia política. El mensaje de lectura visual no es sandbox ni limita sus herramientas. El controlador no responde a esas solicitudes.

Limpieza explícita y conservadora a partir de 24 h. No hay borrado garantizado de capturas en plazo ni eliminación del almacenamiento interno o remoto de Claude. No usar `cleanup` mientras haya operaciones activas ni antes de que el consumidor termine.

## App nativa

La app invoca un puente JSON local por stdin/stdout, sin shell libre, red ni servicio persistente. Captura y envío siguen requiriendo acción del usuario (⌘⌃7 o Capturar en menú y luego Enter/avión en popup), sin pregunta adicional. Descartar solo puede eliminar imágenes no intentadas y comparte bloqueo con enviar. Marcador exclusivo por operación para impedir repetir una tentativa. El puente no exige TTY porque la interacción se hace en la GUI; no es una frontera de seguridad frente a otro proceso del mismo usuario.

Por petición posterior del usuario, el atajo global ⌘⌃7 se registra automáticamente al abrir la app y ahora inicia selección de región directamente por esa pulsación; no envía, no crea preferencias del sistema y puede desactivarse desde el menú. Capturar no exige todavía elegir sesión; Enter/avión en el popup posterior sí exige un destino local válido. El agente abrió la app para verificar el registro autorizado: código 0, sin capturas ni envíos. El diagnóstico del último evento propio del atajo guarda solo enum, PID y código en un archivo privado del repositorio; no registra otras teclas ni contenido. La app puede pedir permisos distintos de la CLI, sujetos a prueba manual y decisión del usuario. Compilación/firma local no demuestra comportamiento real de la UI. Ver `docs/desktop.md`.

## Fuera de alcance actual

SSH y auxiliar remoto, distribución autónoma/notarizada, atajo configurable/persistente, registro por wrapper, texto multilínea, múltiples imágenes, reanudación e historial. No se finge soporte de estos casos.
