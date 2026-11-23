# TVBalance Pro

TVBalance ist für einen Fernseher kostenlos. Eine **Pro-Lizenz**, einmal für den ganzen Haushalt gekauft, hebt die
Begrenzung auf und schaltet die erweiterten Funktionen frei, sobald sie erscheinen.

| | Free | Pro |
| --- | --- | --- |
| Überwachte Fernseher | 1 | Unbegrenzt |
| Profile und Kalender | Nein | Ja |
| Erweiterte Budgets (pro Wochentag, App-Gruppen, Übertrag) | Nein | Ja |
| Verlauf über 7 Tage hinaus, Nutzung pro App, Wochenbericht | Nein | Ja |
| Regeln, Zeitbudgets, Eltern-Aktionen, Benachrichtigungen, Home Assistant | Ja | Ja |

Die Lizenz ist ein Schlüssel, den Sie in die App einfügen. Er wird auf Ihrem eigenen Gerät per Signatur geprüft,
braucht also keine Internetverbindung, und nichts über Sie wird irgendwohin gesendet.

## Profile und Kalender

Ein **Profil** ist ein Regelsatz, den Sie für den ganzen Haushalt auf einmal einschalten, zum Beispiel „Ferien“ oder
„Wochenende bei den Großeltern“. Solange er an ist, folgt jeder Fernseher ihm statt seinem eigenen Regelsatz, außer
den Fernsehern, die Sie ausnehmen (etwa den der Eltern).

- **Von Hand:** Drücken Sie unter **Regeln** bei einem Satz *Als Profil aktivieren*, wählen Sie die Dauer (30 Minuten
  bis 4 Stunden oder bis Mitternacht) und die auszunehmenden Fernseher. Die Übersicht zeigt das aktive Profil mit einer
  Schaltfläche *Profil beenden*.
- **Per Kalender:** Fügen Sie unter **Regeln > Kalender** Einträge hinzu, die einen Regelsatz von selbst einschalten,
  entweder jede Woche an gewählten Tagen und Uhrzeiten (ein Fenster, das vor seinem Beginn endet, läuft über
  Mitternacht hinaus) oder zwischen zwei Daten.
- **Aus Home Assistant:** die Dienste `tvbalance.activate_profile` und `tvbalance.stop_profile` und das Blueprint
  „calendar“.

Gelten mehrere, gewinnt das jüngste manuelle Profil, dann ein datierter Kalendereintrag, dann ein wöchentlicher, dann
der eigene Regelsatz des Fernsehers. Wird ein Profil beendet oder läuft es ab, kehrt jeder Fernseher zu seinen eigenen
Regeln zurück.

Profile und Kalender lassen sich in jedem Tarif einrichten; sie werden gespeichert, aber nur mit einer Pro-Lizenz
angewendet, und die Bildschirme weisen darauf hin. Nichts geht verloren, wenn eine Lizenz endet.

## Erweiterte Budgets

Das Tagesbudget eines Regelsatzes lässt sich unter **Regeln > Zeiten** verfeinern:

- **Budget pro Wochentag:** eine andere Minutenzahl für jeden Tag, zum Beispiel mehr am Samstag. Ein leer gelassener
  Tag verwendet das Tagesbudget.
- **App-Gruppen:** eine Gruppe von Apps, etwa „Spiele“, die sich ein Tageskontingent teilen. Ist die Zeit der Gruppe
  aufgebraucht, werden ihre Apps gesperrt, während alles andere verfügbar bleibt, und vor dem Ende erscheint eine
  Warnung. Wählen Sie die Apps aus der vom Fernseher gelesenen Liste.
- **Nicht genutzte Zeit übertragen:** Minuten, die gestern nicht genutzt wurden, werden zu heute addiert, bis zu einem
  Maximum, das Sie wählen. Übertragene Minuten häufen sich nie von einem Tag zum nächsten an.

Sie lassen sich in jedem Tarif einrichten und werden in jedem Fall gespeichert, aber nur mit einer Pro-Lizenz
angewendet; im Free-Tarif gilt das einfache Tagesbudget. Nichts geht verloren, wenn eine Lizenz endet.

## Verlauf und Wochenbericht

**Aktivität** kann die letzten 7, 30, 90 oder 365 Tage zeigen, mit einem Balken pro Tag und den meistgesehenen Apps,
Eingängen und Sendern jedes Fernsehers. Im Free-Tarif endet der Verlauf bei 7 Tagen, und ein Hinweis sagt das.

Jeden Montag um 8:00 Uhr (Ortszeit des Haushalts) liegt der **Wochenbericht** für die Vorwoche bereit: wie lange jeder
Fernseher lief, an welchen Tagen, die meistgenutzten Apps und wie oft Inhalte gesperrt wurden. Er erscheint in der
Aktivität und kann auch als Benachrichtigung kommen: Schalten Sie für ein Gerät unter **Einstellungen >
Benachrichtigungen** „Ein Wochenbericht am Montag“ ein (standardmäßig aus). Home Assistant erhält ein Ereignis
`weekly_report`.

## Eine Lizenz erhalten und aktivieren
1. Wählen Sie unter **Einstellungen → TVBalance Pro** **Pro kaufen** (sichtbar, wenn die Kaufseite eingerichtet ist).
2. Nach der Zahlung erhalten Sie einen Lizenzschlüssel: eine lange Zeile aus Buchstaben und Ziffern mit einem Punkt in
   der Mitte.
3. Fügen Sie ihn in **Lizenzschlüssel** ein und wählen Sie **Aktivieren**. Nur der Administrator sieht diese Karte.

Die Karte zeigt dann den Tarif, für wen die Lizenz gilt und das Ablaufdatum, falls es eines gibt. Die meisten Lizenzen
laufen nie ab.

## Was im Free-Tarif mit mehreren Fernsehern geschieht
Sie können immer beliebig viele Fernseher hinzufügen und einrichten. Im Free-Tarif wird nur der **älteste aktivierte
Fernseher** überwacht; die anderen behalten ihre Einstellungen, werden aber nicht überwacht und sind mit **Erfordert
Pro** markiert. Schalten Sie den ältesten Fernseher aus, rückt der nächste nach.

## Ablauf und Entfernen
Nichts wird gelöscht, wenn eine Lizenz abläuft oder Sie sie entfernen. Der Haushalt kehrt einfach zum Free-Tarif
zurück, und die zusätzlichen Fernseher werden nicht mehr überwacht, bis wieder eine Lizenz aktiv ist. Ein gespeicherter
Schlüssel, der ungültig wird (zum Beispiel nach einem Schlüsselwechsel), wird genauso behandelt, und die Karte sagt
es.

Die Lizenz entfernen Sie unter **Einstellungen → TVBalance Pro → Lizenz entfernen**.
