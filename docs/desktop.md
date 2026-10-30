# App nativa local

## Componentes

- `macos/ClaudeShot.swift`: interfaz SwiftUI/AppKit mínima en barra de menús: captura directa por atajo y popup flotante de sesión/texto con Enter para enviar. Atajo Carbon ⌘⌃7 activado al arrancar por petición del usuario, sin preferencias persistentes del sistema.
- `scripts/build-app`: compila y firma un bundle local en `build/Claude Shot.app`; cachés Swift/Clang en el repositorio. Firma ad-hoc si no hay configuración; reutiliza certificado estable si el propietario lo configuró. No instala certificados ni abre la app.
- `scripts/sign-app.py`: valida/selecciona identidad por huella completa y llavero explícito; metadata privada en `.local-signing/identity.json`. No modifica llaveros, confianza ni TCC. Una identidad configurada inválida hace fallar el build, sin fallback silencioso.
- `src/claude_shot/desktop.py`: operaciones JSON limitadas, una petición por proceso hijo. Reutiliza validación, copia privada, bloqueo, revalidación y adaptador SDK del controlador CLI.
- `scripts/claude-shot.py desktop`: entrada del puente. No necesita TTY: la autorización es la acción Enter/Enviar en la app. La CLI interactiva conserva su propio flujo; este puente no es un servicio ni una frontera de seguridad frente a otros procesos del mismo usuario.

## Protocolo

JSON por stdin, máximo 64 KiB; EOF cierra la petición. JSON único por stdout, sin concatenación con shell. Avisos SDK se redirigen fuera de stdout. La app no guarda prompts ni vuelca stderr a Console.

Acciones permitidas:

- `sessions`: inventario de destinos locales, incluido título como etiqueta e identidad PID/TTY/arranque/ID.
- `prepare` con `path`: valida/copia un PNG local; si se incluye `operation`, añade al lote existente. Devuelve ID y `image_paths` en orden, con `image_path` de la última por compatibilidad.
- `capture`: abre selección nativa por acción del usuario; crea lote o añade al indicado. Esc devuelve `capture_cancelled` y preserva imágenes previas; sin imágenes devuelve `cancelled`. Nunca transmite.
- `remove` con `operation` e `index` (desde 0): elimina una imagen no intentada y actualiza orden. Quitar la última cancela el lote.
- `send` con operación, snapshot de identidad y texto: valida identidad/imagen/texto y llama al adaptador sin reintentos. Solo permite una tentativa por operación.
- `cancel`: elimina imagen únicamente si la escritura no se ha intentado.

La UI no expone el puente como opción de automatización desatendida y no acepta mensajes por URL, red o Apple Events. Un proceso local con los permisos del usuario podría invocar el puente directamente: no se afirma aislamiento contra ese actor.

## Exclusión y errores

La UI bloquea controles durante cada petición. El flujo gráfico es captura → popup compacto de sesión/texto → Enter/avión → ocultar popup; no hay ventana inicial ni vista previa grande. Esc durante la primera captura no muestra popup; al añadir captura devuelve el popup con las previas intactas. Esc en el popup descarta el lote completo. ⌘⌃7 captura una imagen o muestra el popup pendiente sin añadir. ⌘⌃⇧7 inicia/amplía el lote, igual que +; Enter envía y cierra el lote, sin reutilizar una operación intentada. Añadir no sobrescribe ni borra texto; números × quitan imágenes. Se admiten 6 imágenes, 20 MiB por imagen y 60 MiB por lote. La lista se consulta al arrancar y actualiza después de capturar; no se exige destino para iniciar selección de región. El backend usa bloqueo por operación y por destino; un marcador exclusivo `attempted` impide duplicar entregas incluso si dos peticiones apuntan a paneles diferentes. Añadir/quitar/cancelar/enviar comparten bloqueo por operación. `images.json` privado enumera solo nombres internos validados, sin rutas de origen ni texto. Actualización atómica del manifiesto; un fallo al añadir elimina solo la copia nueva. Antes de enviar se revalidan todos los PNG y el límite agregado. Una sola llamada al adaptador envía todos los paths en un mensaje, seguida de un único Enter. No hay bucle de envíos por imagen. Un marcador sin recibo final se trata como incierto y nunca se reenvía automáticamente. La limpieza reconoce ese marcador solo en operaciones finalizadas y antiguas.

