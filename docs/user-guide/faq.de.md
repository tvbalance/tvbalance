# Häufige Fragen

## Braucht TVBalance ein Konto oder das Internet?
Nein. Es läuft in Ihrem eigenen Netzwerk und spricht direkt mit dem Fernseher. Es gibt kein Cloud-Konto und keine
Telemetrie. Die Pro-Lizenz ist ein signierter Schlüssel, der auf Ihrem Gerät geprüft wird und ebenfalls keine
Verbindung braucht.

## Wo liegen meine Daten?
Im Datenordner der Engine (`/data` im Add-on und in Docker): die Datenbank `tvbalance.db` mit Fernsehern, Regeln,
Nutzungsverlauf und Ereignissen sowie `secret.key`, der die gespeicherten Zugangsdaten der Fernseher schützt. Die Daten
des Add-ons sind Teil der Home-Assistant-Backups. Bewahren Sie Datenbank und Schlüssel zusammen auf.

## Welche Fernseher werden unterstützt?
LG webOS 4 und neuer wird unterstützt und auf echter Hardware geprüft. Roku, Google/Android TV und Samsung Tizen sind
geplant und noch nicht nutzbar. Jede Marke kann etwas anderes, und die App bietet nur an, was der Fernseher wirklich
kann. Was ein LG unterstützt, steht unter [LG webOS](tv-lg-webos.md).

## Funktioniert es ohne Home Assistant?
Ja. Die Web-App funktioniert allein, mit Docker oder dem Add-on. Home Assistant ergänzt Entitäten, Dienste, Ereignisse
und Blueprints für Automatisierungen. Siehe [Installieren](install.md) und [Home Assistant](home-assistant.md).

## Was ist kostenlos und was ist Pro?
Ein Fernseher mit allen Grundregeln (Zeitpläne, Tagesbudgets, Sperren von Apps, Eingängen und Sendern, Eltern-Aktionen,
Benachrichtigungen, Home Assistant) ist kostenlos. Pro ist eine einmalige Lizenz für den Haushalt, die mehr Fernseher,
Profile und einen Kalender, erweiterte Budgets, einen langen Verlauf und Wochenberichte erlaubt. Siehe
[TVBalance Pro](pro.md).

## Was geschieht, wenn meine Pro-Lizenz abläuft?
Nichts wird gelöscht. Die Pro-Einstellungen bleiben gespeichert und werden nicht mehr angewendet: Die Fernseher nach dem
ersten werden nicht mehr überwacht, und die Regeln fallen auf die einfachen zurück. Mit einer gültigen Lizenz greifen
sie wieder.

## Kann mein Kind es umgehen?
TVBalance wirkt am Fernseher, ein Smartphone oder eine andere Fernbedienung hilft also nicht. Es ist ein Familienwerkzeug,
kein Schloss: Ein Kind mit Zugang zum Einstellungsmenü des Fernsehers kann ihn trotzdem vom Strom nehmen oder das
Netzwerk ändern. Nutzen Sie die PIN des Fernsehers und auf gemeinsam genutzten Geräten eine PIN für die Eltern-Steuerung
von TVBalance. Zum Ändern von Regeln ist das Administrator-Passwort nötig.

## Kann ich mehrere Fernseher verwenden?
Ja, mit [Pro](pro.md). Jeder Fernseher folgt einem Regelsatz, und mehrere Fernseher können sich denselben Satz teilen.

## Welche Sprachen gibt es?
Englisch, Italienisch, Deutsch, Französisch und Spanisch. Die Web-App folgt Ihrem Browser oder Home Assistant, und Sie
können sie unter **Einstellungen → Allgemein** ändern. Diese Dokumentation gibt es in denselben fünf Sprachen.

## Funktioniert es über HTTPS?
Ja. HTTPS ist standardmäßig an, mit einem Zertifikat einer lokalen Zertifizierungsstelle, der Ihre Geräte einmal
vertrauen. Sie können auch Ihr eigenes Zertifikat verwenden. Siehe [HTTPS in Ihrem Netzwerk](https.md).

## Wie aktualisiere ich?
Mit dem Add-on aktualisieren Sie es im Add-on-Store. Mit Docker laden Sie das neue Image und erstellen den Container
neu. Daten und Einstellungen bleiben erhalten, und die Datenbank wird beim Start aktualisiert.

## Wie melde ich ein Problem oder wünsche mir eine Fernsehermarke?
Eröffnen Sie ein Issue unter <https://github.com/tvbalance/tvbalance/issues>. Hängen Sie den Diagnose-Download an und
posten Sie keine Token oder Lizenzschlüssel. Entwickler können eine Marke selbst mit einem Adapter-Paket ergänzen:
siehe [Einen Adapter schreiben](../developers/adapters.md).
