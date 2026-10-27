# Soul Link Tracker 4.9 – Pokémon Nero 2 / Bianco 2

Un'app per Windows con BizHawk dentro, per giocare una Randomizer Soul Link Nuzlocke **da 2 a 4 giocatori**. Le regole del Soul Link le applica l'app stessa; la partita condivisa sta in un piccolo database gratuito su **Supabase**. Niente sito, niente porte da aprire sul router, e non serve che l'altro sia acceso.

## Cosa fa da sola
- **Incontri e catture**: riconosce lotte selvatiche, luogo, primo incontro, cattura o fallimento. Il **primo selvatico della run (tutorial) non conta**.
- **Gruppi legati e morti**: tutti i Pokémon catturati nello stesso luogo formano un gruppo (coppia con 2 giocatori, fino a 4 con 4). Se ne muore uno muoiono tutti, e se anche un solo giocatore fallisce l'incontro il gruppo si rompe e gli altri vanno nel box. Il game over parte da solo.
- **PC e medaglie**: legge il PC e le medaglie; il level cap sale da solo.
- **Obiettivi del gioco**: le 20 lotte importanti di Nero 2 in ordine di storia (rivale, gli 8 capipalestra, il Team Plasma, i Superquattro e Iris), ognuna col luogo dove si combatte. Si segnano da soli, con il tempo dall'inizio della run come negli speedrun. Quando tutti battono Iris, la run è vinta.
- **Mappa di Unima**: uno schema con città e percorsi, dove sono tutti gli obiettivi (fatti, il tuo prossimo, quelli dopo) e dove si trova ognuno di voi.
- **Notifiche e statistiche**: morti, legami e obiettivi compaiono come notifiche nell'angolo. La scheda *Statistiche* mostra i numeri della run per ogni giocatore e i record tra una run e l'altra.
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
1. Crea un repository su **github.com** (pubblico, se vuoi gli aggiornamenti automatici) e caricaci il contenuto di questa cartella. Con GitHub Desktop: *Add existing repository* → *Publish*. Se trascini i file a mano, carica anche la cartella `.github`.
2. Nella scheda **Actions** parte **"Crea exe"**: dopo 3-4 minuti l'exe è nella pagina **Releases** della repo (e anche in *Actions → Artifacts → SoulLinkTracker*).

ROM, randomizer e salvataggi non finiscono mai su GitHub: sono esclusi da `.gitignore`.

## Aggiornamenti automatici
All'avvio l'app guarda su GitHub se c'è una versione nuova. Se c'è, mostra le novità e chiede: **Aggiorna e riavvia** scarica il nuovo exe, lo controlla, fa un backup della partita, chiude BizHawk e riparte da sola con la stessa partita. Puoi anche dire *Più tardi* o *Salta questa versione*, cercare a mano da **Altro → Cerca aggiornamenti…** e spegnere il controllo in *Impostazioni*.

Perché funzioni la repo GitHub deve essere **pubblica** (le versioni di una repo privata non si vedono senza credenziali). L'exe va tenuto in una cartella tua (per esempio Documenti o il Desktop), non in *Programmi*, così l'app può sostituirlo.

**Per pubblicare una versione nuova** (lo fa chi gestisce la repo):
1. cambia il numero in `app/sl/__init__.py` (per esempio `VERSIONE = "5.1.0"`);
2. scrivi le novità in `NOVITA.md`;
3. carica le modifiche sul ramo `main`.
GitHub crea l'exe e pubblica da solo la Release `v5.1.0`: le app di tutti la trovano al prossimo avvio. Se il numero non cambia, l'exe si crea lo stesso (in *Actions*) ma non viene pubblicato come aggiornamento.

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
- **Scegliendo tu il punto** (consigliato, così si risparmia più tempo): salva il più vicino possibile alla **Vedetta di Alisopoli**, prima della scena dello starter. Poi premi **Partenza → Usa il salvataggio attuale come partenza**. Se lo starter è già in squadra, l'app lo rifiuta.

Il file sta in `Documenti\SoulLink Tracker\salvataggio_base.SaveRAM`. Puoi cancellarlo dallo stesso menu.

## 5. L'interfaccia
- **In alto**: run, durata, catture, legami vivi e morti. Poi una scheda per ogni giocatore con le medaglie, dov'è, il livello più alto rispetto al level cap (Lv 14/18: livello/cap) e **cosa sta facendo in questo momento**:
  - **IN GIRO** con il luogo in cui si trova e, sotto, il prossimo obiettivo;
  - **SELVATICO** con il Pokémon incontrato e il livello;
  - **ALLENATORE** con il nome dell'allenatore (per esempio *Pupa Lucia*);
  - **BOSS** con il nome del capopalestra, del rivale, del Team Plasma, dei Superquattro o di Iris (la scheda si colora);
  - in lotta, sotto, c'è anche il luogo (📍) dove si combatte;
  - **IN ATTESA** se l'app è aperta ma il gioco no, **OFFLINE** se l'app è chiusa.
  Lo stato degli altri arriva in 3–4 secondi. Passa col mouse su una scheda per vedere la squadra intera.
