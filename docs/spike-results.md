# Spike de viabilidad — Fase 0 / Fase 1 parcial

Fecha de observación UTC: 2026-10-27. **Gate: NO-GO provisional para envío automático.** No implica imposibilidad definitiva: faltan pruebas autorizadas y una solución para P3. No se implementan las fases 2–5.

## Límites respetados

No se enviaron mensajes ni pulsaciones a terminales, no se tomaron ni transmitieron capturas, no se usó el portapapeles, no se instalaron dependencias ni se modificó configuración. No se iniciaron sesiones Claude ni conexiones SSH. Se descargó documentación pública oficial mediante HTTPS (sin imágenes ni datos de sesiones). La enumeración de paneles se procesó localmente sin guardar títulos, rutas ni identificadores.

## Inventario reproducible

Ejecutar desde la raíz: `python3 scripts/spike-readonly.py`. Solo usa biblioteca estándar; timeout de 10 s por comando. No autentica ni habilita APIs por su cuenta.

| Componente | Comando / observación | Resultado |
|---|---|---|
| macOS | `sw_vers` | 26.2, build 25C56 |
| iTerm2 | `/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /Applications/iTerm.app/Contents/Info.plist` | 3.7.6 |
| Claude Code | `claude --version` | 2.1.304; ejecutable en `~/.local/bin/claude` |
| Python | `python3 --version` | 3.15.0 |
| SDK Python iTerm2 | `importlib.util.find_spec('iterm2')` | No instalado en este Python; no se instaló |
| CLI oficial iTerm2 | `command -v it2` | `/Applications/iTerm.app/Contents/Resources/utilities/it2` |
| API iTerm2 | preferencia existente `EnableAPIServer` | 1; no modificada |
| Enumeración real | `it2 session list --json` | exit 0, JSON lista; sin guardar datos de paneles |
| Remotos / Hammerspoon | No inspeccionados | Pendientes de selección y consentimiento |

Se consultó inicialmente `defaults read com.googlecode.iterm2`; reveló preferencias innecesarias para el inventario. No se guardan aquí y el script reproducible no vuelca preferencias completas.

## Evidencia y fuentes

Copias de las respuestas oficiales consultadas en `docs/spike-evidence/` (documentación web actual, **no fijada** a Claude 2.1.304):

- https://code.claude.com/docs/en/common-workflows.md — sección “Work with images”.
- https://code.claude.com/docs/en/hooks.md — eventos y sección Notification.
- https://iterm2.com/python-api/session.html — identificación y envío de sesiones.

Reproducir descarga: `curl -fLsS --max-time 25 URL -o ARCHIVO` con las URLs anteriores. La ayuda local se obtuvo con `claude --help`, `it2 --help`, `it2 session list --help`, `it2 session send --help`, `it2 session get-status --help` e `it2 monitor prompt --help`.

## P1 — Imagen en conversación interactiva existente

**Resultado: lectura visual por ruta confirmada por el usuario en la conversación elegida; envío automático NO validado.**

### Ensayo local 01

El usuario autorizó el único mensaje, confirmó el estado del prompt y que `Send Input to Current Session Only` ya estaba marcado. Se revalidó el panel `C850EB4F-5405-4155-B468-2E501A90AEF0`, TTY `ttys001`, proceso `claude` PID 11362. Se generó un PNG sintético de 480×240 con cuatro figuras y orden de colores aleatorio, usando solo biblioteca estándar. No es una captura. Ruta con espacios: `docs/spike-evidence/p1-local-01/visual sample.png`. El texto no revela la respuesta esperada, guardada en `expected.json` y no leída por el evaluador durante el intento.

Comando ejecutado **una sola vez** (no repetir sobre este directorio):

```sh
python3 scripts/spike-p1.py \
  --session C850EB4F-5405-4155-B468-2E501A90AEF0 \
  --tty ttys001 --pid 11362 \
  --trial docs/spike-evidence/p1-local-01 \
  --confirmed-empty-idle-broadcast-off
```

El script pasó el mensaje completo más `\\r` en una sola llamada `it2 session send ... --session ID`. iTerm2 respondió exit 0. El recibo `submitted` significa únicamente escritura aceptada por iTerm2, **no envío confirmado a Claude**. Dos lecturas mediante `it2 session read --session ID --lines 28` y luego `--lines 35`, aproximadamente 5 y 13 segundos después, mostraron el mensaje aún en el editor `❯`, sin respuesta. La salida de lectura contiene caracteres NUL entre algunas palabras, por lo que no se considera una fuente perfecta del buffer.

Observación: la combinación texto + retorno en esta vía **no demostró envío automático**. Podría intervenir el tratamiento de pegado o entrada de Claude; causa no verificada. No se mandó un segundo Enter, no se borró el borrador ni se reintentó. Tampoco se confirma transmisión de la imagen al proveedor. Se pide al usuario observar el panel y, si el mensaje está efectivamente pendiente, decidir si enviarlo manualmente para aislar la prueba de lectura visual. Esto cambia solo el ensayo; no valida el requisito de envío automático del MVP.

El usuario confirmó que el mensaje estaba pendiente en el prompt y comunicó la respuesta posterior de Claude: cuatro rectángulos verticales iguales sobre fondo blanco, en orden verde, rojo, azul y amarillo; también indicó que Claude declaró haber leído únicamente ese archivo, sin ejecutar comandos. Tras recibir esa respuesta se leyó `expected.json`: `["verde", "rojo", "azul", "amarillo"]`, coincidencia exacta. La geometría también coincide con los rectángulos generados (80×100 píxeles). Evidencia de respuesta aportada por el usuario, no inspección de los bloques internos enviados al modelo. Se conserva la conversación elegida y no se inició otro proceso Claude. La lectura ocurrió después de la intervención manual; no se atribuye al retorno incluido en la llamada inicial.

