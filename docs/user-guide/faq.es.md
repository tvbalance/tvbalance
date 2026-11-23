# Preguntas frecuentes

## ¿TVBalance necesita una cuenta o internet?
No. Funciona en tu propia red y habla directamente con el televisor. No hay cuenta en la nube ni telemetría. La licencia
Pro es una clave firmada que se comprueba en tu dispositivo, así que tampoco necesita conexión.

## ¿Dónde están mis datos?
En la carpeta de datos del motor (`/data` en el complemento y en Docker): la base de datos `tvbalance.db` con los
televisores, las reglas, el historial de uso y los eventos, y `secret.key`, que protege las credenciales guardadas de los
televisores. Los datos del complemento forman parte de las copias de seguridad de Home Assistant. Guarda juntas la base
de datos y la clave.

## ¿Qué televisores se admiten?
LG webOS 4 y posteriores está admitido y verificado en hardware real. Roku, Google/Android TV y Samsung Tizen están
previstos y aún no se pueden usar. Cada marca puede hacer cosas distintas, y la aplicación solo ofrece lo que el
televisor puede hacer de verdad. Consulta [LG webOS](tv-lg-webos.md) para saber qué admite una LG.

## ¿Funciona sin Home Assistant?
Sí. La aplicación web funciona por sí sola, con Docker o con el complemento. Home Assistant añade entidades, servicios,
eventos y blueprints para automatizaciones. Consulta [Instalar](install.md) y [Home Assistant](home-assistant.md).

## ¿Qué es gratis y qué es Pro?
Un televisor con todas las reglas básicas (horarios, presupuestos diarios, bloqueo de aplicaciones, entradas y canales,
acciones parentales, notificaciones, Home Assistant) es gratis. Pro es una licencia única para el hogar que permite más
televisores, perfiles y calendario, presupuestos avanzados, historial largo e informes semanales. Consulta
[TVBalance Pro](pro.md).

## ¿Qué pasa si caduca mi licencia Pro?
No se borra nada. Los ajustes Pro siguen guardados y dejan de aplicarse: los televisores a partir del primero ya no se
supervisan, y las reglas vuelven a las básicas. Añade una licencia válida y vuelven a aplicarse.

## ¿Puede mi hijo saltárselo?
TVBalance actúa sobre el televisor, así que un móvil o un mando distinto no sirven. Es una herramienta familiar, no un
candado: un niño con acceso al menú de ajustes del televisor aún puede desenchufarlo o cambiar la red. Usa el PIN del
televisor y, en dispositivos compartidos, un PIN para los controles parentales de TVBalance. Para iniciar sesión y
cambiar reglas hace falta la contraseña de administrador.

## ¿Puedo usar varios televisores?
Sí, con [Pro](pro.md). Cada televisor sigue un conjunto de reglas, y varios televisores pueden compartir el mismo.

## ¿Qué idiomas hay?
Inglés, italiano, alemán, francés y español. La aplicación web sigue a tu navegador o a Home Assistant, y puedes
cambiarlo en **Ajustes → General**. Esta documentación está disponible en los mismos cinco idiomas.

## ¿Funciona por HTTPS?
Sí. HTTPS está activado por defecto, con un certificado de una autoridad local en la que tus dispositivos confían una vez.
También puedes usar tu propio certificado. Consulta [HTTPS en tu red](https.md).

## ¿Cómo actualizo?
Con el complemento, actualízalo desde la tienda de complementos. Con Docker, descarga la nueva imagen y vuelve a crear el
contenedor. Tus datos y ajustes se conservan y la base de datos se actualiza al arrancar.

## ¿Cómo informo de un problema o pido una marca de televisor?
Abre una incidencia en <https://github.com/tvbalance/tvbalance/issues>. Adjunta la descarga de diagnóstico y no publiques
tokens ni claves de licencia. Los desarrolladores pueden añadir una marca por su cuenta con un paquete adaptador:
consulta [Escribir un adaptador](../developers/adapters.md).
