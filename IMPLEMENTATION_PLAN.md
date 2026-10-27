# Claude Shot — Plan de implementación

## 1. Objetivo

Herramienta para macOS que permita capturar una región de pantalla, elegir una sesión abierta de Claude Code en iTerm2 —local o conectada mediante SSH directo—, añadir texto opcional y enviar la imagen sin copiar ni pegar.

Estado: plan propuesto, sin validación técnica ni implementación. Las APIs y mecanismos de adjunto descritos como candidatos deben verificarse contra las versiones instaladas y su documentación oficial.

## 2. Alcance y decisiones

### MVP

- macOS, iTerm2 y Claude Code interactivo.
- Sesiones locales y remotas mediante SSH directo.
- Sesiones abiertas; no reanudar conversaciones históricas.
- Selección de región con la herramienta nativa de captura.
- Selector por proyecto, host y panel.
- Texto opcional antes del envío.
- Envío automático después de confirmar, únicamente si el destino está listo.
- Cancelación sin efectos sobre la terminal.
- Instalación de un auxiliar en los hosts remotos.

### Decisiones propuestas pendientes de aceptación

- Usar Hammerspoon para el atajo y la interfaz inicial.
- Requerir un wrapper `claude-shot` para registrar sesiones. El usuario todavía no ha confirmado este requisito; validar y aceptar esta limitación antes de cerrar el MVP.
- Atajo inicial configurable, por ejemplo `Cmd+Shift+7`, sujeto a conflictos del equipo.
- Una captura por envío; no soportar múltiples adjuntos inicialmente.

### Fuera de alcance

- Otras terminales, tmux, contenedores y Windows/Linux como cliente de escritorio.
- Descubrimiento garantizado de procesos Claude iniciados sin integración.
- Control mediante títulos de ventanas, OCR o coordenadas de pantalla.
- Inyección de mensajes mientras hay permisos, menús o texto pendiente.
- Servicio público, sincronización cloud o modificación de archivos internos de conversación de Claude.

## 3. Flujo de usuario

1. El usuario activa el atajo.
2. Se crea un archivo temporal privado y se abre la selección nativa de región.
3. Si cancela, se limpia el archivo y termina el flujo.
4. Se obtiene la lista de sesiones registradas y se actualiza su disponibilidad.
5. El selector muestra `proyecto · host · panel · estado`.
6. El usuario elige destino e introduce texto opcional.
7. Una confirmación explícita inicia el envío; no se requiere ir a la terminal ni pulsar Enter allí.
8. Se comprueba nuevamente el destino y se prepara el adjunto.
9. Para SSH, se transfiere la imagen y se comprueba la integridad antes de adjuntar.
10. Se envía una sola vez y se informa del resultado.

Sin sesiones disponibles: explicar cómo iniciar una. Sesión ocupada o estado desconocido: no modificarla; ofrecer reintentar o elegir otra. No mantener una cola automática en el MVP.

## 4. Arquitectura

### A. Frontend de escritorio

Hammerspoon, sujeto a una prueba de usabilidad:

- Atajo global.
- Lanzamiento de captura nativa con ruta explícita.
- Selector de sesiones y campo de texto.
- Notificaciones de éxito/error.
- Comunicación con el controlador mediante JSON por stdin/stdout, nunca concatenando texto del usuario en comandos de shell.

Validar permisos reales de captura, Accesibilidad y Automatización para los procesos implicados. Solicitar solo los necesarios.

### B. Controlador local

Propuesta: Python 3.11+ instalado en un entorno dedicado.

Responsabilidades:

- Registro y consulta de sesiones.
- Adaptador para la API oficial de iTerm2, cuya activación/configuración deberá verificarse.
- Orquestación de captura, transferencia, adjunto y envío.
- Exclusión mutua por sesión e identificación de cada operación.
- Limpieza, diagnóstico y errores estructurados.

