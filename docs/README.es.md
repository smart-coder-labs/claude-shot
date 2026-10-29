# Claude Shot — guía de uso en español

[← README principal](../README.md)

Ejecuta todos los comandos desde la raíz del repositorio. Esta guía conserva el detalle operativo; las capturas y el resumen visual están en el README principal.

Selecciona un Claude Code abierto en iTerm2, elige un PNG o captura una región y envía una petición de lectura visual, sin portapapeles y sin iniciar otra conversación.

**Estado: `0.1.0.dev0`, app nativa y CLI locales para probar; no es el MVP local+SSH completo.** La app compila y su bundle/firma local se verificaron; su interacción gráfica todavía necesita prueba manual. La lectura por ruta y el envío con texto/Enter separados se comprobaron en el spike. El controlador usa el SDK oficial para suprimir broadcast. Tras corregir la coexistencia SDK/CLI, el usuario confirmó una entrega local real exitosa y la interpretación correcta de la imagen. El usuario también confirmó que la captura funciona. El aislamiento real con broadcast activo y otros casos de la checklist siguen pendientes. Las pruebas automatizadas simulan el SDK: no son evidencia de entrega real.

## Cambio de alcance aceptado

Los hooks no distinguieron prompt vacío, borrador y menú. El usuario aceptó sustituir P3 automático por **disponibilidad comprobada por el usuario** y autorizó el SDK dentro del repositorio. A petición suya, la confirmación se reduce a pulsar Enter en el campo de texto: no se pide escribir `ENVIAR`.

Debes comprobar que el destino está inactivo, sin permisos/menús y con el prompt vacío, y no escribir durante la operación. Si confirmas incorrectamente o el estado cambia, el envío puede mezclarse con texto, quedar en cola o accionar un diálogo. No afirmamos haber resuelto P3.

**Solo local, iTerm2, proceso `claude` en primer plano.** No SSH, tmux, reanudación ni cola propia. Hay app nativa SwiftUI y atajo global **⌘⌃7**, activado automáticamente al abrirla por petición del usuario. Texto opcional de una línea y una imagen PNG de 8 bits no entrelazada, hasta 20 MiB y 40 millones de píxeles. No es adjunto nativo: se referencia la copia privada de la imagen. El mensaje contiene la ruta entre comillas y tu texto, sin el prefijo «Analiza visualmente esta imagen local». Si no introduces texto, se añade «Describe lo que ves.». Este formato abreviado todavía requiere validación visual real; no se supone que la ruta por sí sola adjunte la imagen.

## App de macOS

Ya se construyó dentro del repositorio. Para abrirla cuando quieras probarla:

```sh
open 'build/Claude Shot.app'
```

La app queda en la **barra de menús**, sin ventana inicial ni icono en el Dock.

1. Pulsa **⌘⌃7**: abre directamente el selector nativo de región, sin pedir sesión ni confirmación. Esc durante la selección cancela sin abrir popup.
2. Al capturar aparece un **popup compacto**, sin vista previa grande: selector de Claude por título/TTY/PID y campo de texto.
3. Elige destino, escribe texto opcional y **Enter envía y oculta el popup**, sin confirmación adicional. El icono de avión hace lo mismo.
4. **Esc en el popup** descarta la imagen sin tocar Claude. El icono de la barra de menús ofrece mostrar popup, elegir PNG, ver la captura en Finder y salir. La flecha del selector actualiza sesiones.

Si ya hay una captura pendiente, el atajo muestra su popup en lugar de sobrescribirla. Durante la selección una segunda pulsación no abre la app sobre la captura. No se elige un destino remoto ni se envía al capturar. Sin Claude local se conserva la imagen y se pide abrir una sesión local.

El foco pasa al campo de texto al preparar la imagen. Después de enviar o de una entrega incierta se deshabilita el reenvío de esa misma operación. Si falla antes de intentar escribir, puedes corregir el destino/texto; nunca hay reintentos automáticos. Los controles se bloquean mientras hay una operación; salir durante un envío no está permitido por la UI. Una terminación forzada puede dejar un resultado incierto.

