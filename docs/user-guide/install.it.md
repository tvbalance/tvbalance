# Installa TVBalance

TVBalance gira su un piccolo computer sempre acceso in casa: la macchina che esegue Home Assistant, un NAS o un
Raspberry Pi. Deve stare sulla stessa rete della TV. Scegli uno dei due modi qui sotto.

## Come Add-on di Home Assistant (consigliato)

Funziona con Home Assistant OS e con le installazioni Supervised, su amd64 e aarch64.

1. In Home Assistant apri **Impostazioni → Add-on → Add-on Store → ⋮ → Repository**.
2. Aggiungi `https://github.com/tvbalance/tvbalance`.
3. Installa **TVBalance**, avvialo e apri il pannello **TVBalance** nella barra laterale.
4. Segui la configurazione guidata. Vedi [Primi passi](getting-started.md).

All'avvio l'Add-on si annuncia a Home Assistant. Compare una notifica **TVBalance** in
**Impostazioni → Dispositivi e servizi**: scegli **Configura** e conferma. Non serve scrivere né indirizzi né token.
Più dettagli in [Home Assistant](home-assistant.md).

L'Add-on usa la rete dell'host, così può trovare le TV e accenderle. Tutti i suoi dati stanno nella cartella `/data`
dell'Add-on e fanno parte dei backup di Home Assistant.

## Con Docker

Un'unica immagine multi-architettura (amd64 e arm64) serve tutto il resto:

```
docker run -d --name tvbalance --restart unless-stopped \
  --network host \
  -v tvbalance-data:/data \
  ghcr.io/tvbalance/tvbalance:latest
```

Poi apri `http://<indirizzo-della-macchina>:8765` in un browser.

- **Rete host.** Il rilevamento delle TV e Wake-on-LAN la richiedono, e funziona così solo su Linux. Su Docker
  Desktop (Windows e macOS) usa invece `-p 8765:8765 -p 8766:8766` e aggiungi la TV con il suo indirizzo, perché non
  può essere trovata in automatico.
- **Il volume dei dati.** `/data` contiene `tvbalance.db` (TV, regole, storico d'uso ed eventi) e `secret.key` (la
  chiave che protegge le credenziali delle TV). Tienili insieme e fanne il backup insieme. Se la chiave va persa, i
  dati restano ma ogni TV va associata di nuovo.
- **Aggiornamenti.** Scarica la nuova immagine e ricrea il contenitore. Il database viene aggiornato all'avvio.

### Impostazioni

Il motore legge le impostazioni da variabili d'ambiente. I valori predefiniti vanno bene per la maggior parte delle
case.

| Variabile | Predefinito | Significato |
| --- | --- | --- |
| `TVBALANCE_DATA_DIR` | `/data` | Dove stanno il database e la chiave |
| `TVBALANCE_PORT` | `8765` | Porta HTTP |
| `TVBALANCE_HTTPS_PORT` | `8766` | Porta HTTPS |
| `TVBALANCE_TLS` | `auto` | `auto` per l'autorità di certificazione locale integrata, `off` per disattivare HTTPS |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | non impostate | Il tuo certificato e la tua chiave (imposta entrambe) |
| `TVBALANCE_TLS_NAMES` | non impostata | Nomi locali aggiuntivi per il certificato automatico |

HTTPS è spiegato in [HTTPS sulla tua rete](https.md).

### Home Assistant con un motore autonomo

Crea un token API nell'app web e installa l'integrazione con HACS. I passaggi sono in
[Home Assistant](home-assistant.md).

## Le porte in sintesi

| Porta | Protocollo | Usata per |
| --- | --- | --- |
| 8765 | HTTP | L'app web, Ingress di Home Assistant, il controllo di salute |
| 8766 | HTTPS | L'app web e l'API sulla tua rete |

## Passo successivo

Apri l'app web e segui [Primi passi](getting-started.md). Se qualcosa non funziona, vedi
[Risoluzione dei problemi](troubleshooting.md).
