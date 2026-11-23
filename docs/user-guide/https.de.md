# HTTPS in Ihrem Netzwerk

TVBalance kann in Ihrem Heimnetz über HTTPS antworten. Browser behandeln die Web-App dann als sicher: Web-Push-
Benachrichtigungen funktionieren, das Anmelde-Cookie ist als `Secure` markiert, und Ihr Passwort wird nicht mehr im
Klartext gesendet.

HTTPS ist standardmäßig eingeschaltet. Die Engine lauscht auf zwei Ports:

| Port | Protokoll | Verwendet für |
| ---- | --------- | ------------- |
| 8765 | HTTP      | Home-Assistant-Ingress, die Funktionsprüfung, die Add-on-Erkennung und ein erster Blick aus dem Browser |
| 8766 | HTTPS     | Die Web-App und die API in Ihrem Netzwerk |

HTTP bleibt absichtlich offen. Öffnen Sie die Web-App über `http://`, bietet ein Banner die sichere Adresse an, und die
Karte Benachrichtigungen verlinkt darauf.

## Das Zertifikat

Eine Webadresse in Ihrem eigenen Netzwerk (`tvbalance.local`, `10.x.x.x`) kann kein Zertifikat von einer öffentlichen
Stelle bekommen. TVBalance erstellt deshalb beim ersten Start eine kleine **lokale Zertifizierungsstelle** (CA) und
signiert damit sein eigenes Serverzertifikat. Das Serverzertifikat gilt 397 Tage und wird 30 Tage vor Ablauf ohne
Neustart von selbst erneuert. Es ändert sich auch, wenn sich Name oder Adresse der Engine ändern.

Ihre Geräte müssen der CA einmal vertrauen. Bis dahin warnt der Browser, dass die Verbindung nicht privat ist.

### Die CA auf einem Gerät installieren

Öffnen Sie in der Web-App **Einstellungen → Sichere Verbindung**. Dort stehen die sicheren Adressen, der Ablauf des
Zertifikats und sein **Fingerabdruck**, dazu zwei Downloads: das Zertifikat (`.crt`) und ein Profil für iPhone und iPad.

Vergleichen Sie den Fingerabdruck, den das Gerät zeigt, mit dem in den Einstellungen, bevor Sie vertrauen.

- **iPhone und iPad:** Öffnen Sie das Profil, erlauben Sie es in den Einstellungen, installieren Sie es und aktivieren
  Sie es dann unter Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen.
- **Android:** Einstellungen → nach „CA-Zertifikat“ suchen → Trotzdem installieren → die heruntergeladene Datei
  wählen.
- **Windows:** Datei öffnen → Zertifikat installieren → Lokaler Computer → Vertrauenswürdige Stammzertifizierungsstellen.
- **macOS:** Öffnen Sie die Datei in der Schlüsselbundverwaltung und setzen Sie das Vertrauen auf „Immer vertrauen“.

Unter Windows und Linux führen manche Browser eine eigene Liste von Zertifizierungsstellen (Firefox tut das): Importieren
Sie die Datei dort ebenfalls.

### Mit einer neuen CA neu beginnen

**Neues Zertifikat erstellen** auf derselben Karte erzeugt eine neue CA und ein neues Serverzertifikat. Nutzen Sie es,
wenn ein Gerät, das der alten CA vertraute, verloren ging oder Sie vermuten, dass der CA-Schlüssel kompromittiert ist.
Danach muss jedes Gerät die neue CA installieren, und die Home-Assistant-Integration bittet Sie, den neuen
Fingerabdruck zu bestätigen.

## Ihr eigenes Zertifikat

Haben Sie schon ein Zertifikat, dem Ihre Geräte vertrauen (zum Beispiel eines für Home Assistant), richten Sie
TVBalance stattdessen darauf:

- Eigenständige Engine: Setzen Sie `TVBALANCE_TLS_CERTFILE` und `TVBALANCE_TLS_KEYFILE` auf die Zertifikatskette und den
  privaten Schlüssel, beides PEM-Dateien.
