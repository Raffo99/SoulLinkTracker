# Soul Link Tracker 4.9 – Pokémon Nero 2 / Bianco 2

Un'app per Windows con BizHawk dentro, per giocare una Randomizer Soul Link Nuzlocke **da 2 a 4 giocatori**. Le regole del Soul Link le applica l'app stessa; la partita condivisa sta in un piccolo database gratuito su **Supabase**. Niente sito, niente porte da aprire sul router, e non serve che l'altro sia acceso.

## Cosa fa da sola
- **Incontri e catture**: riconosce lotte selvatiche, luogo, primo incontro, cattura o fallimento. Il **primo selvatico della run (tutorial) non conta**.
- **Gruppi legati e morti**: tutti i Pokémon catturati nello stesso luogo formano un gruppo (coppia con 2 giocatori, fino a 4 con 4). Se ne muore uno muoiono tutti, e se anche un solo giocatore fallisce l'incontro il gruppo si rompe e gli altri vanno nel box. Il game over parte da solo.
- **PC e medaglie**: legge il PC e le medaglie; il level cap sale da solo.
- **Obiettivi a tappe**: 9 tappe della storia (da *Si parte!* ad Alisopoli fino alla *Lega Pokémon*), ognuna con i suoi sotto-obiettivi: le lotte importanti (capipalestra, rivale, Team Plasma, Superquattro, Iris) più qualche piccola sfida (prima cattura, squadra di 4, prima evoluzione, squadra al completo). Si segnano da soli, con il tempo dall'inizio della run come negli speedrun. Quando tutti battono Iris, la run è vinta.
- **Traguardi bonus**: 8 traguardi facoltativi, per esempio *Palestra impeccabile* (medaglia senza perdite dalla precedente), *Disciplina* (medaglia con tutta la squadra entro il cap), *Fedele compagno* (starter vivo alla 4ª medaglia), *Colpo di fortuna* (uno shiny).
- **Notifiche e statistiche**: morti, legami, obiettivi e traguardi compaiono come notifiche nell'angolo. La scheda *Statistiche* mostra i numeri della run per ogni giocatore e i record tra una run e l'altra.
- **Nuova run**: genera la ROM randomizzata, riparte dal salvataggio di partenza e riavvia BizHawk sulla ROM giusta.
- **Regole**: clausola doppioni, clausola shiny e incontro del tutorial, nel menu *Regole*.

---

## 1. Supabase (una volta sola, lo fa uno dei due)
1. Vai su **supabase.com**, crea un account e un **New project** gratuito. Come regione va bene *Central EU (Frankfurt)*.
2. Apri **SQL Editor**, incolla tutto il file `supabase/schema.sql` e premi **Run**.
3. Copia l'**URL del progetto** (tipo `https://abcdefgh.supabase.co`): lo trovi nella pagina principale del progetto o in *Project Settings → Data API*.
4. In *Project Settings → API Keys* copia la **Publishable key** (`sb_publishable_…`). Va bene anche la vecchia chiave *anon*.
5. Scegli un **codice della partita**, cioè una parola segreta tipo `pikachu-raffo-2026`. È la "chiave" della vostra partita: chi non la conosce non la vede.
6. Manda URL, chiave e codice agli amici (fino a 4 giocatori in tutto, ognuno con un nome diverso).

Il piano gratuito basta e avanza: l'app scarica la partita solo quando cambia qualcosa (pochi KB a sessione). Supabase **mette in pausa i progetti gratuiti dopo un periodo senza uso**. Se succede, l'app segnala l'errore: entra su supabase.com e premi *Restore*.

## 2. L'exe (GitHub lo crea per voi)
1. Crea un repository su **github.com** (anche privato) e caricaci il contenuto di questa cartella. Con GitHub Desktop: *Add existing repository* → *Publish*. Se trascini i file a mano, carica anche la cartella `.github`.
2. Nella scheda **Actions** parte **"Crea exe"**: dopo 3-4 minuti apri l'esecuzione e scarica **Artifacts → SoulLinkTracker**.