Atajo global **⌘⌃7 (Command + Control + 7)**: se registra automáticamente al abrir la app y **activa directamente la captura por petición del usuario**. No envía: requiere Enter/avión en el popup posterior. Puedes desactivarlo desde el menú Claude Shot hasta el próximo arranque; salir libera el atajo. No es configurable todavía ni modifica atajos del sistema. La ventana muestra si está activo o el código de error de registro. Se comprobó registro real con código 0; la pulsación física, los conflictos y reapertura tras cerrar ventana aún requieren prueba manual. El último evento propio de registro/activación/desactivación se guarda sin contenido en `.claude-shot/hotkey-status.json` (PID y código; puede quedar obsoleto tras cierre forzado).

Para reconstruir usando el Swift ya instalado (sin descargar dependencias):

```sh
./scripts/build-app
```

El producto y las cachés quedan en `build/`. Firma ad-hoc local, sin notarización ni instalación en `/Applications`. La app depende de este repositorio y su `.venv`; **no es un bundle autónomo distribuible**. Si mueves el repositorio, reconstruye. Compilado en este Mac con Swift 6.3.3, destino macOS 14+ y arquitectura del equipo; no se ha probado en otros sistemas.

Los permisos de captura/Automatización de la app pueden diferir de los de Terminal. Si macOS o iTerm2 los solicita, decide manualmente si los concedes; no se habilitan ni aceptan automáticamente. Inicialmente solo se compiló; después, con autorización del usuario para activar el atajo, se abrió y verificó su registro. No se tomaron capturas ni hicieron envíos para probar la GUI. Consulta [pruebas de escritorio](../tests/manual/desktop.md).

## Instalación en este repositorio

Ya se creó `.venv` en este Mac, con Python 3.15.0 y SDK `iterm2==2.30`. No se modificó configuración del sistema ni de Claude.

Para reproducir la instalación, **solo si autorizas descargar estas dependencias**:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

No hace falta activar el entorno ni instalar el paquete globalmente. El lanzador usa `.venv` explícitamente:

```sh
./scripts/claude-shot doctor
./scripts/claude-shot sessions
./scripts/claude-shot sessions --json
```

`sessions` cruza IDs/TTY del CLI oficial `it2` con procesos locales en primer plano. Muestra el título de la pestaña obtenido con `it2 session list --format '\(tab.title)'` (con fallback al título del panel), únicamente como etiqueta. No usa títulos para decidir dónde hay Claude ni como identidad, no lee conversaciones y no presenta el estado como `ready`. No necesita wrapper. PID y hora de arranque se revalidan para detectar cambios de proceso.

Para comprobar conexión SDK y consulta CLI simultáneas **sin enviar ni capturar**:

```sh
.venv/bin/python -B scripts/check-iterm.py
```

Esta comprobación sí conecta al SDK y puede pedir autorización. Se probó en este Mac con un Claude local coincidente; no sustituye la prueba de entrega.

La API de iTerm2 debe estar disponible. El SDK puede solicitar autorización de iTerm2/Automatización en el primer envío. Decide tú si la concedes; la herramienta no habilita la API ni cambia permisos automáticamente. No se requieren Accesibilidad ni Hammerspoon para esta CLI. No garantizamos que otros equipos tengan los permisos necesarios.

## Primera prueba: imagen sintética, sin capturar pantalla

1. Abre un Claude Code **local** en otro panel de iTerm2. Resuelve manualmente la confianza de carpeta si aparece y deja el prompt vacío.
2. Desde una terminal local, ejecuta:

```sh
./scripts/claude-shot send \
  --image 'docs/spike-evidence/p1-local-02/visual sample.png' \
  --text 'Indica las figuras y sus colores de izquierda a derecha.'
```

3. Selecciona el número de lista del destino (`1` para la primera fila), su PID o su ID de panel completo. Si número de lista y PID resultan ambiguos, usa el ID completo. Una entrada inválida vuelve a preguntar sin enviar. Verás título de pestaña, ID de panel, TTY y PID. También puedes usar `--session <ID>` obtenido con `sessions`.
4. Introduce texto opcional y **pulsa Enter para enviar**, incluso si dejas el campo vacío. Si pasaste `--text`, se muestra como texto predefinido: Enter lo usa; escribir otro texto lo sustituye. No hay otra confirmación. Enter autoriza la lectura/transmisión de la imagen a Claude. **Ctrl+C cancela antes del envío**; vacío en el selector de destino también cancela.
5. No escribas en el destino durante la operación. La herramienta inserta el texto y, tras dos segundos y otra comprobación de identidad, envía Enter; ambas llamadas usan `suppress_broadcast=True`.
6. Comprueba la respuesta en Claude. `SUBMITTED` solo significa que iTerm2 aceptó las llamadas: no confirma recepción ni interpretación. El orden esperado de esta imagen es amarillo, rojo, verde y azul.