- Home-Assistant-Add-on: Legen Sie die Dateien in den Ordner `/ssl` und setzen Sie **Zertifikatsdatei** und
  **Schlüsseldatei** in den Add-on-Optionen (zum Beispiel `fullchain.pem` und `privkey.pem`).

Die Engine prüft, ob der Schlüssel zum Zertifikat passt und ob es nicht abgelaufen ist. Einstellungen → Sichere
Verbindung zeigt dann nur noch den Status, denn die Erneuerung liegt bei Ihnen. Starten Sie die Engine neu, nachdem Sie
die Dateien ersetzt haben.

## Einstellungen

| Umgebungsvariable | Add-on-Option | Bedeutung |
| ----------------- | ------------- | --------- |
| `TVBALANCE_TLS` | HTTPS | `auto` (Standard) oder `off` |
| `TVBALANCE_HTTPS_PORT` | | Port für HTTPS, standardmäßig 8766 (muss sich von `TVBALANCE_PORT` unterscheiden) |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | Zertifikatsdatei, Schlüsseldatei | Ihr eigenes Zertifikat |
| `TVBALANCE_TLS_NAMES` | Zusätzliche Namen | Weitere Hostnamen oder Adressen für das automatische Zertifikat, durch Kommas getrennt |

Umgebungsvariablen haben Vorrang vor Add-on-Optionen.

Das automatische Zertifikat deckt `localhost`, den Hostnamen des Rechners und seinen `.local`-Namen sowie seine private
IPv4-Adresse ab. Nicht lokale Namen bleiben außen vor, und die Einstellungen sagen Ihnen, welche.

Ist der HTTPS-Port belegt, protokolliert die Engine einen Fehler und liefert weiter HTTP aus.

## Home Assistant

Über HTTP innerhalb des Add-ons ändert sich nichts. Um die Integration über HTTPS zu verbinden, geben Sie eine
`https://`-Adresse und das API-Token ein. Ist das Zertifikat der Engine nicht vertrauenswürdig, lädt die Integration
die CA herunter, zeigt ihren Fingerabdruck und bittet Sie, ihn mit Einstellungen → Sichere Verbindung zu vergleichen.
Nach Ihrer Bestätigung akzeptiert Home Assistant für diese Engine nur diese CA. Ändert sich die CA später, bittet eine
erneute Authentifizierung um Bestätigung.

## Sicherheitshinweise

- **Was die CA signieren kann.** Die CA trägt X.509-Namensbeschränkungen: Sie kann nur Zertifikate für `localhost`,
  `.local`, `.lan`, `.home.arpa`, `.internal` und private Adressbereiche ausstellen. Ein Gerät, das ihr vertraut, ist
  keinem gefälschten Zertifikat für eine öffentliche Website ausgesetzt, solange der Client Namensbeschränkungen
  durchsetzt (aktuelle Browser und Betriebssysteme tun das).
- **Wo der Schlüssel liegt.** Der CA-Schlüssel wird verschlüsselt zusammen mit den übrigen Geheimnissen der Engine
  (`secret.key`) gespeichert, und der Serverschlüssel ist eine Datei mit Zugriffsrechten nur für den Besitzer im
  Datenordner. Wer den Datenordner lesen kann, kann Zertifikate für lokale Namen ausstellen; schützen Sie ihn also wie
  Ihre übrigen Backups.
- **Der Download ist öffentlich.** Das CA-Zertifikat (nie sein Schlüssel) lässt sich ohne Anmeldung herunterladen, weil
  ein neues Gerät es braucht, bevor es irgendetwas vertrauen kann. Bestätigen Sie immer den Fingerabdruck: Er belegt,
  dass die Datei von Ihrer Engine stammt.
- **HTTP bleibt verfügbar.** Melden Sie sich in gemeinsam genutzten Netzwerken über HTTPS an. Das Banner erinnert Sie
  daran.
