# Home Assistant

TVBalance include un'integrazione personalizzata che mostra ogni TV come dispositivo in Home Assistant, ti invia gli
eventi e permette alle automazioni di concedere o togliere tempo di TV.

## Configurazione

### Con l'Add-on (consigliato)

Installa l'Add-on TVBalance e avvialo. Home Assistant mostra una notifica **TVBalance** in
**Impostazioni → Dispositivi e servizi**: scegli **Configura** e conferma. L'Add-on crea e conserva il token API per
te; se lo revochi, riavvia l'Add-on e Home Assistant riconosce quello nuovo.

### Con un motore autonomo

1. Nell'app web di TVBalance apri **Impostazioni → Token API** e crea un token con gli ambiti **lettura** e
   **controllo**. Aggiungi **admin** solo se vuoi il servizio `tvbalance.set_monitoring`. Il segreto viene mostrato una
   sola volta.
2. Installa l'integrazione con HACS (aggiungi `https://github.com/tvbalance/tvbalance-ha` come repository
   personalizzato, categoria Integrazione), oppure copia `custom_components/tvbalance` nella cartella
   `config/custom_components` di Home Assistant. Riavvia Home Assistant.
3. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → TVBalance**. Inserisci l'indirizzo del motore e il
   token.

Per usare HTTPS, inserisci un indirizzo `https://` (porta 8766 per impostazione predefinita). Se il certificato non è
ancora attendibile, la configurazione mostra l'impronta dell'autorità di certificazione locale del motore: confrontala
con **Impostazioni → Connessione sicura** nell'app web di TVBalance e conferma. Home Assistant accetterà poi solo
quell'autorità per questo motore. Se l'autorità cambia (è stato creato un nuovo certificato), Home Assistant chiede di
confermarla di nuovo. Vedi https.md.

Se il token viene revocato o scade, Home Assistant ne chiede uno nuovo (compare un avviso di riparazione; scegli
**Riconfigura**). Non serve rifare nient'altro.

## Cosa ottieni per ogni TV

| Entità | Significato |
| --- | --- |
| Stato (sensore) | `watching`, `standby`, `off`, `unreachable`, `needs_pairing` o `not_monitored` |
| App, Programma (sensori) | Cosa c'è sullo schermo ora. Esistono anche Ingresso e Canale, disattivati per impostazione predefinita |
| Profilo (sensore) | Il nome del profilo in vigore per questa TV, sconosciuto se non ce n'è |
| Guardato oggi, Tempo rimasto (sensori) | Minuti; Tempo rimasto è sconosciuto se la TV non ha un budget giornaliero |
| Bloccata (sensore binario) | Attivo mentre l'applicazione dei blocchi blocca la TV; l'attributo `reason` dice perché |
| Connessa, Da riaccoppiare (sensori binari) | Stato del collegamento |
| Pausa (pulsante) | Mette in pausa i blocchi per 30 minuti. Sicuro da premere per chiunque |
| Attività (entità evento) | Si attiva a ogni evento di TVBalance |

Il motore invia i cambiamenti in tempo reale, quindi gli stati si aggiornano entro un secondo. Se il flusso si
interrompe, Home Assistant si riconnette da solo e continua comunque a interrogare ogni 30 secondi.

## Servizi (solo amministratori)

Tutto ciò che dà più tempo di TV o cambia l'applicazione delle regole è riservato agli amministratori di Home
Assistant, così un bambino che usa una dashboard non può chiamarlo. Le automazioni e gli script possono. Ogni servizio
accetta un `device_id` (la TV).

| Servizio | Campi |
| --- | --- |
| `tvbalance.bonus` | `minutes` (1–240) |
| `tvbalance.allow` | `minutes` (1–1440) o `until_midnight` |
| `tvbalance.block` | `minutes` (1–1440) o `until_midnight` |
| `tvbalance.pause` | `minutes` (1–1440) |
| `tvbalance.clear_override` | nessuno |
| `tvbalance.set_monitoring` | `enabled`; richiede un token con ambito admin |

I servizi dei profili riguardano tutta la famiglia, non una TV, e richiedono il piano Pro:

| Servizio | Campi |
| --- | --- |
| `tvbalance.activate_profile` | `policy_id`, `minutes` (1–1440) o `until_midnight`, facoltativo `excluded_device_ids` |
| `tvbalance.stop_profile` | nessuno |

`allow`, `block` e `activate_profile` richiedono esattamente uno tra `minutes` e `until_midnight`. Nessun PIN fa mai
parte di una chiamata a un servizio.

## Eventi

Ogni evento del motore viene inviato anche sul bus di Home Assistant come `tvbalance_event`, con `device_id`, `tv_id`,
`type` e `payload`. Tipi: `time_warning` (`minutes_left`, `limit`), `blocked` (`reason`), `redirected` (`action`),
`powered_off`, `enforcement_paused`, `enforcement_unavailable` (`reason`), `tv_unreachable`, `tv_reachable`,
`pairing_lost`, `tv_paired`, `profile_started` (`name`, `until`, `source`), `profile_ended` (`name`), `weekly_report`
(`first`, `last`, `total_seconds`, `blocks`, `top`).

## Blueprint

Si trovano in `blueprints/automation/tvbalance/`; copiali in `config/blueprints/automation/tvbalance/`.

- **warning_light**: fa lampeggiare una luce quando a una TV restano N minuti o meno.
- **notify_parent**: invia una notifica per gli eventi che scegli.
- **button_bonus**: concede minuti di bonus quando si preme un pulsante fisico.
- **calendar_profile**: attiva un set di regole per la famiglia mentre dura un evento di un calendario di Home
  Assistant, e lo disattiva quando finisce (Pro).
