# P3 — Observación de estado sin envío automático

## Estado y límites

Este arnés **no resuelve P3**. Permite comprobar qué eventos llegan realmente en la versión instalada y comparar esos eventos con estados que observa el usuario. Ningún evento ni etiqueta humana convierte la sesión en `ready`: el diagnóstico siempre devuelve `state: unknown` y `safe_to_submit: false`.

No envía pulsaciones, no lee pantalla ni escucha teclas, no captura imágenes y no registra prompts, respuestas, nombres/argumentos/resultados de herramientas, rutas del proyecto o transcripciones. El JSON original solo se procesa en memoria; se conserva una lista permitida de eventos, tipo de notificación conocido, huella del ID de sesión y tiempos. El `session_id` completo no se escribe. Las etiquetas humanas proceden de una lista fija, sin texto libre.

Los hooks son observacionales: no devuelven decisiones, contexto ni permisos. Son síncronos, con timeout de 5 segundos; pueden añadir latencia. Fallos de hooks pueden producir avisos en Claude. El arnés no intenta ocultar esos fallos ni garantizar que todos los eventos lleguen.

## Preparación

Desde la raíz del repositorio:

```sh
python3 -B scripts/spike-p3.py prepare
```

Crea `.spike-runtime/p3-<id>/` con modo `0700`, configuración y log `0600`, excluidos de git. Imprime el comando de lanzamiento. No arranca Claude ni transmite mensajes. Los tests usan eventos sintéticos en directorios temporales y no sustituyen la validación real.

El primer ensayo `p3-1b5e31224680` ya arrancó y terminó; no puede reutilizarse. Se preparó el nuevo `p3-5eabd637d437`. En los comandos de ejemplo siguientes, sustituir el ID antiguo por este nuevo ID (o el que imprima `prepare`). No borrar `launched` para forzar reutilización.

## Arranque interactivo por el usuario

En un **panel local nuevo**:

```sh
cd /path/to/claude-shot
python3 -B scripts/spike-p3.py launch --run p3-1b5e31224680
```

El lanzador exige TTY y ejecuta Claude sin prompt inicial, sin `-p` y sin reanudar conversaciones. Este ensayo sí crea una sesión de prueba nueva; no es un mecanismo para adjuntar a la conversación anterior. Conserva el terminal mediante `exec`, sin proxy PTY. Solo permite un arranque por ensayo.

Opciones usadas:

- `--setting-sources ''`: desactiva fuentes user/project/local para esta invocación.
- `--settings <ruta del ensayo>`: carga únicamente nuestra configuración explícita además de lo que imponga la política administrada.
- `--permission-mode manual`: modo con permisos manuales, sin bypass.
- `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`: no carga los MCP personales.

No escribe configuración global. Esto **no es un sandbox** ni bloquea todos los efectos nativos de Claude: autenticación, políticas administradas, memoria/descubrimiento de instrucciones y almacenamiento normal de Claude pueden seguir interviniendo. No se modifican esos mecanismos; si necesitas aislamiento completo, detén el ensayo y acordamos un entorno distinto. No usar `--safe-mode` ni `--bare`: pueden desactivar los hooks que queremos observar.

Si aparece confianza de workspace, autenticación o error de política, detenerse y comunicarlo; no aceptar automáticamente. No introducir mensajes todavía. Esperar a que el prompt esté visible e indicar al asistente que la sesión instrumentada está abierta.

## Lectura y marcas

Desde otra terminal (o mediante el asistente):

```sh
python3 -B scripts/spike-p3.py status --run p3-1b5e31224680
python3 -B scripts/spike-p3.py mark --run p3-1b5e31224680 idle-empty
```

`mark` solo registra una etiqueta humana y tiempo; no interactúa con Claude. No significa disponibilidad demostrada. Ordenar por `monotonic_ns` ayuda a comparar observaciones, pero no garantiza orden causal de hooks concurrentes ni del motor de Claude.

## Secuencia manual, sin enviar mensajes aún

1. **Arranque:** comprobar `SessionStart`. Si no llega, diagnosticar configuración/política antes de interpretar ausencia de eventos.
2. **Prompt vacío:** marcar `idle-empty`.
3. **Borrador:** marcar `draft` y escribir manualmente `BORRADOR P3 — NO ENVIAR`, sin Enter. Observar si existe algún evento que revele ese cambio. No se registra el contenido.
4. **Multilínea:** tras limpiar manualmente el borrador, marcar `draft-multiline` e introducir varias líneas sin enviar, usando el mecanismo de tu terminal. No introducir secretos.
5. **Menú:** tras limpiar manualmente, marcar `menu` y abrir un selector de Claude. El asistente no introduce comandos, Esc ni Enter. Cerrar manualmente después.

Estas manipulaciones son acciones del usuario sobre una sesión desechable. No automatizamos borrado/restauración de borradores. La ausencia de eventos es una observación limitada: no prueba inexistencia universal de otra interfaz.

## Estados que requieren otra autorización

Antes de probarlos, acordar los mensajes exactos y autorizar su envío:

- **busy / Stop / idle_prompt:** un turno inocuo; observar inicio, fin y espera de aproximadamente 60 segundos sin teclear. No prometer latencia exacta de notificaciones.
- **permission:** un turno que solicite una operación local inocua dentro del directorio de ensayo; comprobar si realmente aparece permiso y correlacionar con `PermissionRequest` / `Notification`. No aprobar la operación automáticamente. Un modo manual no garantiza que toda herramienta pida permiso.
- **typing-race:** ensayo adversarial de cambios de borrador entre comprobación y envío. No automatizar Enter ni bloqueo de teclas hasta tener un candidato de mecanismo seguro y autorización específica.

## Investigación de interfaces

Fuentes oficiales actuales guardadas en `docs/spike-evidence/`:

- `hooks-p3.md`: eventos y payloads; no se encontró evento documentado de cambio de borrador o consulta de buffer en las secciones revisadas.
- `interactive-mode-p3.md`: editor externo, stash/restore, historial, menús y cola. Son acciones de UI, no APIs de consulta sin efectos. No se usarán para extraer/borrar texto pendiente.
- `cli-reference-p3.md`, `settings-p3.md`: flags y precedencia; configuración explícita no equivale a aislamiento completo.
- `iterm-keyboard-p3.html`: `KeystrokeFilter` desactiva el tratamiento habitual de teclas coincidentes durante su contexto. No documenta un bloqueo integral de pegado, entrada por API, diálogos internos o borradores ya existentes. No se instaló SDK ni activó filtro alguno.

Consultar borrador y luego enviar tampoco elimina una carrera. Para superar P3 necesitamos una operación oficial condicional o un mecanismo de exclusión con cobertura demostrada sobre los cambios relevantes, además de estado del editor y modos internos. Sin esa capacidad no se implementará `ready` ni envío desatendido.

## Limpieza

Salir manualmente de la sesión y después borrar únicamente su directorio `.spike-runtime/p3-<id>/` si ya no se necesita la evidencia. No borrar mientras los hooks puedan ejecutarse. No hay retención automática en este arnés ni promesa de borrar los archivos que Claude gestione fuera del repositorio.
