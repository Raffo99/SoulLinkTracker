**6.3.1**
- **Due melonDS**: corrette due cause. L'app poteva far partire melonDS due volte se arrivava un altro avvio mentre era aperta una domanda (per esempio «Riprendere da dove avevi lasciato?»). E la finestra del touch, che è «di proprietà» della prima, poteva restare fuori dall'app: ora l'app la stacca dalla prima prima di incastrarla, e se arriva in ritardo la incastra appena compare.
- **Giocatori in alto, rifatti**: una striscia con il colore del giocatore al posto del cerchio con l'iniziale, il nome intero con le medaglie, una riga che dice cosa sta facendo («Boss: Komor», «Selvatico: Pidove Lv.6», oppure dov'è) e sotto il luogo con livello e cap. Una linea sottile sul fondo mostra quanto manca al level cap (gialla al cap, rossa sopra).

**6.3.0: impostazioni e collegamento rifatti**
- **Scelta del collegamento**: due schede affiancate, «Diretto tra le app» e «Supabase», con pro e contro di ognuna e uno schema di come viaggiano i dati. I campi di Supabase compaiono solo se lo scegli. «Prova il collegamento» funziona anche per il diretto: dice quanti relay rispondono.
- **Impostazioni a pagine**: a sinistra gli argomenti (Tu e la partita, Collegamento, Gioco, Salvataggi, Altro), a destra una pagina per ognuno, con una riga di spiegazione sotto ogni campo. Accanto al codice ci sono «Copia» e «Nuovo codice». Al primo avvio un pallino segna cosa manca.
- **Stato del collegamento in alto**, accanto al codice della partita: «In diretta con 2», «Tramite relay», «In attesa degli amici», «Senza rete» o «Supabase». Un clic apre la pagina del collegamento.
- **Scelta della partita**: una riga dice quale collegamento stai usando, con «Cambia».
- **Mosse**: la scritta fisica / speciale / stato ora sta sotto il tipo della mossa.

**6.2.1**
- **Schermi affiancati senza riavvio**: melonDS ora apre due finestre (una per lo schermo superiore, una per il touch) e l'app le mette uno sopra l'altro o affiancate (superiore a sinistra, touch a destra). Il cambio da *Altro → Schermi affiancati* è immediato. Il gioco resta nella colonna di sinistra come in verticale; le schede restano a destra.
- **Niente più "piccolo e grande"**: l'app non risistema più melonDS ogni secondo. Lo fa solo quando cambia lo spazio del gioco, e una misura nuova di menu e bordi vale solo se si ripete uguale.
- Riduci, ingrandisci e chiudi sono in orizzontale, in alto a destra.

**6.2.0: collegamento diretto tra le app**
- **Niente più Supabase obbligatorio.** Le app si trovano con il **codice della partita** sui relay Nostr pubblici, poi parlano **direttamente** (WebRTC, come una videochiamata). Se un router blocca la connessione diretta, i dati passano da relay **MQTT** pubblici, che tengono anche l'ultimo stato: chi si collega dopo lo recupera anche se gli altri sono offline. Niente server vostro, niente account, niente impostazioni del router.
- **Tutto cifrato** con la chiave del codice della partita (i relay vedono solo dati illeggibili). Viaggiano solo i dati del tracker, mai ROM o salvataggi. Ogni app tiene anche una copia della partita sul PC.
- **Supabase resta come alternativa** in *Impostazioni → Collegamento*. Chi lo usava già continua con Supabase finché non cambia. Per passare al collegamento diretto, cambiate tutti in *Diretto*: la prima app che entra si porta dietro la partita di Supabase.
- I codici nuovi sono più lunghi (es. `drago-luna-4821-k7q2xm`), perché il codice è anche la chiave della partita.
- L'exe è più grande (circa 150 MB) per via di WebRTC.

