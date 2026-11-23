# Erste Schritte

Von der frischen Installation bis zu einem Fernseher, der Ihren Regeln folgt, vergehen etwa fünf Minuten. Sie
brauchen TVBalance [installiert](install.md) und Ihren Fernseher eingeschaltet, im selben Netzwerk.

## 1. Die Web-App öffnen
Öffnen Sie das Panel **TVBalance** in Home Assistant oder `http://<Adresse-des-Rechners>:8765`, wenn Sie Docker
verwenden. Der erste Besuch startet die Einrichtung.

## 2. Den Haushalt einrichten
Die App fragt nach drei Dingen:

1. **Einem Passwort** für den Administrator, mindestens 10 Zeichen. Bewahren Sie es sicher auf.
2. **Sprache und Zeitzone.** Zeiten und Tageslimits richten sich nach dieser Zeitzone.
3. **Einem ersten Regelsatz.** Beginnen Sie mit „Schultage“ oder mit einem leeren Satz. Alles lässt sich später ändern.

## 3. Ihren Fernseher hinzufügen
Wählen Sie **Fernseher hinzufügen**. Der Assistent durchsucht Ihr Netzwerk und listet die gefundenen Fernseher auf.
Fehlt Ihrer, geben Sie seine Adresse von Hand ein. Folgen Sie den Schritten für Ihre Marke, zum Beispiel
[LG webOS](tv-lg-webos.md): Der Fernseher bittet Sie, das neue Gerät zu akzeptieren, und das tun Sie einmal mit der
Fernbedienung.

Geben Sie dem Fernseher einen Namen und wählen Sie den Regelsatz, dem er folgen soll. Das ist alles: Die Karte des
Fernsehers in der Übersicht zeigt nun, was läuft, wie viele Minuten geschaut wurden und wie viele noch übrig sind.

## 4. Prüfen, ob es funktioniert
- Öffnen Sie eine App, die Ihre Regeln sperren, oder warten Sie das Ende eines erlaubten Zeitfensters ab. TVBalance
  zeigt eine Meldung auf dem Fernseher und schickt ihn zurück zum Startbildschirm oder schaltet ihn aus, je nach
  Regelsatz.
- Probieren Sie **Pause** auf der Karte des Fernsehers: Die Durchsetzung ruht 30 Minuten.
- Probieren Sie **Bonus**, um dem heutigen Budget 15 oder 30 Minuten hinzuzufügen.

## 5. Home Assistant verbinden
Bestätigen Sie beim Add-on die Benachrichtigung **TVBalance** unter **Einstellungen → Geräte & Dienste**. Jeder
Fernseher wird zu einem Gerät mit Sensoren, einer Pause-Taste und Ereignissen für Automatisierungen. Siehe
[Home Assistant](home-assistant.md).

## 6. Vom Smartphone aus nutzen
Für Benachrichtigungen auf dem Smartphone und ein App-ähnliches Symbol öffnen Sie die sichere Adresse und
vertrauen dem Zertifikat einmal. Siehe [HTTPS in Ihrem Netzwerk](https.md).

## Wie es weitergeht
- [Die Web-App](web-ui.md): Regeln, Übersicht, Aktivität und Einstellungen im Detail.
- [TVBalance Pro](pro.md): Profile, ein Kalender, erweiterte Budgets und Berichte.
- [Fehlerbehebung](troubleshooting.md), wenn der Fernseher nicht gefunden wird oder die Verbindung abreißt.
