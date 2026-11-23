# Solución de problemas

Empieza por el panel: cada tarjeta de televisor indica si está encendido, no se alcanza o **Hay que volver a emparejar**.
**Actividad** muestra los últimos eventos, como problemas de conexión, con palabras sencillas.

## No se encuentra el televisor
- Comprueba que el televisor está encendido y en la misma red que TVBalance, no en una red de invitados.
- Algunos routers bloquean los mensajes de descubrimiento entre dispositivos. Elige la marca en *Escribir la dirección*
  en el asistente y escribe la dirección IP del televisor, que encuentras en sus ajustes de red.
- Con Docker en Windows o macOS, el descubrimiento no puede funcionar porque el contenedor está tras una red virtual.
  Escribe la dirección a mano. Consulta [Instalar](install.md).
- Dale al televisor una dirección fija en tu router (una reserva DHCP) para que la dirección escrita siga siendo válida.
- Para televisores LG, revisa los ajustes en [LG webOS](tv-lg-webos.md).

## El emparejamiento no termina
- Ten a mano el mando a distancia y acepta la solicitud en el televisor en tres minutos. El televisor solo la muestra
  mientras está encendido.
- Si pulsaste **No**, o no pasó nada, usa **Reintentar** en el asistente.
- Asegúrate de que el televisor no muestra otro aviso a pantalla completa ni un salvapantallas.

## La tarjeta dice «Hay que volver a emparejar»
El televisor olvidó la clave que guarda TVBalance, por ejemplo tras un restablecimiento de fábrica o una actualización de
software. Abre **Emparejar de nuevo** en la tarjeta y acepta la solicitud en el televisor otra vez. Las reglas, el
historial y los ajustes se conservan. Con Web Push activado, también recibes una notificación cuando ocurre.

## El televisor está «no alcanzable»
TVBalance no puede conectar con el televisor, lo cual es normal si está desenchufado. Si ocurre con el televisor
encendido:

- Comprueba la dirección del televisor en tu router. Si cambió, quita el televisor y vuelve a añadirlo con su nueva
  dirección, o dale una dirección fija.
- Comprueba que las funciones de red del televisor siguen activadas (para LG, consulta [LG webOS](tv-lg-webos.md)).
- Reinicia el televisor por completo (desenchúfalo un minuto). Algunos televisores dejan de responder tras mucho tiempo
  encendidos.

## Una regla parece no aplicarse
- Comprueba que el televisor tiene la vigilancia activada (página de detalles del televisor) y que sigue el conjunto de
  reglas que editaste.
- En televisores LG con **Quick Start+**, un televisor con la pantalla apagada notifica espera, así que el presupuesto
  diario no corre. Es lo esperado. Consulta los límites en [LG webOS](tv-lg-webos.md).
- Un **Permitir** o **Bloquear** manual se impone a las reglas hasta que termina. Usa **Quitar el forzado** en la
  tarjeta.
- Los perfiles, el calendario y los presupuestos avanzados se guardan en todos los planes pero solo se aplican con
  [Pro](pro.md). Las pantallas lo indican.
- Los horarios siguen la zona horaria elegida en la configuración, no el reloj del televisor. Compruébala en **Ajustes →
  General**.

## El navegador avisa de que la conexión no es privada
La dirección segura usa un certificado de una pequeña autoridad que creó TVBalance. Tu dispositivo debe confiar en ella
una vez. Sigue [HTTPS en tu red](https.md): descarga el certificado en **Ajustes → Conexión segura**, instálalo y compara
la huella. Firefox tiene su propia lista, así que impórtalo también allí.

## No llegan notificaciones al móvil
Los navegadores solo permiten notificaciones push en una conexión segura.

- Abre la aplicación web a través de Home Assistant por HTTPS, o a través de la dirección segura de TVBalance, no por una
  dirección `http://` simple. La tarjeta de **Ajustes → Notificaciones** enlaza a la dirección segura cuando existe.
- En iPhone y iPad, añade primero TVBalance a la pantalla de inicio y activa las notificaciones desde ese icono.
- Envía una prueba desde la misma tarjeta. Si no llega, permite las notificaciones del sitio o de la aplicación en los
  ajustes del móvil.

## Home Assistant no encuentra TVBalance
- Con el complemento, reinícialo y busca la notificación **TVBalance** en **Ajustes → Dispositivos y servicios**.
- Si revocaste el token «Home Assistant (Add-on)» en **Ajustes → Tokens de API**, reinicia el complemento: crea uno
  nuevo.
- Con un motor independiente, comprueba la dirección, el puerto y que el token tiene los ámbitos **lectura** y
  **control**. Consulta [Home Assistant](home-assistant.md).

## Se rechaza un PIN
Tras cinco PIN incorrectos, el inicio de sesión con PIN se bloquea un rato. Espera, o inicia sesión con la contraseña de
administrador y cambia el PIN en **Ajustes → Seguridad**.

## Contraseña de administrador olvidada
TVBalance aún no tiene restablecimiento de contraseña, porque nada se envía fuera de tu casa. Si algún navegador sigue
con la sesión iniciada, puedes cambiar la contraseña en **Ajustes → Seguridad**. Si no, lo único posible hoy es empezar
con una carpeta de datos vacía: se pierden las reglas, el historial y las claves guardadas de los televisores, y hay que
emparejar de nuevo cada televisor. Restaura una copia de seguridad hecha antes de perder la contraseña, si la tienes.

## Sigue sin funcionar
Abre una incidencia en <https://github.com/tvbalance/tvbalance/issues> y adjunta la descarga de diagnóstico. No
publiques tokens, claves de licencia ni el contenido de la carpeta de datos.
