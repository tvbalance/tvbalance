# Home Assistant

TVBalance incluye su propia integración, que muestra cada televisor como un dispositivo en Home Assistant, te envía
eventos y permite a las automatizaciones conceder o retirar tiempo de televisión.

## Configuración

### Con el complemento (recomendado)

Instala el complemento TVBalance y arráncalo. Home Assistant muestra una notificación **TVBalance** en **Ajustes →
Dispositivos y servicios**: elige **Configurar** y confirma. El complemento crea y conserva el token de API por ti; si lo
revocas, reinicia el complemento y Home Assistant adopta el nuevo.

### Con un motor independiente

1. En la aplicación web de TVBalance, abre **Ajustes → Tokens de API** y crea un token con los ámbitos **lectura** y
   **control**. Añade **admin** solo si quieres el servicio `tvbalance.set_monitoring`. El secreto se muestra una sola
   vez.
2. Instala la integración con HACS (añade `https://github.com/tvbalance/tvbalance-ha` como repositorio personalizado,
   categoría Integración) o copia `custom_components/tvbalance` en la carpeta `config/custom_components` de Home
   Assistant. Reinicia Home Assistant.
3. **Ajustes → Dispositivos y servicios → Añadir integración → TVBalance**. Escribe la dirección del motor y el token.

Para HTTPS, escribe una dirección `https://` (puerto 8766 por defecto). Si el certificado aún no es de confianza, la
configuración muestra la huella de la autoridad local del motor: compárala con **Ajustes → Conexión segura** en la
aplicación web de TVBalance y confirma. Home Assistant acepta entonces solo esa autoridad para este motor. Si cambia (se
creó un certificado nuevo), Home Assistant pide confirmar de nuevo. Consulta https.md.

Si el token se revoca o caduca, Home Assistant pide uno nuevo (aparece una reparación; elige **Reconfigurar**). No hay
que rehacer nada más.

## Qué obtienes por cada televisor

| Entidad | Significado |
| --- | --- |
| Estado (sensor) | `watching`, `standby`, `off`, `unreachable`, `needs_pairing` o `not_monitored` |
| Aplicación, Programa (sensores) | Lo que hay en pantalla. También hay entrada y canal, desactivados por defecto |
| Perfil (sensor) | El nombre del perfil que se aplica a este televisor, desconocido si no hay ninguno |
| Visto hoy, Tiempo restante (sensores) | Minutos; Tiempo restante es desconocido si el televisor no tiene presupuesto diario |
| Bloqueado (sensor binario) | Activo mientras la aplicación de las reglas bloquea el televisor; el atributo `reason` da el motivo |
| Conectado, Volver a emparejar (sensores binarios) | Estado de la conexión |
| Pausa (botón) | Detiene la aplicación de las reglas durante 30 minutos. Seguro para cualquiera |
| Actividad (entidad de evento) | Se dispara con cada evento de TVBalance |

El motor emite los cambios en directo, así que los estados se actualizan en menos de un segundo. Si el flujo se corta,
Home Assistant se reconecta solo y sigue consultando cada 30 segundos.

## Servicios (solo administradores)

Todo lo que da más tiempo de televisión o cambia la aplicación de las reglas está limitado a los administradores de Home
Assistant, para que un niño ante un panel no pueda llamarlo. Las automatizaciones y los scripts sí pueden. Cada servicio
recibe un `device_id` (el televisor).

| Servicio | Campos |
| --- | --- |
| `tvbalance.bonus` | `minutes` (1–240) |
| `tvbalance.allow` | `minutes` (1–1440) o `until_midnight` |
| `tvbalance.block` | `minutes` (1–1440) o `until_midnight` |
| `tvbalance.pause` | `minutes` (1–1440) |
| `tvbalance.clear_override` | ninguno |
| `tvbalance.set_monitoring` | `enabled`; necesita un token con el ámbito admin |

Los servicios de perfil afectan a todo el hogar, no a un televisor, y requieren el plan Pro:

| Servicio | Campos |
| --- | --- |
| `tvbalance.activate_profile` | `policy_id`, `minutes` (1–1440) o `until_midnight`, `excluded_device_ids` opcional |
| `tvbalance.stop_profile` | ninguno |

`allow`, `block` y `activate_profile` necesitan exactamente uno de `minutes` o `until_midnight`. Un PIN nunca forma parte
de una llamada a un servicio.

## Eventos

Cada evento del motor se dispara también como `tvbalance_event` en el bus de Home Assistant, con `device_id`, `tv_id`,
`type` y `payload`. Tipos: `time_warning` (`minutes_left`, `limit`), `blocked` (`reason`), `redirected` (`action`),
`powered_off`, `enforcement_paused`, `enforcement_unavailable` (`reason`), `tv_unreachable`, `tv_reachable`,
`pairing_lost`, `tv_paired`, `profile_started` (`name`, `until`, `source`), `profile_ended` (`name`), `weekly_report`
(`first`, `last`, `total_seconds`, `blocks`, `top`).

## Blueprints

Están en `blueprints/automation/tvbalance/`; cópialos a `config/blueprints/automation/tvbalance/`.

- **warning_light**: hace parpadear una luz cuando a un televisor le quedan N minutos o menos.
- **notify_parent**: envía una notificación para los eventos elegidos.
- **button_bonus**: concede minutos de bonus cuando se pulsa un botón físico.
- **calendar_profile**: activa un conjunto de reglas para el hogar mientras dura un evento del calendario de Home
  Assistant, y lo desactiva cuando termina (Pro).