No asumir que enumerar paneles permite conocer el estado interno de Claude. Esa capacidad requiere validación o integración adicional soportada.

### C. Wrapper de sesión

Comando propuesto: `claude-shot [argumentos de Claude]`.

- Genera un ID aleatorio de sesión y registra proyecto, host y asociación con el panel.
- Arranca Claude conservando el comportamiento interactivo, señales, tamaño de terminal y código de salida.
- Retira el registro al salir; recupera registros huérfanos tras cierres inesperados.
- Usa hooks oficiales solo si existen y aportan señales suficientes en la versión instalada.
- No implementar un proxy PTY salvo que sea indispensable y se evalúe por separado.

Si el wrapper hace `exec`, no puede ejecutar limpieza posterior: elegir explícitamente entre supervisión compatible con terminal o registro con expiración y validación externa.

### D. Auxiliar remoto

Instalado por usuario, sin root:

- Crea directorios temporales privados.
- Recibe capturas y confirma tamaño y hash.
- Registra y valida sesiones remotas.
- Limpia artefactos expirados.
- No escucha en puertos públicos ni acepta órdenes arbitrarias.

Para conectar el registro remoto con el controlador local, evaluar un canal explícito autenticado mediante SSH. No asumir que variables locales de iTerm2 atraviesan SSH ni que un PID remoto identifica un panel local.

## 5. Bloqueos técnicos y prueba de viabilidad

La implementación completa depende de superar estas pruebas. Cada una debe producir un script reproducible y notas con versiones utilizadas.

### P1 — Adjuntar una imagen real

Revisar documentación oficial y versión de Claude Code para encontrar un mecanismo soportado que adjunte una imagen a una conversación interactiva existente.

Probar, por orden:

1. Integración oficial, si existe, para el proceso interactivo activo.
2. Entrada soportada de adjuntos desde terminal, si puede automatizarse sin portapapeles.
3. Referencia explícita a un archivo que Claude pueda leer como imagen, únicamente si se verifica su funcionamiento y se acepta esta diferencia de UX.

Una ruta escrita por sí sola no demuestra que haya un adjunto. Usar una imagen de prueba con contenido visual único y comprobar que Claude puede interpretarlo. No confundir `claude -p` o una ejecución independiente con la conversación interactiva elegida.

**Criterio de salida:** adjunto o lectura visual confirmados en la sesión seleccionada, conservando su conversación. Si solo existe una alternativa con semántica diferente, documentarla y obtener aprobación antes de continuar.

### P2 — Selección inequívoca de panel

Demostrar enumeración de paneles y envío dirigido mediante la API de iTerm2, sin depender del foco. Manejar cierre y recreación del panel entre selección y envío.

### P3 — Estado seguro de entrada

Identificar señales fiables de prompt listo, ejecución en curso, permisos y texto pendiente. Evaluar hooks y otras interfaces oficiales; un hook de fin de respuesta no prueba por sí solo que el input esté vacío.

No usar una coincidencia visual del prompt como garantía. Si no puede comprobarse el estado, detener el diseño de envío inmediato y acordar una alternativa. Nunca enviar Enter a ciegas.

### P4 — Mapeo local ↔ SSH ↔ Claude remoto

Probar dos paneles conectados al mismo host y proyecto. El envío debe distinguirlos. Evaluar un lanzador explícito `claude-shot ssh <alias>`, que establece identidad y canal antes de arrancar el wrapper remoto. Esta variante puede requerir cambiar el flujo actual y necesita aprobación.

### P5 — Entrega remota

Transferir una imagen por SSH, verificar su hash y utilizar su ruta remota en el mecanismo validado en P1. Probar rutas con espacios y alias de `~/.ssh/config`.

**Gate de viabilidad:** si P1, P3 o P4 no se resuelven, no construir una UI que prometa envío seguro. Presentar limitaciones y decidir rediseño o reducción de alcance.

## 6. Interfaces y datos propuestos

CLI del controlador:

