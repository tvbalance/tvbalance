# Televisores LG webOS

TVBalance habla con los televisores LG (webOS 4 y posteriores) por tu red doméstica. Nada sale de tu casa.

## Preparar el televisor
1. Conecta el televisor a la misma red que el ordenador donde se ejecuta TVBalance.
2. Activa **Ajustes > General > Dispositivos externos > Encender TV con móvil > Encender mediante Wi-Fi** (en modelos más
   antiguos se llama *LG Connect Apps*). El televisor acepta entonces conexiones de otros dispositivos.
3. Dale al televisor una dirección fija en tu router (una reserva DHCP) para que siga siendo accesible.

## Emparejar
1. Enciende el televisor, ten a mano el mando a distancia y abre **Añadir televisor** en la aplicación web.
2. Elige tu televisor de la lista. Si no aparece (algunas redes bloquean la búsqueda), elige **LG webOS** en *Escribir la
   dirección* y escribe la dirección IP del televisor, que encuentras en sus ajustes de red.
3. Pulsa **Iniciar el emparejamiento** y mira el televisor: te pregunta si se debe permitir el nuevo dispositivo.
   Confirma con el mando a distancia en tres minutos. TVBalance guarda la clave que entrega el televisor; esto se hace
   una sola vez por televisor.
4. Pon nombre al televisor y elige su conjunto de reglas.

Si pulsas **No** o no pasa nada, usa **Reintentar**. Si el televisor olvida la clave (por ejemplo, tras un restablecimiento
de fábrica), el panel muestra **Hay que volver a emparejar**: abre **Emparejar de nuevo** en su tarjeta y acepta otra vez.

## Qué puede hacer TVBalance en una LG
Leer qué se está viendo (aplicación, entrada HDMI, canal en directo y programa), listar aplicaciones, entradas y canales,
mostrar un mensaje en pantalla, volver al inicio, abrir una aplicación, una entrada o un canal, y apagar el televisor.

## Límites conocidos
- **Quick Start+**: con esta opción el televisor responde aunque la pantalla esté apagada. TVBalance lo notifica como en
  espera, no como viendo, así que el presupuesto diario no corre.
- **Los títulos de los programas** solo están disponibles mientras la televisión en directo está en primer plano, y no lo
  están en webOS 4.5 y anteriores.
- **Encender el televisor** aún no está soportado.
- Los iconos de las aplicaciones los sirve el televisor con un certificado autofirmado; la aplicación web los muestra a
  través de un proxy propio.
