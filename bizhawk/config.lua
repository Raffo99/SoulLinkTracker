-- =========================================
--  CONFIGURAZIONE - modifica solo questo file
-- =========================================
return {
  -- il tuo nome (diverso da quello dell'amico)
  giocatore = "Raffaele",

  -- l'indirizzo del vostro sito su Cloudflare Pages (senza / finale)
  server = "https://soullink.pages.dev",

  -- la parola segreta impostata su Cloudflare (variabile CODICE), uguale per tutti e due
  codice = "cambiami",

  -- dove hai messo BizHawk (lo usa anche avvia_bizhawk.bat)
  bizhawk = "C:/BizHawk/EmuHawk.exe",

  -- salta l'inizio del gioco: salva una volta in camera prima di uscire a prendere lo starter.
  -- Quando ricevi lo starter lo script tiene da parte quel salvataggio e lo copia su ogni nuova run.
  salta_inizio = true,
  -- cartella dei salvataggi di BizHawk per il Nintendo DS (vuoto = <cartella di BizHawk>/NDS/SaveRAM)
  cartella_saveram = "",

  -- randomizzazione automatica (all'inizio e a ogni nuova run)
  randomizer = {
    attivo = true,
    java = "java",                                  -- oppure il percorso completo di java.exe
    jar = "../randomizer/PokeRandoZX.jar",
    impostazioni = "../settings/soullink.rnqs",
    rom_originale = "../rom/Nero2.nds",
    cartella_output = "../rom_randomizzate",
  },

  -- ogni quanti secondi chiedere al sito se ci sono novita'
  secondi_controllo = 10,

  -- le richieste al sito bloccano il gioco per un attimo, quindi partono solo quando
  -- non premi tasti da questo numero di frame (90 = 1,5 secondi)...
  fermo_frame = 90,
  -- ...oppure dopo questi secondi se c'e' qualcosa di importante da mandare
  attesa_massima = 20,

  -- true = mostra a schermo i dati letti dalla memoria e li manda alla dashboard (per la verifica iniziale)
  diagnostica = true,
}