**Conclusión P1:** funciona la alternativa de lectura visual explícita por ruta local, incluida una ruta con espacios. No se demuestra adjunto nativo ni consumo automático de una ruta aislada. El usuario autorizó este ensayo, pero la adopción de esa semántica como UX definitiva del MVP sigue requiriendo acuerdo. El envío automático requiere otro ensayo acotado; no se ejecutará un Enter adicional sobre esta operación ya respondida.

El script exige autorización manual, verifica ID/TTY/proceso y se niega a reutilizar un directorio de ensayo. No resuelve P3, broadcast se basa en confirmación humana y no debe usarse como adaptador de producción.

La documentación oficial ofrece tres vías: arrastrar imagen, pegar imagen y pedir explícitamente analizar una ruta (`Analyze this image: /path/to/your/image.png`). La tercera es candidata sin portapapeles, pero no demuestra adjunto materializado: puede implicar lectura mediante herramienta y permisos. No se ha escrito ninguna ruta en una sesión y no se afirma que funcione en la versión instalada.

La ayuda de 2.1.304 limita `--input-format stream-json` a `--print`; no es una interfaz demostrada para inyectar imágenes al proceso interactivo activo. `--file` descarga recursos al inicio, no adjunta a un proceso existente. `--resume`, `--continue`, `attach` y Remote Control no se han validado como API de adjuntos; no se utilizaron como sustitutos de la sesión elegida. No se identificó en las interfaces revisadas un endpoint oficial de adjunto al proceso activo. Esto no es prueba de inexistencia.

### Prueba autorizada propuesta (NO ejecutada)

1. Elegir una conversación interactiva de prueba ya abierta, sin información sensible. Registrar su identidad con el usuario, sin inspeccionar conversaciones internas.
2. Generar **dentro del repositorio**, sin captura de pantalla, un PNG con figuras/colores aleatorios cuyo contenido no aparezca en el nombre ni en el mensaje. El evaluador conserva la respuesta esperada fuera del contexto de Claude.
3. Obtener consentimiento específico para transmitir esa imagen al proveedor y para enviar un único mensaje a ese panel. Aceptar primero la diferencia de UX: solicitud de lectura visual de archivo, no promesa de adjunto nativo.
4. El usuario comprueba prompt vacío, ausencia de diálogos y sesión inactiva. Esto es una condición manual de prueba, NO solución automática a P3. Acordar exclusividad de teclado durante el ensayo.
5. Enviar una petición explícita de análisis de la ruta absoluta (con espacios en una segunda prueba), sin describir el contenido. Verificar respuesta visual correcta y continuidad de la conversación. Si pide permiso, resolverlo manualmente; nunca responder con Enter automático.
6. Registrar resultado, permisos, destino y semántica observada. No confundir acuse de escritura de terminal con interpretación de imagen.

No hay todavía script de envío: deliberadamente se evita ofrecer un comando que pueda modificar sesiones reales antes de aprobar el mecanismo y el destino.

### Reinspección por procesos tras autorización de P1

El usuario autorizó realizar la prueba. La primera inspección por TTY encontró únicamente `ssh`, `pi`, `ssh` en los tres paneles existentes; no se dedujo ausencia de Claude remoto por sus títulos. Tras el usuario preparar de nuevo el entorno, `it2 session list --json` junto con `ps -axo pid=,ppid=,tty=,comm=` identificó un cuarto panel, TTY `ttys001`, con cadena `login → zsh → claude` (PID observado 11362, padre 11356). Esto identifica un candidato local por proceso, no por nombre. Los PID son observaciones transitorias y deben revalidarse. No se ha leído pantalla ni enviado texto. Queda por confirmar con el usuario prompt vacío/inactivo para el ensayo manual; esta confirmación no resuelve P3 automáticamente.

## P2 — Panel inequívoco

**Parcial:** enumeración real exitosa mediante el CLI incluido en iTerm2, sin instalar SDK. `it2 session send --help` declara `--session <id>` y envío sin newline; `session run` añade newline y no debe usarse aquí. No se ejecutó ninguno.

La API Python oficial expone `Session.session_id` y `Session.async_send_text(text, suppress_broadcast=False)`. Un adaptador futuro debe usar ID explícito y `suppress_broadcast=True`, revalidar existencia y nunca caer al panel activo. El CLI requiere investigar su comportamiento ante broadcast antes de adoptarlo para envío. No se ha probado envío sin foco, cierre/recreación ni rechazo de ID obsoleto. Debe hacerse en dos paneles de prueba con receptores inocuos, no Claude, previa aprobación para crearlos y escribir en ellos.

### Bloqueo adicional antes del ensayo autorizado

Tras confirmar el usuario que el panel local estaba listo, se revisó la seguridad de broadcast antes de escribir. `it2 app broadcast --help` ofrece `add`, `off`, `on`, pero no una consulta de estado. No se ejecutaron cambios.

El código oficial actual descargado en `spike-evidence/SessionCommand.swift` construye el envío CLI sin establecer `suppressBroadcast`. El servidor en `spike-evidence/iTermAPIHelper.m` usa `writeTaskNoBroadcast` únicamente si ese campo es verdadero; en caso contrario usa `writeTask`. Fuentes: `https://raw.githubusercontent.com/gnachman/iTerm2/master/it2cli/Sources/it2core/Commands/SessionCommand.swift` y `https://raw.githubusercontent.com/gnachman/iTerm2/master/sources/API/iTermAPIHelper.m`. Son fuentes de master, no verificación binaria de 3.7.6; se consideran evidencia de riesgo, no garantía del comportamiento instalado.

