# Fehlerbehebung

Beginnen Sie mit der Übersicht: Jede Fernseher-Karte sagt, ob der Fernseher an ist, nicht erreichbar ist oder **neu
gekoppelt werden muss**. **Aktivität** zeigt die neuesten Ereignisse, etwa Verbindungsprobleme, in einfachen Worten.

## Der Fernseher wird nicht gefunden
- Prüfen Sie, ob der Fernseher an ist und im selben Netzwerk wie TVBalance hängt, nicht in einem Gastnetz.
- Manche Router blockieren die Suchnachrichten zwischen Geräten. Wählen Sie im Assistenten unter *Adresse eingeben* die
  Marke und tippen Sie die IP-Adresse des Fernsehers ein, die Sie in seinen Netzwerkeinstellungen finden.
- Mit Docker unter Windows oder macOS kann die Suche nicht funktionieren, weil der Container hinter einem virtuellen
  Netzwerk sitzt. Geben Sie die Adresse von Hand ein. Siehe [Installieren](install.md).
- Geben Sie dem Fernseher in Ihrem Router eine feste Adresse (eine DHCP-Reservierung), damit die eingegebene Adresse
  gültig bleibt.
- Bei LG-Fernsehern prüfen Sie die Einstellungen unter [LG webOS](tv-lg-webos.md).

## Die Kopplung wird nicht abgeschlossen
- Halten Sie die Fernbedienung bereit und akzeptieren Sie die Anfrage am Fernseher innerhalb von drei Minuten. Der
  Fernseher zeigt sie nur an, solange er eingeschaltet ist.
- Haben Sie **Nein** gedrückt oder ist nichts passiert, verwenden Sie **Erneut versuchen** im Assistenten.
- Achten Sie darauf, dass der Fernseher keine andere Vollbild-Abfrage und keinen Bildschirmschoner zeigt.

## Die Karte sagt „Neu koppeln“
Der Fernseher hat den Schlüssel vergessen, den TVBalance hält, zum Beispiel nach einem Werksreset oder einem
Software-Update. Öffnen Sie **Erneut koppeln** auf der Karte und akzeptieren Sie die Anfrage am Fernseher noch einmal.
Regeln, Verlauf und Einstellungen bleiben erhalten. Ist Web Push eingeschaltet, erhalten Sie dabei auch eine
Benachrichtigung.

## Der Fernseher ist „nicht erreichbar“
TVBalance kann sich nicht mit dem Fernseher verbinden, was normal ist, wenn er vom Strom getrennt ist. Passiert es bei
eingeschaltetem Fernseher:

- Prüfen Sie die Adresse des Fernsehers in Ihrem Router. Hat sie sich geändert, entfernen Sie den Fernseher und fügen
  Sie ihn mit der neuen Adresse wieder hinzu, oder geben Sie ihm eine feste Adresse.
- Prüfen Sie, ob die Netzwerkfunktionen des Fernsehers noch aktiviert sind (bei LG siehe
  [LG webOS](tv-lg-webos.md)).
- Starten Sie den Fernseher vollständig neu (eine Minute vom Strom trennen). Manche Fernseher antworten nach langer
  Laufzeit nicht mehr.

## Eine Regel scheint nicht zu greifen
- Prüfen Sie, ob beim Fernseher die Überwachung an ist (Detailseite des Fernsehers) und ob er dem Regelsatz folgt, den
  Sie bearbeitet haben.
- Bei LG-Fernsehern mit **Quick Start+** meldet ein Fernseher mit ausgeschaltetem Bildschirm Standby, sodass das
  Tagesbudget nicht läuft. Das ist erwartet. Siehe die Grenzen unter [LG webOS](tv-lg-webos.md).
- Ein manuelles **Erlauben** oder **Sperren** setzt die Regeln außer Kraft, bis es endet. Verwenden Sie **Überschreibung
  aufheben** auf der Karte.
- Profile, der Kalender und erweiterte Budgets werden in jedem Tarif gespeichert, aber nur mit [Pro](pro.md)
  angewendet. Die Bildschirme weisen darauf hin.
- Zeiten folgen der bei der Einrichtung gewählten Zeitzone, nicht der Uhr des Fernsehers. Prüfen Sie sie unter
  **Einstellungen → Allgemein**.

## Der Browser warnt, dass die Verbindung nicht privat ist
Die sichere Adresse nutzt ein Zertifikat einer kleinen Zertifizierungsstelle, die TVBalance erstellt hat. Ihr Gerät muss
ihr einmal vertrauen. Folgen Sie [HTTPS in Ihrem Netzwerk](https.md): Laden Sie das Zertifikat unter **Einstellungen →
Sichere Verbindung** herunter, installieren Sie es und vergleichen Sie den Fingerabdruck. Firefox führt eine eigene
Liste, importieren Sie es dort also ebenfalls.

## Keine Benachrichtigungen auf dem Smartphone
Browser erlauben Push-Benachrichtigungen nur über eine sichere Verbindung.

- Öffnen Sie die Web-App über Home Assistant per HTTPS oder über die sichere Adresse von TVBalance, nicht über eine
  einfache `http://`-Adresse. Die Karte unter **Einstellungen → Benachrichtigungen** verlinkt auf die sichere Adresse,
  wenn es eine gibt.
- Legen Sie TVBalance auf iPhone und iPad zuerst auf den Home-Bildschirm und schalten Sie Benachrichtigungen über
  dieses Symbol ein.
- Senden Sie einen Test von derselben Karte. Kommt er nicht an, erlauben Sie Benachrichtigungen für die Website oder
  App in den Einstellungen des Telefons.

## Home Assistant findet TVBalance nicht
- Mit dem Add-on starten Sie es neu und suchen unter **Einstellungen → Geräte & Dienste** die Benachrichtigung
  **TVBalance**.
- Haben Sie das Token „Home Assistant (Add-on)“ unter **Einstellungen → API-Token** widerrufen, starten Sie das Add-on
  neu: Es erstellt ein neues.
- Bei einer eigenständigen Engine prüfen Sie Adresse und Port und ob das Token die Bereiche **lesen** und **steuern**
  hat. Siehe [Home Assistant](home-assistant.md).

## Eine PIN wird abgelehnt
Nach fünf falschen PINs sperrt sich die PIN-Anmeldung für eine Weile. Warten Sie oder melden Sie sich mit dem
Administrator-Passwort an und ändern Sie die PIN unter **Einstellungen → Sicherheit**.

## Administrator-Passwort vergessen
TVBalance hat noch keine Passwortzurücksetzung, weil nichts außerhalb Ihres Hauses gesendet wird. Ist noch ein Browser
angemeldet, können Sie das Passwort unter **Einstellungen → Sicherheit** ändern. Ist keiner angemeldet, bleibt heute nur
der Neubeginn mit einem leeren Datenordner: Regeln, Verlauf und die gespeicherten Fernseher-Schlüssel gehen verloren,
und jeder Fernseher muss neu gekoppelt werden. Spielen Sie ein Backup ein, das vor dem Verlust des Passworts erstellt
wurde, falls Sie eines haben.

## Immer noch nicht gelöst
Eröffnen Sie ein Issue unter <https://github.com/tvbalance/tvbalance/issues> und hängen Sie den Diagnose-Download an.
Posten Sie keine Token, Lizenzschlüssel oder Inhalte des Datenordners.
