# Instalar TVBalance

TVBalance funciona en un pequeño ordenador siempre encendido en tu casa: el equipo que ejecuta Home Assistant, un NAS o
una Raspberry Pi. Debe estar en la misma red que tu televisor. Elige una de las dos vías siguientes.

## Como complemento de Home Assistant (recomendado)

Funciona con Home Assistant OS y con instalaciones Supervised, en amd64 y aarch64.

1. En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios**.
2. Añade `https://github.com/tvbalance/tvbalance`.
3. Instala **TVBalance**, arráncalo y abre el panel **TVBalance** de la barra lateral.
4. Sigue la configuración en pantalla. Consulta [Primeros pasos](getting-started.md).

Al arrancar, el complemento se anuncia a Home Assistant. En **Ajustes → Dispositivos y servicios** aparece una
notificación **TVBalance**: elige **Configurar** y confirma. No hace falta escribir dirección ni token. Más detalles en
[Home Assistant](home-assistant.md).

El complemento usa la red del anfitrión para poder encontrar y despertar los televisores. Todos los datos están en la
carpeta `/data` del complemento y forman parte de las copias de seguridad de Home Assistant.

## Con Docker

Una única imagen multiarquitectura (amd64 y arm64) cubre todo lo demás:

```
docker run -d --name tvbalance --restart unless-stopped \
  --network host \
  -v tvbalance-data:/data \
  ghcr.io/tvbalance/tvbalance:latest
```

Después abre `http://<dirección-del-equipo>:8765` en un navegador.

- **Red del anfitrión.** La búsqueda de televisores y Wake-on-LAN la necesitan, y así solo funciona en Linux. Con Docker
  Desktop (Windows y macOS) usa en su lugar `-p 8765:8765 -p 8766:8766` y añade tu televisor por su dirección, porque no
  se puede encontrar automáticamente.
- **El volumen de datos.** `/data` contiene `tvbalance.db` (tus televisores, reglas, historial de uso y eventos) y
  `secret.key` (la clave que protege las credenciales guardadas de los televisores). Guarda ambos juntos y haz copia de
  ambos juntos. Si pierdes la clave, los datos se conservan, pero hay que emparejar de nuevo cada televisor.
- **Actualizaciones.** Descarga la nueva imagen y vuelve a crear el contenedor. La base de datos se actualiza al
  arrancar.

### Ajustes

El motor lee sus ajustes de variables de entorno. Los valores por defecto sirven para la mayoría de los hogares.

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `TVBALANCE_DATA_DIR` | `/data` | Dónde están la base de datos y la clave |
| `TVBALANCE_PORT` | `8765` | Puerto HTTP |
| `TVBALANCE_HTTPS_PORT` | `8766` | Puerto HTTPS |
| `TVBALANCE_TLS` | `auto` | `auto` para la autoridad local integrada, `off` para desactivar HTTPS |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | sin definir | Tu propio certificado y tu clave (definir ambos) |
| `TVBALANCE_TLS_NAMES` | sin definir | Nombres locales adicionales para el certificado automático |

HTTPS se explica en [HTTPS en tu red](https.md).

### Home Assistant con un motor independiente

Crea un token de API en la aplicación web e instala la integración con HACS. Los pasos están en
[Home Assistant](home-assistant.md).

## Los puertos de un vistazo

| Puerto | Protocolo | Se usa para |
| --- | --- | --- |
| 8765 | HTTP | La aplicación web, el Ingress de Home Assistant, la comprobación de estado |
| 8766 | HTTPS | La aplicación web y la API en tu red |

## Siguiente paso

Abre la aplicación web y sigue [Primeros pasos](getting-started.md). Si algo no funciona, consulta la
[Solución de problemas](troubleshooting.md).