Por tanto, tener `--session ID` **no basta para prometer aislamiento** con broadcast activo. La ayuda instalada no ofrece una opción de supresión. No se envió texto ni Enter. El ensayo queda bloqueado hasta usar el SDK oficial con `suppress_broadcast=True` (requiere aprobar instalación) o confirmar manualmente broadcast desactivado, manteniéndolo así durante la prueba. No se modificó configuración para eludir el bloqueo.

### Segundo ensayo autorizado: detenido por destino cerrado

El usuario aceptó continuar con lectura por ruta y autorizó un mensaje nuevo para probar inserción y Enter en llamadas separadas. Antes de escribir se revalidó el ID anterior: no apareció en `it2 session list --json`; la lectura dirigida respondió `Session not found` (exit 3). La enumeración por TTY/procesos mostró únicamente dos paneles: `ttys000` con `zsh → pi` y `ttys001` con `zsh → ssh`. El TTY `ttys001` se había reutilizado y ya no correspondía al Claude anterior. No se sustituyó el destino por el panel activo ni por el mismo TTY. No se envió texto, retorno ni imagen. El segundo ensayo queda pendiente de que el usuario prepare e identifique una nueva sesión local. Esta observación valida el rechazo de un destino cerrado en lectura, no el envío dirigido ante cierre concurrente.

### Segundo ensayo local: éxito de lectura y envío supervisado

Fecha: 2026-10-27, comprobación final 22:06 UTC. Tras preparar el usuario un nuevo Claude local y confirmar que estaba listo, se identificó por proceso PID 1949, TTY `ttys002`, panel `29474A44-21CC-4C24-9196-F688689EAA57`. La lectura inicial mostró el editor sin mensaje escrito (con sugerencia); esto solo complementa la confirmación humana, no demuestra P3.

```sh
python3 scripts/spike-p1.py \
  --session 29474A44-21CC-4C24-9196-F688689EAA57 \
  --tty ttys002 --pid 1949 \
  --trial docs/spike-evidence/p1-local-02 \
  --confirmed-empty-idle-broadcast-off --split-submit
```

Se insertó la petición de lectura visual sin retorno; tras 2 segundos y revalidación de identidad se envió un único `\\r` en otra llamada al mismo ID. No hubo reintento ni pulsación manual de Enter. Una lectura del panel unos 6 segundos después mostró lectura del PNG y ejecución en curso; otra unos 8 segundos más tarde mostró respuesta completa: cuatro rectángulos iguales más altos que anchos, de izquierda a derecha **amarillo, rojo, verde, azul**. A continuación se consultó `expected.json`: coincidencia exacta. El modelo declaró leer únicamente ese archivo y no ejecutar comandos. No se inspeccionaron bloques internos ni conversaciones históricas. Evidencia: observación de la salida del panel y archivo de control, no afirmación de adjunto nativo.

**Cambio de versión:** `claude --version` después del ensayo devolvió **2.1.312**; el panel mostraba un aviso de actualización. El agente no ejecutó instalación, actualización ni reinicio. No se verificó la versión del proceso ya arrancado por separado; este ensayo no se atribuye con certeza a 2.1.304. La versión del ejecutable disponible al final es 2.1.312.

**Conclusión:** P1 pasa como lectura visual explícita por ruta local, mecanismo aceptado por el usuario para continuar. Separar texto y Enter funcionó en este ensayo supervisado, con estado y broadcast confirmados manualmente. No garantiza seguridad frente a carreras, menús o borradores; P3 sigue bloqueado y P4 sigue pendiente. El gate global NO pasa. No se implementan fases 2–5.

Pruebas del arnés (sin llamadas reales a iTerm2): `python3 -B -m unittest discover -s tests/unit -v`. Cubren dos llamadas separadas, PNG generado, destino explícito, rechazo de repetición del directorio y rechazo de panel cerrado. No sustituyen las pruebas reales ni validan estado seguro.

## P3 — Estado seguro de entrada

**No resuelto; bloquea envío inmediato.**

- Hooks oficiales: `UserPromptSubmit` informa después de enviar; `Stop` significa fin de respuesta, no editor vacío; `PermissionRequest` identifica ciertas solicitudes de permiso, no todos los menús.
- `Notification/idle_prompt` se documenta aproximadamente 60 s después de terminar, si no se ha escrito desde entonces y no hay agentes de fondo. Es evidencia útil, pero no una lectura atómica del buffer actual ni una reserva que impida teclear entre comprobación y envío. No se instalaron hooks.
- `it2 monitor prompt` requiere integración de **shell**: no garantiza estado del editor de Claude.
- `get-status` informa estado almacenado mediante `set-status`; `turn_open` es null hasta establecerlo. No es una fuente independiente de verdad sobre el input.
- Leer pantalla, escuchar teclas o detectar un prompt no prueba que no exista texto pendiente, pegado previo, diálogo o carrera. No se usaron esas heurísticas.

En las interfaces revisadas no se verificó una API de lectura del borrador y envío condicional atómico al proceso activo. No es correcto declarar `ready` solo por un hook. Hasta resolverlo, el estado seguro es `unknown` y no se modifica la terminal.

### Instrumentación autorizada de P3

Se añadió `scripts/spike-p3.py` con comandos `prepare`, `launch`, `hook`, `mark` y `status`. El usuario autorizó preparar instrumentación, no nuevos mensajes. Se preparó dentro del repositorio el ensayo privado `p3-1b5e31224680`; **no se lanzó Claude ni se enviaron mensajes** durante esta preparación. El siguiente paso es el arranque interactivo por el usuario y comprobar `SessionStart` real. Protocolo completo: [p3-protocol.md](p3-protocol.md).