```text
claude-shot doctor
claude-shot sessions --json
claude-shot capture
claude-shot send --session <id> --image <path> [--text-file <path>]
claude-shot cleanup
claude-shot [argumentos de Claude]
claude-shot ssh <alias>  # solo si se adopta el lanzador SSH
```

Separar internamente comandos de control y argumentos de Claude para evitar ambigüedad; la sintaxis final se fija tras el spike.

Registro de sesión, versionado:

```json
{
  "schema_version": 1,
  "session_id": "uuid",
  "transport": "local",
  "host_label": "mac",
  "project_label": "frontend",
  "project_path": "/path/to/project",
  "iterm_session_id": "opaque-id",
  "remote_session_id": null,
  "started_at": "ISO-8601",
  "last_seen_at": "ISO-8601",
  "state": "unknown"
}
```

Los detalles de conexión SSH se conservan localmente en un perfil validado, no se ejecutan desde un registro remoto. Nunca incluir credenciales en estos archivos.

Estados de sesión: `ready`, `busy`, `blocked`, `unknown`, `closed`. Separar estado observado y antigüedad de la observación; evidencia vencida equivale a `unknown`.

Estados de operación: `captured → selected → preparing → transferring? → ready_to_submit → submitted → confirmed` o `cancelled/failed/uncertain`.

`submitted` significa que se emitió la acción de envío, no que Claude recibió o procesó el mensaje. Si no existe confirmación fiable, mostrar resultado incierto, no éxito garantizado.

## 7. Seguridad y fiabilidad

- Directorios privados `0700`, archivos `0600`, nombres aleatorios y escrituras atómicas.
- Límites configurables de tamaño y tiempo de transferencia; validar PNG real y no seguir enlaces simbólicos inesperados.
- Nunca registrar contenido de imágenes, prompts completos, secretos o argumentos sensibles.
- SSH con claves del usuario y verificación normal de host; nunca desactivar `StrictHostKeyChecking`.
- Respetar alias SSH. No reutilizar ciegamente argumentos arbitrarios tomados de procesos.
- Evitar interpolación de rutas/texto en shell, también en el extremo remoto. Usar un protocolo de entrada estructurado con operaciones permitidas.
- Bloqueo por sesión; revalidación justo antes de interactuar con la terminal.
- No borrar ni sustituir texto ya escrito en el prompt.
- Ningún reintento automático después de una entrega incierta: podría duplicar mensajes.
- Conservar el archivo mientras pueda necesitarlo el consumidor. Borrar tras confirmación segura de consumo; si no hay señal, usar retención configurable y advertir su limitación.
- Valor inicial propuesto: limpieza de capturas a las 24 horas, local y remota, ejecutada al arrancar y periódicamente donde sea viable. No prometer borrado puntual si el host está apagado.
- No usar el portapapeles; si el único mecanismo viable lo exige, pedir aprobación por el cambio de alcance.

## 8. Estructura propuesta del repositorio

```text
claude-shot/
  IMPLEMENTATION_PLAN.md
  README.md
  pyproject.toml
  src/claude_shot/
    cli.py
    controller.py
    registry.py
    models.py
    capture.py
    iterm_adapter.py
    claude_adapter.py
    ssh_transport.py
    remote_helper.py
    cleanup.py
  hammerspoon/claude_shot.lua
  scripts/install-local
  scripts/install-remote
  tests/unit/
  tests/integration/
  tests/manual/
  docs/spike-results.md
  docs/security.md
```

Preferir dependencias mínimas; fijar versiones después del spike. No instalar ni modificar configuración del usuario sin consentimiento y copia de respaldo.

## 9. Fases y entregables

### Fase 0 — Inventario y acuerdos

- Registrar macOS, iTerm2, Claude Code y Python, locales y remotos.
- Revisar documentación oficial de las APIs involucradas.
- Confirmar wrapper, eventual lanzador SSH y mecanismo de adjunto aceptable.
- Identificar hosts de prueba y políticas de autenticación.

