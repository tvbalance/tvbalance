# Domande frequenti

## TVBalance richiede un account o internet?
No. Gira sulla tua rete e parla direttamente con la TV. Non c'è alcun account cloud né telemetria. La licenza Pro è
una chiave firmata verificata sul tuo dispositivo, quindi non richiede nemmeno una connessione.

## Dove sono i miei dati?
Nella cartella dei dati del motore (`/data` nell'Add-on e in Docker): il database `tvbalance.db` con TV, regole,
storico d'uso ed eventi, e `secret.key`, che protegge le credenziali delle TV memorizzate. I dati dell'Add-on fanno
parte dei backup di Home Assistant. Tieni insieme il database e la chiave.

## Quali TV sono supportate?
LG webOS 4 e successivi è supportata e verificata su hardware reale. Roku, Google/Android TV e Samsung Tizen sono
previste e per ora non utilizzabili. Ogni marca può fare cose diverse, e l'app offre solo ciò che la TV può fare
davvero. Vedi [LG webOS](tv-lg-webos.md) per cosa supporta una LG.

## Funziona senza Home Assistant?
Sì. L'app web funziona da sola, con Docker o con l'Add-on. Home Assistant aggiunge entità, servizi, eventi e
blueprint per le automazioni. Vedi [Installazione](install.md) e [Home Assistant](home-assistant.md).

## Cosa è gratis e cosa è Pro?
Una TV con tutte le regole di base (orari, budget giornalieri, blocco di app, ingressi e canali, azioni dei genitori,
notifiche, Home Assistant) è gratis. Pro è una licenza una tantum per la famiglia che permette più TV, profili e
calendario, budget avanzati, storico lungo e report settimanali. Vedi [TVBalance Pro](pro.md).

## Cosa succede se la mia licenza Pro scade?
Non viene cancellato nulla. Le impostazioni Pro restano salvate e smettono di essere applicate: le TV oltre la prima
non sono più supervisionate e le regole tornano a quelle di base. Aggiungi una licenza valida e tornano ad
applicarsi.

## Mio figlio può aggirarlo?
TVBalance agisce sulla TV, quindi un telefono o un altro telecomando non servono. È uno strumento di famiglia, non un
lucchetto: chi ha accesso al menu delle impostazioni della TV può comunque staccarla o cambiare la rete. Usa il PIN
della TV e un PIN per i comandi dei genitori di TVBalance sui dispositivi condivisi. Per cambiare le regole serve la
password dell'amministratore.

## Posso usare più TV?
Sì, con [Pro](pro.md). Ogni TV segue un set di regole, e più TV possono condividere lo stesso set.

## Quali lingue sono disponibili?
Inglese, italiano, tedesco, francese e spagnolo. L'app web segue il browser o Home Assistant e puoi cambiarla in
**Impostazioni → Generali**. Questa documentazione è disponibile nelle stesse cinque lingue.

## Funziona con HTTPS?
Sì. HTTPS è attivo per impostazione predefinita, con un certificato di un'autorità locale a cui i tuoi dispositivi
danno fiducia una volta sola. Puoi anche usare un tuo certificato. Vedi [HTTPS sulla tua rete](https.md).

## Come aggiorno?
Con l'Add-on, aggiornalo dall'Add-on Store. Con Docker, scarica la nuova immagine e ricrea il contenitore. I tuoi dati
e le tue impostazioni restano e il database viene aggiornato all'avvio.

## Come segnalo un problema o chiedo una marca di TV?
Apri una segnalazione su <https://github.com/tvbalance/tvbalance/issues>. Allega il download della diagnostica e non
pubblicare token o chiavi di licenza. Gli sviluppatori possono aggiungere una marca da soli con un pacchetto adattatore:
vedi [Scrivere un adattatore](../developers/adapters.md) (in inglese).