Se consultó documentación oficial actual mediante `curl -fLsS --max-time 25 URL -o ARCHIVO`: `https://code.claude.com/docs/en/hooks.md`, `https://code.claude.com/docs/en/interactive-mode.md`, `https://code.claude.com/docs/en/cli-reference.md`, `https://code.claude.com/docs/en/settings.md`, `https://iterm2.com/python-api/keyboard.html`. Copias con sufijo `p3` en `spike-evidence/`. La ayuda local de 2.1.312 confirma `--settings`, `--setting-sources` y `--permission-mode manual`.

No se encontró una interfaz documentada de lectura del borrador y envío condicional en las secciones revisadas. El editor externo y stash tienen efectos sobre el input; no se usan como consulta. `KeystrokeFilter` oficial solo documenta supresión del manejo de teclas coincidentes, no exclusión total de otras entradas o transiciones internas. No se instaló SDK ni se activó bloqueo de teclado.

El arnés registra exclusivamente metadatos permitidos y siempre informa `unknown`, `safe_to_submit: false`. Configuración por invocación, sin modificar settings globales. La sesión de prueba sigue teniendo los efectos nativos de Claude (por ejemplo persistencia/autenticación), no se promete sandbox. Ocho pruebas unitarias totales pasan, incluidas privacidad del log, no promoción a ready, rechazo de enlaces en el log, nombres de ensayo inválidos y lanzamiento sin TTY. Son pruebas sintéticas; todavía no hay evidencia de hooks reales en esta sesión.

### Primeros eventos reales y diagnóstico de relanzamiento

El 2026-10-28 se comprobó el log del ensayo `p3-1b5e31224680`: `SessionStart` a las 14:28:48 UTC y `SessionEnd` a las 14:29:29 UTC, con la misma huella de sesión. Confirma ejecución real de ambos hooks, no disponibilidad ni borrador vacío. El usuario comunicó después un error genérico al lanzar ese ID. La inspección encontró el marcador `launched` ya existente, coherente con rechazo de reutilización (la excepción original no se guardó, así que no se afirma reconstrucción inequívoca del intento fallido).

Se corrigió el lanzador para explicar por separado ensayo ya utilizado, falta de TTY y fallo de ejecución, sin volcar payloads ni borrar el marcador. Se añadió prueba de rechazo de relanzamiento; nueve pruebas totales pasan. Se preparó el nuevo ensayo `p3-5eabd637d437`, sin arrancarlo ni enviar mensajes. El ensayo anterior permanece intacto.

El segundo ensayo `p3-5eabd637d437` registró `SessionStart` el 2026-10-28 a las 14:36:41 UTC y `SessionEnd` a las 14:36:45 UTC con la misma huella. El usuario informó que no vio salida y proporcionó una ruta de captura; no se abrió ni transmitió esa captura sin consultar. Hay otro proceso Claude en `ttys003`, pero no se asume su asociación al ensayo: el título de proceso no conserva argumentos identificadores. `SessionEnd` tampoco prueba por sí solo salida del proceso: puede deberse a clear/resume. Se amplió la lista permitida del observador para conservar solo el enum oficial `reason` en próximos eventos; los eventos antiguos no contienen ese dato y no se reconstruye. Diez pruebas unitarias totales pasan. No hubo nuevos mensajes ni pulsaciones.

El usuario aclaró que veía el diálogo de confianza de workspace, con `No, exit` seleccionado y `Yes, I trust this folder` como alternativa. Es coherente con que Enter sobre la opción predeterminada cierre el arranque, aunque no se registró qué tecla pulsó. Demuestra además que `SessionStart` puede haberse observado sin que el editor normal esté disponible: no basta para declarar ready. Tras autorización explícita se intentó abrir únicamente la captura proporcionada; la ruta temporal devolvió ENOENT, por lo que no se leyó la imagen. El diagnóstico del diálogo se basa en el texto aportado por el usuario. No se aceptó confianza ni se modificó configuración por el agente. Se preparó el nuevo ensayo `p3-ced6e3bfafca` para que el usuario decida manualmente sobre la confianza del repositorio. No se envían teclas a ese diálogo.

Tras confirmar el usuario el prompt normal del ensayo `p3-ced6e3bfafca`, se observó `SessionStart` real el 2026-10-28 a las 14:49:36 UTC, sin `SessionEnd` en esa consulta. Se registró la etiqueta humana `idle-empty` a las 14:50:08 UTC; no es una lectura técnica del borrador. El inventario local muestra dos procesos Claude en `ttys002` y `ttys003`; no se deduce asociación inequívoca solo por tener un proceso Claude. Para observar hooks se usa el ID privado del ensayo, sin enviar a ninguno de esos paneles. Próximo paso: escritura manual de un borrador sin Enter y comparación de eventos.

### Borrador pendiente: resultado observado

El usuario confirmó haber escrito el borrador de prueba sin enviarlo. El 2026-10-28 a las 15:06:53 UTC se añadió la etiqueta humana `draft` y se consultó el log: no había nuevos eventos de hooks desde `SessionStart`; únicamente las etiquetas humanas distinguían `idle-empty` y `draft`. No se leyó ni guardó el contenido del borrador ni se enviaron pulsaciones. La etiqueta representa el momento de confirmación, no el instante exacto de escritura.

Esto muestra que **los hooks suscritos no notificaron la transición de vacío a borrador en este ensayo**. No demuestra que ninguna interfaz posible pueda exponerlo ni que ningún evento se haya perdido, pero sí impide usar esta combinación de hooks como prueba positiva de editor vacío. Un hook de arranque operativo tampoco demuestra entrega de todos los hooks posteriores. Se mantiene `unknown` / `safe_to_submit: false`. Próximo ensayo observacional propuesto: abrir un menú manualmente, sin enviar mensaje.

