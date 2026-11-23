# HTTPS sulla tua rete

TVBalance può rispondere in HTTPS sulla tua rete domestica. I browser considerano allora sicura l'app web: le
notifiche Web Push funzionano, il cookie di accesso è marcato `Secure` e la tua password non viaggia più in chiaro.

HTTPS è attivo per impostazione predefinita. Il motore ascolta su due porte:

| Porta | Protocollo | Usata per |
| ----- | ---------- | --------- |
| 8765  | HTTP       | Ingress di Home Assistant, il controllo di salute, il rilevamento dell'Add-on e una prima occhiata da un browser |
| 8766  | HTTPS      | L'app web e l'API sulla tua rete |

HTTP resta aperta di proposito. Quando apri l'app web tramite `http://`, un banner propone l'indirizzo sicuro, e la
scheda Notifiche rimanda a esso.

## Il certificato

Un indirizzo web sulla tua rete (`tvbalance.local`, `10.x.x.x`) non può ottenere un certificato da un'autorità
pubblica. TVBalance crea quindi una piccola **autorità di certificazione locale** (CA) al primo avvio e firma con essa
il proprio certificato del server. Il certificato del server dura 397 giorni e si rinnova da solo 30 giorni prima della
scadenza, senza riavvio. Cambia anche quando cambiano il nome o l'indirizzo del motore.

I tuoi dispositivi devono dare fiducia alla CA una volta sola. Fino ad allora un browser avvisa che la connessione non
è privata.

### Installa la CA su un dispositivo

Apri **Impostazioni → Connessione sicura** nell'app web. Elenca gli indirizzi sicuri, la scadenza del certificato e la
sua **impronta**, e offre due download: il certificato (`.crt`) e un profilo per iPhone e iPad.

Confronta l'impronta mostrata dal dispositivo con quella nelle Impostazioni prima di dargli fiducia.

- **iPhone e iPad:** apri il profilo, consentilo in Impostazioni, installalo, poi attivalo in
  Impostazioni → Generali → Info → Impostazioni attendibilità certificati.
- **Android:** Impostazioni → cerca "certificato CA" → Installa comunque → scegli il file scaricato.
- **Windows:** apri il file → Installa certificato → Computer locale → Autorità di certificazione radice attendibili.
- **macOS:** apri il file in Accesso Portachiavi, poi imposta la fiducia su Considera sempre attendibile.

Su Windows e Linux alcuni browser tengono un proprio elenco di autorità (Firefox lo fa): importa il file anche lì.

### Ricominciare con una nuova CA

**Crea un nuovo certificato** nella stessa scheda genera una nuova CA e un nuovo certificato del server. Usalo se un
dispositivo che si fidava della vecchia CA è andato perso o se sospetti che la chiave della CA sia trapelata. Ogni
dispositivo deve poi installare la nuova CA, e l'integrazione di Home Assistant ti chiede di confermare la nuova
impronta.

## Il tuo certificato

Se hai già un certificato di cui i tuoi dispositivi si fidano (per esempio uno creato per Home Assistant), indica a
TVBalance di usare quello:

- Motore autonomo: imposta `TVBALANCE_TLS_CERTFILE` e `TVBALANCE_TLS_KEYFILE` sulla catena di certificati e sulla
  chiave privata, entrambi file PEM.
- Add-on di Home Assistant: metti i file nella cartella `/ssl` e imposta **Certificate file** e **Key file** nelle
  opzioni dell'Add-on (per esempio `fullchain.pem` e `privkey.pem`).

Il motore controlla che la chiave corrisponda al certificato e che non sia scaduto. Impostazioni → Connessione sicura
mostra allora solo lo stato, perché il rinnovo spetta a te. Riavvia il motore dopo aver sostituito i file.

## Impostazioni

| Variabile d'ambiente | Opzione dell'Add-on | Significato |
| -------------------- | ------------------- | ----------- |
| `TVBALANCE_TLS` | HTTPS | `auto` (predefinito) oppure `off` |
| `TVBALANCE_HTTPS_PORT` | | Porta per HTTPS, 8766 per impostazione predefinita (deve essere diversa da `TVBALANCE_PORT`) |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | Certificate file, Key file | Il tuo certificato |
| `TVBALANCE_TLS_NAMES` | Extra names | Altri nomi host o indirizzi per il certificato automatico, separati da virgole |

Le variabili d'ambiente prevalgono sulle opzioni dell'Add-on.

Il certificato automatico copre `localhost`, il nome host della macchina e il suo nome `.local`, e il suo indirizzo
IPv4 privato. I nomi non locali vengono esclusi, e le Impostazioni indicano quali.

Se la porta HTTPS è occupata, il motore registra un errore e continua a servire HTTP.

## Home Assistant

Su HTTP dentro l'Add-on non cambia nulla. Per collegare l'integrazione tramite HTTPS, inserisci un indirizzo
`https://` e il token API. Quando il certificato del motore non è attendibile, l'integrazione scarica la CA, mostra la
sua impronta e ti chiede di confrontarla con Impostazioni → Connessione sicura. Dopo la tua conferma, Home Assistant
accetta solo quella CA per questo motore. Se la CA cambia in seguito, una nuova autenticazione ti chiede di
confermare di nuovo.

## Note sulla sicurezza

- **Cosa può firmare la CA.** La CA porta i Name Constraints X.509: può emettere certificati solo per `localhost`,
  `.local`, `.lan`, `.home.arpa`, `.internal` e intervalli di indirizzi privati. Un dispositivo che si fida di essa non
  è esposto a un certificato falso per un sito pubblico, a patto che il client applichi i name constraints (i
  browser e i sistemi operativi attuali lo fanno).
- **Dove sta la chiave.** La chiave della CA è conservata cifrata con gli altri segreti del motore (`secret.key`), e la
  chiave del server è un file con permessi riservati al proprietario nella cartella dei dati. Chiunque possa leggere
  la cartella dei dati può emettere certificati per nomi locali, quindi proteggila come il resto dei tuoi backup.
- **Il download è pubblico.** Il certificato della CA (mai la sua chiave) si può scaricare senza accedere, perché un
  nuovo dispositivo ne ha bisogno prima di potersi fidare di qualunque cosa. Conferma sempre l'impronta: è il
  controllo che il file venga davvero dal tuo motore.
- **HTTP è ancora disponibile.** Accedi tramite HTTPS sulle reti condivise. Il banner serve a ricordartelo.
