# LG-webOS-Fernseher

TVBalance spricht über Ihr Heimnetz mit LG-Fernsehern (webOS 4 und neuer). Nichts verlässt Ihr Haus.

## Den Fernseher vorbereiten
1. Verbinden Sie den Fernseher mit demselben Netzwerk wie den Rechner, auf dem TVBalance läuft.
2. Aktivieren Sie **Einstellungen > Allgemein > Externe Geräte > TV-Einschalten per Mobilgerät > Über WLAN
   einschalten** (bei älteren Modellen *LG Connect Apps* genannt). Der Fernseher akzeptiert dann Verbindungen von
   anderen Geräten.
3. Geben Sie dem Fernseher in Ihrem Router eine feste Adresse (eine DHCP-Reservierung), damit er erreichbar bleibt.

## Koppeln
1. Schalten Sie den Fernseher ein, halten Sie die Fernbedienung bereit und öffnen Sie **Fernseher hinzufügen** in der
   Web-App.
2. Wählen Sie Ihren Fernseher aus der Liste. Fehlt er (manche Netzwerke blockieren die Suche), wählen Sie **LG webOS**
   unter *Adresse eingeben* und tippen Sie die IP-Adresse des Fernsehers ein, die Sie in seinen Netzwerkeinstellungen
   finden.
3. Drücken Sie **Kopplung starten** und beobachten Sie den Fernseher: Er fragt, ob das neue Gerät erlaubt werden soll.
   Bestätigen Sie mit der Fernbedienung innerhalb von drei Minuten. TVBalance speichert den Schlüssel, den der
   Fernseher herausgibt; das tun Sie nur einmal pro Fernseher.
4. Benennen Sie den Fernseher und wählen Sie seinen Regelsatz.

Drücken Sie **Nein** oder passiert nichts, verwenden Sie **Erneut versuchen**. Vergisst der Fernseher den Schlüssel
(zum Beispiel nach einem Werksreset), zeigt die Übersicht **Neu koppeln**: Öffnen Sie **Erneut koppeln** auf seiner
Karte und akzeptieren Sie noch einmal.

## Was TVBalance auf einem LG kann
Lesen, was läuft (App, HDMI-Eingang, Live-Sender und Sendung), Apps, Eingänge und Sender auflisten, eine Meldung auf
dem Bildschirm anzeigen, zum Startbildschirm gehen, eine App, einen Eingang oder einen Sender öffnen und den Fernseher
ausschalten.

## Bekannte Grenzen
- **Quick Start+**: Mit dieser Option antwortet der Fernseher auch bei ausgeschaltetem Bildschirm. TVBalance meldet
  ihn als Standby, nicht als schauend, sodass das Tagesbudget nicht läuft.
- **Sendungstitel** sind nur verfügbar, solange das Live-TV im Vordergrund ist, und auf webOS 4.5 und älter gar nicht.
- **Den Fernseher einschalten** wird noch nicht unterstützt.
- App-Symbole liefert der Fernseher mit einem selbstsignierten Zertifikat aus; die Web-App zeigt sie über einen
  eigenen Proxy.
