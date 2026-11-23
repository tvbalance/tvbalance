# TV LG webOS

TVBalance parla con le TV LG (webOS 4 e successivi) attraverso la tua rete domestica. Niente esce da casa tua.

## Prepara la TV
1. Collega la TV alla stessa rete della macchina che esegue TVBalance.
2. Attiva **Impostazioni > Generali > Dispositivi esterni > Accensione TV con dispositivo mobile > Accendi tramite
   Wi-Fi** (chiamato *LG Connect Apps* sui modelli più vecchi). La TV accetta così le connessioni da altri
   dispositivi.
3. Dai alla TV un indirizzo fisso nel router (una prenotazione DHCP) perché resti sempre raggiungibile.

## Associa
1. Accendi la TV, tieni il telecomando a portata di mano e apri **Aggiungi una TV** nell'app web.
2. Scegli la tua TV dall'elenco. Se non c'è (alcune reti bloccano la ricerca), scegli **LG webOS** sotto
   *Inserisci l'indirizzo* e scrivi l'indirizzo IP della TV, che trovi nelle impostazioni di rete della TV.
3. Premi **Avvia l'associazione** e guarda la TV: ti chiede se consentire il nuovo dispositivo. Accetta con il
   telecomando entro tre minuti. TVBalance conserva la chiave che la TV rilascia; lo fai una volta sola per ogni TV.
4. Dai un nome alla TV e scegli il suo set di regole.

Se premi **No**, o non succede nulla, usa **Riprova**. Quando la TV dimentica la chiave (per esempio dopo un ripristino
di fabbrica) il pannello mostra **Da riaccoppiare**: apri **Associa di nuovo** sulla sua scheda e accetta ancora una
volta.

## Cosa può fare TVBalance su una LG
Leggere cosa sta andando in onda (app, ingresso HDMI, canale in diretta e programma), elencare app, ingressi e canali,
mostrare un messaggio sullo schermo, andare alla schermata iniziale, aprire un'app, un ingresso o un canale e
spegnere la TV.

## Limiti noti
- **Quick Start+**: con questa opzione la TV continua a rispondere anche a schermo spento. TVBalance la riporta come
  in standby, non come in visione, quindi il budget giornaliero non scorre.
- **I titoli dei programmi** sono disponibili solo quando la TV in diretta è in primo piano, e per niente su webOS 4.5
  e precedenti.
- **Accendere la TV** non è ancora supportato.
- Le icone delle app sono servite dalla TV con un certificato autofirmato; l'app web le mostrerà tramite un proprio
  proxy.
