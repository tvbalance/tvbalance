# Primi passi

Dall'installazione a una TV che segue le tue regole bastano circa cinque minuti. Ti servono TVBalance
[installato](install.md) e la TV accesa, sulla stessa rete.

## 1. Apri l'app web
Apri il pannello **TVBalance** in Home Assistant, oppure `http://<indirizzo-della-macchina>:8765` se usi Docker. La
prima visita avvia la configurazione.

## 2. Configura la famiglia
L'app ti chiede tre cose:

1. **Una password** per l'amministratore, di almeno 10 caratteri. Conservala con cura.
2. **Lingua e fuso orario.** Gli orari e i limiti giornalieri seguono questo fuso orario.
3. **Un primo set di regole.** Parti da "Giorni di scuola" oppure da un set vuoto. Potrai cambiare tutto dopo.

## 3. Aggiungi la TV
Scegli **Aggiungi una TV**. La procedura cerca nella rete e mostra le TV trovate. Se la tua non c'è, inserisci il suo
indirizzo a mano. Segui i passaggi per la tua marca, per esempio [LG webOS](tv-lg-webos.md): la TV ti chiede di
accettare il nuovo dispositivo e lo fai una volta sola con il telecomando.

Dai un nome alla TV e scegli il set di regole che deve seguire. Fatto: la scheda della TV nel pannello mostra cosa
sta andando in onda, quanti minuti sono stati guardati e quanti ne restano.

## 4. Verifica che funzioni
- Apri un'app che le regole bloccano, oppure aspetta la fine di una fascia consentita. TVBalance mostra un messaggio
  sulla TV e la riporta alla schermata iniziale, oppure la spegne, secondo il set di regole.
- Prova **Pausa** sulla scheda della TV: i blocchi si fermano per 30 minuti.
- Prova **Bonus** per aggiungere 15 o 30 minuti al budget di oggi.

## 5. Collega Home Assistant
Con l'Add-on, conferma la notifica **TVBalance** in **Impostazioni → Dispositivi e servizi**. Ogni TV diventa un
dispositivo con sensori, un pulsante di pausa ed eventi da usare nelle automazioni. Vedi
[Home Assistant](home-assistant.md).

## 6. Usalo dal telefono
Per le notifiche sul telefono e un'icona simile a un'app, apri l'indirizzo sicuro e dai fiducia al certificato una
volta sola. Vedi [HTTPS sulla tua rete](https.md).

## Dove andare dopo
- [L'app web](web-ui.md): regole, pannello, attività e impostazioni nel dettaglio.
- [TVBalance Pro](pro.md): profili, calendario, budget avanzati e report.
- [Risoluzione dei problemi](troubleshooting.md) se la TV non si trova o la connessione si perde.
