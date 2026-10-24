# Soul Link Tracker v3: Pokémon Nero 2 / Bianco 2

## Novità: l'app (SoulLinkTracker.exe)

Il modo consigliato per giocare. Un solo programma con dentro tutto:
- **BizHawk incastrato nella finestra**, a sinistra. A destra squadre, percorsi e coppie, obiettivi, cimitero, diario e diagnostica. In basso i comandi.
- **Niente più microscatti**: lo script parla con l'app sul PC, istantaneamente. Al sito ci pensa l'app in sottofondo.
- **Run gestite dall'app**: genera la ROM, prepara il salvataggio di partenza, chiude e riavvia BizHawk sulla ROM giusta. Al game over chiede se iniziare la nuova run e fa tutto da sola.
- **Niente file da modificare**: si configura dalla finestra *Impostazioni*, che si apre da sola al primo avvio.

### Ottenere l'exe (GitHub lo crea per voi)
1. Create un account su github.com e un **nuovo repository** (anche privato).
2. Caricate il contenuto di questa cartella. Con GitHub Desktop: *Add existing repository* → *Publish*. Oppure trascinate i file nella pagina del repository: in quel caso la cartella `.github` va caricata anche lei. ROM, randomizer e salvataggi sono esclusi da `.gitignore`.
3. Nella scheda **Actions** parte da sola l'esecuzione **"Crea exe"** (3-4 minuti).
4. Aprite l'esecuzione finita → in fondo, **Artifacts → SoulLinkTracker** → scaricate e scompattate: ecco `SoulLinkTracker.exe`.

A ogni modifica caricata, GitHub rifà l'exe. Se create un tag `v3.0.0` (*Releases → Draft a new release*), l'exe viene allegato anche alla release.

### Primo avvio
1. Avviate `SoulLinkTracker.exe`. Windows potrebbe avvisare che il programma non è firmato: *Ulteriori informazioni → Esegui comunque*.
2. Nelle **Impostazioni** inserite:
   - il vostro nome, l'indirizzo del sito e il codice (c'è il pulsante *Prova collegamento*);
   - dove sta `EmuHawk.exe`;
   - randomizer (`.jar`), impostazioni (`.rnqs`) e ROM originale.
3. L'app genera la ROM della run attuale e apre BizHawk dentro la finestra.

L'app usa una **configurazione di BizHawk tutta sua**, così la vostra resta intatta. In quella configurazione attiva l'opzione che permette a BizHawk di ricevere i tasti anche quando è dentro un'altra finestra. Conseguenza: anche con l'app non in primo piano, i tasti premuti arrivano al gioco.

ROM generate e salvataggio di partenza stanno in `Documenti\SoulLink Tracker`.

Il sito su Cloudflare serve ancora: è quello che tiene insieme i due giocatori. La dashboard web resta comoda da telefono o per chi guarda.

---

## Senza app (BizHawk + script, come prima)

Tutto gira dentro BizHawk e sul vostro sito Cloudflare. **Non serve più nessun programma Python** e nessun file viene riscritto di continuo: lo script legge la memoria del gioco e manda gli aggiornamenti al sito **solo quando cambia qualcosa**.

## Cosa fa da solo

| | |
|---|---|
| **Incontri selvatici** | Riconosce quando inizia una lotta con un Pokémon selvatico, in che percorso sei, e registra il **primo incontro** del luogo. Le lotte contro gli allenatori vengono ignorate. |
| **Catture / fallimenti** | A fine lotta controlla se il Pokémon è finito in squadra o nel PC. Se no, l'incontro è **fallito**, e l'amico viene avvisato di mettere nel box il partner. |
| **Coppie** | Si formano da sole in base al luogo di cattura salvato nel Pokémon (starter compresi). |
| **PC** | Legge anche i box: depositi, ritiri e catture con la squadra piena. |
| **Morti e legami** | Un Pokémon con PS a 0 muore e si porta via il partner. Il messaggio compare a schermo all'altro giocatore. |
| **Game over** | Squadra tutta KO oppure nessun Pokémon vivo rimasto. |
| **Nuova run** | Dalla dashboard: ogni script genera la sua ROM nuova con Universal Pokémon Randomizer ZX e la carica in BizHawk. Si riparte con un salvataggio pulito. |
| **Medaglie e level cap** | Lette dalla memoria: il cap sale da solo. Solo "Superquattro battuti" va spuntato a mano. |
| **Obiettivi** | Capipalestra, le 5 lotte col rivale, Acromio, Ghecis, Superquattro e Iris si segnano da soli quando vinci la lotta (per le palestre fa fede anche la medaglia). Dopo i Superquattro il level cap passa a Iris. Quando tutti e due battete Iris, la run è **vinta**. |
| **Inizio più veloce** | Salvate una volta in camera, prima di uscire a prendere lo starter. Dalla run successiva ogni ROM nuova parte da quel salvataggio: premete *Continua* e siete già in camera, starter compreso nella randomizzazione nuova. |
| **Regole** | Clausola doppioni (stessa famiglia evolutiva) e clausola shiny, attivabili dalla dashboard. Avvisi per catture fuori regola, tipi primari doppi, livelli sopra il cap e partner nel box. |

