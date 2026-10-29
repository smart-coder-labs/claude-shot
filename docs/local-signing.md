# Firma local estable y permiso de captura en macOS

## Por qué Ajustes puede mostrar permiso y la app volver a pedirlo

La firma ad-hoc identifica una compilación por su hash. Al cambiar el ejecutable, cambia su requisito de identidad y puede dejar de coincidir con una autorización anterior, aunque Ajustes siga mostrando el mismo nombre de app. No es la única causa posible: también pueden influir otra copia instalada, una instancia antigua o la atribución del proceso auxiliar.

El aviso «audio y pantalla» corresponde a la categoría de privacidad de macOS. Claude Shot utiliza `screencapture` para generar PNG, no implementa grabación de audio ni vídeo. No hace falta habilitar Accesibilidad para registrar el atajo Carbon.

Una firma con certificado estable evita que cada compilación tenga una identidad designada distinta. **No concede permiso de captura**, no evita los diálogos de macOS y no demuestra que el permiso actual funcione. Al migrar desde ad-hoc puede ser necesario autorizar una vez la identidad nueva.

## Configuración opcional y explícita

Por defecto, un checkout nuevo y CI siguen usando firma ad-hoc. `build-app` **nunca crea certificados, modifica confianza, instala claves ni resetea TCC**.

Para configurar firma estable:

1. Disponer en el llavero de usuario de una identidad de firma de código válida. Para desarrollo local se puede crear un certificado autofirmado de tipo **Code Signing** mediante el asistente de Acceso a Llaveros. Cualquier instalación de certificado/cambio de confianza debe ser una acción explícita del propietario; limitar la confianza a firma de código, no a SSL ni a todos los usos. No se necesita un certificado Developer ID para esta prueba local; un certificado autofirmado **no sirve como distribución confiable/notarizada**.
2. Consultar las identidades válidas, sin exportar claves:

   ```sh
   security find-identity -v -p codesigning
   ```

3. Copiar la huella completa de 40 caracteres hexadecimales del certificado elegido y configurar este checkout:

   ```sh
   .venv/bin/python -B scripts/sign-app.py \
     --configure 'REEMPLAZAR_POR_LA_HUELLA_DE_40_HEX' \
     --keychain "$HOME/Library/Keychains/login.keychain-db"
   ./scripts/build-app
   ```

La huella SHA-1 es el identificador que acepta `codesign`, no el algoritmo usado para firmar el código. Se guarda junto a la ruta del llavero en `.local-signing/identity.json`: directorio 0700 y archivo 0600, ignorados por Git. El helper no lee ni exporta el contenido de la clave privada.

Las siguientes compilaciones reutilizan esa identidad automáticamente. Si está configurada pero caducada, ausente o no es válida, el build falla antes de sobrescribir el ejecutable; **no cambia silenciosamente a ad-hoc**. Un rechazo de acceso a la clave durante la firma también hace fallar el build. `--timestamp=none` evita solicitar sellado de tiempo externo: esta firma es solo local.

Comprobar sin firmar ni modificar el llavero:

```sh
.venv/bin/python -B scripts/sign-app.py --check
codesign -dr - 'build/Claude Shot.app'
codesign --verify --deep --strict 'build/Claude Shot.app'
```

Con certificado, el requisito designado debe contener el identificador del bundle y una referencia al certificado, no únicamente `cdhash`. Conservar el mismo certificado/clave entre builds. Cambiar el nombre del certificado o recrearlo no conserva la identidad; no borrarlo ni regenerarlo para cada compilación.

## Aplicar la nueva identidad y comprobar captura

1. Salir de la app desde su menú; no cerrar por fuerza una captura o envío pendiente.
2. Abrir la compilación firmada en su ubicación habitual:

   ```sh
   open 'build/Claude Shot.app'
   ```

3. Probar ⌘⌃7 y decidir manualmente si se concede el permiso solicitado. Si la entrada de Ajustes sigue apuntando a una identidad anterior, el propietario puede eliminar **solo Claude Shot** y añadir la copia actual. No resetear permisos de otras apps ni ejecutar reseteos generales de TCC.
4. Cerrar/abrir y probar otra vez; posteriormente recompilar con el mismo certificado y repetir. Estas son pruebas reales pendientes, no consecuencia garantizada de verificar la firma.

No conceder permisos adicionales a Python, iTerm2 o Accesibilidad sin diagnosticar a qué proceso atribuye macOS la solicitud. Si el aviso persiste, registrar texto, copia/ruta de app, hora del proceso y requisito de firma antes de cambiar nada más.

## Evidencia local del cambio

Con autorización expresa del propietario, se instaló una identidad local autofirmada RSA-3072/SHA-256, con uso de clave `digitalSignature`, uso extendido `codeSigning` y confianza de usuario restringida a `codeSign`. La clave se importó como no extraíble, con acceso autorizado a `/usr/bin/codesign`, no a cualquier aplicación. Los archivos temporales de clave se eliminaron tras importarla; la clave queda en el llavero. Certificado público/configuración local están excluidos del repositorio.

La app se firmó y pasó verificación estricta. Se firmaron dos ejecutables de prueba diferentes, **sin ejecutarlos**: hashes de código distintos y el mismo requisito designado que Claude Shot. Esto demuestra estabilidad de identidad frente a cambios del binario, **no autorización TCC ni captura real**. No se tomaron capturas, no se enviaron mensajes a Claude, no se reseteó TCC ni se reinició por fuerza la app durante esta comprobación.

## Deshacer sin cambios implícitos

Eliminar o renombrar `.local-signing/identity.json` vuelve al modo ad-hoc en la próxima compilación, cambiando la identidad y posiblemente sus permisos. Esto **no elimina el certificado, la clave ni su confianza del llavero**. Su retirada debe hacerse explícitamente desde Acceso a Llaveros sobre esta identidad concreta, no borrando otras identidades. El repositorio no incluye un desinstalador que modifique el llavero automáticamente.