- **Prossimo obiettivo**: chi devi battere, dove (📍) e il livello massimo adesso, con una piccola mappa centrata su di te e sul prossimo obiettivo (clic per aprire la mappa grande), più i prossimi obiettivi degli altri.
- **Dove sei**: quanti **allenatori** ci sono ancora da battere e quanti **strumenti** da raccogliere nel luogo, e se hai ancora l'incontro, per te e per gli altri.
- **Coppie**: ogni tuo Pokémon accanto ai suoi partner (fino a 3), con livello e PS. Se un partner è nel box la riga diventa gialla.
- **Altre schede**: Percorsi (tasto destro per correggere), Obiettivi (l'elenco con chi li ha fatti, doppio clic per correggere, e il pulsante per la mappa grande), Cimitero, Statistiche, Diario, Sistema (registro dell'app e diagnostica).

Sopra il gioco, in BizHawk, non compare nessuna scritta: messaggi e avvisi arrivano come notifiche nell'app. Ogni giocatore ha un colore (avatar, nomi nelle coppie, colonne di Percorsi e Obiettivi), uguale per tutti. Il carattere usato è Inter (licenza SIL OFL, in `risorse/font`).

## Tracker della lotta
Quando inizi una lotta, al posto di *Prossimo obiettivo* e *Dove sei* compare la lotta, con le informazioni sui **tuoi** Pokémon. Dell'avversario vedi solo quello che vedi anche nel gioco: il Pokémon in campo (nome e livello) e, per gli allenatori, quanti Pokémon hanno (come le Poké Ball del gioco, grigie quando vanno KO), mai quali. Il tracker cerca da solo nella memoria del gioco le strutture della lotta (PS, stato, PP e modifiche di ogni Pokémon) e segue chi è in campo: all'inizio il tuo primo Pokémon in piedi, poi quello che usa una mossa o prende un colpo; per l'avversario, quando va KO, il successivo. Dall'alto in basso:
- la tua squadra, ognuno con il miglior moltiplicatore contro l'avversario: è selezionato quello in campo, ma puoi cliccarne un altro per confrontarlo;
- la **striscia dell'avversario**: nome, livello, tipi, PS in percentuale, stato, **modifiche alle statistiche** (Att +1, Dif −1…) e la sua **abilità** con la descrizione, ma solo dopo che il gioco l'ha mostrata;
- il riquadro del tuo Pokémon: nome, tipi, stato, barra dei PS e le **statistiche in caselle** (verde quella aumentata dalla natura, rossa quella diminuita, accanto le modifiche in lotta come +1 o −2), più la natura;
- l'**abilità** e tra quanti livelli arriva la **prossima mossa** (quale non si dice), su una riga; la descrizione dell'abilità compare passando sopra col mouse;
- le **mosse in quattro riquadri** come nel gioco, colorati col tipo: nome **verde** se superefficace (rosso se poco efficace, grigio se non ha effetto), **stella dorata** se STAB, a destra il moltiplicatore totale (efficacia × 1,5 se STAB: superefficace + STAB = ×3), sotto la **potenza in grande** (arancione se la mossa è fisica, azzurra se speciale), tipo e PP, e una **nota sugli effetti** (probabilità di stato, statistiche che cambiano, priorità, colpi multipli, contraccolpo, danni particolari come Movimento Sismico o Superzanna). Col mouse sopra c'è anche la descrizione del gioco.
PS, PP e modifiche alle statistiche del Pokémon in campo sono in tempo reale. La fine della lotta si riconosce da quando il codice di lotta del gioco sparisce dalla memoria, quindi il riquadro resta anche nelle lotte lunghe.