---

## Parte 1: Il sito su Cloudflare Pages (lo fa uno solo dei due)

Vi serve un account Cloudflare gratuito e **Node.js** (nodejs.org, versione LTS). Aprite il Prompt dei comandi nella cartella `sito`:

```bat
cd percorso\di\soullink\sito
npx wrangler login
npx wrangler d1 create soullink
```

1. L'ultimo comando stampa un `database_id`. Aprite `wrangler.toml` e incollatelo al posto di `METTI-QUI-L-ID-DEL-DATABASE`.
2. Create il progetto e la parola segreta, poi pubblicate:

```bat
npx wrangler pages project create soullink --production-branch main
npx wrangler pages secret put CODICE --project-name soullink
npx wrangler pages deploy
```

- Quando vi chiede il valore di `CODICE`, scrivete una parola segreta e passatela al vostro amico.
- Alla fine vi dà l'indirizzo, tipo `https://soullink.pages.dev` (o `soullink-xxx.pages.dev` se il nome è già preso). **Quello è il sito.**
- La tabella del database si crea da sola alla prima richiesta.
- Per aggiornare il sito in futuro basta rifare `npx wrangler pages deploy`.

> **Alternativa con GitHub**: mettete la cartella in un repository, su Cloudflare create un progetto Pages collegato al repo (*root directory* `sito`, *build output* `public`, nessun comando di build). Poi in *Settings* aggiungete il binding **D1 → `DB`** e la variabile segreta **`CODICE`**. Il trascinamento manuale dei file **non** funziona, perché non pubblica le Functions.

**Quanto costa**: niente. Il piano gratuito include 100.000 richieste al giorno e 100.000 scritture su D1. Una serata di gioco ne usa poche migliaia (la dashboard aperta fa una richiesta ogni 3 secondi).

## Parte 2: BizHawk (tutti e due)

| Cosa | Dove |
|---|---|
| BizHawk 2.9 o più recente | github.com/TASEmulators/BizHawk/releases |
| Java | adoptium.net |
| Universal Pokémon Randomizer ZX | github.com/Ajarmar/universal-pokemon-randomizer-zx/releases |
| La vostra ROM di Nero 2 / Bianco 2 | dalla vostra cartuccia |

Struttura della cartella:
```
soullink/
├─ bizhawk/
│   ├─ soullink.lua        lo script
│   ├─ config.lua          ← da modificare
│   └─ avvia_bizhawk.bat   ← si avvia da qui
├─ randomizer/PokeRandoZX.jar   (contenuto dello zip del randomizer)
├─ settings/soullink.rnqs       (impostazioni del randomizer, uguali per tutti e due)
├─ rom/Nero2.nds                (ROM originale)
└─ sito/                        (solo per chi pubblica il sito)
```

