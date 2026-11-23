# Home Assistant

TVBalance liefert eine eigene Integration mit, die jeden Fernseher als Gerät in Home Assistant zeigt, Ihnen Ereignisse
sendet und Automatisierungen erlaubt, Fernsehzeit zu gewähren oder zu entziehen.

## Einrichtung

### Mit dem Add-on (empfohlen)

Installieren Sie das TVBalance-Add-on und starten Sie es. Home Assistant zeigt unter
**Einstellungen → Geräte & Dienste** eine Benachrichtigung **TVBalance**: Wählen Sie **Konfigurieren** und bestätigen
Sie. Das Add-on erstellt und behält das API-Token für Sie; widerrufen Sie es, starten Sie das Add-on neu, und Home
Assistant übernimmt das neue.

### Mit einer eigenständigen Engine

1. Öffnen Sie in der TVBalance-Web-App **Einstellungen → API-Token** und erstellen Sie ein Token mit den Bereichen
   **lesen** und **steuern**. Fügen Sie **admin** nur hinzu, wenn Sie den Dienst `tvbalance.set_monitoring` möchten.
   Das Geheimnis wird nur einmal angezeigt.
2. Installieren Sie die Integration mit HACS (fügen Sie `https://github.com/tvbalance/tvbalance-ha` als benutzerdefiniertes
   Repository hinzu, Kategorie Integration) oder kopieren Sie `custom_components/tvbalance` in den Ordner
   `config/custom_components` von Home Assistant. Starten Sie Home Assistant neu.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → TVBalance**. Geben Sie die Engine-Adresse und das
   Token ein.

Für HTTPS geben Sie eine `https://`-Adresse ein (standardmäßig Port 8766). Ist das Zertifikat noch nicht
vertrauenswürdig, zeigt die Einrichtung den Fingerabdruck der lokalen Zertifizierungsstelle der Engine: Vergleichen
Sie ihn mit **Einstellungen → Sichere Verbindung** in der TVBalance-Web-App und bestätigen Sie. Home Assistant
akzeptiert dann für diese Engine nur diese Zertifizierungsstelle. Ändert sie sich (ein neues Zertifikat wurde
erstellt), bittet Home Assistant erneut um Bestätigung. Siehe https.md.

Wird das Token widerrufen oder läuft es ab, fragt Home Assistant nach einem neuen (eine Reparaturmeldung erscheint;
wählen Sie **Neu konfigurieren**). Sonst muss nichts neu eingerichtet werden.

## Was Sie pro Fernseher bekommen

| Entität | Bedeutung |
| --- | --- |
| Status (Sensor) | `watching`, `standby`, `off`, `unreachable`, `needs_pairing` oder `not_monitored` |
| App, Sendung (Sensoren) | Was gerade auf dem Bildschirm ist. Eingang und Sender gibt es auch, standardmäßig deaktiviert |
| Profil (Sensor) | Der Name des für diesen Fernseher geltenden Profils, unbekannt wenn keines gilt |
| Heute geschaut, Verbleibende Zeit (Sensoren) | Minuten; Verbleibende Zeit ist unbekannt, wenn der Fernseher kein Tagesbudget hat |
| Gesperrt (Binärsensor) | An, solange die Durchsetzung den Fernseher sperrt; das Attribut `reason` nennt den Grund |
| Verbunden, Neu koppeln (Binärsensoren) | Zustand der Verbindung |
| Pause (Taste) | Pausiert die Durchsetzung für 30 Minuten. Für jeden gefahrlos drückbar |
| Aktivität (Ereignis-Entität) | Löst bei jedem TVBalance-Ereignis aus |

Die Engine überträgt Änderungen live, die Zustände aktualisieren sich also innerhalb einer Sekunde. Reißt der Strom
ab, verbindet sich Home Assistant von selbst neu und fragt weiterhin alle 30 Sekunden ab.

## Dienste (nur Administratoren)

Alles, was mehr Fernsehzeit gibt oder die Durchsetzung ändert, ist auf Home-Assistant-Administratoren beschränkt, damit
ein Kind an einem Dashboard es nicht aufrufen kann. Automatisierungen und Skripte können es. Jeder Dienst nimmt eine
`device_id` (den Fernseher).

| Dienst | Felder |
| --- | --- |
| `tvbalance.bonus` | `minutes` (1–240) |
| `tvbalance.allow` | `minutes` (1–1440) oder `until_midnight` |
| `tvbalance.block` | `minutes` (1–1440) oder `until_midnight` |
| `tvbalance.pause` | `minutes` (1–1440) |
| `tvbalance.clear_override` | keine |
| `tvbalance.set_monitoring` | `enabled`; braucht ein Token mit dem Bereich admin |

Die Profil-Dienste gelten für den ganzen Haushalt, nicht für einen Fernseher, und erfordern den Pro-Tarif:

| Dienst | Felder |
| --- | --- |
| `tvbalance.activate_profile` | `policy_id`, `minutes` (1–1440) oder `until_midnight`, optional `excluded_device_ids` |
| `tvbalance.stop_profile` | keine |

`allow`, `block` und `activate_profile` brauchen genau eines von `minutes` oder `until_midnight`. Eine PIN ist nie
Teil eines Dienstaufrufs.

## Ereignisse

Jedes Engine-Ereignis wird auch als `tvbalance_event` auf dem Home-Assistant-Bus ausgelöst, mit `device_id`, `tv_id`,
`type` und `payload`. Typen: `time_warning` (`minutes_left`, `limit`), `blocked` (`reason`), `redirected` (`action`),
`powered_off`, `enforcement_paused`, `enforcement_unavailable` (`reason`), `tv_unreachable`, `tv_reachable`,
`pairing_lost`, `tv_paired`, `profile_started` (`name`, `until`, `source`), `profile_ended` (`name`), `weekly_report`
(`first`, `last`, `total_seconds`, `blocks`, `top`).

## Blueprints

Sie liegen unter `blueprints/automation/tvbalance/`; kopieren Sie sie nach `config/blueprints/automation/tvbalance/`.

- **warning_light**: lässt ein Licht blinken, wenn einem Fernseher noch N Minuten oder weniger bleiben.
- **notify_parent**: sendet eine Benachrichtigung für die gewählten Ereignisse.
- **button_bonus**: gewährt Bonusminuten, wenn eine physische Taste gedrückt wird.
- **calendar_profile**: schaltet einen Regelsatz für den Haushalt ein, solange ein Home-Assistant-Kalenderereignis
  läuft, und aus, wenn es endet (Pro).
