# TVBalance Pro

TVBalance es gratis para un televisor. Una **licencia Pro**, comprada una vez para todo el hogar, quita el límite y
desbloquea las funciones avanzadas a medida que llegan.

| | Free | Pro |
| --- | --- | --- |
| Televisores supervisados | 1 | Ilimitados |
| Perfiles y calendario | No | Sí |
| Presupuestos avanzados (por día de la semana, grupos de aplicaciones, traslado) | No | Sí |
| Historial de más de 7 días, uso por aplicación, informe semanal | No | Sí |
| Reglas, presupuestos de tiempo, acciones parentales, notificaciones, Home Assistant | Sí | Sí |

La licencia es una clave que pegas en la aplicación. Se comprueba en tu propio dispositivo con una firma, así que no
necesita conexión a internet y nada sobre ti se envía a ningún sitio.

## Perfiles y calendario

Un **perfil** es un conjunto de reglas que activas de una vez para todo el hogar, por ejemplo «Vacaciones» o «Fin de
semana con los abuelos». Mientras está activo, cada televisor lo sigue en lugar de su propio conjunto de reglas, salvo
los televisores que excluyas (digamos el de los padres).

- **A mano:** en **Reglas**, pulsa *Activar como perfil* en un conjunto, elige la duración (de 30 minutos a 4 horas, o
  hasta medianoche) y los televisores que quedan fuera. El panel muestra el perfil activo con un botón *Terminar perfil*.
- **Por calendario:** en **Reglas > Calendario**, añade entradas que activan un conjunto de reglas por sí solas, ya sea
  cada semana en días y horas elegidos (una franja que termina antes de empezar pasa de medianoche) o entre dos fechas.
- **Desde Home Assistant:** los servicios `tvbalance.activate_profile` y `tvbalance.stop_profile` y el blueprint
  «calendar».

Cuando se aplican varios, gana el perfil manual más reciente, luego una entrada de calendario con fecha, luego una
semanal y luego el conjunto de reglas propio del televisor. Terminar un perfil o dejar que caduque devuelve cada
televisor a sus propias reglas.

Puedes configurar perfiles y calendario con cualquier plan; se guardan pero solo se aplican con una licencia Pro, y las
pantallas lo indican. No se pierde nada si una licencia termina.

## Presupuestos avanzados

El presupuesto diario de un conjunto de reglas se puede afinar en **Reglas > Horarios**:

- **Presupuesto por día de la semana:** un número de minutos distinto para cada día, por ejemplo más el sábado. Un día
  que se deja vacío usa el presupuesto diario.
- **Grupos de aplicaciones:** un grupo de aplicaciones, como «Juegos», que comparten una única asignación diaria. Cuando
  se agota el tiempo del grupo, sus aplicaciones se bloquean mientras todo lo demás sigue disponible, y aparece un aviso
  antes de que se acabe. Elige las aplicaciones de la lista leída del televisor.
- **Trasladar el tiempo no usado:** los minutos no usados ayer se suman a hoy, hasta un máximo que eliges. Los minutos
  trasladados nunca se acumulan de un día a otro.

Se pueden configurar con cualquier plan y se guardan en cualquier caso, pero solo se aplican con una licencia Pro; en
Free se aplica el presupuesto diario simple. No se pierde nada si una licencia termina.

## Historial e informe semanal

**Actividad** puede mostrar los últimos 7, 30, 90 o 365 días, con una barra por día y las aplicaciones, entradas y
canales más vistos de cada televisor. En el plan Free el historial se detiene a los 7 días y un aviso lo indica.

Cada lunes a las 8:00 (hora del hogar) está listo el **informe semanal** de la semana anterior: cuánto se vio cada
televisor, en qué días, las aplicaciones principales y cuántas veces se bloqueó contenido. Aparece en Actividad y también
puede llegar como notificación: activa «Un informe semanal el lunes» para un dispositivo en **Ajustes > Notificaciones**
(desactivado por defecto). Home Assistant recibe un evento `weekly_report`.

## Obtener y activar una licencia
1. En **Ajustes → TVBalance Pro**, elige **Comprar Pro** (se muestra cuando la página de compra está configurada).
2. Tras pagar recibes una clave de licencia: una línea larga de letras y dígitos con un punto en medio.
3. Pégala en **Clave de licencia** y elige **Activar**. Solo el administrador ve esta tarjeta.

La tarjeta muestra entonces el plan, para quién es la licencia y la fecha de caducidad, si la hay. La mayoría de las
licencias nunca caducan.

## Qué pasa en el plan Free con varios televisores
Siempre puedes añadir y configurar tantos televisores como quieras. En el plan Free solo se supervisa el **televisor
activado más antiguo**; los demás conservan sus ajustes pero no se vigilan, y se marcan como **Requiere Pro**. Desactiva
el televisor más antiguo y el siguiente ocupa su lugar.

## Caducidad y eliminación
No se borra nada cuando una licencia caduca o la quitas. El hogar simplemente vuelve al plan Free, y los televisores
adicionales dejan de supervisarse hasta que haya de nuevo una licencia activa. Una clave guardada que deja de ser válida
(por ejemplo tras una rotación de claves) se trata igual, y la tarjeta lo indica.

Quitar la licencia está en **Ajustes → TVBalance Pro → Quitar licencia**.
