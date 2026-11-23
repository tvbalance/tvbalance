# HTTPS en tu red

TVBalance puede responder por HTTPS en tu red doméstica. Los navegadores tratan entonces la aplicación web como segura:
las notificaciones Web Push funcionan, la cookie de sesión se marca como `Secure` y tu contraseña deja de enviarse en
claro.

HTTPS está activado por defecto. El motor escucha en dos puertos:

| Puerto | Protocolo | Se usa para |
| ------ | --------- | ----------- |
| 8765 | HTTP | El Ingress de Home Assistant, la comprobación de estado, el descubrimiento del complemento y un primer vistazo desde el navegador |
| 8766 | HTTPS | La aplicación web y la API en tu red |

HTTP queda abierto a propósito. Cuando abres la aplicación web por `http://`, un aviso ofrece la dirección segura, y la
tarjeta Notificaciones enlaza a ella.

## El certificado

Una dirección web de tu propia red (`tvbalance.local`, `10.x.x.x`) no puede obtener un certificado de una autoridad
pública. Por eso TVBalance crea una pequeña **autoridad de certificación local** (CA) la primera vez que arranca y firma
con ella su propio certificado de servidor. El certificado de servidor dura 397 días y se renueva solo 30 días antes de
caducar, sin reiniciar. También cambia cuando cambian el nombre o la dirección del motor.

Tus dispositivos deben confiar en la CA una vez. Hasta entonces, el navegador avisa de que la conexión no es privada.

### Instalar la CA en un dispositivo

Abre **Ajustes → Conexión segura** en la aplicación web. Lista las direcciones seguras, la caducidad del certificado y su
**huella**, y ofrece dos descargas: el certificado (`.crt`) y un perfil para iPhone y iPad.

Compara la huella que muestra el dispositivo con la de Ajustes antes de confiar.

- **iPhone y iPad:** abre el perfil, permítelo en Ajustes, instálalo y actívalo en Ajustes → General → Información →
  Ajustes de confianza de certificados.
- **Android:** Ajustes → busca «certificado de CA» → Instalar de todos modos → elige el archivo descargado.
- **Windows:** abre el archivo → Instalar certificado → Equipo local → Entidades de certificación raíz de confianza.
- **macOS:** abre el archivo en Acceso a Llaveros y pon la confianza en Confiar siempre.

En Windows y Linux, algunos navegadores tienen su propia lista de autoridades (Firefox la tiene): importa también el
archivo allí.

### Empezar de cero con una CA nueva

**Crear un certificado nuevo** en la misma tarjeta genera una CA nueva y un certificado de servidor nuevo. Úsalo si se
pierde un dispositivo que confiaba en la CA anterior o sospechas que se filtró la clave de la CA. Todos los dispositivos
deben instalar entonces la nueva CA, y la integración de Home Assistant te pide confirmar la nueva huella.

## Tu propio certificado

Si ya tienes un certificado en el que confían tus dispositivos (por ejemplo uno hecho para Home Assistant), indícaselo a
TVBalance en su lugar:

- Motor independiente: define `TVBALANCE_TLS_CERTFILE` y `TVBALANCE_TLS_KEYFILE` con la cadena de certificados y la clave
  privada, ambos archivos PEM.
- Complemento de Home Assistant: coloca los archivos en la carpeta `/ssl` y rellena **Archivo de certificado** y
  **Archivo de clave** en las opciones del complemento (por ejemplo `fullchain.pem` y `privkey.pem`).

El motor comprueba que la clave coincide con el certificado y que no ha caducado. Ajustes → Conexión segura muestra
entonces solo el estado, porque la renovación es cosa tuya. Reinicia el motor después de sustituir los archivos.

## Ajustes

| Variable de entorno | Opción del complemento | Significado |
| ------------------- | ---------------------- | ----------- |
| `TVBALANCE_TLS` | HTTPS | `auto` (por defecto) u `off` |
| `TVBALANCE_HTTPS_PORT` | | Puerto de HTTPS, 8766 por defecto (debe diferir de `TVBALANCE_PORT`) |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | Archivo de certificado, Archivo de clave | Tu propio certificado |
| `TVBALANCE_TLS_NAMES` | Nombres adicionales | Más nombres de host o direcciones para el certificado automático, separados por comas |

Las variables de entorno prevalecen sobre las opciones del complemento.

El certificado automático cubre `localhost`, el nombre de host del equipo y su nombre `.local`, y su dirección IPv4
privada. Los nombres que no son locales se dejan fuera, y Ajustes te dice cuáles.

Si el puerto HTTPS está ocupado, el motor registra un error y sigue sirviendo HTTP.

## Home Assistant

Por HTTP dentro del complemento no cambia nada. Para conectar la integración por HTTPS, escribe una dirección `https://`
y el token de API. Cuando el certificado del motor no es de confianza, la integración descarga la CA, muestra su huella
y te pide compararla con Ajustes → Conexión segura. Tras confirmar, Home Assistant acepta solo esa CA para este motor.
Si la CA cambia más adelante, una reautenticación pide confirmar de nuevo.

## Notas de seguridad

- **Qué puede firmar la CA.** La CA lleva restricciones de nombre X.509: solo puede emitir certificados para
  `localhost`, `.local`, `.lan`, `.home.arpa`, `.internal` y rangos de direcciones privadas. Un dispositivo que confía en
  ella no queda expuesto a un certificado falso de un sitio público, siempre que el cliente aplique las restricciones de
  nombre (los navegadores y sistemas actuales lo hacen).
- **Dónde está la clave.** La clave de la CA se guarda sellada junto con los demás secretos del motor (`secret.key`), y
  la clave del servidor es un archivo con permisos solo para el propietario en la carpeta de datos. Quien pueda leer la
  carpeta de datos puede emitir certificados para nombres locales; protégela como el resto de tus copias de seguridad.
- **La descarga es pública.** El certificado de la CA (nunca su clave) se puede descargar sin iniciar sesión, porque un
  dispositivo nuevo lo necesita antes de poder confiar en nada. Confirma siempre la huella: es la comprobación de que el
  archivo viene de tu motor.
- **HTTP sigue disponible.** Inicia sesión por HTTPS en redes compartidas. El aviso está para recordártelo.
