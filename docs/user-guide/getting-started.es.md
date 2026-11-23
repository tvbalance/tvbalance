# Primeros pasos

Desde una instalación nueva hasta un televisor que sigue tus reglas pasan unos cinco minutos. Necesitas TVBalance
[instalado](install.md) y el televisor encendido, en la misma red.

## 1. Abrir la aplicación web
Abre el panel **TVBalance** en Home Assistant, o `http://<dirección-del-equipo>:8765` si usas Docker. La primera visita
inicia la configuración.

## 2. Configurar el hogar
La aplicación te pide tres cosas:

1. **Una contraseña** para el administrador, de al menos 10 caracteres. Guárdala en un lugar seguro.
2. **Idioma y zona horaria.** Los horarios y los límites diarios siguen esa zona.
3. **Un primer conjunto de reglas.** Empieza con «Días de colegio» o con uno vacío. Todo se puede cambiar después.

## 3. Añadir tu televisor
Elige **Añadir televisor**. El asistente explora tu red y lista los televisores que encuentra. Si el tuyo no aparece,
escribe su dirección a mano. Sigue los pasos de tu marca, por ejemplo [LG webOS](tv-lg-webos.md): el televisor te pide
aceptar el nuevo dispositivo, y lo haces una vez con el mando a distancia.

Ponle un nombre al televisor y elige el conjunto de reglas que debe seguir. Eso es todo: la tarjeta del televisor en el
panel muestra ya qué se está viendo, cuántos minutos se han visto y cuántos quedan.

## 4. Comprobar que funciona
- Abre una aplicación que tus reglas bloqueen, o espera a que termine una franja permitida. TVBalance muestra un mensaje
  en el televisor y lo devuelve al inicio o lo apaga, según el conjunto de reglas.
- Prueba **Pausa** en la tarjeta del televisor: la aplicación de las reglas se detiene 30 minutos.
- Prueba **Bonus** para añadir 15 o 30 minutos al presupuesto de hoy.

## 5. Conectar Home Assistant
Con el complemento, confirma la notificación **TVBalance** en **Ajustes → Dispositivos y servicios**. Cada televisor se
convierte en un dispositivo con sensores, un botón de pausa y eventos para automatizaciones. Consulta
[Home Assistant](home-assistant.md).

## 6. Usarlo desde el móvil
Para recibir notificaciones en el móvil y tener un icono como el de una aplicación, abre la dirección segura y confía en
el certificado una vez. Consulta [HTTPS en tu red](https.md).

## Qué sigue
- [La aplicación web](web-ui.md): reglas, panel, actividad y ajustes en detalle.
- [TVBalance Pro](pro.md): perfiles, calendario, presupuestos avanzados e informes.
- [Solución de problemas](troubleshooting.md) si no se encuentra el televisor o se corta la conexión.
