# TVBalance Pro

TVBalance è gratuito per una TV. Una **licenza Pro**, acquistata una volta per tutta la famiglia, toglie il limite e
sblocca le funzioni avanzate man mano che arrivano.

| | Free | Pro |
| --- | --- | --- |
| TV supervisionate | 1 | Illimitate |
| Profili e calendario | No | Sì |
| Budget avanzati (per giorno della settimana, gruppi di app, riporto) | No | Sì |
| Storico oltre 7 giorni, uso per app, report settimanale | No | Sì |
| Regole, budget di tempo, azioni dei genitori, notifiche, Home Assistant | Sì | Sì |

La licenza è una chiave che incolli nell'app. Viene verificata sul tuo dispositivo tramite una firma, quindi non
richiede connessione a internet e di te non viene inviato nulla da nessuna parte.

## Profili e calendario

Un **profilo** è un set di regole che attivi per tutta la famiglia in una volta, per esempio "Vacanze" o "Weekend dei
nonni". Finché è attivo, ogni TV segue quello invece del proprio set di regole, tranne le TV che escludi (per esempio
la TV dei genitori).

- **A mano:** in **Regole**, premi *Attiva come profilo* su un set, scegli per quanto tempo (da 30 minuti a 4 ore,
  oppure fino a mezzanotte) e le TV da escludere. Il pannello mostra il profilo attivo con un pulsante *Termina
  profilo*.
- **Con il calendario:** in **Regole > Calendario**, aggiungi voci che attivano da sole un set di regole, ogni
  settimana in giorni e orari scelti (una fascia che finisce prima di iniziare prosegue oltre la mezzanotte) oppure tra
  due date.
- **Da Home Assistant:** i servizi `tvbalance.activate_profile` e `tvbalance.stop_profile` e il blueprint
  "calendar".

Quando ne valgono più d'uno, vince il profilo manuale più recente, poi una voce del calendario con date, poi una
settimanale, poi il set di regole della TV stessa. Terminare un profilo o lasciarlo scadere riporta ogni TV alle
proprie regole.

Puoi preparare profili e calendario con qualsiasi piano; vengono salvati ma applicati solo con una licenza Pro, e le
schermate lo dicono. Non si perde nulla se una licenza finisce.

## Budget avanzati

Il budget giornaliero di un set di regole si può affinare in **Regole > Tempo**:

- **Budget per giorno della settimana:** un numero diverso di minuti per ogni giorno, per esempio di più il sabato.
  Un giorno lasciato vuoto usa il budget giornaliero.
- **Gruppi di app:** un gruppo di app, come "Giochi", che condividono un solo tempo giornaliero. Quando il tempo del
  gruppo è esaurito le sue app vengono bloccate mentre tutto il resto resta disponibile, e un avviso compare prima che
  finisca. Scegli le app dall'elenco letto dalla TV.
- **Riporta il tempo non usato:** i minuti non usati ieri vengono aggiunti a oggi, fino a un massimo che scegli. I
  minuti riportati non si accumulano mai da un giorno all'altro.

Si possono impostare con qualsiasi piano e vengono salvati in ogni caso, ma sono applicati solo con una licenza Pro;
con Free vale il semplice budget giornaliero. Non si perde nulla se una licenza finisce.

## Storico e report settimanale

**Attività** può mostrare gli ultimi 7, 30, 90 o 365 giorni, con una barra per ogni giorno e le app, gli ingressi e i
canali più guardati di ogni TV. Con il piano Free lo storico si ferma a 7 giorni e un avviso lo dice.

Ogni lunedì alle 8:00 (ora della famiglia) è pronto il **report settimanale** della settimana precedente: quanto è
stata guardata ogni TV, in quali giorni, le app principali e quante volte un contenuto è stato bloccato. Compare in
Attività e può arrivare anche come notifica: attiva "Un report settimanale il lunedì" per un dispositivo in
**Impostazioni > Notifiche** (è disattivato per impostazione predefinita). Home Assistant riceve un evento
`weekly_report`.

## Ottenere e attivare una licenza
1. In **Impostazioni → TVBalance Pro**, scegli **Acquista Pro** (compare quando la pagina di acquisto è configurata).
2. Dopo il pagamento ricevi una chiave di licenza: una lunga riga di lettere e cifre con un punto nel mezzo.
3. Incollala in **Chiave di licenza** e scegli **Attiva**. Solo l'amministratore vede questa scheda.

La scheda mostra poi il piano, a chi è intestata la licenza e la data di scadenza, se c'è. La maggior parte delle
licenze non scade mai.

## Cosa succede con il piano Free e più TV
Puoi sempre aggiungere e configurare tutte le TV che vuoi. Con il piano Free viene supervisionata solo la **TV attiva
più vecchia**; le altre conservano le impostazioni ma non vengono controllate e sono marcate **Richiede Pro**.
Disattiva la TV più vecchia e la successiva prende il suo posto.

## Scadenza e rimozione
Non viene cancellato nulla quando una licenza scade o la rimuovi. La famiglia torna semplicemente al piano Free, e le
TV in più smettono di essere supervisionate finché non c'è di nuovo una licenza attiva. Una chiave conservata che
smette di essere valida (per esempio dopo una rotazione delle chiavi) viene trattata allo stesso modo, e la scheda
lo dice.

Rimuovere la licenza si fa in **Impostazioni → TVBalance Pro → Rimuovi la licenza**.
