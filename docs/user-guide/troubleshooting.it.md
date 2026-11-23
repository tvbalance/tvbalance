# Risoluzione dei problemi

Parti dal pannello: ogni scheda TV dice se la TV è accesa, irraggiungibile o **Da riaccoppiare**. **Attività** mostra
gli ultimi eventi, come i problemi di connessione, a parole semplici.

## La TV non viene trovata
- Controlla che la TV sia accesa e sulla stessa rete di TVBalance, non su una rete ospiti.
- Alcuni router bloccano i messaggi di ricerca tra dispositivi. Scegli la marca sotto *Inserisci l'indirizzo*
  nella procedura e scrivi l'indirizzo IP della TV, che trovi nelle impostazioni di rete della TV.
- Con Docker su Windows o macOS la ricerca non può funzionare, perché il contenitore sta dietro una rete virtuale.
  Inserisci l'indirizzo a mano. Vedi [Installazione](install.md).
- Dai alla TV un indirizzo fisso nel router (una prenotazione DHCP), così l'indirizzo che hai scritto resta valido.
- Per le TV LG, controlla le impostazioni in [LG webOS](tv-lg-webos.md).

## L'associazione non si completa
- Tieni il telecomando a portata di mano e accetta la richiesta sulla TV entro tre minuti. La TV la mostra solo
  mentre è accesa.
- Se hai premuto **No**, o non è successo nulla, usa **Riprova** nella procedura.
- Controlla che la TV non stia mostrando un altro messaggio a schermo intero o uno screensaver.

## La scheda dice "Da riaccoppiare"
La TV ha dimenticato la chiave che TVBalance conserva, per esempio dopo un ripristino di fabbrica o un aggiornamento
del software. Apri **Associa di nuovo** sulla scheda e accetta la richiesta sulla TV ancora una volta. Regole, storico
e impostazioni restano. Con Web Push attivo, quando succede ricevi anche una notifica.

## La TV è "irraggiungibile"
TVBalance non riesce a connettersi alla TV, cosa normale se la TV è scollegata. Se succede a TV accesa:

- Controlla l'indirizzo della TV nel router. Se è cambiato, rimuovi la TV e aggiungila di nuovo con il nuovo
  indirizzo, oppure dalle un indirizzo fisso.
- Controlla che le funzioni di rete della TV siano ancora attive (per LG, vedi [LG webOS](tv-lg-webos.md)).
- Riavvia completamente la TV (staccala dalla corrente per un minuto). Alcune TV smettono di rispondere dopo molto
  tempo di accensione continua.

## Una regola sembra non applicarsi
- Controlla che la TV abbia il controllo attivo (la pagina dei dettagli della TV) e che segua il set di regole che hai
  modificato.
- Sulle TV LG con **Quick Start+**, una TV con lo schermo spento risulta in standby, quindi il budget giornaliero non
  scorre. È previsto. Vedi i limiti in [LG webOS](tv-lg-webos.md).
- Un **Consenti** o **Blocca** manuale scavalca le regole finché non termina. Usa **Annulla override** sulla scheda.
- Profili, calendario e budget avanzati vengono salvati con ogni piano ma applicati solo con [Pro](pro.md). Le
  schermate lo dicono.
- Gli orari seguono il fuso orario scelto alla configurazione, non l'orologio della TV. Controllalo in
  **Impostazioni → Generali**.

## Il browser avvisa che la connessione non è privata
L'indirizzo sicuro usa un certificato di una piccola autorità creata da TVBalance. Il tuo dispositivo deve darle
fiducia una volta sola. Segui [HTTPS sulla tua rete](https.md): scarica il certificato in
**Impostazioni → Connessione sicura**, installalo e confronta l'impronta. Firefox tiene un elenco proprio, quindi
importalo anche lì.

## Nessuna notifica sul telefono
I browser consentono le notifiche push solo su una connessione sicura.

- Apri l'app web tramite Home Assistant su HTTPS, oppure tramite l'indirizzo sicuro di TVBalance, non da un indirizzo
  `http://` semplice. La scheda in **Impostazioni → Notifiche** rimanda all'indirizzo sicuro quando c'è.
- Su iPhone e iPad, aggiungi prima TVBalance alla schermata Home e attiva le notifiche da quell'icona.
- Invia una prova dalla stessa scheda. Se non arriva, consenti le notifiche per il sito o l'app nelle impostazioni
  del telefono.

## Home Assistant non trova TVBalance
- Con l'Add-on, riavvialo e cerca in **Impostazioni → Dispositivi e servizi** la notifica **TVBalance**.
- Se hai revocato il token "Home Assistant (Add-on)" in **Impostazioni → Token API**, riavvia l'Add-on: ne crea uno
  nuovo.
- Con un motore autonomo, controlla l'indirizzo, la porta e che il token abbia gli ambiti **lettura** e
  **controllo**. Vedi [Home Assistant](home-assistant.md).

## Un PIN viene rifiutato
Dopo cinque PIN errati, l'accesso con PIN si blocca per un po'. Aspetta, oppure accedi con la password
dell'amministratore e cambia il PIN in **Impostazioni → Sicurezza**.

## Password dell'amministratore dimenticata
TVBalance non ha ancora un ripristino della password, perché non viene inviato nulla fuori da casa tua. Se un browser
è ancora collegato, puoi cambiare la password in **Impostazioni → Sicurezza**. Se nessuno lo è, l'unica strada oggi è
ricominciare con una cartella dei dati vuota: si perdono regole, storico e chiavi delle TV memorizzate, e ogni TV va
associata di nuovo. Se ne hai uno, ripristina un backup fatto prima di perdere la password.

## Sei ancora bloccato
Apri una segnalazione su <https://github.com/tvbalance/tvbalance/issues> e allega il download della diagnostica. Non
pubblicare token, chiavi di licenza né il contenuto della cartella dei dati.
