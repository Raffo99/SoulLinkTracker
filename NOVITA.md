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