## Mappa, obiettivi e tappe della storia
Gli obiettivi sono solo quelli veri del gioco, nell'ordine della storia di Nero 2: rivale ad Alisopoli e alla Fattoria di Venturia, Komor, Velia, Artemisio, Camelia, Rafan, rivale al PWT, Anemone, rivale a Spiraria, Aristide, Ciprian, Acromio sulla Fregata Plasma e Ghecis alla Fossa Gigante, rivale alla Via Vittoria, i Superquattro e Iris.
In mezzo ci sono le **tappe della storia**: i posti dove bisogna andare per proseguire, per esempio il Cantiere di Zondopoli, il **Pokéwood** (il primo film serve per la nave), le Fogne di Austropoli, il Ponte Libecciopoli, la Torre Cielo, Poggiovento e il Monte Antipodi, la Grotta Costiera. Una tappa si segna da sola quando ci passi (o quando hai già battuto un obiettivo che viene dopo). La scheda *Obiettivi* mostra tutta la storia con chi ha fatto cosa; nel riquadro *Prossimo obiettivo* compare "Prima: …" quando c'è un posto da raggiungere prima della prossima lotta importante.
La **mappa di Unima** (clic sulla piccola mappa nel riquadro *Prossimo obiettivo*, o pulsante nella scheda *Obiettivi*) è uno schema disegnato dall'app, non la mappa del gioco: città e percorsi collegati, i simboli degli obiettivi (numero della medaglia per i capipalestra, R rivale, P Team Plasma, 4 Lega, ✓ fatto da tutti), un anello viola che pulsa sul tuo prossimo obiettivo, un rombo azzurro sulla prossima tappa della storia e un cerchio colorato per ognuno di voi dove si trova adesso. Passa col mouse su un luogo per vedere obiettivi e giocatori lì.

## Allenatori e strumenti del luogo
Nel riquadro *Dove sei* compaiono quanti allenatori ci sono ancora da battere e quanti strumenti da raccogliere, contando tutto il luogo (anche le case e gli edifici con lo stesso nome). L'app li legge dalla vostra ROM (chi c'è sulla mappa) e dalla memoria del gioco (cosa hai già raccolto). Gli strumenti sono quelli visibili nelle Poké Ball a terra, non quelli nascosti. Per gli allenatori battuti, all'inizio l'app conta le lotte vinte che ha visto in questa run; dopo un paio di lotte vinte contro allenatori capisce dove il gioco li segna e li legge direttamente da lì (anche quelli battuti prima).

## Scheda dei Pokémon
Nelle **Coppie** ogni Pokémon mostra anche lo stato (addormentato, scottato, paralizzato…) e i PS, in tempo reale durante la lotta (anche quelli degli amici). Clicca un Pokémon, tuo o di un amico, per aprire la sua scheda: PS ed esperienza che manca al prossimo livello, abilità, natura, statistiche con le barre, mosse (tipo, categoria, potenza, precisione, PP), quante mosse impara e tra quanti livelli la prossima, i legami. La scheda si aggiorna da sola mentre giocate. Statistiche e mosse ci sono per i Pokémon in squadra; quelle degli amici arrivano dalla loro app (servono la versione 5.3 o successiva e il gioco aperto almeno una volta). Dalla scheda, **Correggi…** apre le correzioni a mano di prima.

## Nomi di luoghi e allenatori
I nomi dei luoghi, a quale luogo appartiene ogni zona e i nomi degli allenatori si leggono dalla ROM, quindi sono quelli della versione italiana e non compaiono più zone con solo un numero. Perché i luoghi coincidano per tutti, usate tutti la stessa versione dell'app (l'aggiornamento automatico ci pensa da solo).

## Notifiche importanti
Alcune notifiche sono più grandi e restano di più:
- quando entri in un luogo dove **devi ancora fare la cattura** (una volta per luogo; solo dove ci sono selvatici, letto dalla ROM; se ci sono solo con Surf o pesca arriva una notifica normale);
- all'inizio di una **lotta importante** (capipalestra, rivale, Team Plasma, Lega), con il level cap e chi lo supera;
- quando tu o un altro **battete uno degli obiettivi importanti**;
- quando il Pokémon in campo di qualcuno (anche degli amici) è **in pericolo**, con il 20% dei PS o meno.
Se l'app non è in primo piano, l'icona lampeggia nella barra delle applicazioni.

