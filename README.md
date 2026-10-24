# Soul Link Tracker 4 – Pokémon Nero 2 / Bianco 2

Un'app per Windows con BizHawk dentro, per giocare una Randomizer Soul Link Nuzlocke in due. Le regole del Soul Link le applica l'app stessa; la partita condivisa sta in un piccolo database gratuito su **Supabase**. Niente sito, niente porte da aprire sul router, e non serve che l'altro sia acceso.

## Cosa fa da sola
- **Incontri e catture**: riconosce lotte selvatiche, luogo, primo incontro, cattura o fallimento. Il **primo selvatico della run (tutorial) non conta**.
- **Coppie e morti**: le coppie si formano in base al luogo di cattura. La morte si porta via il partner, il game over parte da solo.
- **PC, medaglie, obiettivi**: legge il PC e le medaglie, con il level cap che sale da solo. Segna gli obiettivi (capipalestra, rivale, Team Plasma, Superquattro, Iris). Quando tutti e due battete Iris, la run è vinta.
- **Nuova run**: genera la ROM randomizzata, riparte dal salvataggio di partenza e riavvia BizHawk sulla ROM giusta.
- **Regole**: clausola doppioni, clausola shiny e incontro del tutorial, nel menu *Regole*.

---

## 1. Supabase (una volta sola, lo fa uno dei due)
1. Vai su **supabase.com**, crea un account e un **New project** gratuito. Come regione va bene *Central EU (Frankfurt)*.
2. Apri **SQL Editor**, incolla tutto il file `supabase/schema.sql` e premi **Run**.
3. Copia l'**URL del progetto** (tipo `https://abcdefgh.supabase.co`): lo trovi nella pagina principale del progetto o in *Project Settings → Data API*.
4. In *Project Settings → API Keys* copia la **Publishable key** (`sb_publishable_…`). Va bene anche la vecchia chiave *anon*.
5. Scegli un **codice della partita**, cioè una parola segreta tipo `pikachu-raffo-2026`. È la "chiave" della vostra partita: chi non la conosce non la vede.
6. Manda URL, chiave e codice all'amico.

Il piano gratuito basta e avanza: l'app scarica la partita solo quando cambia qualcosa (pochi KB a sessione). Supabase **mette in pausa i progetti gratuiti dopo un periodo senza uso**. Se succede, l'app segnala l'errore: entra su supabase.com e premi *Restore*.

## 2. L'exe (GitHub lo crea per voi)
1. Crea un repository su **github.com** (anche privato) e caricaci il contenuto di questa cartella. Con GitHub Desktop: *Add existing repository* → *Publish*. Se trascini i file a mano, carica anche la cartella `.github`.
2. Nella scheda **Actions** parte **"Crea exe"**: dopo 3-4 minuti apri l'esecuzione e scarica **Artifacts → SoulLinkTracker**.

ROM, randomizer e salvataggi non finiscono mai su GitHub: sono esclusi da `.gitignore`.

## 3. Primo avvio
Ti serve: **BizHawk 2.9+**, **Java** (adoptium.net), **Universal Pokémon Randomizer ZX** e la tua **ROM** di Nero 2.

1. Avvia `SoulLinkTracker.exe`. Se Windows avvisa che non è firmato: *Ulteriori informazioni → Esegui comunque*.
2. Nelle **Impostazioni** inserisci:
   - il tuo nome (diverso da quello dell'amico);
   - URL, chiave e codice di Supabase (prova con *Prova collegamento*);
   - dove sta `EmuHawk.exe`;
   - il randomizer (`PokeRandoZX.jar`), le impostazioni (`.rnqs`, uguali per tutti e due) e la ROM originale.
3. L'app genera la ROM della run attuale e apre BizHawk dentro la finestra.

L'app usa una configurazione di BizHawk tutta sua. In quella configurazione è attiva l'opzione che fa arrivare i tasti al gioco anche quando BizHawk è dentro un'altra finestra; conseguenza: i tasti arrivano al gioco anche con l'app non in primo piano.

## 4. Saltare l'inizio del gioco
Il salvataggio di partenza viene copiato su ogni ROM nuova, così si riparte da lì premendo *Continua*. Lo starter resta quello randomizzato della ROM nuova, perché lo ricevi dopo.

- **Automatico**: se nella prima run salvi prima di prendere lo starter, quando lo ricevi l'app mette da parte quell'ultimo salvataggio.
- **Scegliendo tu il punto** (consigliato, così si risparmia più tempo): salva il più vicino possibile alla **Vedetta di Alisopoli**, prima della scena dello starter. Poi premi **Salvataggio di partenza → Usa il salvataggio attuale come partenza**. Se lo starter è già in squadra, l'app lo rifiuta.

Il file sta in `Documenti\SoulLink Tracker\salvataggio_base.SaveRAM`. Puoi cancellarlo dallo stesso menu.

## 5. L'interfaccia
- **In alto**: run, durata, catture, coppie vive, morti; per ogni giocatore medaglie, zona e level cap.
- **Prossimo obiettivo**: chi devi battere e il livello massimo adesso, più i progressi dell'amico.
- **Dove sei**: se nel luogo attuale hai ancora l'incontro, per te e per l'amico.
- **Coppie**: ogni tuo Pokémon accanto al suo partner, con livello e PS. Se il partner è nel box la riga diventa gialla.
- **Altre schede**: Percorsi (tasto destro per correggere), Obiettivi (doppio clic per correggere), Cimitero, Diario, Registro dell'app, Diagnostica.

## Da verificare la prima volta
La lettura della memoria è la stessa che hai già verificato con la diagnostica sulla tua versione italiana. La parte nuova è l'incastro della finestra di BizHawk, che ho potuto provare solo con un BizHawk simulato (il mio ambiente non è Windows). Se BizHawk si apre fuori dalla finestra, non riceve i tasti o è tagliato, mandami la scheda **Registro** e uno screenshot.