Identidad cambiante se rechaza; renombrar pestañas no cambia identidad. No se detecta automáticamente editor vacío, menús o permisos. La confirmación es Enter/Enviar después del aviso visible, conforme al alcance aceptado.

Después de una entrega incierta, la UI retira el botón de reenvío de esa operación pero conserva los archivos. Si el proceso muere antes de responder, la UI no asume que el envío falló. Preparar otra imagen sería una acción nueva del usuario y podría duplicar contenido: inspeccionar Claude primero.

El bundle depende de una ruta absoluta al repositorio en `Contents/Resources/repository-path.txt`, generada al construir. Se ejecuta `.venv/bin/python` directamente, con PATH explícito para `it2`, sin activar shells ni modificar su configuración. No es una app empaquetada para distribución; reconstruir si cambia la ubicación del repositorio.

## Permisos y ciclo de vida

No se lanza captura al abrir la app. **El atajo ⌘⌃7 sí activa directamente selección de región**, como pidió posteriormente el usuario; esa pulsación es la autorización de captura. También puede iniciarse desde el menú de estado. Nunca envía automáticamente después de capturar: necesita Enter/avión en el popup. La app usa política accessory, sin Dock, y conserva un icono de barra de menús para mostrar, capturar, elegir PNG, inspeccionar archivo, desactivar atajo o salir. El atajo ⌘⌃7 se registra al arrancar, conforme al cambio solicitado por el usuario; puede desactivarse desde el menú hasta el siguiente arranque. La ventana muestra el resultado y código del registro, independientemente del estado de las consultas a sesiones. Se utiliza `openWindow(id:)` para recrear la escena si fue cerrada, en lugar de depender solo del título de una ventana existente. Salir libera registros de atajo por el proceso. No se crea autoarranque ni servicio, no se instala Hammerspoon y no se pide Accesibilidad mediante automatización de UI.

El backend de captura y la autorización SDK pueden tener atribución de permisos distinta de la CLI en Terminal. El usuario debe probar y decidir en los diálogos nativos. No se cambia TCC, confianza de carpetas, API iTerm2 ni configuración global. Firma ad-hoc por defecto; recompilar puede causar nuevas preguntas de autorización. La [firma local estable opcional](local-signing.md) conserva el requisito de identidad entre builds, pero no concede permisos. En este Mac se instaló/configuró un certificado local con autorización expresa del propietario; solo confianza de usuario para firma de código, sin resetear TCC. La nueva identidad requiere reiniciar la app y aceptación manual para comprobar captura. No se deshabilita Gatekeeper ni se promete notarización.

Salir normalmente descarta el lote preparado; durante una petición en curso la app pide esperar mediante su estado, sin interrumpirla. Cerrar la ventana no equivale necesariamente a terminar el proceso. Cierre forzado, errores o desconexión pueden dejar artefactos privados; retención y limpieza explícitas como en la CLI.

## Validación

Compilación y firma verificadas, además de pruebas unitarias del puente con SDK/captura simulados. Tras la construcción inicial, se abrió la UI con autorización para activar el atajo y se observó registro real código 0 con proceso vivo. No se ejecutó envío/captura real desde ella durante el desarrollo. Pulsación física y reapertura siguen pendientes. Ambos atajos Carbon usan IDs distintos, validación de firma/ID del evento y modificadores exactos; el fallo del segundo registro intenta deshacer el primero. Desactivar/salir libera ambos registros. No se ha simulado ninguna pulsación física para tomar capturas. El diagnóstico mínimo del último registro/evento propio del atajo queda dentro del repositorio en `.claude-shot/hotkey-status.json`, privado, sin capturar otras teclas ni texto. La entrega ya confirmada por el usuario corresponde a la CLI, no acredita la GUI. Ver `tests/manual/desktop.md` antes de dar por aceptada la experiencia de escritorio. SSH continúa fuera de alcance y sin gate remoto superado.
