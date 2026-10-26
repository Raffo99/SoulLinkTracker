-- =====================================================================
--  SOUL LINK TRACKER v2 - script per BizHawk (core NDS / melonDS)
--  Pokemon Nero 2 / Bianco 2
--
--  Legge la memoria del gioco e parla direttamente con il sito su Cloudflare:
--  squadra, PC, incontri selvatici, catture, medaglie. Al game over genera
--  la nuova ROM randomizzata e la carica. Nessun file intermedio.
--
--  Va avviato con avvia_bizhawk.bat (serve l'opzione --url_post di BizHawk).
--  Indirizzi B2W2 basati sul lavoro del progetto NDS Ironmon Tracker.
-- =====================================================================

-- ---------------- cartella e configurazione ----------------
local function cartella_script()
  local src = debug.getinfo(1, "S").source:gsub("^@", "")
  return src:match("^(.*[/\\])") or ""
end
local DIR = cartella_script()
local WIN = package.config:sub(1, 1) == "\\"
local okcfg, CFG = pcall(dofile, DIR .. "config.lua")
if not okcfg then
  print("[Soul Link] ERRORE in config.lua: " .. tostring(CFG))
  CFG = {}
end
CFG.server = (CFG.server or ""):gsub("/+$", "")

-- Modalita' APP: BizHawk avviato dall'app Soul Link Tracker (opzioni --socket_ip/--socket_port).
-- Lo script parla con l'app sul PC (istantaneo, niente scatti); internet, ROM e salvataggi li gestisce l'app.
local APP = false
do
  local ok, conn = pcall(comm.socketServerIsConnected)
  if ok and conn then
    APP = true
    pcall(comm.socketServerSetTimeout, 3000)
    CFG.randomizer = { attivo = false }
    CFG.salta_inizio = false
    CFG.diagnostica = false
  end
end
CFG.secondi_controllo = CFG.secondi_controllo or 10
CFG.randomizer = CFG.randomizer or { attivo = false }

local function assoluto(p)
  if not p or p == "" then return p end
  if p:match("^%a:[/\\]") or p:match("^[/\\]") then return p end
  return DIR .. p
end
local function sistema(p) -- separatori giusti per il sistema
  if WIN then return (p:gsub("/", "\\")) end
  return p
end
local function esiste(p)
  local f = io.open(p, "rb"); if f then f:close(); return true end; return false
end

-- ---------------- memoria ----------------
local DOM = "Main RAM"
local coda_app = {}             -- risposte ai comandi dell'app (backup fatto, stato caricato, esperienza)
local diag = {}                 -- dati per la diagnostica
local scrivi_dump               -- definita piu' avanti (comando DUMP dell'app)
local lotta = { attiva = false } -- lotta in corso (usata anche dai comandi dell'app e dall'esperienza)
local salva_calibrazione        -- definita piu' avanti
local function r8(a)  return memory.read_u8(a, DOM) end
local function r16(a) return memory.read_u16_le(a, DOM) end
local function r32(a) return memory.read_u32_le(a, DOM) end
local function valido_addr(a) return a and a >= 0 and a + 0xDC <= 0x400000 end

