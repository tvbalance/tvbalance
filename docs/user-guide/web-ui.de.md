# Die Web-App

Die Web-App von TVBalance läuft in jedem Browser in Ihrem Heimnetz und in Home Assistant als Seitenpanel. Sie ist gut
auf dem Smartphone nutzbar und lässt sich wie eine App auf den Startbildschirm legen. Sie spricht Englisch,
Italienisch, Deutsch, Französisch und Spanisch.

## Erster Start
Beim ersten Besuch fragt die App nach drei Dingen:
1. **Einem Passwort** für den Administrator (mindestens 10 Zeichen). Bewahren Sie es sicher auf; es öffnet alles.
2. **Sprache und Zeitzone.** Zeiten und Tageslimits richten sich nach dieser Zeitzone.
3. **Einem ersten Regelsatz**, ausgehend von „Schultage“ (werktags 16:00–20:00, am Wochenende 09:00–21:00, zwei
   Stunden pro Tag, Warnungen bei 10 und 5 Minuten) oder von einem leeren Satz. Alles lässt sich danach ändern.

## Einen Fernseher hinzufügen
Solange es noch keinen Fernseher gibt, bietet die Übersicht **Fernseher hinzufügen** an (nur für Administratoren;
eine PIN-Sitzung sieht es nie). Der Assistent durchsucht Ihr Netzwerk oder nimmt die Adresse des Fernsehers von Hand
entgegen, führt Sie dann durch das Akzeptieren der Verbindung am Fernseher und endet damit, dass Sie den Fernseher
benennen und seinen Regelsatz wählen. Ein Fernseher, der seinen Schlüssel verloren hat, zeigt **Neu koppeln** mit
einem Link **Erneut koppeln**. Die markenspezifischen Schritte stehen in den Fernseher-Anleitungen, etwa
[LG webOS](tv-lg-webos.md).

## Anmelden
- **Passwort:** voller Zugriff.
- **PIN:** ein optionaler kurzer Code für ein gemeinsam genutztes Gerät, etwa ein Tablet in der Küche. Eine
  PIN-Sitzung kann die Übersicht ansehen und die Eltern-Steuerung nutzen, aber keine Regeln, Passwörter oder Token
  ändern. Nach fünf falschen PINs sperrt sie sich für eine Weile.
- In Home Assistant sind Sie bereits über Home Assistant angemeldet.

## Übersicht
Eine Karte pro Fernseher zeigt, ob er an ist, was läuft, wie viele Minuten geschaut wurden und wie viele noch übrig
sind, und ob der aktuelle Inhalt erlaubt ist. Die Karte aktualisiert sich von selbst.

Eltern-Steuerung auf jeder Karte:
- **Pause** hält die Durchsetzung für 30 Minuten an.
- **Bonus** fügt dem heutigen Budget 15 oder 30 Minuten hinzu.
- **Erlauben** oder **Sperren** setzt die Regeln für 15, 30, 60 oder 120 Minuten oder bis Mitternacht außer Kraft.
- **Überschreibung aufheben** kehrt zu den Regeln zurück.

## Regeln
Ein Regelsatz legt fest, wann und wie lange ein Fernseher genutzt werden darf. Mehrere Fernseher können sich einen
Satz teilen, und jeder Fernseher folgt einem. Öffnen Sie **Regeln**, wählen Sie einen Satz (oder legen Sie einen
an) und bearbeiten Sie ihn in vier Registern:

- **Zeiten:** die Zeitfenster für jeden Wochentag. Fügen Sie so viele Fenster hinzu, wie Sie brauchen, kopieren Sie
  einen Tag auf andere und fügen Sie Sondertage für ein einzelnes Datum hinzu, etwa einen Feiertag. Ein Fenster, das
  vor seinem Beginn endet, läuft über Mitternacht hinaus.
- **Dauer:** ein optionales Tagesbudget in Minuten und die Warnungen, die bei so vielen verbleibenden Minuten
  erscheinen. Mit Pro können Sie außerdem ein Budget für jeden Wochentag festlegen, gemeinsame Kontingente für
  App-Gruppen und nicht genutzte Zeit auf den nächsten Tag übertragen. Siehe [TVBalance Pro](pro.md).
- **Inhalte:** zu sperrende Apps, Eingänge und Sender; ein Modus „Nur gewählte Apps erlauben“; was immer erlaubt ist;
  und wohin der Fernseher geht, wenn etwas gesperrt ist (Startbildschirm, eine App, ein Eingang oder ein Sender).
  Wählen Sie Einträge aus der vom Fernseher gelesenen Liste, mit App-Symbolen. Ist der Fernseher aus oder nicht
  erreichbar, geben Sie die IDs von Hand ein.