## Correggere il tracker
- **Correggi…** nella scheda di un Pokémon (clic nelle Coppie), doppio clic nel Cimitero, oppure tasto destro → *Modifica…* nei Percorsi: puoi cambiare lo stato, riportarlo in vita insieme ai suoi legati, cambiare il luogo della cattura (cambia anche il legame), contarlo come cattura valida o toglierlo dal tracker. Ogni correzione resta scritta nel diario.
- **Altro → Controlla il tracker con il gioco…** confronta i tuoi Pokémon con squadra e PC letti dalla memoria: Pokémon morti nel tracker ma vivi nel gioco, liberati che sono ricomparsi, Pokémon che non trovo più. Se dopo un backup ricaricato (o all'avvio del gioco) le cose non tornano, la finestra si apre da sola.

## Regole opzionali
Dal menu **Regole** scegli cosa usare: tutorial, clausola doppioni, clausola shiny, **tipo primario unico in squadra** (spento finché non lo attivi), avviso del **level cap**, **Condividi esperienza** (tutta la squadra prende esperienza, anche chi non ha combattuto: si usa con o senza la modalità qui sotto) con il suo moltiplicatore (**Esperienza con Condividi**: ×1 normale, ×½, ×¼, ×⅛), **Blocca il level cap** ed esperienza solo dagli allenatori (queste ultime due sono sperimentali, spiegate più sotto).

## Tempo della run
Il tempo in alto conta solo quando almeno un giocatore sta giocando: se nessuno ha il gioco aperto si ferma.

## Velocità del gioco
In basso c'è **Velocità** (×1, ×2, ×3, ×4, ×8 o il più veloce possibile): sostituisce le scorciatoie di BizHawk per la velocità, che sono spente perché scattavano anche scrivendo in altre finestre. **Tab** tenuto premuto resta l'avanti veloce di BizHawk. Tra parentesi c'è la velocità **vera** del gioco in quel momento: se resta più bassa di quella scelta, è il processore del PC che non ce la fa (il Nintendo DS è pesante da emulare; la RAM conta poco).

## Tasti
Quando usi un'altra finestra (Discord, il browser…) il gioco ignora la tastiera, anche se BizHawk è incastrato nell'app. Le scorciatoie di BizHawk che potevano scattare per sbaglio (F = avanza di un frame, Pausa, F1–F10…) sono disattivate. Se giochi con il controller tenendo l'app in secondo piano, togli la spunta in *Impostazioni*.

## Modalità sperimentale: esperienza solo dagli allenatori
Per run senza farmare: **Regole → Esperienza solo dagli allenatori (sperimentale)**. Vale per tutti i giocatori della partita.
- **Selvatici**: non danno esperienza. Niente livelli che salgono e poi tornano indietro: il gioco proprio non la assegna.
- **Allenatori**: danno quanto basta per portare il tuo **primo Pokémon** della squadra al livello del Pokémon più forte di quell'allenatore, senza mai superare il level cap. Se sei già a quel livello o sopra, niente esperienza. Se in lotta usi più Pokémon, se la dividono come sempre. Livelli, mosse nuove ed evoluzioni li gestisce il gioco normalmente.
- All'inizio di ogni lotta con un allenatore una notifica dice quanta esperienza darà (per esempio "esperienza ×3"), senza svelare niente della sua squadra. In alto compare la scritta *EXP solo dagli allenatori*.

Come funziona: come i codici Action Replay "moltiplicatore di esperienza", durante la lotta l'app cambia due istruzioni del calcolo dell'esperienza (×0 per i selvatici, ×N per gli allenatori, oppure ÷2, ÷4… per ridurla) e a fine lotta le rimette com'erano. Le tocca solo se trova esattamente il codice atteso (riconosce sia le istruzioni prima sia quelle 4 KB prima, come nei codici delle varie versioni); la prima volta lo cerca da sola e poi si ricorda dove sta. Se nella tua versione non lo trova, te lo dice e l'esperienza resta normale.

## Modalità sperimentale: level cap bloccato
**Regole → Blocca il level cap (sperimentale)**, per tutti i giocatori: nessun Pokémon va oltre il level cap. Se un Pokémon al 12 con cap 13 battendo un avversario salirebbe al 14, si ferma al 13 (e non impara le mosse del 14); al cap non sale più. Prima di ogni Pokémon battuto l'app calcola quanta esperienza arriverebbe e la riduce quanto basta. Con Condividi esperienza la riduzione vale per tutta la squadra, quindi decide il Pokémon più vicino al cap. In alto compare la scritta *Cap bloccato*.

Le tre regole sull'esperienza (cap bloccato, Condividi ridotto, solo allenatori) usano lo stesso sistema e si possono combinare. Finché l'app non ha deciso, con solo allenatori o cap bloccato l'esperienza è zero: meglio niente che troppa. Per non prendere esperienza dai selvatici basta *Esperienza solo dagli allenatori*: danno esattamente zero. Nel registro (scheda *Sistema*) prima di ogni Pokémon battuto c'è scritto quanta esperienza darà.

## Diagnosi
Se qualcosa che dipende dal gioco non funziona (esperienza, chi è in campo, allenatori e strumenti contati male), usa **Altro → Crea file per la diagnosi…**, meglio durante o subito dopo una lotta con un allenatore, nel posto dove i numeri non tornano. Durante ogni lotta con un allenatore l'app tiene anche da sola un'istantanea della memoria, che finisce nel file. L'app salva un file .zip in *Documenti\SoulLink Tracker\diagnosi* con la memoria della lotta, il codice dell'esperienza, gli allenatori e gli strumenti della zona letti dalla ROM e il registro (niente chiavi di Supabase). Mandamelo e sistemo.

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