local function codice_gioco()
  local t = {}
  for i = 0, 3 do local c = r8(0x3FFE0C + i); t[#t + 1] = (c >= 32 and c < 127) and string.char(c) or "?" end
  return table.concat(t)
end
local CODICE_ROM = codice_gioco()          -- es. IREI = Nero 2 italiano, IRDI = Bianco 2 italiano
local BIANCO2 = CODICE_ROM:sub(1, 3) == "IRD"

-- offset rispetto al puntatore principale (0x02000024), dal NDS Ironmon Tracker
local OFF = {
  conta_squadra = 0x19724, squadra = 0x19728, zona = 0x41B5C, zona_padre = 0x41B44,
  allenatore_nemico = 0x5262E, nemico = 0x53B70, medaglie = 0x21A24,
  lotta_dati = 0x526A8,     -- puntatori ai Pokemon in campo durante la lotta (BTL_POKEPARAM), dall'Ironmon Tracker
  pid_mio_lotta = 0x91BD0, pid_nemico_lotta = 0x91C2C,   -- PID dei Pokemon in campo (Ironmon Tracker)
  abilita_vista = 0x90104,  -- abilita' appena attivata, una ogni 8 byte per posto (giocatore, avversario...)
  flag_evento = 0x19724 - 0x18E04 + 0x1FF00 + 0x35E,   -- flag degli eventi (blocco EventWork del salvataggio, PKHeX)
  box = 0x19724 - 0x18E04 + 0x400,   -- il PC in RAM ha la stessa disposizione del salvataggio
  medicine = 0x19724 - 0x18E04 + 0x18BD8,   -- tasca Medicine della borsa (salvataggio 0x18400 + 0x7D8, 48 posti)
}
local STATO_LOTTA = BIANCO2 and 0x1B5178 or 0x1B5138
local SQUADRA_FISSA = BIANCO2 and 0x21E42C or 0x21E3EC   -- indirizzo della versione europea (yPokeStats)

-- ---------------- decifratura Pokemon (Gen 5) ----------------
local ORDINE = { "ABCD","ABDC","ACBD","ACDB","ADBC","ADCB","BACD","BADC","BCAD","BCDA","BDAC","BDCA",
                 "CABD","CADB","CBAD","CBDA","CDAB","CDBA","DABC","DACB","DBAC","DBCA","DCAB","DCBA" }
local POS = {}
for i, s in ipairs(ORDINE) do
  local p = {}; for j = 1, 4 do p[s:sub(j, j)] = j end; POS[i - 1] = p
end
local function prng(s) return (s * 0x41C64E6D + 0x6073) & 0xFFFFFFFF end

-- con_lotta = true per i 220 byte di squadra/nemico, false per i 136 byte del PC
local function leggi_pkm(addr, con_lotta)
  if not valido_addr(addr) then return nil end
  local pid, chk = r32(addr), r16(addr + 6)
  if pid == 0 and chk == 0 then return nil end
  local enc, s, somma = {}, chk, 0
  for off = 0x08, 0x86, 2 do
    s = prng(s)
    local w = r16(addr + off) ~ (s >> 16)
    enc[off] = w; somma = (somma + w) & 0xFFFF
  end
  if somma ~= chk then return nil end
  local p = POS[((pid & 0x3E000) >> 13) % 24]
  local function b(l, o) return enc[0x08 + (p[l] - 1) * 32 + o] end
  local specie = b("A", 0)
  if specie == 0 or specie > 649 then return nil end
  local nome = {}
  for i = 0, 10 do
    local c = b("C", i * 2)
    if c == 0xFFFF or c == 0 then break end
    if c >= 0xD800 and c <= 0xF8FF then c = 0x3F end
    nome[#nome + 1] = utf8.char(c)
  end
  local pk = { pid = pid, specie = specie, soprannome = table.concat(nome), luogo = b("D", 0x18),
               esperienza = b("A", 0x08) | (b("A", 0x0A) << 16),
               uovo = ((b("B", 0x12) >> 14) & 1) == 1, id_allenatore = b("A", 4), id_segreto = b("A", 6) }
  if con_lotta then
    local bat, s2 = {}, pid
    for off = 0x88, 0x9A, 2 do s2 = prng(s2); bat[off] = r16(addr + off) ~ (s2 >> 16) end
    pk.livello, pk.ps, pk.ps_max = bat[0x8C] & 0xFF, bat[0x8E], bat[0x90]
    if pk.livello < 1 or pk.livello > 100 or pk.ps_max == 0 or pk.ps > pk.ps_max then return nil end
    -- per il tracker della lotta: mosse, PP, statistiche, stato (sonno, veleno, scottatura...)
    pk.mosse = { b("B", 0), b("B", 2), b("B", 4), b("B", 6) }
    local pp1, pp2, su1, su2 = b("B", 8), b("B", 10), b("B", 12), b("B", 14)
    pk.pp = { pp1 & 0xFF, pp1 >> 8, pp2 & 0xFF, pp2 >> 8 }
    pk.pp_su = { su1 & 0xFF, su1 >> 8, su2 & 0xFF, su2 >> 8 }
    pk.stat = { bat[0x92], bat[0x94], bat[0x96], bat[0x98], bat[0x9A] }    -- att, dif, vel, att.sp, dif.sp
    pk.stato_alt = bat[0x88] & 0xFF
    pk.abilita = b("A", 0x0C) >> 8
    pk.natura = (b("B", 0x18) >> 8) & 0xFF
    pk.strumento = b("A", 2)
  end
  return pk
end

-- ---------------- modalita' "esperienza solo dagli allenatori" ----------------
-- Il gioco calcola l'esperienza in una funzione del codice di lotta; due istruzioni (lsls r0,r0,#16 / lsrs r4,r0,#16)
-- si possono sostituire con "movs r4,#N / muls r4,r0": l'esperienza data diventa N volte quella normale
-- (lo stesso trucco dei codici Action Replay "moltiplicatore di esperienza"). N = 0 per i selvatici,
-- N scelto dall'app per gli allenatori. Il codice si tocca solo durante la lotta e solo se e' quello atteso.
local function w16(a, v) memory.write_u16_le(a, v & 0xFFFF, DOM) end
local ESP_ORIGINALE, ESP_FIRMA = 0x0C040400, 0x68424805          -- istruzioni originali e controllo 0x1000 byte prima
local ESP_PRIMA = 0x18080C09                                    -- le due istruzioni subito prima (lsrs r1,r1,#16 / adds r0,r1,r0)
local esp_sito = nil                                            -- indirizzo trovato (relativo alla RAM)

-- il punto e' modificato da noi? "movs r4,#N / muls r4,r0" (moltiplica) oppure "lsrs r4,r0,#S / movs r4,r4" (divide per 2^S)
local function esp_modificato(v)
  return ((v >> 16) == 0x4344 and (v & 0xFF00) == 0x2400) or ((v >> 16) == 0x0024 and (v & 0xF83F) == 0x0804)
end
local function sito_valido(a)
  if not a or a < 0x1000 or a + 4 > 0x400000 then return false end
  if r32(a - 0x1000) ~= ESP_FIRMA and r32(a - 4) ~= ESP_PRIMA then return false end
  local v = r32(a)
  return v == ESP_ORIGINALE or esp_modificato(v)
end
local function sito_candidato(a)
  return r32(a) == ESP_ORIGINALE and (r32(a - 4) == ESP_PRIMA or r32(a - 0x1000) == ESP_FIRMA)
end

local function cerca_sito_esp()
  -- prima gli indirizzi noti (USA, Giappone) e quello salvato, poi una ricerca nella zona del codice di lotta
  for _, a in ipairs({ esp_sito or 0, 0x1BD6F8, 0x1BD738, 0x1BD0F8, 0x1BD0D8 }) do
    if sito_valido(a) then return a end
  end
  -- prima vicino agli indirizzi noti (veloce), poi in tutta la zona solo se serve davvero a una regola attiva
  for a = 0x1B4000, 0x1C8000, 2 do
    if sito_candidato(a) then return a end
  end
  if not (SOLO_ALLENATORI or CONDIVIDI_ESP or CONTROLLO_ESP) then return nil end
  for a = 0x100000, 0x280000, 2 do
    if (a < 0x1B4000 or a > 0x1C8000) and sito_candidato(a) then return a end
  end
  return nil
end

local esp_segnalato = nil                                       -- ultimo esito mandato all'app

local esp_ricerche_fallite = 0
local function assicura_sito_esp()
  if esp_sito and sito_valido(esp_sito) then return true end
  if lotta.esp_cercato then return false end     -- una ricerca sola per lotta (e' lenta)
  lotta.esp_cercato = true
  if not esp_sito and esp_ricerche_fallite >= 3 and not (SOLO_ALLENATORI or CONDIVIDI_ESP or CONTROLLO_ESP) then return false end
  local trovato = cerca_sito_esp()
  if trovato then esp_sito = trovato elseif not esp_sito then esp_ricerche_fallite = esp_ricerche_fallite + 1 end
  local esito = trovato and ("si" .. trovato) or "no"
  diag.esp_ricerca = esito
  if esito ~= esp_segnalato and (trovato or (esp_segnalato == nil and (SOLO_ALLENATORI or CONDIVIDI_ESP or CONTROLLO_ESP))) then
    esp_segnalato = esito
    coda_app[#coda_app + 1] = { tipo = "esp_sito", ok = trovato ~= nil, indirizzo = trovato }
    if trovato then salva_calibrazione() end
  end
  return trovato ~= nil
end

-- n >= 0: esperienza moltiplicata per n; n < 0: esperienza divisa per 2^(-n)
local function codifica_esp(n)
  n = math.floor(n or 1)
  if n < 0 then
    local sh = math.min(31, -n)
    return (0x0024 << 16) | (0x0804 | (sh << 6))
  end
  return (0x4344 << 16) | 0x2400 | math.min(255, n)
end
local function applica_esp(n)
  if not assicura_sito_esp() then return false end
  local v = codifica_esp(n)
  if r32(esp_sito) ~= v then
    w16(esp_sito, v & 0xFFFF); w16(esp_sito + 2, v >> 16)
  end
  diag.esp_applicato = n
  return true
end

-- ---- Condividi esperienza (opzionale): tutta la squadra prende esperienza anche senza combattere ----
-- Come il codice Action Replay "Exp Share": dopo le istruzioni 0x9903 0x4281 (ldr r1,[sp,#0xC] / cmp r1,r0)
-- c'e' il salto che esclude chi non ha partecipato; durante la lotta lo si sostituisce con un "nop" (0x46C0).
local COND_FIRMA, NOP = 0x42819903, 0x46C0
local cond_sito, cond_orig, cond_segnalato = nil, nil, nil
local function e_salto(h) return (h & 0xF000) == 0xD000 and ((h >> 8) & 0xF) < 0xE end

local function cond_valido(a)
  if not a or a + 6 > 0x400000 or r32(a) ~= COND_FIRMA then return false end
  local h = r16(a + 4)
  return e_salto(h) or (h == NOP and cond_orig ~= nil)
end

local function cerca_cond()
  local cand = {}
  local function prova_zona(da, a)
    for x = da, a, 2 do
      if r32(x) == COND_FIRMA and e_salto(r16(x + 4)) then cand[#cand + 1] = x end
    end
  end
  if esp_sito then
    -- vicino al calcolo dell'esperienza: nella versione USA 0xE7B4 byte prima, in quella giapponese 0xE794
    prova_zona(esp_sito - 0xE7B4 - 0x400, esp_sito - 0xE794 + 0x400)
  end
  if #cand == 0 then prova_zona(0x180000, 0x240000) end
  if #cand == 1 then return cand[1] end          -- solo se il punto e' unico, altrimenti meglio non toccare niente
  return nil
end

local function applica_condividi()
  if not (cond_sito and cond_valido(cond_sito)) then
    if lotta.cond_cercato then return false end
    lotta.cond_cercato = true
    assicura_sito_esp()
    local trovato = cerca_cond()
    if trovato then cond_sito = trovato; cond_orig = r16(trovato + 4) end
    local esito = trovato and ("si" .. trovato) or "no"
    if esito ~= cond_segnalato and (trovato or cond_segnalato == nil) then
      cond_segnalato = esito
      coda_app[#coda_app + 1] = { tipo = "condividi_sito", ok = trovato ~= nil, indirizzo = trovato }
    end
    if not trovato then return false end
  end
  if r16(cond_sito + 4) ~= NOP then
    if e_salto(r16(cond_sito + 4)) then cond_orig = r16(cond_sito + 4) end
    w16(cond_sito + 4, NOP)
  end
  return true
end

local function ripristina_condividi()
  if cond_sito and cond_orig and r32(cond_sito) == COND_FIRMA and r16(cond_sito + 4) == NOP then
    w16(cond_sito + 4, cond_orig)
  end
end

-- il codice di lotta e' in memoria? (true / false; nil se non sappiamo ancora dove sta)
local function codice_lotta_caricato()
  if not esp_sito then return nil end
  return sito_valido(esp_sito)
end

local function ripristina_esp()
  if esp_sito and sito_valido(esp_sito) and r32(esp_sito) ~= ESP_ORIGINALE then
    w16(esp_sito, 0x0400); w16(esp_sito + 2, 0x0C04)
  end
end

-- ---------------- indirizzi correnti ----------------
local A = { fonte = "nessuna" }
local function risolvi()
  local ptr = r32(0x24) & 0xFFFFFF
  if ptr < 0x0A0000 or ptr > 0x3C0000 then ptr = -0x100000 end   -- gioco non ancora avviato
  local function con_base(base, fonte)
    local t = { base = base, fonte = fonte }
    for k, v in pairs(OFF) do t[k] = base + v end
    return t
  end
  local cand = con_base(ptr, "puntatore")
  local n = valido_addr(cand.conta_squadra) and (r32(cand.conta_squadra) & 0xFF) or 99
  if n >= 1 and n <= 6 and leggi_pkm(cand.squadra, true) then A = cand; return end
  if leggi_pkm(SQUADRA_FISSA, true) then A = con_base(SQUADRA_FISSA - OFF.squadra, "fisso"); return end
  if n == 0 and valido_addr(cand.squadra) then A = cand; A.fonte = "puntatore (squadra vuota)"; return end
  A = { fonte = "nessuna" }
end

local function leggi_squadra()
  if not A.squadra then return nil end
  local n = r32(A.conta_squadra) & 0xFF
  if n < 1 or n > 6 then return nil end
  local sq = {}
  for i = 0, n - 1 do
    local pk = leggi_pkm(A.squadra + i * 0xDC, true)
    if not pk then return nil end          -- dati a meta' (caricamento, menu): meglio non mandare niente
    pk.slot = i + 1; sq[#sq + 1] = pk
  end
  return sq
end

-- ---------------- PC (box) ----------------
local FILE_CAL = DIR .. "calibrazione.txt"   -- scritto una sola volta se il PC va cercato
-- (salva_calibrazione e' dichiarata in alto)
local box_ancora = nil                       -- indirizzo assoluto di un posto valido del PC (se trovato con la ricerca)
do
  local f = io.open(FILE_CAL, "r")
  if f then
    local v = f:read("l"); f:close()
    local d = v and tonumber(v:match("box_delta=(-?%d+)"))
    if d then box_ancora = { delta = d } end
  end
end

local function leggi_box()
  if not A.box then return nil, false end
  local out, trovati = {}, 0
  local function prova(addr)
    local pk = leggi_pkm(addr, false)
    if pk and not pk.uovo then out[#out + 1] = pk; trovati = trovati + 1 end
  end
  if box_ancora then
    local base = A.base + box_ancora.delta
    for m = -23, 23 do for n = -29, 29 do prova(base + m * 0x1000 + n * 0x88) end end
  else
    for box = 0, 23 do for slot = 0, 29 do prova(A.box + box * 0x1000 + slot * 0x88) end end
  end
  return out, trovati > 0
end

-- cerca nel blocco di salvataggio un Pokemon depositato (per imparare dove sta il PC)
local function cerca_nel_pc(pid)
  if not A.base then return false end
  for a = A.base, math.min(A.base + 0x30000, 0x3FFF00), 4 do
    if r32(a) == pid and leggi_pkm(a, false) then
      box_ancora = { delta = a - A.base }
      salva_calibrazione()
      print(string.format("[Soul Link] PC trovato: delta 0x%X", box_ancora.delta))
      return true
    end
  end
  return false
end

-- ---------------- JSON ----------------
local function esc(s)
  return (s:gsub('[%c"\\]', function(c)
    if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" end
    return string.format("\\u%04x", c:byte())
  end))
end
local function json(v)
  local t = type(v)
  if t == "table" then
    if v[1] ~= nil or next(v) == nil then
      local o = {}; for _, x in ipairs(v) do o[#o + 1] = json(x) end
      return "[" .. table.concat(o, ",") .. "]"
    end
    local o = {}
    for k, x in pairs(v) do o[#o + 1] = '"' .. esc(tostring(k)) .. '":' .. json(x) end
    return "{" .. table.concat(o, ",") .. "}"
  elseif t == "string" then return '"' .. esc(v) .. '"'
  elseif t == "boolean" then return v and "true" or "false"
  elseif t == "number" then return (math.type(v) == "integer") and tostring(v) or string.format("%.3f", v)
  end
  return "null"
end

-- ---------------- messaggi a schermo ----------------
local messaggi = {}
local function avvisa(t, secondi)
  messaggi[#messaggi + 1] = { testo = t, fine = emu.framecount() + 60 * (secondi or 8) }
  while #messaggi > 5 do table.remove(messaggi, 1) end
  print("[Soul Link] " .. t)
end

-- ---------------- ROM e randomizer ----------------
local function run_della_rom()
  -- BizHawk puo' mostrare "SoulLink_Raffo_run1" come "SoulLink Raffo run1": togliamo spazi e trattini
  local n = (gameinfo.getromname() or ""):lower():gsub("[%s_%-%.]", "")
  if not n:find("soullink", 1, true) then return nil end
  return tonumber(n:match("run(%d+)$") or n:match("run(%d+)"))
end
local function rom_per_run(run)
  local cart = assoluto(CFG.randomizer.cartella_output or "../rom_randomizzate")
  return sistema(cart .. "/SoulLink_" .. CFG.giocatore .. "_run" .. run .. ".nds"), sistema(cart)
end

-- Salvataggio di partenza: un salvataggio fatto in camera, prima dello starter, che viene copiato
-- su ogni nuova ROM. BizHawk chiama il salvataggio come la ROM con "_" -> " " e lo tiene in NDS/SaveRAM.
local FILE_BASE = DIR .. "salvataggio_base.SaveRAM"
local function cartella_saveram()
  if CFG.cartella_saveram and CFG.cartella_saveram ~= "" then return assoluto(CFG.cartella_saveram) end
  local exe = CFG.bizhawk or ""
  local dir = exe:match("^(.*)[/\\][^/\\]+$")
  return dir and (dir .. "/NDS/SaveRAM") or nil
end
local function file_saveram(nome_rom)
  local d = cartella_saveram()
  return d and sistema(d .. "/" .. nome_rom:gsub("_", " ") .. ".SaveRAM") or nil
end
local function copia(da, a)
  local f = io.open(da, "rb"); if not f then return false end
  local dati = f:read("a"); f:close()
  local g = io.open(a, "wb"); if not g then return false end
  g:write(dati); g:close()
  return true, dati
end
local function salvataggio_vuoto(dati)
  if not dati or #dati < 0x1000 then return true end
  local primo = dati:sub(1, 0x400)
  return not primo:find("[^\255]") or not primo:find("[^\0]")
end
-- prima di aprire la ROM di una nuova run: ci mettiamo dentro il salvataggio di partenza
local function prepara_salvataggio(percorso_rom)
  if not CFG.salta_inizio or not esiste(FILE_BASE) then return end
  local nome = percorso_rom:match("([^/\\]+)%.%w+$")
  local dest = nome and file_saveram(nome)
  if not dest then avvisa("Imposta 'bizhawk' in config.lua per usare il salvataggio di partenza", 15); return end
  if esiste(dest) then return end            -- la run ha gia' un suo salvataggio: non lo tocchiamo
  if copia(FILE_BASE, dest) then avvisa("Salvataggio di partenza copiato: premi Continua!", 12) end
end
-- quando ricevi lo starter, il salvataggio in camera e' ancora quello sulla cartuccia: lo teniamo da parte
local base_controllata = false
local salva_base_pendente = nil   -- modalita' app: nome della ROM il cui salvataggio va tenuto da parte
local salva_base_manuale = false  -- richiesto dal pulsante dell'app
local function cattura_salvataggio_base(n_prima, n_ora)
  if APP then
    if not base_controllata and n_prima == 0 and n_ora >= 1 then
      base_controllata = true
      pcall(client.saveram)
      salva_base_pendente = gameinfo.getromname() or ""
    end
    return
  end
  if base_controllata or not CFG.salta_inizio or esiste(FILE_BASE) then return end
  if not (n_prima == 0 and n_ora >= 1) then return end
  base_controllata = true
  pcall(client.saveram)                       -- scrive su disco il salvataggio della cartuccia
  local src = file_saveram(gameinfo.getromname() or "")
  if not src then return end
  local f = io.open(src, "rb"); if not f then avvisa("Non trovo il salvataggio in " .. src, 15); return end
  local dati = f:read("a"); f:close()
  if salvataggio_vuoto(dati) then
    avvisa("Non avevi salvato prima dello starter: niente salvataggio di partenza per ora.", 12); return
  end
  local g = io.open(FILE_BASE, "wb")
  if g then g:write(dati); g:close(); avvisa("Salvataggio di partenza creato! Dalla prossima run si parte dalla camera.", 15) end
end

local function randomizza(run)
  local R = CFG.randomizer
  local out, cart = rom_per_run(run)
  if esiste(out) then return out end
  local jar, imp, rom = sistema(assoluto(R.jar)), sistema(assoluto(R.impostazioni)), sistema(assoluto(R.rom_originale))
  for _, f in ipairs({ { jar, "randomizer (jar)" }, { imp, "impostazioni .rnqs" }, { rom, "ROM originale" } }) do
    if not esiste(f[1]) then avvisa("Manca il file " .. f[2] .. ": " .. f[1], 15); return nil end
  end
  avvisa("Genero la ROM randomizzata della run #" .. run .. "... (qualche secondo)", 20)
  gui.text(2, 60, "Randomizzazione in corso...", "yellow", "black"); emu.frameadvance()
  local logf = sistema(cart .. "/randomizer_run" .. run .. ".txt")
  local java = R.java or "java"
  local cmd
  if WIN then
    os.execute('mkdir "' .. cart .. '" >NUL 2>NUL')
    cmd = string.format('""%s" -Xmx2048M -jar "%s" cli -s "%s" -i "%s" -o "%s" -l >"%s" 2>&1"', java, jar, imp, rom, out, logf)
  else
    os.execute('mkdir -p "' .. cart .. '"')
    cmd = string.format('"%s" -Xmx2048M -jar "%s" cli -s "%s" -i "%s" -o "%s" -l >"%s" 2>&1', java, jar, imp, rom, out, logf)
  end
  os.execute(cmd)
  if esiste(out) then avvisa("ROM pronta!"); return out end
  avvisa("Errore del randomizer: guarda " .. logf, 20)
  return nil
end

-- ---------------- rete ----------------
local stato_rete = { ok = nil, ultimo_msg = -1, run = nil, stato = nil, errore = nil, http_assente = false, ignorato = nil }
SOLO_ALLENATORI = false         -- modalita' sperimentale: esperienza solo dagli allenatori
CONTROLLO_ESP = false           -- l'app controlla l'esperienza di ogni lotta (level cap bloccato, Condividi ridotto)
BLOCCA_INPUT = false            -- true quando l'utente sta usando un'altra finestra
VELOCITA = nil                  -- percentuale impostata dall'app (100 = normale)
CONDIVIDI_ESP = false           -- regola opzionale: Condividi esperienza per tutta la squadra
if APP then stato_rete.ultimo_msg = 0 end
local function invia(dati)
  local ok, risp
  if APP then
    if #coda_app > 0 then dati.risposte = coda_app; coda_app = {} end
    if salva_base_pendente then
      dati.salva_base = salva_base_pendente
      dati.salva_base_manuale = salva_base_manuale
      dati.salva_base_squadra = A.conta_squadra and (r32(A.conta_squadra) & 0xFF) or 0
    end
    local okS, n = pcall(comm.socketServerSend, json(dati))
    if not okS or not n or n <= 0 then stato_rete.ok = false; return false end
    ok, risp = pcall(comm.socketServerResponse)
    if ok and risp and risp ~= "" then salva_base_pendente, salva_base_manuale = nil, false end
  else
    if CFG.server == "" then stato_rete.errore = "server non impostato in config.lua"; return false end
    dati.codice, dati.giocatore, dati.ultimo_msg = CFG.codice, CFG.giocatore, stato_rete.ultimo_msg
    ok, risp = pcall(comm.httpPost, CFG.server .. "/api/gioco", json(dati))
  end
  if not ok or risp == nil or risp == "" then
    stato_rete.ok = false
    if not ok then stato_rete.http_assente = true end
    return false
  end
  stato_rete.ok, stato_rete.errore, stato_rete.ignorato = true, nil, nil
  for riga in risp:gmatch("[^\r\n]+") do
    local cmd, resto = riga:match("^(%u+)%s*(.*)$")
    if cmd == "RUN" then
      local n, st = resto:match("^(%d+)%s+(%S+)")
      stato_rete.run, stato_rete.stato = tonumber(n), st
    elseif cmd == "MSG" then
      local id, t = resto:match("^(%d+)%s+(.*)$")
      id = tonumber(id)
      if id and id > stato_rete.ultimo_msg then stato_rete.ultimo_msg = id; avvisa(t) end
    elseif cmd == "ULTIMO" then
      stato_rete.ultimo_msg = tonumber(resto) or 0
    elseif cmd == "IGNORATO" then
      stato_rete.ignorato = resto
    elseif cmd == "SALVABASE" then
      pcall(client.saveram)                 -- scrive su disco l'ultimo salvataggio fatto nel gioco
      salva_base_pendente, salva_base_manuale = gameinfo.getromname() or "", true
    elseif cmd == "BACKUP" then
      -- backup chiesto dall'app: scrive su disco il salvataggio del gioco e fa uno stato salvato del momento
      local id, percorso = resto:match("^(%d+)%s+(.+)$")
      if id then
        pcall(client.saveram)
        local okB = pcall(savestate.save, percorso, true)
        if not okB then okB = pcall(savestate.save, percorso) end   -- BizHawk vecchi: senza il secondo parametro
        coda_app[#coda_app + 1] = { tipo = "backup", id = tonumber(id), ok = okB and true or false }
      end
    elseif cmd == "CARICA" then
      local id, percorso = resto:match("^(%d+)%s+(.+)$")
      if id then
        local okC = pcall(savestate.load, percorso, true)
        if not okC then okC = pcall(savestate.load, percorso) end
        coda_app[#coda_app + 1] = { tipo = "caricato", id = tonumber(id), ok = okC and true or false }
      end
    elseif cmd == "AVVISO" then
      avvisa(resto, 12)
    elseif cmd == "DIAG" then
      CFG.diagnostica = resto == "1"
    elseif cmd == "CONDIVIDI" then
      local prima = CONDIVIDI_ESP
      CONDIVIDI_ESP = resto == "1"
      if prima and not CONDIVIDI_ESP then ripristina_condividi(); lotta.condividi = nil end
    elseif cmd == "VELOCITA" then
      -- velocita' scelta nell'app (le scorciatoie di BizHawk per la velocita' sono spente)
      local v = tonumber(resto)
      if v and v ~= VELOCITA then VELOCITA = v; pcall(client.speedmode, v) end
    elseif cmd == "FOCUS" then
      BLOCCA_INPUT = resto == "0"           -- l'app non e' in primo piano: i tasti non vanno al gioco
    elseif cmd == "MODO" then
      local prima = SOLO_ALLENATORI
      SOLO_ALLENATORI = resto:match("^(%S+)") == "allenatori"
      if prima and not SOLO_ALLENATORI and not CONTROLLO_ESP then ripristina_esp(); lotta.molt = nil end
    elseif cmd == "ESP" then
      -- moltiplicatore per la lotta con l'allenatore in corso (risposta dell'app)
      local all, n = resto:match("^(%d+)%s+(-?%d+)")
      if lotta.attiva and lotta.allenatore == tonumber(all) and SOLO_ALLENATORI then
        lotta.molt = tonumber(n); applica_esp(lotta.molt)
      end
    elseif cmd == "ESPX" then
      -- esperienza per il prossimo Pokemon battuto, calcolata dall'app (cap bloccato, Condividi ridotto, solo allenatori)
      local n = tonumber(resto:match("^(-?%d+)"))
      if n and lotta.attiva and (SOLO_ALLENATORI or CONTROLLO_ESP) then lotta.molt = n; applica_esp(n) end
    elseif cmd == "CONTROLLO" then
      local prima = CONTROLLO_ESP
      CONTROLLO_ESP = resto == "1"
      if prima and not CONTROLLO_ESP and not SOLO_ALLENATORI then ripristina_esp(); lotta.molt = nil end
    elseif cmd == "DUMP" then
      local okD, err = pcall(scrivi_dump, resto)
      coda_app[#coda_app + 1] = { tipo = "dump", ok = okD and true or false, errore = (not okD) and tostring(err) or nil, percorso = resto }
    elseif cmd == "ERR" then
      stato_rete.errore = resto; avvisa("Server: " .. resto, 10)
    end
  end
  return true
end

-- ---------------- stato del gioco ----------------
local coda = {}                 -- eventi da spedire (incontri, esiti)
lotta = { attiva = false }
local controllo_cattura = nil   -- {pid, fino_a, era_piena}
local ultima_firma, ultima_firma_box = nil, nil
local ultimo_invio, ultimo_controllo_box = -99999, -99999
local squadra, box, box_ok = nil, nil, false
local tentata_rom = {}
local ultimo_input, pendente_da = 0, nil
local n_squadra_prima = nil

local function popcount(x) local c = 0; while x > 0 do c = c + (x & 1); x = x >> 1 end; return c end

local function contiene(lista, pid)
  for _, m in ipairs(lista or {}) do if m.pid == pid then return true end end
  return false
end

local function firma_squadra(sq)
  local t = {}
  for _, m in ipairs(sq or {}) do t[#t + 1] = string.format("%d:%d:%d:%d:%s", m.pid, m.specie, m.livello, m.ps, m.soprannome) end
  return table.concat(t, ";")
end
local function firma_box(bx)
  local t = {}
  for _, m in ipairs(bx or {}) do t[#t + 1] = m.pid .. ":" .. m.specie end
  table.sort(t)
  return table.concat(t, ";")
end

-- ---- indicatore "in lotta": quello della versione inglese, oppure trovato da solo ----
-- Finche' non e' calibrato, l'inizio di una lotta si riconosce da un Pokemon nemico NUOVO in memoria
-- e la fine da: Pokemon catturato, cambio di zona o lotta successiva.
local cal_lotta = { addr = nil, candidati = nil, lotte = 0, fuori = 0 }
do
  local f = io.open(FILE_CAL, "r")
  if f then
    for riga in f:lines() do
      local v = riga:match("lotta=(%d+)")
      if v then cal_lotta.addr = tonumber(v) end
      local e = riga:match("esp=(%d+)")
      if e then esp_sito = tonumber(e) end
    end
    f:close()
  end
end
salva_calibrazione = function()
  local f = io.open(FILE_CAL, "w")
  if not f then return end
  if box_ancora then f:write("box_delta=" .. box_ancora.delta .. "\n") end
  if cal_lotta.addr then f:write("lotta=" .. cal_lotta.addr .. "\n") end
  if esp_sito then f:write("esp=" .. esp_sito .. "\n") end
  f:close()
end
local function e_lotta(v) return v == 0x2100 or v == 0x2101 end

local function in_lotta_secondo_flag()
  if cal_lotta.addr then return e_lotta(r16(cal_lotta.addr)) end
  return nil
end

local function chiudi_calibrazione()
  local n, unico = 0, nil
  for a in pairs(cal_lotta.candidati or {}) do n = n + 1; unico = a end
  if n == 1 and cal_lotta.lotte >= 2 and cal_lotta.fuori >= 1 then
    cal_lotta.addr = unico; salva_calibrazione()
    print(string.format("[Soul Link] Indicatore di lotta trovato: 0x%06X", unico))
  elseif n == 0 and cal_lotta.candidati then cal_lotta.candidati, cal_lotta.lotte, cal_lotta.fuori = nil, 0, 0 end
end
-- chiamata quando siamo SICURAMENTE in lotta (nemico nuovo appena apparso)
local function calibra_in_lotta()
  if cal_lotta.addr then return end
  local nuovi = {}
  if cal_lotta.candidati == nil then
    for a = 0x190000, 0x1CFFFE, 2 do if e_lotta(r16(a)) then nuovi[a] = true end end
    nuovi[STATO_LOTTA] = e_lotta(r16(STATO_LOTTA)) or nil
  else
    for a in pairs(cal_lotta.candidati) do if e_lotta(r16(a)) then nuovi[a] = true end end
  end
  cal_lotta.candidati = nuovi
  cal_lotta.lotte = cal_lotta.lotte + 1
  chiudi_calibrazione()
end
-- chiamata quando siamo SICURAMENTE fuori dalla lotta (cambio di zona)
local function calibra_fuori_lotta()
  if cal_lotta.addr or not cal_lotta.candidati then return end
  for a in pairs(cal_lotta.candidati) do if e_lotta(r16(a)) then cal_lotta.candidati[a] = nil end end
  cal_lotta.fuori = cal_lotta.fuori + 1
  chiudi_calibrazione()
end
local function n_candidati()
  local n = 0; for _ in pairs(cal_lotta.candidati or {}) do n = n + 1 end; return n
end

local ultimo_pid_nemico = nil   -- nil = non ancora letto (all'avvio non generiamo eventi)
local ultima_zona = nil
local verifica_fuori = nil

local function chiudi_controllo(esito)
  local c = controllo_cattura
  coda[#coda + 1] = { tipo = "esito", pid = c.pid, esito = esito }
  controllo_cattura = nil
end

local function squadra_viva()
  for _, m in ipairs(squadra or {}) do if m.ps > 0 then return true end end
  return false
end
-- una lotta contro un allenatore e' finita: vinta se ci resta almeno un Pokemon in piedi
-- squadra avversaria (fino a 6 Pokemon in fila dopo il primo)
local function nemici_allenatore()
  local out = {}
  if not A.nemico then return out end
  for i = 0, 5 do
    local pk = leggi_pkm(A.nemico + i * 0xDC, true)
    if not pk then break end
    out[#out + 1] = { specie = pk.specie, livello = pk.livello }
  end
  return out
end

-- Durante la lotta il gioco tiene per ogni Pokemon una struttura (BTL_POKEPARAM) con PS attuali, stato, PP, modifiche
-- alle statistiche e un puntatore al Pokemon vero. Una tabella di puntatori a queste strutture sta in lotta_dati.
local function struttura_lotta(p)
  if not p or p < 0x1000 or p + 0x140 > 0x400000 then return nil end
  local pkm = r32(p) & 0xFFFFFF
  if pkm < 0x1000 or pkm + 0xDC > 0x400000 then return nil end
  local ps, ps_max = r16(p + 0x10), r16(p + 0x0E)
  if ps_max == 0 or ps > ps_max then return nil end
  local illusione = r32(p + 4)
  local st1, st2 = r32(p + 0xFC), r32(p + 0x100)
  local t = { pid = r32(pkm), ps = ps, ps_max = ps_max, stato = r32(p + 0x20) & 0xFF, pp = {}, mosse = {},
              illusione = ((illusione >> 24) == 0x02) and r32(illusione & 0xFFFFFF) or nil,
              stadi = { st1 & 0xFF, (st1 >> 8) & 0xFF, (st2) & 0xFF, (st1 >> 16) & 0xFF, (st1 >> 24) & 0xFF } }  -- att, dif, vel, att.sp, dif.sp
  for i = 0, 3 do
    t.mosse[i + 1] = r16(p + 0x104 + i * 14)
    t.pp[i + 1] = r8(p + 0x104 + i * 14 + 2)
  end
  return t
end
-- tutte le strutture raggiungibili dalla tabella, per PID (solo quelle che portano a un Pokemon della lotta)
local function strutture_lotta(validi)
  local per_pid, posto = {}, {}
  if not A.lotta_dati then return per_pid, posto end
  for off = 0, 0x1FC, 4 do
    local v = r32(A.lotta_dati + off)
    if (v >> 24) == 0x02 then
      local t = struttura_lotta(v & 0xFFFFFF)
      if t and validi[t.pid] and not per_pid[t.pid] then per_pid[t.pid] = t; posto[t.pid] = off end
    end
  end
  return per_pid, posto
end

local function dettagli_lotta()
  if not lotta.attiva or not A.nemico then return nil end
  local nemici, per_pid, validi, pk_nem = {}, {}, {}, {}
  for i = 0, 5 do
    local pk = leggi_pkm(A.nemico + i * 0xDC, true)
    if not pk then break end
    nemici[#nemici + 1] = { specie = pk.specie, livello = pk.livello, ps = pk.ps, ps_max = pk.ps_max }
    per_pid[pk.pid] = #nemici; validi[pk.pid] = true; pk_nem[#nemici] = pk
    if not lotta.allenatore and lotta.letto then break end      -- selvatico: uno solo
  end
  for _, m in ipairs(squadra or {}) do validi[m.pid] = true end
  local st, posto = strutture_lotta(validi)
  lotta.ps_visti = lotta.ps_visti or {}
  lotta.abilita_viste = lotta.abilita_viste or {}
  -- chi e' in campo per l'avversario: il PID che il gioco tiene da parte, oppure i posti +0x1C/+0x20 della tabella
  local in_campo = {}
  local pidn = A.pid_nemico_lotta and r32(A.pid_nemico_lotta) or 0
  if per_pid[pidn] then in_campo[per_pid[pidn]] = true end
  for pid, off in pairs(posto) do
    if per_pid[pid] and (off == 0x1C or off == 0x20) then in_campo[per_pid[pid]] = true end
  end
  for i in pairs(in_campo) do nemici[i].in_campo = true end
  for pid, i in pairs(per_pid) do
    local t = st[pid]
    if t then
      lotta.ps_visti[i] = t.ps
      nemici[i].stato = t.stato
    end
  end
  for i, ps in pairs(lotta.ps_visti) do if nemici[i] then nemici[i].ps = ps end end   -- PS veri di chi si e' visto
  -- abilita' dell'avversario: si sa solo quando il gioco la mostra (e' scritta qui nel momento in cui si attiva)
  if A.abilita_vista then
    for k, off in ipairs({ 4, 0x0C }) do
      local ab = r16(A.abilita_vista + off)
      if ab ~= 0 then
        for i, pk in pairs(pk_nem) do
          if nemici[i].in_campo and pk.abilita == ab then lotta.abilita_viste[i] = ab end
        end
      end
    end
  end
  for i, ab in pairs(lotta.abilita_viste) do if nemici[i] then nemici[i].abilita = ab end end
  -- il mio Pokemon in campo e i PS / stato veri di tutta la mia squadra
  local mio = nil
  local pidm = A.pid_mio_lotta and r32(A.pid_mio_lotta) or 0
  if st[pidm] and contiene(squadra, pidm) then mio = st[pidm] end
  if not mio then
    for pid, off in pairs(posto) do
      if (off == 0 or off == 4) and contiene(squadra, pid) then mio = st[pid]; break end
    end
  end
  local vivi = {}
  for _, m in ipairs(squadra or {}) do
    local t = st[m.pid]
    if t then vivi[#vivi + 1] = { pid = m.pid, ps = t.ps, ps_max = t.ps_max, stato = t.stato } end
  end
  diag.lotta_strutture = 0; for _ in pairs(st) do diag.lotta_strutture = diag.lotta_strutture + 1 end
  diag.lotta_pid_nemico = string.format("%08X", pidn)
  return { allenatore = lotta.allenatore or 0, letto = lotta.letto, nemici = nemici, mio = mio, squadra = vivi }
end
local function firma_dettagli(d)
  if not d then return "-" end
  local t = { tostring(d.allenatore), tostring(d.letto) }
  for _, n in ipairs(d.nemici) do
    t[#t + 1] = n.specie .. ":" .. n.ps .. ":" .. tostring(n.stato) .. ":" .. tostring(n.abilita) .. (n.in_campo and "*" or "")
  end
  if d.mio then
    t[#t + 1] = d.mio.pid .. ":" .. d.mio.ps .. ":" .. table.concat(d.mio.pp, ",") .. ":" .. table.concat(d.mio.stadi, ",")
  end
  for _, m in ipairs(d.squadra or {}) do t[#t + 1] = m.pid .. "/" .. m.ps .. "/" .. m.stato end
  return table.concat(t, ";")
end
local ultima_firma_dettagli = nil

-- comando DUMP: scrive in un file di testo la memoria che serve per capire cosa non va (lotta, flag, codice dell'esperienza)
scrivi_dump = function(percorso)
  local f = assert(io.open(percorso, "w"))
  local function sezione(nome, da, n)
    if not da or da < 0 or da + n > 0x400000 then f:write("#sezione " .. nome .. " assente\n"); return end
    f:write(string.format("#sezione %s 0x%06X %d\n", nome, da, n))
    local riga = {}
    for i = 0, n - 1 do
      riga[#riga + 1] = string.format("%02x", r8(da + i))
      if #riga == 32 then f:write(table.concat(riga), "\n"); riga = {} end
    end
    if #riga > 0 then f:write(table.concat(riga), "\n") end
  end
  local info = { rom = CODICE_ROM, fonte = A.fonte, base = A.base, esp_sito = esp_sito, cond_sito = cond_sito,
                 solo_allenatori = SOLO_ALLENATORI, controllo = CONTROLLO_ESP, condividi = CONDIVIDI_ESP,
                 lotta_attiva = lotta.attiva, allenatore = lotta.allenatore, molt = lotta.molt, zona = diag.zona,
                 diag = diag, frame = emu.framecount() }
  f:write("#info ", json(info), "\n")
  if A.base then
    sezione("lotta_dati", A.lotta_dati, 0x200)
    local n = 0
    for off = 0, 0x1FC, 4 do
      local v = r32(A.lotta_dati + off)
      if (v >> 24) == 0x02 and n < 24 then
        n = n + 1
        sezione(string.format("struttura+%03X", off), v & 0xFFFFFF, 0x140)
        local pk = r32((v & 0xFFFFFF)) 
        if (pk >> 24) == 0x02 then sezione(string.format("pkm+%03X", off), pk & 0xFFFFFF, 0x10) end
      end
    end
    sezione("pid_lotta", A.pid_mio_lotta, 0x80)
    sezione("pid_nemico", A.pid_nemico_lotta, 0x20)
    sezione("abilita_vista", A.abilita_vista, 0x40)
    sezione("nemici", A.nemico, 0xDC * 6)
    sezione("squadra", A.squadra, 0xDC * 6)
    sezione("flag", A.flag_evento, 0x17F)
    sezione("zona", A.zona, 0x40)
  end
  if esp_sito then sezione("codice_esp", esp_sito - 0x6000, 0x8000) end
  if cond_sito then sezione("codice_condividi", cond_sito - 0x200, 0x400) end
  sezione("ram_stato_lotta", STATO_LOTTA - 0x40, 0x80)
  f:close()
end

-- flag degli eventi del gioco (strumenti raccolti, allenatori battuti...): 0x17F byte
local N_FLAG = 0x17F
local function leggi_flag()
  if not A.flag_evento or not valido_addr(A.flag_evento) then return nil end
  local t = {}
  if memory.read_bytes_as_array then
    t = memory.read_bytes_as_array(A.flag_evento, N_FLAG, DOM)
  else
    for i = 0, N_FLAG - 1 do t[i + 1] = r8(A.flag_evento + i) end
  end
  return t
end
local function flag_in_testo(t)
  if not t then return nil end
  local h = {}
  for i = 1, #t do h[i] = string.format("%02x", t[i]) end
  return table.concat(h)
end
local ultima_flag = nil
local ultima_lettura_flag, flag_letti = nil, nil
local controllo_flag = nil       -- dopo una lotta vinta: quali flag si sono accesi (per capire dove il gioco segna gli allenatori)

local function fine_lotta()
  if lotta.allenatore and not lotta.chiusa then
    lotta.chiusa = true
    local vinta = squadra_viva()
    coda[#coda + 1] = { tipo = "fine_allenatore", allenatore = lotta.allenatore, vinta = vinta }
    if APP and vinta and lotta.flag_prima then
      controllo_flag = { allenatore = lotta.allenatore, prima = lotta.flag_prima, quando = emu.framecount() + 240 }
    end
  end
end
local function verifica_flag(fc)
  if not controllo_flag or fc < controllo_flag.quando then return end
  local dopo = leggi_flag()
  if dopo then
    local nuovi = {}
    for i = 1, math.min(#dopo, #controllo_flag.prima) do
      local acceso = dopo[i] & (~controllo_flag.prima[i]) & 0xFF
      for b = 0, 7 do
        if (acceso >> b) & 1 == 1 then nuovi[#nuovi + 1] = (i - 1) * 8 + b end
      end
    end
    if #nuovi > 0 and #nuovi <= 64 then
      coda_app[#coda_app + 1] = { tipo = "flag_allenatore", allenatore = controllo_flag.allenatore, nuovi = nuovi }
    end
  end
  controllo_flag = nil
end

-- all'inizio di una lotta (quando si sa se e' un selvatico): quanta esperienza dare
local function prepara_esperienza()
  assicura_sito_esp()
  if CONDIVIDI_ESP then lotta.condividi = true; applica_condividi() end
  if not (SOLO_ALLENATORI or CONTROLLO_ESP) then lotta.molt = nil; return end
  -- finche' l'app non risponde: niente (solo allenatori) oppure normale (solo controllo del cap / Condividi)
  lotta.molt = SOLO_ALLENATORI and 0 or 1
  if lotta.allenatore and SOLO_ALLENATORI then
    local primo, vivi = nil, 0
    for _, m in ipairs(squadra or {}) do
      if m.ps > 0 and not m.uovo then vivi = vivi + 1; primo = primo or m end
    end
    coda_app[#coda_app + 1] = { tipo = "allenatore_esp", allenatore = lotta.allenatore, nemici = nemici_allenatore(), vivi = vivi,
                                primo = primo and { specie = primo.specie, livello = primo.livello, esperienza = primo.esperienza } or nil }
  end
  applica_esp(lotta.molt)
end

local function aggiorna_esperienza()
  if lotta.attiva and lotta.letto then
    if (SOLO_ALLENATORI or CONTROLLO_ESP) and lotta.molt then applica_esp(lotta.molt) end
    if CONDIVIDI_ESP then lotta.condividi = true; applica_condividi() end
  elseif not lotta.attiva and lotta.finita then
    if esp_sito and lotta.molt ~= nil then ripristina_esp(); lotta.molt = nil end   -- a lotta finita il codice torna com'era
    if lotta.condividi then ripristina_condividi(); lotta.condividi = nil end
  end
end

local function aggiorna_lotta(fc)
  local zona = r16(A.zona)
  local cambio_zona = ultima_zona ~= nil and zona ~= ultima_zona
  ultima_zona = zona
  -- dopo un cambio di zona siamo fuori dalla lotta: lo verifichiamo mezzo secondo dopo,
  -- e solo se nel frattempo non e' iniziata una lotta (erba sul confine della zona)
  if cambio_zona then verifica_fuori = { quando = fc + 30, da = fc } end
  if verifica_fuori and fc >= verifica_fuori.quando then
    if not (lotta.inizio and lotta.inizio >= verifica_fuori.da) then calibra_fuori_lotta() end
    verifica_fuori = nil
  end

  local flag = in_lotta_secondo_flag()
  diag.stato_lotta = cal_lotta.addr and string.format("0x%04X", r16(cal_lotta.addr)) or string.format("0x%04X", r16(STATO_LOTTA))

  local nem = A.nemico and leggi_pkm(A.nemico, true) or nil
  local pid = nem and nem.pid or 0
  if ultimo_pid_nemico == nil then ultimo_pid_nemico = pid; return end
  -- i PS del nemico che cambiano dicono che la lotta e' ancora in corso (serve senza indicatore calibrato)
  if lotta.attiva and nem and pid == ultimo_pid_nemico and nem.ps ~= lotta.ps then
    lotta.ps, lotta.ps_max, lotta.vivo = nem.ps, nem.ps_max, fc
  end

  -- NUOVA LOTTA: compare in memoria un Pokemon nemico mai visto
  if nem and pid ~= ultimo_pid_nemico then
    ultimo_pid_nemico = pid
    if lotta.attiva or lotta.finita then fine_lotta() end
    lotta = { attiva = true, inizio = fc, nemico = nem, letto = false, ps = nem.ps, ps_max = nem.ps_max, vivo = fc }
    calibra_in_lotta()
    if controllo_cattura then                                   -- la lotta prima e' sicuramente finita
      local c = controllo_cattura
      local preso = contiene(squadra, c.pid)
      if not preso and c.era_piena then
        local bx, ok = leggi_box()
        if ok then box, box_ok = bx, true; preso = contiene(bx, c.pid) end
      end
      chiudi_controllo(preso and "catturato" or ((c.era_piena and not box_ok) and "incerto" or "fallito"))
    end
  end

  -- dopo un secondo leggiamo chi e' l'avversario (0 = selvatico)
  if lotta.attiva and not lotta.letto and fc - lotta.inizio >= 60 then
    lotta.letto = true
    local all = r16(A.allenatore_nemico)
    diag.allenatore, diag.nemico = all, lotta.nemico.specie
    if all ~= 0 then lotta.allenatore = all; lotta.flag_prima = leggi_flag() end
    prepara_esperienza()
    if all == 0 then
      local n = lotta.nemico
      local tid, sid = 0, 0
      if squadra and squadra[1] then tid, sid = squadra[1].id_allenatore, squadra[1].id_segreto end
      local shiny = (tid ~ sid ~ (n.pid >> 16) ~ (n.pid & 0xFFFF)) < 8
      coda[#coda + 1] = { tipo = "incontro", pid = n.pid, specie = n.specie, livello = n.livello, shiny = shiny, zona = zona }
      controllo_cattura = { pid = n.pid, inizio = fc, era_piena = squadra and #squadra >= 6, prossimo_box = fc }
    end
  end

  -- fine lotta: con l'indicatore calibrato lo sappiamo subito; altrimenti quando il codice di lotta
  -- sparisce dalla memoria (due controlli di fila), o col cambio di zona
  if lotta.attiva and lotta.letto then
    local caricato = codice_lotta_caricato()
    if caricato then lotta.codice_visto = true end
    -- conta solo se in questa lotta il codice c'era (un indirizzo vecchio o di un'altra versione non deve chiudere le lotte)
    if caricato == false and lotta.codice_visto then lotta.via = (lotta.via or 0) + 1 else lotta.via = 0 end
    if flag == false or cambio_zona or lotta.via >= 2 then
      lotta.attiva = false; lotta.finita = fc
      diag.fine_lotta = flag == false and "indicatore" or cambio_zona and "cambio di zona" or "codice di lotta sparito"
    end
  end
  -- la squadra si aggiorna qualche istante dopo la fine: aspettiamo 2 secondi prima di dire vinta/persa
  if not lotta.attiva and lotta.finita and fc - lotta.finita >= 120 then fine_lotta() end
end

local function aggiorna_controllo_cattura(fc)
  local c = controllo_cattura
  if not c then return end
  local preso = contiene(squadra, c.pid)
  if not preso and c.era_piena and fc >= c.prossimo_box then
    c.prossimo_box = fc + 120
    local bx, ok = leggi_box()
    if ok then box, box_ok = bx, true; preso = contiene(bx, c.pid)
    elseif not c.cercato then c.cercato = true; preso = cerca_nel_pc(c.pid) end
  end
  if preso then chiudi_controllo("catturato"); ultimo_controllo_box = -99999; return end
  -- fallito: lotta finita da 10 s (indicatore o cambio zona) senza cattura, oppure dopo 15 minuti
  local finita = (not lotta.attiva) and lotta.finita and fc - lotta.finita > 600
  if finita or fc - c.inizio > 60 * 60 * 15 then
    chiudi_controllo((c.era_piena and not box_ok) and "incerto" or "fallito")
  end
end

local function gestisci_rom()
  if APP then return end
  if not CFG.randomizer.attivo or not stato_rete.run then return end
  local run = stato_rete.run
  if run_della_rom() == run or tentata_rom[run] then return end
  tentata_rom[run] = true
  local out = randomizza(run)
  if out then
    avvisa("Carico la ROM della run #" .. run)
    prepara_salvataggio(out)
    client.openrom(out)
    CODICE_ROM = codice_gioco()
    A, squadra, box, box_ok, ultima_firma, ultima_firma_box = { fonte = "nessuna" }, nil, nil, false, nil, nil
  end
end

-- cosa sta facendo il giocatore, per la barra in alto dell'app (anche degli altri giocatori)
local function attivita_attuale(fc)
  if not lotta.attiva or not lotta.nemico then return { lotta = false } end
  -- senza indicatore calibrato la fine della lotta si vede solo cambiando zona: dopo 90 s senza
  -- movimenti dei PS del nemico la consideriamo finita (solo per la visualizzazione)
  -- senza indicatore e senza codice di lotta conosciuto la fine si vede solo cambiando zona:
  -- dopo 4 minuti senza movimenti dei PS del nemico la consideriamo finita (solo per la visualizzazione)
  if not cal_lotta.addr and not lotta.codice_visto and fc - (lotta.vivo or lotta.inizio) > 60 * 240 then
    return { lotta = false }
  end
  local a = { lotta = true, specie = lotta.nemico.specie, livello = lotta.nemico.livello, ps = lotta.ps, ps_max = lotta.ps_max }
  if lotta.letto then a.allenatore = lotta.allenatore or 0 end
  if lotta.mio then a.mio = lotta.mio end      -- il mio Pokemon in campo (per l'avviso "in pericolo" a tutti)
  return a
end
local function firma_attivita(a)
  if not a.lotta then return "-" end
  local m = a.mio and (a.mio.pid .. "/" .. a.mio.ps) or ""
  return tostring(a.specie) .. ":" .. tostring(a.allenatore) .. ":" .. tostring(a.ps) .. ":" .. m
end
local ultima_attivita = nil

-- ---------------- disegno ----------------
local schermo_pulito = false
local function disegna(fc)
  -- con l'app tutto si vede nella finestra dell'app: niente scritte sopra il gioco
  if APP then
    if not schermo_pulito then pcall(gui.clearGraphics); schermo_pulito = true end
    return
  end
  local y = 2
  local stato
  if APP then stato = stato_rete.ok and ("Soul Link: collegato all'app" .. (stato_rete.run and (" - run #" .. stato_rete.run) or "")) or "Soul Link: app non raggiungibile"
  elseif stato_rete.http_assente then stato, y = "Soul Link: avvia BizHawk con avvia_bizhawk.bat!", y
  elseif stato_rete.ok == nil then stato = "Soul Link: mi collego..."
  elseif stato_rete.ok then stato = "Soul Link: online" .. (stato_rete.run and (" - run #" .. stato_rete.run) or "")
  else stato = "Soul Link: server non raggiungibile" end
  gui.text(2, y, stato, stato_rete.ok and "lime" or "yellow"); y = y + 16
  if stato_rete.ignorato then gui.text(2, y, "Dati ignorati: " .. stato_rete.ignorato, "orange"); y = y + 16 end
  if stato_rete.stato == "game_over" then gui.text(2, y, "GAME OVER - avvia la nuova run dall'app", "red"); y = y + 16 end
  if stato_rete.stato == "vinta" then gui.text(2, y, "RUN VINTA! Complimenti!", "gold"); y = y + 16 end
  if CFG.diagnostica then
    for _, riga in ipairs({
      "ROM " .. CODICE_ROM .. "  indirizzi: " .. A.fonte .. (A.base and string.format(" (base 0x%06X)", A.base) or ""),
      "squadra: " .. (squadra and (#squadra .. " - 1o specie " .. squadra[1].specie .. " luogo " .. squadra[1].luogo) or "non letta"),
      "zona " .. tostring(diag.zona) .. " / padre " .. tostring(diag.zona_padre) .. "  lotta: " .. (lotta.attiva and "SI" or "no") ..
        (cal_lotta.addr and string.format(" (indicatore 0x%06X)", cal_lotta.addr) or (" (calibrazione: " .. n_candidati() .. " candidati, " .. cal_lotta.lotte .. " lotte)")),
      "ultimo nemico: specie " .. tostring(diag.nemico) .. " allenatore " .. tostring(diag.allenatore),
      "medaglie: " .. tostring(diag.medaglie) .. "  PC: " .. (box_ok and (#box .. " Pokemon") or "non trovato") .. (box_ancora and " (calibrato)" or ""),
    }) do gui.text(2, y, riga, "cyan", "#C0000000"); y = y + 14 end
  end
  local i = 1
  while i <= #messaggi do
    if messaggi[i].fine < fc then table.remove(messaggi, i)
    else gui.text(2, y, messaggi[i].testo, "white", "#B0000000"); y = y + 16; i = i + 1 end
  end
end

-- ---------------- ciclo principale ----------------
if APP then print("[Soul Link] v3 - ROM " .. CODICE_ROM .. " - modalita' app")
else
  print("[Soul Link] v3 - ROM " .. CODICE_ROM .. " - giocatore " .. tostring(CFG.giocatore) .. " - server " .. CFG.server)
  if not CFG.giocatore or CFG.giocatore == "" then avvisa("Imposta il tuo nome in config.lua!", 30) end
end

local tasti_rilasciati = nil
local function blocca_tasti()
  -- BizHawk accetta i tasti anche in background (serve perche' e' dentro l'app): se l'utente scrive
  -- in un'altra finestra li forziamo tutti "rilasciati" per questo frame
  if not tasti_rilasciati then
    local ok, t = pcall(joypad.get)
    if not ok or type(t) ~= "table" then return end
    tasti_rilasciati = {}
    for k, v in pairs(t) do if type(v) == "boolean" then tasti_rilasciati[k] = false end end
  end
  pcall(joypad.set, tasti_rilasciati)
end

while true do
  local fc = emu.framecount()
  if APP and BLOCCA_INPUT then blocca_tasti() end
  do
    local ok, tasti = pcall(joypad.get)
    if ok and type(tasti) == "table" then
      for _, v in pairs(tasti) do if v == true then ultimo_input = fc; break end end
    end
  end
  -- con l'app: un contatto leggero ogni 15 frame, per sapere subito se l'utente e' passato a un'altra finestra
  if APP and fc % 30 == 15 and fc - ultimo_invio >= 10 then
    invia({ ping = true, fc = fc })        -- non tocca ultimo_invio: i dati veri partono come sempre
  end
  if fc % 30 == 0 then
    risolvi()
    if A.base then
      diag.zona, diag.zona_padre = r16(A.zona), r16(A.zona_padre)
      diag.medaglie = popcount(r8(A.medaglie))
      local sq = leggi_squadra()
      local n_ora = A.conta_squadra and (r32(A.conta_squadra) & 0xFF) or nil
      if n_ora and n_ora <= 6 then
        if n_squadra_prima ~= nil and sq and #sq >= 1 and run_della_rom() then cattura_salvataggio_base(n_squadra_prima, n_ora) end
        n_squadra_prima = n_ora
      end
      if sq then squadra = sq end
      aggiorna_lotta(fc)
      aggiorna_esperienza()
      aggiorna_controllo_cattura(fc)
      -- il PC si rilegge quando cambia la squadra (deposito/ritiro) o ogni 30 secondi
      local fs = firma_squadra(squadra)
      local cambio_squadra = fs ~= ultima_firma
      if (cambio_squadra or fc - ultimo_controllo_box > 1800) and not lotta.attiva then
        local bx, ok = leggi_box()
        if not ok and box_ancora == nil and squadra and ultima_firma then
          -- un Pokemon e' sparito dalla squadra: forse e' stato depositato, proviamo a trovare il PC
          for pid in (ultima_firma or ""):gmatch("(%d+):%d+:%d+:%d+:") do
            if not contiene(squadra, tonumber(pid)) and cerca_nel_pc(tonumber(pid)) then bx, ok = leggi_box(); break end
          end
        end
        box, box_ok = bx, ok
        ultimo_controllo_box = fc
      end

      local run_rom = run_della_rom()
      if not CFG.randomizer.attivo then run_rom = nil
      elseif run_rom == nil then run_rom = -1 end      -- ROM non del Soul Link: i dati non contano

      local fb = box_ok and firma_box(box) or nil
      local att = attivita_attuale(fc)
      local fa = firma_attivita(att)
      local det = APP and att.lotta and dettagli_lotta() or nil
      if det and det.mio then
        local m = nil
        for _, x in ipairs(squadra or {}) do if x.pid == det.mio.pid then m = x end end
        lotta.mio = { pid = det.mio.pid, ps = det.mio.ps, ps_max = det.mio.ps_max, specie = m and m.specie or 0,
                      nome = m and m.soprannome or "" }
        att.mio = lotta.mio
        fa = firma_attivita(att)
      end
      local fd = firma_dettagli(det)
      if APP and fc - (ultima_lettura_flag or -999) >= 90 then      -- i flag cambiano di rado: ogni secondo e mezzo basta
        ultima_lettura_flag = fc
        flag_letti = flag_in_testo(leggi_flag())
      end
      local ff = APP and flag_letti or nil
      verifica_flag(fc)
      local da_mandare = (#coda > 0) or (squadra and fs ~= ultima_firma) or (fb and fb ~= ultima_firma_box)
                         or (APP and fa ~= ultima_attivita) or #coda_app > 0 or (APP and fd ~= ultima_firma_dettagli)
                         or (ff and ff ~= ultima_flag)
      if da_mandare and not pendente_da then pendente_da = fc elseif not da_mandare then pendente_da = nil end
      -- le richieste bloccano l'emulatore per un attimo: le facciamo quando non stai premendo tasti
      -- con l'app la richiesta e' locale e istantanea: niente attese
      local fermo = APP or fc - ultimo_input >= (CFG.fermo_frame or 90)
      local tocca_poll = fc - ultimo_invio >= (APP and 60 or CFG.secondi_controllo * 60)
      local urgente = pendente_da and fc - pendente_da >= 60 * (CFG.attesa_massima or 20)
      if (da_mandare and (fermo or urgente) and fc - ultimo_invio >= (APP and 30 or 60)) or (tocca_poll and fermo)
         or fc - ultimo_invio >= 60 * 60 then
        local dati = { attivo = true, run_rom = run_rom, medaglie = diag.medaglie, zona = diag.zona, attivita = att }
        ultima_attivita = fa
        if APP and fd ~= ultima_firma_dettagli then dati.lotta_dettagli = det or false; ultima_firma_dettagli = fd end
        if ff and ff ~= ultima_flag then dati.flag_evento = ff; ultima_flag = ff end
        if squadra and fs ~= ultima_firma then dati.squadra = squadra end
        if fb and fb ~= ultima_firma_box then dati.squadra = squadra; dati.box = box; dati.box_ok = true end
        if #coda > 0 then dati.eventi = coda end
        if CFG.diagnostica then
          dati.diagnostica = { rom = CODICE_ROM, fonte = A.fonte, base = A.base, zona = diag.zona, zona_padre = diag.zona_padre,
            stato_lotta = diag.stato_lotta, in_lotta = lotta.attiva == true, lotta_calibrata = cal_lotta.addr,
            lotta_candidati = n_candidati(), lotte_viste = cal_lotta.lotte, ultimo_nemico = diag.nemico, ultimo_allenatore = diag.allenatore,
            medaglie = diag.medaglie, squadra = squadra and #squadra or 0, pc = box_ok and #box or -1,
            pc_calibrato = box_ancora ~= nil, rom_nome = gameinfo.getromname(), run_rom = run_rom,
            fine_lotta = diag.fine_lotta, codice_lotta = esp_sito }
        end
        ultimo_invio = fc
        if invia(dati) then
          if not stato_rete.ignorato then          -- se il sito ha scartato i dati, li rimandiamo dopo
            if dati.squadra then ultima_firma = fs end
            if dati.box then ultima_firma_box = fb end
            if dati.eventi then coda = {} end
          end
          gestisci_rom()
        end
        if #coda > 50 then coda = { table.unpack(coda, #coda - 49) } end
      end
    elseif fc - ultimo_invio >= (APP and 60 or CFG.secondi_controllo * 60) then
      -- gioco non ancora caricato (titolo, nuova partita): solo contatto col server
      ultimo_invio = fc
      if invia({ attivo = false }) then gestisci_rom() end
    elseif APP and #coda_app > 0 and fc - ultimo_invio >= 10 then
      ultimo_invio = fc
      invia({ attivo = A.base ~= nil })
    end
  end
  disegna(fc)
  emu.frameadvance()
end