- **Erweitert:** wie streng Sperren durchgesetzt werden. Die Standardwerte passen für fast alle.

### Profile und Kalender (Pro)
*Als Profil aktivieren* bei einem Regelsatz setzt ihn für alle Fernseher des Haushalts für die gewählte Zeit in Kraft,
ohne die Fernseher, die Sie ankreuzen. Die Übersicht zeigt das geltende Profil und lässt Sie es beenden; jede
Fernseher-Karte zeigt seinen Namen. **Regeln > Kalender** listet die Einträge auf, die Regelsätze automatisch
einschalten, wöchentlich oder zwischen zwei Daten. Siehe [TVBalance Pro](pro.md).

Lässt sich ein Regelsatz nicht speichern, benennt eine Meldung das Problem, zum Beispiel ein Ausweichziel, das selbst
gesperrt ist, eine Warnung, die länger als das Budget ist, oder zwei sich überschneidende Fenster.

## Fernseher-Details und Aktivität
Wählen Sie in der Übersicht den Namen eines Fernsehers, um ihn umzubenennen, die Überwachung ein- oder auszuschalten,
seinen Regelsatz zu ändern, die letzten sieben Tage als Balken zu sehen und seine neuesten Ereignisse zu lesen. Das
Entfernen eines Fernsehers verlangt eine Bestätigung.

**Aktivität** zeigt dasselbe für alle Fernseher, mit einem Filter und dem vollständigen Ereignisprotokoll: Warnungen,
Sperren, Abschaltungen und Verbindungsprobleme. Mit Pro wählen Sie einen längeren Zeitraum (bis zu einem Jahr), sehen
die meistgenutzten Apps und lesen den Bericht der letzten Woche. Siehe [TVBalance Pro](pro.md).

Regeln, Fernseher und Einstellungen zu ändern erfordert das Administrator-Passwort.

Öffnen Sie die Web-App über eine einfache `http://`-Adresse und die Engine bietet HTTPS an, schlägt ein Banner die
sichere Adresse vor. Sie können es schließen; die Wahl wird in diesem Browser gemerkt.

## Einstellungen
- **Allgemein:** Sprache, Zeitzone und helle oder dunkle Darstellung.
- **Benachrichtigungen:** Sie erhalten auf diesem Gerät eine Push-Benachrichtigung, wenn der Fernseher neu gekoppelt
  werden muss, nicht erreichbar ist, ein Inhalt gesperrt wurde oder die Zeit gleich abläuft. Wählen Sie, welche Sie
  möchten, senden Sie einen Test, schalten Sie sie aus und entfernen Sie andere Geräte. Nur der Administrator sieht
  diese Karte. Browser erlauben Push nur über eine sichere Verbindung, es funktioniert also über Home Assistant per
  HTTPS (Ingress), von `localhost` oder von der sicheren Adresse Ihres Netzwerks (siehe https.md), nicht von einer
  einfachen `http://`-Adresse. Die Karte verlinkt auf die sichere Adresse, wenn es eine gibt. Auf iPhone und iPad
  legen Sie TVBalance zuerst auf den Home-Bildschirm.
- **TVBalance Pro:** der aktuelle Tarif, für wen die Lizenz gilt und wann sie abläuft, ein Feld zum Einfügen eines
  Lizenzschlüssels und eine Schaltfläche zum Entfernen. Nur der Administrator sieht diese Karte. Siehe pro.md.
- **Sichere Verbindung:** die HTTPS-Adressen, Ablauf und Fingerabdruck des Zertifikats, Downloads des Zertifikats und
  des Profils für iPhone und iPad, Installationsschritte je Gerät und eine Schaltfläche, um ein neues Zertifikat zu
  erstellen. Nur der Administrator sieht diese Karte. Siehe https.md.
- **Sicherheit:** das Passwort ändern; die Eltern-PIN setzen oder entfernen.
- **Angemeldete Geräte:** jeden angemeldeten Browser sehen und einen davon oder alle außer diesem abmelden.
- **API-Token:** für andere Programme. Das Geheimnis eines Tokens wird beim Erstellen nur einmal angezeigt, kopieren
  Sie es also sofort. Wählen Sie **lesen** und **steuern** für Home Assistant (siehe home-assistant.md). Ein Token
  lässt sich jederzeit widerrufen.

**System** zeigt die Version und die Fernsehermarken, die diese Version unterstützt, mit ihrem Reifegrad.
