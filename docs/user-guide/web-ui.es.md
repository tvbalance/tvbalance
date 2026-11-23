# La aplicación web

La aplicación web de TVBalance funciona en cualquier navegador de tu red doméstica, y dentro de Home Assistant como panel
lateral. Se usa cómodamente en el móvil y se puede añadir a la pantalla de inicio como una aplicación. Habla inglés,
italiano, alemán, francés y español.

## Primer arranque
En la primera visita, la aplicación te pide tres cosas:
1. **Una contraseña** para el administrador (mínimo 10 caracteres). Guárdala en un lugar seguro; abre todo.
2. **Idioma y zona horaria.** Los horarios y los límites diarios siguen esa zona.
3. **Un primer conjunto de reglas**, a partir de «Días de colegio» (entre semana 16:00–20:00, fines de semana
   09:00–21:00, dos horas al día, avisos a los 10 y 5 minutos) o de uno vacío. Todo se puede cambiar después.

## Añadir un televisor
Mientras no haya ningún televisor, el panel ofrece **Añadir televisor** (solo para administradores; una sesión con PIN
nunca lo ve). El asistente explora tu red o acepta la dirección del televisor escrita a mano, te guía para aceptar la
conexión en el televisor y termina con el nombre del televisor y la elección de su conjunto de reglas. Un televisor que
ha perdido su clave muestra **Hay que volver a emparejar** con un enlace **Emparejar de nuevo**. Los pasos de cada marca
están en las guías de los televisores, por ejemplo [LG webOS](tv-lg-webos.md).

## Iniciar sesión
- **Contraseña:** acceso completo.
- **PIN:** un código corto opcional para un dispositivo compartido, como una tableta en la cocina. Una sesión con PIN
  puede ver el panel y usar los controles parentales, pero no puede cambiar reglas, contraseñas ni tokens. Tras cinco
  PIN incorrectos, se bloquea durante un rato.
- Dentro de Home Assistant ya has iniciado sesión a través de Home Assistant.

## Panel
Una tarjeta por televisor indica si está encendido, qué se está viendo, cuántos minutos se han visto y cuántos quedan, y
si el contenido actual está permitido. La tarjeta se actualiza sola.

Controles parentales en cada tarjeta:
- **Pausa** detiene la aplicación de las reglas durante 30 minutos.
- **Bonus** añade 15 o 30 minutos al presupuesto de hoy.
- **Permitir** o **Bloquear** se impone a las reglas durante 15, 30, 60 o 120 minutos, o hasta medianoche.
- **Quitar el forzado** vuelve a las reglas.

## Reglas
Un conjunto de reglas define cuándo y durante cuánto tiempo se puede usar un televisor. Varios televisores pueden
compartir un conjunto, y cada televisor sigue uno. Abre **Reglas**, elige un conjunto (o crea uno) y edítalo en cuatro
pestañas:

- **Horarios:** las franjas de cada día de la semana. Añade todas las franjas que necesites, copia un día a otros y añade
  días especiales para una fecha concreta, como un festivo. Una franja que termina antes de empezar pasa de
  medianoche.
- **Duración:** un presupuesto diario opcional en minutos y los avisos que aparecen cuando quedan esos minutos. Con Pro
  también puedes fijar un presupuesto para cada día de la semana, cuotas compartidas para grupos de aplicaciones y
  trasladar al día siguiente el tiempo no usado. Consulta [TVBalance Pro](pro.md).
- **Contenidos:** las aplicaciones, entradas y canales que se bloquean; un modo «Permitir solo las aplicaciones
  elegidas»; lo que siempre está permitido; y adónde va el televisor cuando algo se bloquea (inicio, una aplicación, una
  entrada o un canal). Elige los elementos de la lista leída del televisor, con los iconos de las aplicaciones. Si el
  televisor está apagado o no se alcanza, escribe los identificadores a mano.
- **Avanzado:** con qué rigor se aplican los bloqueos. Los valores por defecto sirven para casi todos.

### Perfiles y calendario (Pro)
*Activar como perfil* en un conjunto de reglas lo aplica a todos los televisores del hogar durante el tiempo elegido,
salvo los que marques. El panel muestra el perfil activo y te deja detenerlo; cada tarjeta de televisor muestra su
nombre. **Reglas > Calendario** lista las entradas que activan conjuntos de reglas automáticamente, cada semana o entre
dos fechas. Consulta [TVBalance Pro](pro.md).

Si un conjunto de reglas no se puede guardar, un mensaje señala el problema, por ejemplo un destino alternativo que está
bloqueado, un aviso más largo que el presupuesto o dos franjas que se solapan.

## Detalles del televisor y actividad
En el panel, elige el nombre de un televisor para renombrarlo, activar o desactivar la vigilancia, cambiar su conjunto de
reglas, ver los últimos siete días en barras y leer sus eventos más recientes. Quitar un televisor pide confirmación.

**Actividad** muestra lo mismo para todos los televisores, con un filtro y el registro completo de eventos: avisos,
bloqueos, apagados y problemas de conexión. Con Pro eliges un periodo más largo (hasta un año), ves las aplicaciones más
vistas y lees el informe de la semana pasada. Consulta [TVBalance Pro](pro.md).

Cambiar reglas, televisores y ajustes requiere la contraseña de administrador.

Si abres la aplicación web con una dirección `http://` simple y el motor ofrece HTTPS, un aviso sugiere la dirección
segura. Puedes cerrarlo; la elección se recuerda en ese navegador.

## Ajustes
- **General:** idioma, zona horaria y tema claro u oscuro.
- **Notificaciones:** recibes en este dispositivo una notificación push cuando hay que volver a emparejar el televisor,
  no se alcanza, se ha bloqueado un contenido o el tiempo está a punto de acabarse. Elige cuáles quieres, envía una
  prueba, desactívalas y quita otros dispositivos. Solo el administrador ve esta tarjeta. Los navegadores solo permiten
  push en una conexión segura, así que funciona a través de Home Assistant por HTTPS (Ingress), desde `localhost` o
  desde la dirección segura de tu red (consulta https.md), no desde una dirección `http://` simple. La tarjeta enlaza a
  la dirección segura cuando existe. En iPhone y iPad, añade primero TVBalance a la pantalla de inicio.
- **TVBalance Pro:** el plan actual, para quién es la licencia y cuándo caduca, un campo para pegar una clave de licencia
  y un botón para quitarla. Solo el administrador ve esta tarjeta. Consulta pro.md.
- **Conexión segura:** las direcciones HTTPS, la caducidad y la huella del certificado, las descargas del certificado y
  del perfil para iPhone y iPad, los pasos de instalación por dispositivo y un botón para crear un certificado nuevo.
  Solo el administrador ve esta tarjeta. Consulta https.md.
- **Seguridad:** cambiar la contraseña; definir o quitar el PIN parental.
- **Dispositivos con sesión:** ver cada navegador con sesión iniciada y cerrar la de uno o la de todos menos este.
- **Tokens de API:** para otros programas. El secreto de un token se muestra una sola vez al crearlo, así que cópialo de
  inmediato. Elige **lectura** y **control** para Home Assistant (consulta home-assistant.md). Un token se puede revocar
  en cualquier momento.

**Sistema** muestra la versión y las marcas de televisor que admite esta versión, con su nivel de madurez.
