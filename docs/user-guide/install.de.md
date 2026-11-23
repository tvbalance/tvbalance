# TVBalance installieren

TVBalance läuft auf einem kleinen, ständig eingeschalteten Rechner bei Ihnen zu Hause: dem Gerät, auf dem Home
Assistant läuft, einem NAS oder einem Raspberry Pi. Er muss im selben Netzwerk wie Ihr Fernseher sein. Wählen Sie
einen der beiden Wege unten.

## Als Home-Assistant-Add-on (empfohlen)

Das funktioniert mit Home Assistant OS und Supervised-Installationen, auf amd64 und aarch64.

1. Öffnen Sie in Home Assistant **Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories**.
2. Fügen Sie `https://github.com/tvbalance/tvbalance` hinzu.
3. Installieren Sie **TVBalance**, starten Sie es und öffnen Sie das Panel **TVBalance** in der Seitenleiste.
4. Folgen Sie der Einrichtung auf dem Bildschirm. Siehe [Erste Schritte](getting-started.md).

Beim Start meldet sich das Add-on bei Home Assistant. Unter **Einstellungen → Geräte & Dienste** erscheint eine
Benachrichtigung **TVBalance**: Wählen Sie **Konfigurieren** und bestätigen Sie. Weder Adresse noch Token müssen
eingegeben werden. Mehr dazu unter [Home Assistant](home-assistant.md).

Das Add-on nutzt das Netzwerk des Hosts, damit es Fernseher finden und aufwecken kann. Alle Daten liegen im Ordner
`/data` des Add-ons und sind Teil der Home-Assistant-Backups.

## Mit Docker

Ein einziges Multi-Architektur-Image (amd64 und arm64) deckt alles andere ab:

```
docker run -d --name tvbalance --restart unless-stopped \
  --network host \
  -v tvbalance-data:/data \
  ghcr.io/tvbalance/tvbalance:latest
```

Öffnen Sie dann `http://<Adresse-des-Rechners>:8765` in einem Browser.

- **Host-Netzwerk.** Die Fernsehersuche und Wake-on-LAN brauchen es, und es funktioniert so nur unter Linux. Mit
  Docker Desktop (Windows und macOS) verwenden Sie stattdessen `-p 8765:8765 -p 8766:8766` und fügen Ihren Fernseher
  über seine Adresse hinzu, da er nicht automatisch gefunden werden kann.
- **Das Datenvolume.** `/data` enthält `tvbalance.db` (Ihre Fernseher, Regeln, Nutzungsverlauf und Ereignisse) und
  `secret.key` (den Schlüssel, der die gespeicherten Zugangsdaten der Fernseher schützt). Bewahren Sie beides
  zusammen auf und sichern Sie beides zusammen. Geht der Schlüssel verloren, bleiben die Daten erhalten, aber jeder
  Fernseher muss neu gekoppelt werden.
- **Updates.** Laden Sie das neue Image und erstellen Sie den Container neu. Die Datenbank wird beim Start
  aktualisiert.

### Einstellungen

Die Engine liest ihre Einstellungen aus Umgebungsvariablen. Die Standardwerte passen für die meisten Haushalte.

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `TVBALANCE_DATA_DIR` | `/data` | Wo Datenbank und Schlüssel liegen |
| `TVBALANCE_PORT` | `8765` | HTTP-Port |
| `TVBALANCE_HTTPS_PORT` | `8766` | HTTPS-Port |
| `TVBALANCE_TLS` | `auto` | `auto` für die integrierte lokale Zertifizierungsstelle, `off` zum Abschalten von HTTPS |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | nicht gesetzt | Ihr eigenes Zertifikat und Ihr Schlüssel (beide setzen) |
| `TVBALANCE_TLS_NAMES` | nicht gesetzt | Weitere lokale Namen für das automatische Zertifikat |

HTTPS wird in [HTTPS in Ihrem Netzwerk](https.md) erklärt.

### Home Assistant mit einer eigenständigen Engine

Erstellen Sie in der Web-App ein API-Token und installieren Sie die Integration mit HACS. Die Schritte stehen unter
[Home Assistant](home-assistant.md).

## Die Ports im Überblick

| Port | Protokoll | Verwendet für |
| --- | --- | --- |
| 8765 | HTTP | Die Web-App, Home-Assistant-Ingress, die Funktionsprüfung |
| 8766 | HTTPS | Die Web-App und die API in Ihrem Netzwerk |

## Nächster Schritt

Öffnen Sie die Web-App und folgen Sie [Erste Schritte](getting-started.md). Wenn etwas nicht funktioniert, lesen Sie
die [Fehlerbehebung](troubleshooting.md).