ROM, randomizer e salvataggi non finiscono mai su GitHub: sono esclusi da `.gitignore`.

## 3. Primo avvio
Ti serve: **BizHawk 2.9+**, **Java a 64 bit** (adoptium.net, "Windows x64"), **Universal Pokémon Randomizer ZX** e la tua **ROM** di Nero 2.

1. Avvia `SoulLinkTracker.exe`. Se Windows avvisa che non è firmato: *Ulteriori informazioni → Esegui comunque*.
2. Nelle **Impostazioni** inserisci:
   - il tuo nome (diverso da quello dell'amico);
   - URL, chiave e codice di Supabase (prova con *Prova collegamento*);
   - dove sta `EmuHawk.exe`;
   - il randomizer (`PokeRandoZX.jar`), le impostazioni (`.rnqs`, uguali per tutti) e la tua ROM di Nero 2.

   La finestra delle impostazioni si può rimpicciolire: il contenuto scorre.
3. L'app genera la ROM della run attuale e apre BizHawk dentro la finestra.

L'app usa una configurazione di BizHawk tutta sua. In quella configurazione è attiva l'opzione che fa arrivare i tasti al gioco anche quando BizHawk è dentro un'altra finestra; conseguenza: i tasti arrivano al gioco anche con l'app non in primo piano.

## 4. Saltare l'inizio del gioco
Il salvataggio di partenza viene copiato su ogni ROM nuova, così si riparte da lì premendo *Continua*. Lo starter resta quello randomizzato della ROM nuova, perché lo ricevi dopo.

- **Automatico**: se nella prima run salvi prima di prendere lo starter, quando lo ricevi l'app mette da parte quell'ultimo salvataggio.
- **Scegliendo tu il punto** (consigliato, così si risparmia più tempo): salva il più vicino possibile alla **Vedetta di Alisopoli**, prima della scena dello starter. Poi premi **Salvataggio di partenza → Usa il salvataggio attuale come partenza**. Se lo starter è già in squadra, l'app lo rifiuta.

Il file sta in `Documenti\SoulLink Tracker\salvataggio_base.SaveRAM`. Puoi cancellarlo dallo stesso menu.

## 5. L'interfaccia
- **In alto**: run, durata, catture, legami vivi e morti. Poi una scheda per ogni giocatore con le medaglie, i PS della squadra, il livello più alto rispetto al level cap e **cosa sta facendo in questo momento**:
  - **IN GIRO** con la zona in cui si trova;
  - **SELVATICO** con il Pokémon incontrato, il livello e i PS rimasti;
  - **ALLENATORE** durante una lotta contro un allenatore qualsiasi;
  - **BOSS** contro capopalestra, rivale, Team Plasma, Superquattro e Iris (la scheda si colora);
  - **IN ATTESA** se l'app è aperta ma il gioco no, **OFFLINE** se l'app è chiusa.
  Lo stato degli altri arriva in 3–4 secondi. Passa col mouse su una scheda per vedere la squadra intera.
- **Prossimo obiettivo**: chi devi battere e il livello massimo adesso, più i progressi degli altri.
- **Dove sei**: se nel luogo attuale hai ancora l'incontro, per te e per gli altri.
- **Coppie**: ogni tuo Pokémon accanto ai suoi partner (fino a 3), con livello e PS. Se un partner è nel box la riga diventa gialla.
- **Altre schede**: Percorsi (tasto destro per correggere), Obiettivi (tappe e traguardi; doppio clic per correggere), Cimitero, Statistiche, Diario, Sistema (registro dell'app e diagnostica).

Sopra il gioco, in BizHawk, non compare nessuna scritta: messaggi e avvisi arrivano come notifiche nell'app. Ogni giocatore ha un colore (avatar, nomi nelle coppie, colonne di Percorsi e Obiettivi), uguale per tutti. Il carattere usato è Inter (licenza SIL OFL, in `risorse/font`).

## Tracker della lotta
Quando inizi una lotta, al posto di *Prossimo obiettivo* e *Dove sei* compare la lotta, con le informazioni sui **tuoi** Pokémon. Dell'avversario vedi solo quello che vedi anche nel gioco: il Pokémon in campo (nome e livello) e, per gli allenatori, quanti Pokémon hanno (come le Poké Ball del gioco), mai quali. Quando un Pokémon dell'allenatore va KO, il successivo compare solo qualche secondo dopo, quando entra in campo:
- la tua squadra, ognuno con il miglior moltiplicatore che ha contro l'avversario: clicca quello che hai in campo;
- il Pokémon scelto: tipi, PS, stato e **abilità con la descrizione**;
- le sue mosse: il nome è **verde** se superefficace (rosso se poco efficace, grigio se non ha effetto), una **stella dorata** se è dello stesso tipo del Pokémon (STAB), poi tipo, potenza, moltiplicatore totale (efficacia × 1,5 se STAB: per esempio superefficace + STAB = ×3) e PP.
I dati delle mosse sono quelli di Nero 2/Bianco 2. PS e PP sono quelli di inizio lotta (durante la lotta il gioco li tiene altrove). La fine della lotta si riconosce da quando il codice di lotta del gioco sparisce dalla memoria, quindi il riquadro resta anche nelle lotte lunghe.

## Correggere il tracker
- **Doppio clic** su un Pokémon (nelle Coppie o nel Cimitero), oppure tasto destro → *Modifica…* nei Percorsi: puoi cambiare lo stato, riportarlo in vita insieme ai suoi legati, cambiare il luogo della cattura (cambia anche il legame), contarlo come cattura valida o toglierlo dal tracker. Ogni correzione resta scritta nel diario.
- **Altro → Controlla il tracker con il gioco…** confronta i tuoi Pokémon con squadra e PC letti dalla memoria: Pokémon morti nel tracker ma vivi nel gioco, liberati che sono ricomparsi, Pokémon che non trovo più. Se dopo un backup ricaricato (o all'avvio del gioco) le cose non tornano, la finestra si apre da sola.

## Regole opzionali
Dal menu **Regole** scegli cosa usare: tutorial, clausola doppioni, clausola shiny, **tipo primario unico in squadra** (spento finché non lo attivi), avviso del **level cap**, **Condividi esperienza** (tutta la squadra prende esperienza, anche chi non ha combattuto: si usa con o senza la modalità qui sotto) ed esperienza solo dagli allenatori.

## Tempo della run
Il tempo in alto conta solo quando almeno un giocatore sta giocando: se nessuno ha il gioco aperto si ferma.

## Tasti
Quando usi un'altra finestra (Discord, il browser…) il gioco ignora la tastiera, anche se BizHawk è incastrato nell'app. Le scorciatoie di BizHawk che potevano scattare per sbaglio (F = avanza di un frame, Pausa, F1–F10…) sono disattivate. Se giochi con il controller tenendo l'app in secondo piano, togli la spunta in *Impostazioni*.

## Modalità sperimentale: esperienza solo dagli allenatori
Per run senza farmare: **Regole → Esperienza solo dagli allenatori (sperimentale)**. Vale per tutti i giocatori della partita.
- **Selvatici**: non danno esperienza. Niente livelli che salgono e poi tornano indietro: il gioco proprio non la assegna.
- **Allenatori**: danno quanto basta per portare il tuo **primo Pokémon** della squadra al livello del Pokémon più forte di quell'allenatore, senza mai superare il level cap. Se sei già a quel livello o sopra, niente esperienza. Se in lotta usi più Pokémon, se la dividono come sempre. Livelli, mosse nuove ed evoluzioni li gestisce il gioco normalmente.
- All'inizio di ogni lotta con un allenatore una notifica dice quanta esperienza darà (per esempio "esperienza ×3"), senza svelare niente della sua squadra. In alto compare la scritta *EXP solo dagli allenatori*.

Come funziona: come i codici Action Replay "moltiplicatore di esperienza", durante la lotta l'app cambia due istruzioni del calcolo dell'esperienza (×0 per i selvatici, ×N per gli allenatori) e a fine lotta le rimette com'erano. Le tocca solo se trova esattamente il codice atteso; la prima volta lo cerca da sola e poi si ricorda dove sta. Se nella tua versione non lo trova, te lo dice e l'esperienza resta normale.

## Backup e chiusura
- **Backup automatici**: ogni 10 minuti l'app salva il punto esatto in cui sei (uno stato salvato di BizHawk) insieme a una copia del salvataggio del gioco. L'intervallo si cambia in *Impostazioni → Backup automatico ogni*.
- **Quando chiudi con la X** l'app fa un backup del momento e poi chiude BizHawk per conto suo: non serve più rispondere a nessuna domanda. Lo stesso succede quando cambi partita o riavvii il gioco.
- **Al prossimo avvio**, se dopo l'ultimo backup non avevi salvato nel gioco, l'app ti chiede se vuoi **riprendere da lì**.
- **Altro → Backup e ripristino…** mostra i backup della run: puoi farne uno subito, riprendere da uno qualsiasi, rimettere solo il salvataggio del gioco di quel momento o aprire la cartella (`Documenti\SoulLink Tracker\backup\<codice>\run<N>`).

Il tracker non torna indietro: se riprendi da un backup, morti e catture già registrate restano. L'app tiene gli ultimi 12 backup automatici e gli ultimi 6 fatti alla chiusura; quelli che fai tu restano (fino a 30).

## Più partite
Puoi avere più Soul Link contemporaneamente, per esempio uno con un gruppo di amici e uno con un altro: ogni partita ha il suo **codice**.
- **All'avvio** l'app chiede quale partita giocare. Per ognuna vedi a che run siete, chi ci gioca, le medaglie di ciascuno, chi è online e quando ci hai giocato l'ultima volta. Se non vuoi la domanda ogni volta, togli la spunta *Chiedi ogni volta all'avvio*.
- **Durante il gioco** clicca sul codice in alto, accanto al titolo (oppure **Altro → Cambia partita…**). L'app chiude BizHawk, quindi salva prima in gioco, e riapre il gioco della partita scelta.
- **Nuova partita** propone un codice tipo `drago-luna-4821`: mandalo agli amici. Loro usano **Entra con un codice**.
- **Togli** toglie una partita dalla lista, e se vuoi cancella anche ROM e salvataggi di quella partita dal PC. La partita online resta: gli amici possono continuare e tu puoi rientrare con il codice.

ROM, salvataggi di BizHawk e progressi di ogni partita sono separati: le ROM stanno in `Documenti\SoulLink Tracker\rom\<codice>`, e il *Reset totale* cancella solo i file della partita in corso. Il salvataggio di partenza (quello prima dello starter) invece è uno solo e vale per tutte le partite. La partita che usavi con la versione precedente compare da sola nella lista, con i suoi salvataggi.

## Reset totale
**Altro → Reset totale…** permette di ricominciare da zero la partita in corso (le altre partite non vengono toccate). Puoi scegliere:
- **azzerare la partita condivisa** (run #1, storico e obiettivi cancellati). Vale per tutti: anche le app degli amici passano da sole a ROM nuove, perché la partita cambia "edizione" e le vecchie ROM non vengono più riprese;
- **cancellare dal tuo PC** le ROM generate e i salvataggi di BizHawk delle run (salvataggi del gioco e stati salvati);
- **cancellare anche il salvataggio di partenza** (di solito conviene tenerlo).

Per sicurezza bisogna scrivere RESET. BizHawk viene chiuso prima di cancellare e riaperto alla fine con la ROM nuova.

## Da verificare la prima volta
La lettura della memoria è la stessa che hai già verificato con la diagnostica sulla tua versione italiana. La parte nuova è l'incastro della finestra di BizHawk, che ho potuto provare solo con un BizHawk simulato (il mio ambiente non è Windows). Se BizHawk si apre fuori dalla finestra, non riceve i tasti o è tagliato, mandami la scheda **Registro** e uno screenshot.