### Menú abierto: resultado observado y cierre de esta vía del spike

El usuario confirmó el menú de comandos abierto tras escribir `/` sin Enter. El 2026-10-28 a las 15:11:36 UTC se registró la etiqueta `menu`. La consulta del log siguió mostrando únicamente `SessionStart` como evento real de hooks, además de las marcas humanas. No se observaron eventos que distinguieran prompt vacío, borrador y menú. No se leyó pantalla ni se enviaron teclas.

**Conclusión de la vía hooks: NO-GO para declarar entrada segura.** Los estados manualmente confirmados `idle-empty`, `draft` y `menu` producen el mismo historial de hooks observado. Esta instrumentación no permite diferenciarlos ni garantizar que Enter no seleccione un comando. No se afirma imposibilidad universal ni entrega perfecta de eventos; se constata que la interfaz y configuración ensayadas no aportan la evidencia requerida. Instalar el SDK de iTerm2 o añadir un wrapper de registro no crea por sí mismo la señal interna que falta.

Se detiene esta vía de implementación de envío inmediato conforme al gate. No se necesitan más mensajes reales para demostrar esta limitación; probar Stop/permisos puede caracterizar otros eventos, pero no corrige la falta ya observada. Posibles continuaciones, sujetas a decisión: localizar/verificar otra interfaz oficial que exponga borrador y envío condicional al mismo proceso; solicitar esa capacidad al proveedor; o rediseñar hacia una sesión gestionada por API/SDK con control propio de entrada (no se presenta como equivalente a la terminal existente). No se instalaron dependencias ni se aceptó ese rediseño.

**Estado P3: no resuelto; vía de hooks insuficiente demostrada en los estados ensayados. Gate global NO-GO.** No se supera el gate por añadir hooks.

## P4 / P5 — SSH

**No ejecutados.** No se han elegido hosts, autenticación ni sesiones de prueba. No se leen claves ni se transfieren imágenes. Dos sesiones en el mismo host/proyecto requieren asociación explícita panel local ↔ instancia remota. Aceptar wrapper y posiblemente lanzador `claude-shot ssh <alias>` antes de modificar el flujo; no asumir que variables iTerm atraviesan SSH. Hash correcto de transferencia no demuestra lectura visual. P4 continúa siendo bloqueo del gate.

## Acuerdo de alcance y controlador local supervisado

Después de los resultados de P3, el usuario propuso enviar directamente al terminal y aceptó explícitamente sustituir la detección automática por confirmación humana por envío. También autorizó instalar el SDK oficial en un entorno virtual dentro del repositorio. Esta decisión **no resuelve P3** ni supera el gate original para el MVP completo; habilita un prototipo local de alcance reducido. El acuerdo se añadió al principio de `IMPLEMENTATION_PLAN.md`.