1. **Impostazioni del randomizer**: aprite il randomizer, scegliete le opzioni, poi *Settings → Save Settings* in `settings/soullink.rnqs`. Mandate il file all'amico. Lasciate i **tipi non randomizzati** e attivate **Change Impossible Evolutions**.
2. **`bizhawk/config.lua`** (Blocco note): il vostro nome (diverso da quello dell'amico), l'indirizzo del sito, il `codice` e dove avete messo BizHawk (`bizhawk = "C:/BizHawk/EmuHawk.exe"`).
3. **Avviate sempre BizHawk da `avvia_bizhawk.bat`**. Il file passa a BizHawk le opzioni che permettono allo script di usare internet (`--url_post`) e carica lo script da solo.

Al primo avvio lo script genera la ROM della run #1 e la apre. In alto a sinistra compare **"Soul Link: online - run #1"**.

## Parte 3: La verifica iniziale (qui mi serve il vostro aiuto)

Gli indirizzi di memoria vengono dal progetto *NDS Ironmon Tracker*, che li ha trovati sulla versione **inglese**. Sulla versione italiana dovrebbero essere identici, ma va verificato. Per questo `config.lua` parte con `diagnostica = true`: lo script mostra a schermo cosa legge, e la dashboard ha un pannello **Diagnostica memoria** con ✓ / ✗ / ?.

Fate questo giro (10 minuti):

1. **Nuova partita → ricevete lo starter** → deve diventare ✓ *squadra letta* e *indirizzi: puntatore* (oppure *fisso*).
2. **Camminate ad Alisopoli e poi sul Percorso 19** → la *zona* deve mostrare il nome giusto.
3. **Fate 2-3 lotte selvatiche, cambiando zona ogni tanto** → sulla dashboard compaiono i primi incontri con il Pokémon giusto e *allenatore 0*. Intanto lo script cerca da solo l'indicatore "in lotta" della versione italiana. Quando lo trova, scrive *indicatore di lotta trovato* e lo salva in `bizhawk/calibrazione.txt`.
4. **Catturate o fate scappare** → l'esito appare da solo. Finché l'indicatore non è calibrato, una fuga viene registrata quando cambiate zona o iniziate un'altra lotta. Dopo la calibrazione, entro 10 secondi.
5. **Lottate contro un allenatore** → *allenatore* diverso da 0, e nessun incontro registrato.
6. **Al Centro Pokémon depositate un Pokémon** → *PC: 1 Pokémon* ✓.
7. **Dopo la prima medaglia** → *medaglie lette: 1*.

Se qualcosa resta ✗ o sbagliato, **mandatemi uno screenshot del pannello Diagnostica e delle scritte azzurre a schermo** in quel momento, e correggo gli indirizzi. Quando è tutto ✓, mettete `diagnostica = false`.

Lo script si arrangia già in parte da solo:
- se il puntatore non funziona prova l'indirizzo fisso della versione europea;
- se il PC non è dove previsto, lo cerca la prima volta che depositate un Pokémon e salva il risultato in `bizhawk/calibrazione.txt` (scritto una volta sola);
- i luoghi che non conosce li impara dalle catture.

## Saltare l'inizio del gioco

Va fatto una volta sola, nella prima run:
1. Nuova partita, fate l'introduzione e scegliete il nome.
2. **Appena potete muovervi in camera, salvate** (menu → Salva).
3. Uscite e prendete lo starter come sempre. Appena lo ricevete compare *"Salvataggio di partenza creato!"*.

Da lì in poi, a ogni nuova run lo script copia quel salvataggio sulla ROM nuova prima di aprirla. Il file è `bizhawk/salvataggio_base.SaveRAM`: per rifarlo basta cancellarlo. Lo starter resta quello randomizzato della nuova ROM, perché nel salvataggio non c'è ancora nessun Pokémon.

Ho scelto un salvataggio di partenza invece di modificare la memoria di gioco per saltare le scene: è molto più affidabile, perché non si rischia di rompere eventi e script della storia. Se i salvataggi di BizHawk non sono in `<cartella di BizHawk>/NDS/SaveRAM`, impostate `cartella_saveram` in `config.lua`.

## Cose da sapere

- **Microscatti**: BizHawk blocca l'emulatore per una frazione di secondo a ogni richiesta, perché non sa farle in sottofondo. Per questo lo script parte **solo quando non state premendo tasti** da 1,5 secondi: fermi, nei menu, durante le animazioni. Se c'è qualcosa di importante (una morte, un incontro) aspetta al massimo 20 secondi. Potete regolare tutto in `config.lua` (`fermo_frame`, `attesa_massima`, `secondi_controllo`).
- Se la ROM caricata non è quella della run attuale, il sito **non registra i dati**. Lo vedete scritto in arancione a schermo e negli avvisi della dashboard.
- La **morte** viene registrata a fine lotta, quando il gioco aggiorna i PS della squadra.
- **"Da confermare"**: se avevate la squadra piena e lo script non trova il PC, non può sapere se la cattura è riuscita. Vi compaiono due pulsanti sulla dashboard.
- Ogni cella della tabella ha il menu `⋯` per correggere a mano (squadra / box / morto / liberato), e ogni incontro ha **annulla**.
- Per **ricominciare da zero**: `npx wrangler d1 execute soullink --remote --command "DELETE FROM partita"`.

## Crediti
Indirizzi di memoria di B2W2 e tabella delle zone: progetto *NDS Ironmon Tracker* (Brian0255 e contributori). Indirizzo europeo della squadra: *yPokeStats*. Nomi e luoghi in italiano: PKHeX e PokéAPI. Sprite: PokéAPI.
