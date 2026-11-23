# L'app web

L'app web di TVBalance funziona in qualsiasi browser della tua rete domestica e dentro Home Assistant come pannello
laterale. Si usa bene da telefono e si installa nella schermata iniziale come un'app. Parla inglese, italiano,
tedesco, francese e spagnolo.

## Primo avvio
Alla prima visita l'app chiede tre cose:
1. **Una password** per l'amministratore (almeno 10 caratteri). Conservala con cura: apre tutto.
2. **Lingua e fuso orario.** Gli orari e i limiti giornalieri seguono questo fuso orario.
3. **Un primo set di regole**, a partire da "Giorni di scuola" (giorni feriali 16:00-20:00, fine settimana
   09:00-21:00, due ore al giorno, avvisi a 10 e 5 minuti) oppure da un set vuoto. Tutto si può cambiare dopo.

## Aggiungere una TV
Se non c'è ancora nessuna TV, il pannello propone **Aggiungi una TV** (solo per gli amministratori; una sessione con
PIN non lo vede mai). La procedura cerca nella rete, oppure accetta l'indirizzo della TV scritto a mano, poi ti guida
ad accettare la connessione sulla TV e termina dando un nome alla TV e scegliendo il suo set di regole. Una TV che ha
perso la chiave mostra **Da riaccoppiare** con un link **Associa di nuovo**. I passaggi specifici per marca sono nelle
guide per le TV, come [LG webOS](tv-lg-webos.md).

## Accedere
- **Password:** accesso completo.
- **PIN:** un codice breve facoltativo per un dispositivo condiviso, come un tablet in cucina. Una sessione con PIN
  può vedere il pannello e usare i comandi dei genitori, ma non può cambiare regole, password o token. Dopo cinque PIN
  errati si blocca per un po'.
- Dentro Home Assistant hai già effettuato l'accesso tramite Home Assistant.

## Pannello
Una scheda per ogni TV mostra se è accesa, cosa sta andando in onda, quanti minuti sono stati guardati e quanti ne
restano, e se il contenuto attuale è consentito. La scheda si aggiorna da sola.

Comandi dei genitori su ogni scheda:
- **Pausa** ferma i blocchi per 30 minuti.
- **Bonus** aggiunge 15 o 30 minuti al budget di oggi.
- **Consenti** o **Blocca** scavalca le regole per 15, 30, 60 o 120 minuti, oppure fino a mezzanotte.
- **Annulla override** torna alle regole.

## Regole
Un set di regole dice quando e per quanto tempo si può usare una TV. Più TV possono condividere un set, e ogni TV ne
segue uno. Apri **Regole**, scegli un set (o creane uno) e modificalo in quattro schede:

- **Orari:** le fasce orarie per ogni giorno della settimana. Aggiungi tutte le fasce che ti servono, copia un giorno
  su altri e aggiungi giorni speciali per una singola data, come una festa. Una fascia che finisce prima di iniziare
  prosegue oltre la mezzanotte.
- **Tempo:** un budget giornaliero facoltativo in minuti e gli avvisi mostrati quando restano quei minuti. Con Pro puoi
  anche impostare un budget per ogni giorno della settimana, tempi condivisi per gruppi di app e riportare il tempo non
  usato al giorno dopo. Vedi [TVBalance Pro](pro.md).
- **Contenuti:** app, ingressi e canali da bloccare; una modalità "Consenti solo le app scelte"; ciò che è sempre
  consentito; e dove va la TV quando qualcosa è bloccato (schermata iniziale, un'app, un ingresso o un canale). Scegli
  gli elementi dall'elenco letto dalla TV, con le icone delle app. Se la TV è spenta o non raggiungibile, scrivi gli id
  a mano.
- **Avanzate:** con quanta fermezza vengono applicati i blocchi. I valori predefiniti vanno bene quasi sempre.

### Profili e calendario (Pro)
*Attiva come profilo* su un set di regole lo mette in vigore per tutte le TV della famiglia per il tempo scelto,
escludendo le TV che spunti. Il pannello mostra il profilo in vigore e permette di terminarlo; ogni scheda TV ne
mostra il nome. **Regole > Calendario** elenca le voci che attivano automaticamente i set di regole, ogni settimana o
tra due date. Vedi [TVBalance Pro](pro.md).

Se un set di regole non si può salvare, un messaggio indica il problema, per esempio un ripiego che è a sua volta
bloccato, un avviso più lungo del budget o due fasce sovrapposte.

## Dettagli della TV e attività
Scegli il nome di una TV nel pannello per rinominarla, attivare o disattivare il controllo, cambiare il suo set di
regole, vedere gli ultimi sette giorni come barre e leggere i suoi eventi più recenti. Rimuovere una TV chiede
conferma.

**Attività** mostra lo stesso per tutte le TV, con un filtro e il registro completo degli eventi: avvisi, blocchi,
spegnimenti e problemi di connessione. Con Pro scegli un periodo più lungo (fino a un anno), vedi le app più guardate
e leggi il report della settimana scorsa. Vedi [TVBalance Pro](pro.md).

Cambiare regole, TV e impostazioni richiede la password dell'amministratore.

Quando apri l'app web da un indirizzo `http://` semplice e il motore serve HTTPS, un banner propone l'indirizzo
sicuro. Puoi chiuderlo: la scelta viene ricordata in questo browser.

## Impostazioni
- **Generali:** lingua, fuso orario e aspetto chiaro/scuro.
- **Notifiche:** ricevi una notifica push su questo dispositivo quando la TV va associata di nuovo, non è
  raggiungibile, ha un contenuto bloccato o sta per finire il tempo. Scegli quali vuoi, invia una prova, disattivale e
  rimuovi gli altri dispositivi. Solo l'amministratore vede questa scheda. I browser permettono le notifiche push solo
  su una connessione sicura, quindi funzionano tramite Home Assistant su HTTPS (Ingress), da `localhost` o
  dall'indirizzo sicuro della tua rete (vedi https.md), non da un indirizzo `http://` semplice. La scheda rimanda
  all'indirizzo sicuro quando c'è. Su iPhone e iPad, aggiungi prima TVBalance alla schermata Home.
- **TVBalance Pro:** il piano attuale, a chi è intestata la licenza e quando scade, un campo in cui incollare la
  chiave di licenza e un pulsante per rimuoverla. Solo l'amministratore vede questa scheda. Vedi pro.md.
- **Connessione sicura:** gli indirizzi HTTPS, la scadenza e l'impronta del certificato, i download del certificato e
  del profilo per iPhone e iPad, i passaggi di installazione per ogni dispositivo e un pulsante per creare un nuovo
  certificato. Solo l'amministratore vede questa scheda. Vedi https.md.
- **Sicurezza:** cambia la password; imposta o rimuovi il PIN dei genitori.
- **Dispositivi collegati:** vedi ogni browser collegato e disconnettine uno qualsiasi, oppure tutti tranne questo.
- **Token API:** per altri programmi. Il segreto di un token viene mostrato una sola volta quando lo crei, quindi
  copialo subito. Scegli **lettura** e **controllo** per Home Assistant (vedi home-assistant.md). Revoca un token
  quando vuoi.

**Sistema** mostra la versione e le marche di TV supportate da questa versione, con la loro maturità.