**Entrega:** matriz de compatibilidad y decisiones aceptadas.

### Fase 1 — Spike de viabilidad

Ejecutar P1–P5, primero local y después SSH. No desarrollar todavía el selector definitivo.

**Entrega:** scripts reproducibles, evidencia y decisión go/no-go.

### Fase 2 — Núcleo local

Registro, integración con iTerm2, adjunto validado, control de estados, bloqueo y errores. CLI funcional sin interfaz gráfica.

**Entrega:** seleccionar una sesión por ID y enviar una imagen de prueba local de forma segura.

### Fase 3 — SSH

Auxiliar remoto, asociación inequívoca, transferencia verificada, limpieza y recuperación de desconexiones.

**Entrega:** envío a dos sesiones distintas en un mismo host, sin cruzar destinos.

### Fase 4 — Experiencia de escritorio

Atajo, captura, selector, texto opcional y notificaciones. Si Hammerspoon no ofrece una UX adecuada, evaluar una pequeña app nativa antes de añadir más herramientas.

**Entrega:** flujo completo sin copiar ni pegar.

### Fase 5 — Endurecimiento y distribución

Instalación/desinstalación, diagnóstico, pruebas de fallos, documentación y piloto de uso real.

**Entrega:** versión 0.1 y checklist de aceptación cumplida.

No fijar fechas hasta superar el spike; el mecanismo de adjunto y la detección de estado dominan la incertidumbre.

## 10. Pruebas

### Unitarias

- Esquema y expiración de registros, estados y bloqueo por sesión.
- Validación de rutas, nombres, texto Unicode y contenido malicioso.
- Transferencias parciales, hash incorrecto y errores estructurados.
- Limpieza segura y estados inciertos sin reintento.

### Integración

- Dos paneles locales con el mismo proyecto.
- Dos paneles SSH al mismo host y proyecto.
- Host con alias y puerto personalizado.
- Cierre de panel después de seleccionarlo.
- Registro huérfano, PID reutilizado y desconexión SSH.
- Doble activación del atajo y concurrencia de envíos.

### Manuales en macOS

- Captura cancelada, permisos denegados y múltiples monitores.
- Escalado Retina y nombres/rutas con espacios.
- Texto opcional vacío, multilínea y Unicode.
- Claude ocupado, diálogo de permisos y prompt con texto pendiente.
- Imagen realmente interpretada por la conversación correcta.
- Inspección de archivos temporales locales/remotos y logs sin contenido sensible.

Las pruebas automatizadas pueden simular adaptadores, pero no sustituyen la validación real con iTerm2 y Claude.

## 11. Criterios de aceptación de la versión 0.1

- [ ] Atajo configurable y captura de región funcional.
- [ ] Lista únicamente sesiones registradas vigentes; no presenta registros obsoletos como disponibles.
- [ ] Identifica claramente proyecto y host, incluso con sesiones similares.
- [ ] Admite texto opcional y envía sin copiar/pegar ni Enter manual en la terminal.
- [ ] La imagen es accesible e interpretada en la conversación seleccionada, local y remota.
- [ ] No toca sesiones con estado inseguro o desconocido.
- [ ] No sobrescribe texto ni responde a permisos accidentalmente.
- [ ] Cancelar no genera mensajes ni deja artefactos innecesarios.
- [ ] Distingue enviado, confirmado e incierto; no duplica envíos mediante reintentos automáticos.
- [ ] Documenta retención y limpieza de capturas.
- [ ] Incluye instalación, desinstalación, diagnóstico y limitaciones conocidas.

## 12. Primera tarea ejecutable

En el Mac de destino, con consentimiento del usuario, recopilar versiones y preparar una sesión local de prueba y una SSH. Después implementar únicamente P1: demostrar una entrega visual real a una conversación interactiva existente. Su resultado determina el adaptador y si el resto del plan es viable sin cambiar la experiencia acordada.