**6.1.0**
- **Backup del momento esatto e ripresa automatica, di nuovo**: ogni 10 minuti e a ogni chiusura l'app fa uno **stato salvato di melonDS** (più la copia del salvataggio). Alla partenza, se l'ultima volta hai chiuso senza salvare nel gioco, ti chiede se **riprendere da lì**. Da *Backup e ripristino* puoi tornare al momento esatto di qualsiasi backup. L'app usa gli slot 7 e 8 di melonDS; gli altri sono tuoi (Maiusc+F1…F6 salva, F1…F6 carica).
- **Schermi affiancati**: in *Altro → Schermi affiancati (in orizzontale)*: schermo superiore a sinistra, touch a destra. Il gioco diventa largo e basso, e le schede (Coppie, Percorsi…) vanno sotto il gioco. Per cambiare, melonDS si riavvia e riprende da dove eri.
- **Frecce**: girate a melonDS, le frecce erano lette come tasti del tastierino numerico e non muovevano il personaggio. Ora vanno. Quando il gioco è selezionato l'app gli ridà la tastiera anche se se l'era ripresa.
- **Cimitero con le tombe**: ogni Pokémon morto ha la sua lapide, con il Pokémon in grigio, il nome inciso, livello, luogo e il giocatore. Doppio clic per correggere.
- **Stato in Coppie**: non resta più «SON». Lo stato in lotta si legge come fa l'Ironmon Tracker (un contatore per ogni stato).
- **In alto, in lotta con un allenatore**: si vede il Pokémon avversario in campo adesso, non sempre il primo.
- **Tracker della lotta senza sfarfallio**: si ridisegna solo quando cambia qualcosa, e tutto in un colpo.
- **Niente barra del titolo di Windows**: riduci, ingrandisci e chiudi sono in alto a destra nell'app. La finestra si sposta trascinando la barra in alto (doppio clic per ingrandirla) e si ridimensiona dai bordi.
- **Schermi piccoli**: tutto si stringe (barra in alto più bassa, titolo e conteggi nascosti, pulsanti più corti), la finestra può diventare molto più piccola, e al primo avvio sta nello schermo (sugli schermi piccoli parte ingrandita). L'app ricorda posizione e dimensione.
- **Più pulita**: tolti la scritta sotto il gioco, i pallini melonDS/Script/Supabase in basso, «Dove sei» con allenatori e strumenti, e le schede Obiettivi, Statistiche e Diario. Il prossimo obiettivo con la mappa resta in alto a destra.
- Il bordo intorno agli schermi ora ha gli angoli vivi, come gli schermi.

**6.0.1**
- **Tastiera**: i tasti arrivano al gioco. melonDS sta dentro l'app e la tastiera a volte restava all'app; ora quando il gioco è selezionato (all'avvio, o dopo un clic sugli schermi o sulla cornice) l'app gira i tasti a melonDS. Un clic sul resto dell'app (Coppie, menu…) restituisce la tastiera all'app; nei campi di testo si scrive normalmente.
- **Schermo centrato e grande quanto la cornice**: l'app misura dove sta davvero lo schermo dentro la finestra di melonDS (menu, bordi, scala dello schermo) e lo fa coincidere con l'apertura della cornice, invece di stimare l'altezza del menu.
- **Volume dall'app**: nuovo pulsante 🔈 in basso con un cursore da 0 a 100%, che si può usare mentre giochi (agisce sul volume di melonDS nel mixer di Windows). Il volume parte dal **5%** e l'app se lo ricorda.

**Versione 6: l'emulatore adesso è melonDS.**

- **melonDS al posto di BizHawk.** La prima volta l'app scarica melonDS da sola (circa 20 MB, dalle release ufficiali su GitHub) e ne usa una copia sua, con le impostazioni giuste per il tracker. In *Impostazioni* non c'è più da indicare BizHawk.
- **Il gioco al centro, in una cornice**: i due schermi uno sopra l'altro con le proporzioni del DS, dentro una cornice che ricorda la console. Il menu di melonDS è nascosto. Per cambiare i tasti: **Altro → Mostra il menu di melonDS** → *Config → Input and hotkeys*.
- **Tasti predefiniti**: X = A · Z = B · S = X · A = Y · Q = L · W = R · Invio = Start · Backspace = Select · frecce; il touch screen con il mouse. Quelli che cambi in melonDS restano.
- **Riprendi la run da dove eri**: alla prima partenza l'app copia da sola il salvataggio della run in corso dalla cartella di BizHawk.
- **Backup**: ora sono copie del salvataggio del gioco, ogni 10 minuti e a ogni chiusura; *Backup e ripristino* rimette quello che scegli. Conta l'ultimo salvataggio fatto nel gioco, quindi salva spesso. Per un punto preciso ci sono gli stati di melonDS (Maiusc+F1…F8 salva, F1…F8 carica).
- **Velocità**: il pulsante accende e spegne l'avanti veloce di melonDS. Cambiare il numero (per esempio da ×3 a ×4) vale dal prossimo *Riavvia gioco*. Tab tenuto premuto resta l'avanti veloce.
- La tastiera arriva al gioco solo quando il gioco è selezionato: niente più tasti che muovono il personaggio mentre scrivi altrove.
- Niente più "ponte" di rete con l'emulatore: lo script del tracker gira dentro l'app e legge direttamente la memoria di melonDS. Tutto il resto (tracker della lotta, regole sull'esperienza, allenatori e strumenti, obiettivi…) funziona come prima.
- Nuovo **README** con il riassunto dell'app.