El usuario confirmó que el controlador corregido envió correctamente el mensaje; se registró el resultado en `docs/spike-results.md`. También confirmó la interpretación visual correcta de ese intento. Sigue pendiente completar el resto de la checklist manual.

## Captura de región

Solo cuando quieras capturar y potencialmente compartir esa región:

```sh
./scripts/claude-shot capture
```

Selecciona destino: el selector nativo se abre directamente, sin otra pregunta. Arrastra la región o pulsa Esc para cancelar. El comando usa `/usr/sbin/screencapture -i -s` y no toca el portapapeles. Si macOS solicita permiso de grabación/captura, decide manualmente si lo concedes. El usuario confirmó que la captura funciona en este Mac. Denegación de permisos, Retina y múltiples monitores siguen pendientes de pruebas específicas.

Después de capturar, introduce texto opcional y pulsa Enter para enviar. Capturar **no envía** por sí solo: el envío comienza con Enter en el campo de texto. Se muestra la ruta privada para poder abrir la imagen manualmente antes de responder. Ctrl+C cancela y elimina la copia antes de que empiece la escritura.

## Fallos, archivos y limpieza

- Sin destino local, no captura ni escribe. Panel cerrado/cambiado: se rechaza; no cae al panel activo.
- Exclusión entre operaciones de esta herramienta por sesión; **no bloquea tu teclado ni otros programas**.
- Un error tras comenzar a escribir se marca `uncertain`; comprueba el panel antes de actuar. Puede quedar un borrador. Nunca se borra o restaura input automáticamente y no hay reintentos de envío.
- Imágenes y recibos se guardan en `.claude-shot/operations/<id>/`, dentro del repositorio, con directorios `0700` y archivos `0600`. No se guardan prompts ni texto de usuario en los recibos.
- La imagen se conserva porque no hay acuse fiable de consumo. Ctrl+C en el campo de texto elimina la copia antes del envío; los fallos pueden conservarla para diagnóstico.
- No hay borrado periódico. Para borrar operaciones finalizadas con más de 24 horas, cuando Claude ya no necesite sus imágenes:

```sh
./scripts/claude-shot cleanup
```

No limpies durante una operación. Un proceso terminado abruptamente puede dejar una operación intermedia que la limpieza conservadora no elimina: inspección y borrado manual, sin reintentar. No se sigue deliberadamente un enlace final de imagen, pero no se promete aislamiento frente a otro proceso malicioso del mismo usuario ni a sustitución de directorios antecesores.

Para desinstalar, termina primero cualquier operación y elimina `.venv` y, si ya no necesitas las imágenes, `.claude-shot` y `.spike-runtime`, **solo dentro de este repositorio**. Cierra también la app y elimina `build/` para retirar el bundle. El atajo solo vive mientras corre la app; no hay servicios, autoarranque ni hooks globales que retirar. No se borra el almacenamiento propio de Claude o de iTerm2.

## Pruebas

```sh
.venv/bin/python -B -m unittest discover -s tests/unit -v
git diff --check
```

Las pruebas no capturan ni conectan a sesiones reales. Cubren descubrimiento por proceso, validación PNG, controles de texto, permisos, enlaces, cancelación, bloqueo, revalidación, entrega incierta, ausencia de reintentos y supresión de broadcast solicitada al SDK.

## Documentación y spike

- [Plan y acuerdo de alcance](../IMPLEMENTATION_PLAN.md)
- [Versiones, evidencia y limitaciones](spike-results.md)
- [Seguridad](security.md)
- [Checklist manual local](../tests/manual/local.md)
- [Checklist de app nativa](../tests/manual/desktop.md)
- [Arquitectura de escritorio](desktop.md)
- [Instrumentación P3](p3-protocol.md)

Inventario original de solo lectura: `python3 scripts/spike-readonly.py`. Los scripts `spike-p1.py` son arneses experimentales, no el controlador nuevo; no usarlos sobre trabajo real sin autorización.