Instalación realmente ejecutada con permiso:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install iterm2
.venv/bin/python -m pip freeze
```

Resultado: `iterm2==2.30`, `protobuf==7.36.2`, `websockets==17.3`, Python 3.15.0. Versiones fijadas en `requirements.lock`. Importación del SDK exitosa. No se modificó configuración del sistema, iTerm2 o Claude, ni se inició conexión SDK, captura o entrega real durante esta implementación.

Se implementó `src/claude_shot/` y el lanzador `scripts/claude-shot`: `doctor`, `sessions [--json]`, `send --image`, `capture`, `cleanup`. Selección por panel/TTY y proceso `claude` local en grupo de primer plano, sin wrapper ni títulos. Revalidación de ID, TTY, PID y hora de arranque; confirmación manual ENVIAR; copia PNG privada; bloqueo por panel; SDK con `suppress_broadcast=True` en texto y Enter separados; no reintentos. El estado sigue siendo desconocido y el recibo `submitted` no confirma recepción ni lectura. Cancelación antes de confirmar no conecta al SDK ni modifica la terminal. Solo texto de una línea. No SSH, GUI ni atajo global.

Validación ejecutada:

```sh
./scripts/claude-shot doctor
./scripts/claude-shot sessions --json
.venv/bin/python -B -m unittest discover -s tests/unit -v
git diff --check
```

`doctor` informó las versiones instaladas; `sessions --json` devolvió `[]`, coherente con el inventario de procesos sin Claude local en ese momento (no se inició uno para simular éxito). **24 pruebas unitarias pasan**, incluyendo arneses y controlador; las del SDK son simuladas. No hay todavía evidencia real de autorización/conexión del SDK, aislamiento de broadcast, entrega del controlador nuevo ni captura nativa. La vía de texto/Enter del spike anterior se probó con CLI it2, no con este adaptador: no se confunden ambos resultados. Reproducir la aceptación mediante `tests/manual/local.md` y los comandos de README con consentimiento explícito en cada ENVIAR.

Privacidad, retención explícita de mínimo 24 horas, limpieza conservadora y riesgos residuales documentados en `docs/security.md`. No se ejecuta limpieza automática ni se borra almacenamiento interno de Claude.

### Primera prueba del selector del controlador

El usuario ejecutó `send` y el descubrimiento mostró un Claude local (PID 14791). Introdujo el PID donde el selector original solo admitía índice de lista; fue rechazado antes de crear operación, conectar SDK o escribir texto. Se corrigió la UX para aceptar índice, PID o ID completo, volver a preguntar ante entradas inválidas y rechazar coincidencias ambiguas entre PID e índice. Se añadieron cuatro pruebas del selector: **28 pruebas totales pasan**. Sigue pendiente la entrega real del nuevo adaptador SDK; no se confunde este rechazo temprano con un fallo o éxito de transmisión.

### Fallo real SDK/CLI y corrección

El usuario confirmó ENVIAR para la operación `e047abdd50ca6e9da7d24aead375eb51`. El recibo, observado sin modificar, quedó `failed` con fecha 2026-10-29 01:16:54 UTC. El código marca ese estado si no ha intentado aún `async_send_text`: falló la consulta CLI de revalidación después de conectar al SDK. No se reenvió la operación ni se leyó su imagen para diagnosticar.

Reproducción real de **solo lectura**: dentro de `iterm2.run_until_complete`, ejecutar `it2 session list --json` con el entorno heredado del SDK devuelve exit 2 y error de autenticación; ejecutar la misma consulta con una copia de entorno sin `ITERM2_COOKIE` ni `ITERM2_KEY` devuelve exit 0. No se imprimieron credenciales ni datos de paneles. Esto confirma interferencia de las credenciales del SDK heredadas por el CLI; no un fallo de PNG o de interpretación.

Correcciones:

- `core.command` elimina esas dos variables únicamente del entorno del subproceso `it2`, conservando la autenticación SDK en su proceso.
- El adaptador usa el runner público `iterm2.run_until_complete(..., retry=False)`, que gestiona dispatcher y websocket. Los errores de entrega se propagan después de la limpieza, sin entregarlos al manejador del SDK que imprime traceback. No se cancela ni silencia un fallo de entrega: se mantiene el recibo failed/uncertain.
- Se eliminó el cierre manual del websocket creado con `async_create`, que provocaba el traceback secundario durante el cierre.

Comprobación real ejecutada, **sin texto ni Enter**:

```sh
.venv/bin/python -B scripts/check-iterm.py
```

Resultado: `SDK + CLI: OK. Claude locales coincidentes: 1. Sin envío ni captura.` Conexión SDK, consulta CLI coexistente y cierre completaron sin traceback. No hubo nuevas dependencias ni cambios de configuración. **30 pruebas unitarias pasan**, incluidas regresiones de aislamiento de credenciales y propagación de errores después de limpiar. La entrega real del controlador corregido sigue pendiente; no se presenta una consulta de solo lectura como prueba de envío.

### Primera entrega real exitosa con el controlador corregido

El usuario volvió a ejecutar el flujo y confirmó: «listo, lo envió bien». Se consultaron únicamente recibos locales: la nueva operación `aa768436a83a4f1c11d0274257702310` figura `submitted` el 2026-10-29 a las 01:34:05 UTC; la anterior permanece `failed`. No se modificaron los recibos ni se repitió el envío desde el agente.

**Resultado:** envío local real del controlador SDK corregido confirmado por el usuario, con texto/Enter separados y conversación existente. Posteriormente el usuario confirmó también que Claude interpretó correctamente la imagen, tras indicarle la respuesta esperada (cuatro rectángulos, amarillo, rojo, verde y azul). Se registra como interpretación visual confirmada por el usuario, sin inspección independiente de la respuesta de este último turno. El recibo se conserva como `submitted`: la confirmación humana se documenta aquí, no se atribuye a una señal automática del adaptador. No demuestra aislamiento con broadcast activo, captura nativa, SSH ni P3 automático. Las pruebas de esos casos siguen pendientes.

### Captura confirmada y simplificación de UX solicitada

El usuario confirmó que la captura funciona y pidió eliminar comprobaciones adicionales: seleccionar sesión y pulsar Enter al introducir texto debe enviar. También pidió mostrar el nombre de la pestaña iTerm2. Se acepta ese ajuste explícito: no se pide ENVIAR ni confirmación previa de captura. Se mantiene aviso breve de disponibilidad a cargo del usuario, Ctrl+C para cancelar antes de enviar y ausencia de reintentos. Enter con texto vacío también envía; `--text` se presenta como predefinido y requiere el mismo Enter interactivo. Se conserva la protección de ID/proceso, bloqueo y supresión de broadcast.

Verificación real de solo lectura: `it2 tab list --json` no incluye título; `it2 session list --json --format '\\(tab.title)'` sí devuelve `formatted` con el título de pestaña. Se usa esa etiqueta con fallback al título/nombre de panel y se eliminan controles para mostrarla. `tab_title` y `tab_id` no participan en igualdad/hash de identidad ni revalidación; un cambio de título no equivale a cambiar el destino. Se observó inventario real de dos Claude locales con títulos diferenciables, sin enviar mensajes.

**33 pruebas unitarias pasan**, incluyendo flujo con un solo Enter en el campo de texto, captura sin pregunta adicional, cancelación por Ctrl+C y títulos sin efecto en identidad. Esta UX nueva no se ha probado aún mediante otro envío real desde el agente. La captura confirmada por el usuario no demuestra todos los casos de permisos, Retina o monitores. No se tomaron ni transmitieron nuevas capturas durante este cambio.

### App nativa local construida — aceptación gráfica pendiente

Tras solicitar el usuario continuar construyendo la app, se implementó `macos/ClaudeShot.swift` (SwiftUI/AppKit, sin Hammerspoon). Inventario: Swift 6.3.3, host arm64 macOS 26.2. App local con selector de títulos/TTY/PID, actualización, elección PNG, captura de región, vista previa, texto de una línea y Enter/Enviar sin confirmaciones extra. Supresión de broadcast, identidad y revalidación siguen en el controlador. Atajo Carbon opcional ⌘⇧7, desactivado por defecto; activarlo abre la ventana, no captura ni envía. No se registró durante el desarrollo.

Puente `src/claude_shot/desktop.py`, acciones JSON limitadas por stdin/stdout, sin shell libre ni servidor. Las operaciones preparadas se descartan sin tocar terminal. Bloqueo por operación y marcador `attempted` evitan repetir una tentativa; resultado incierto conserva imagen y bloquea reenvío de esa operación. No se añaden dependencias ni se habilitan permisos.

Comandos ejecutados:

```sh
.venv/bin/python -B -m unittest discover -s tests/unit -v
./scripts/build-app
codesign --verify --deep --strict 'build/Claude Shot.app'
plutil -lint 'build/Claude Shot.app/Contents/Info.plist'
git diff --check
```

**45 pruebas unitarias pasan.** Compilación con Swift instalado, destino macOS 14+ para arquitectura del equipo, firma ad-hoc local y validación del bundle completadas. Cachés y bundle en `build/`, sin instalar en /Applications ni notarizar. El bundle depende del repositorio/.venv; no es autónomo ni se garantiza compatibilidad en otros Macs. No se abrió la app, registró atajo, conectó al SDK, tomó captura o envió mensaje real durante esta implementación. Por tanto, no se afirma que la GUI, sus permisos o su atajo estén validados: checklist en `tests/manual/desktop.md`.

También se ejecutó `printf '{"action":"sessions"}' | ./scripts/claude-shot desktop`: devolvió JSON válido con `ok: true` y un Claude local en ese inventario. Es una consulta real de solo lectura, sin conexión SDK ni escritura a la terminal; los demás ensayos del puente usan adaptadores simulados.

La entrega/captura confirmadas por el usuario corresponden a la CLI, no sustituyen pruebas gráficas. El formato abreviado sin prefijo se mantiene; no se asume que una ruta aislada sea adjunto nativo. P3 sigue delegado al usuario según acuerdo, y P4/P5 SSH siguen pendientes. Arquitectura y permisos documentados en `docs/desktop.md`.

### Atajo automático y cambio a Command + Control + 7

El usuario informó que el atajo no funcionaba y pidió dejarlo activado directamente; después especificó **Command + Control + 7**. Se cambió a `cmdKey | controlKey` con `kVK_ANSI_7`, registro idempotente en `applicationDidFinishLaunching`, estado/código visible separado del estado de sesiones, y reapertura mediante ID de escena SwiftUI (no solo búsqueda por título). Se conserva la app al cerrar la última ventana y se libera el atajo al salir. No captura ni envía al pulsarlo.

El agente recompiló, verificó firma y abrió el bundle para activar el atajo autorizado. En `.claude-shot/hotkey-status.json` se observó `registered`, código **0**, PID 17323 vivo tras lanzar la nueva versión. Es registro real, no prueba de pulsación física ni de reapertura: esos pasos siguen pendientes del usuario. El diagnóstico guarda solo enum/código/PID, dentro del repositorio con permisos privados; no escucha otras teclas ni contenido.

No se cerró por la fuerza ninguna app anterior ni se modificaron preferencias de teclado/TCC. No se hicieron capturas ni envíos. La prueba inicial con la combinación anterior dejó un evento `disabled` de un proceso ya terminado; no se atribuye una causa específica al fallo original sin evidencia. **45 pruebas del controlador/puente pasan** y la app recompiló; no hay pruebas unitarias de despacho físico de hotkeys. El registro exitoso es evidencia adicional acotada, no aceptación completa de la GUI.

### Captura directa por atajo y popup mínimo

El usuario pidió que ⌘⌃7 active directamente la herramienta nativa y que después aparezca solo un popup con sesión y texto. Se sustituyó la ventana grande por popup compacto flotante, sin vista previa, con selector, input, flecha de actualización y botón avión. Enter/avión envía y oculta; Esc descarta. App accessory, sin Dock ni ventana inicial, con icono de barra de menús. La captura ya no exige sesión previa; el envío sí. El menú ofrece captura, popup pendiente, PNG, archivo en Finder y salir. Captura pendiente se conserva; una segunda pulsación durante selección no abre la ventana sobre la región.

Se recompiló y verificó firma; **45 pruebas de controlador/puente pasan**. Se abrió la versión nueva sin simular pulsaciones: diagnóstico `registered`, código 0, PID 17497 vivo. No se ejecutó captura ni envío durante este desarrollo. El registro no acredita el flujo físico: captura por atajo, ocultación inicial, popup, foco, Enter y Esc quedan pendientes de aceptación visual por el usuario en `tests/manual/desktop.md`. README, arquitectura y seguridad actualizados; el nuevo comportamiento sustituye al anterior atajo que solo mostraba ventana.

### Documentación visual y publicación autorizadas

El usuario pidió un README visual inspirado en NexusMind, optimización de descubrimiento/SEO y subir todo el código al remoto `smart-coder-labs/claude-shot`. Se rehízo el README en inglés, conservando guía en español, con banner original, captura real del popup y detalle recortado claramente identificado. La captura se tomó únicamente de la ventana Claude Shot (CoreGraphics identifica ventana propia; `screencapture -x -o -l <id>`), con autorización expresa. Se revisó su contenido: título del experimento sintético, controles e indicador de envío previo, sin terminales, escritorio ni input privado. No se envió otro mensaje para crear la imagen. El banner es arte original y la tarjeta social combina ese arte con la captura real; no se presentan como pantallas inventadas.

Se aplicaron y verificaron por API oficial la descripción y 12 topics del repositorio. Credencial GitHub existente usada solo en memoria, sin imprimir/guardar tokens ni incluirlos en argv; TLS verificado mediante curl, sin cambiar certificados del sistema. El Python del Mac no resolvió inicialmente su CA de HTTPS; se utilizó curl con verificación normal, no se deshabilitó SSL.

Se añadieron CI de tests/build/documentación, formulario de issues y guía de contribución. `scripts/check-docs.py` valida enlaces/activos sin red. Dependencias, cachés, capturas de trabajo, recibos, mensajes de ensayos y descargas de documentación ajena quedan excluidos del commit; se publican solo fixtures sintéticos, fuente, documentación y assets revisados. Fuentes oficiales de snapshots locales enlazadas desde `spike-evidence/README.md`.

La tarjeta social queda preparada como archivo: no se afirma que se haya configurado la opción Social preview de GitHub, no expuesta por el actualizador de API. No se eligió licencia por el propietario ni se inventó una. No se cambia el gate de SSH ni se dan por probados los permisos/monitores/flujo gráfico por haber capturado el popup. Ver `discoverability.md`.

### Lotes de varias capturas — implementación, pendiente de prueba visual real

El usuario solicitó tomar varias capturas y enviarlas juntas. Se amplió el flujo local a hasta **6 PNG por lote**, **20 MiB por archivo / 60 MiB total**. Cada pulsación de ⌘⌃7 o + añade una imagen a la misma operación y preserva el texto; el popup muestra contador y controles numerados × para quitar imágenes. Esc durante una selección adicional conserva el lote previo; Esc en popup lo descarta entero. Enter/avión construye **un único mensaje con todas las rutas en orden y un solo Enter final**, no varios envíos paralelos ni un turno por captura.

Backend: manifiesto privado `images.json` con nombres internos validados y escritura atómica. Añadir/quitar/cancelar/enviar comparten bloqueo de operación; rollback de la copia nueva si falla o supera límites. Antes de enviar se revalida cada PNG y tamaño agregado; no se permite editar/reintentar un lote intentado. CLI acepta `send --image A --image B` y `capture --count N` (en CLI, Esc durante --count cancela el lote entero).

**56 pruebas unitarias pasan**, incluidas orden/rutas en una única llamada al adaptador, conservación al cancelar selección o fallar un añadido, eliminación individual, límites, manifiestos inválidos/enlaces, limpieza de lote y CLI múltiple. App recompilada y firma verificada. No se tomaron nuevas capturas ni se enviaron mensajes reales durante esta ampliación. **La interpretación de varias imágenes en un mismo turno sigue pendiente de aceptación real**; las pruebas simuladas no demuestran lectura visual múltiple. Las capturas del README muestran la versión anterior de una imagen y se identifican como tales, sin inventar imágenes de los controles nuevos.

### Aviso de captura pese a permiso activado — firma local estable

El usuario mostró el aviso nativo de grabación de audio/pantalla atribuido a Claude Shot y confirmó que la entrada en Ajustes ya estaba activada. Se comprobó que el proceso correspondía a este bundle y arrancó después de la compilación: no era una instancia previa a ese build. La identidad ad-hoc estaba ligada al `cdhash`; no había identidades válidas de firma de código disponibles. Esto identificó una causa probable de permisos que no siguen una recompilación, no un diagnóstico definitivo del estado TCC.

Con aprobación explícita del propietario se generó/importó un certificado de desarrollo local RSA-3072/SHA-256: uso digitalSignature/codeSigning, clave importada no extraíble, ACL para `/usr/bin/codesign`, confianza en dominio de usuario solo para `codeSign`. Archivos temporales de clave eliminados al terminar. Certificado público y configuración quedan ignorados en `.local-signing/`; ninguna clave/certificado/configuración local se publica. No se tocaron permisos TCC ni diálogos automáticamente.

`build-app` usa ahora el helper `sign-app.py`: ad-hoc por defecto para otros checkouts/CI, o identidad local configurada y validada por huella/llavero. Se comprueba antes de compilar; si falta/expira la identidad configurada, falla sin fallback ad-hoc. Firma sin timestamp externo y verificación estricta. El helper no crea/importa certificados ni modifica confianza.

La app se recompiló y verificó con la nueva identidad, cuyo requisito designado referencia bundle ID y certificado. Dos ejecutables de prueba diferentes se firmaron sin ejecutarlos: distinto hash de código, idéntico requisito designado entre ellos y la app. **64 tests pasan**, incluidos 8 de política de firma, configuración privada y rechazo sin fallback. No se forzó cierre/reinicio de la app, no hubo capturas ni mensajes nuevos. **Pendiente: salir/reabrir la app, autorizar la identidad nueva y verificar captura real, incluida persistencia tras recompilar**. [Procedimiento y límites](local-signing.md).

## Decisiones originales / alternativas (histórico)

Este apartado conserva las opciones anteriores al acuerdo local supervisado. La autorización y aceptación de lectura por ruta se actualizaron en el apartado precedente; SSH y UX definitiva siguen pendientes.

Ninguna decisión de UX se considera aceptada todavía: wrapper, lanzador SSH, Hammerspoon y lectura por ruta siguen pendientes.

1. **Ensayos locales realizados:** lectura por ruta confirmada primero por respuesta del usuario y después por observación directa del panel. Texto y retorno juntos dejaron borrador; texto y retorno separados enviaron correctamente en el segundo ensayo supervisado. No se valida envío seguro sin supervisión.
2. **Reducir alcance:** preparar archivo y mostrar ruta/instrucciones; usuario introduce y envía en Claude. Evita prometer envío automático, pero cambia el objetivo original y requiere aceptación.
3. **Integración explícita distinta:** investigar una sesión controlada por una API oficial/SDK desde su inicio. Puede ofrecer entrada estructurada, pero no equivale a controlar conversaciones interactivas existentes. Requiere rediseño y aprobación.
4. Mantener el alcance original y esperar/verificar una interfaz oficial que exponga borrador, disponibilidad y envío condicional. No implementar un selector que prometa seguridad no demostrada.

Para continuar se necesita autorización concreta de prueba local, aceptación o rechazo de lectura por ruta, y después hosts SSH y política de autenticación. **No hay evidencia suficiente para pasar el gate.**
