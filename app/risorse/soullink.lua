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
  box = 0x19724 - 0x18E04 + 0x400,   -- il PC in RAM ha la stessa disposizione del salvataggio
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
               uovo = ((b("B", 0x12) >> 14) & 1) == 1, id_allenatore = b("A", 4), id_segreto = b("A", 6) }
  if con_lotta then
    local bat, s2 = {}, pid
    for off = 0x88, 0x92, 2 do s2 = prng(s2); bat[off] = r16(addr + off) ~ (s2 >> 16) end
    pk.livello, pk.ps, pk.ps_max = bat[0x8C] & 0xFF, bat[0x8E], bat[0x90]
    if pk.livello < 1 or pk.livello > 100 or pk.ps_max == 0 or pk.ps > pk.ps_max then return nil end
  end
  return pk
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
local salva_calibrazione                     -- definita piu' avanti
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
local coda_app = {}             -- risposte ai comandi dell'app (backup fatto, stato caricato)
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
    elseif cmd == "ERR" then
      stato_rete.errore = resto; avvisa("Server: " .. resto, 10)
    end
  end
  return true
end

-- ---------------- stato del gioco ----------------
local coda = {}                 -- eventi da spedire (incontri, esiti)
local lotta = { attiva = false }
local controllo_cattura = nil   -- {pid, fino_a, era_piena}
local ultima_firma, ultima_firma_box = nil, nil
local ultimo_invio, ultimo_controllo_box = -99999, -99999
local squadra, box, box_ok = nil, nil, false
local diag = {}
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
    end
    f:close()
  end
end
salva_calibrazione = function()
  local f = io.open(FILE_CAL, "w")
  if not f then return end
  if box_ancora then f:write("box_delta=" .. box_ancora.delta .. "\n") end
  if cal_lotta.addr then f:write("lotta=" .. cal_lotta.addr .. "\n") end
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
local function fine_lotta()
  if lotta.allenatore and not lotta.chiusa then
    lotta.chiusa = true
    coda[#coda + 1] = { tipo = "fine_allenatore", allenatore = lotta.allenatore, vinta = squadra_viva() }
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
    if all ~= 0 then lotta.allenatore = all end
    if all == 0 then
      local n = lotta.nemico
      local tid, sid = 0, 0
      if squadra and squadra[1] then tid, sid = squadra[1].id_allenatore, squadra[1].id_segreto end
      local shiny = (tid ~ sid ~ (n.pid >> 16) ~ (n.pid & 0xFFFF)) < 8
      coda[#coda + 1] = { tipo = "incontro", pid = n.pid, specie = n.specie, livello = n.livello, shiny = shiny, zona = zona }
      controllo_cattura = { pid = n.pid, inizio = fc, era_piena = squadra and #squadra >= 6, prossimo_box = fc }
    end
  end

  -- fine lotta: con l'indicatore calibrato lo sappiamo subito, altrimenti col cambio di zona
  if lotta.attiva and lotta.letto then
    if flag == false or cambio_zona then lotta.attiva = false; lotta.finita = fc end
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
  if not cal_lotta.addr and fc - (lotta.vivo or lotta.inizio) > 60 * 90 then return { lotta = false } end
  local a = { lotta = true, specie = lotta.nemico.specie, livello = lotta.nemico.livello, ps = lotta.ps, ps_max = lotta.ps_max }
  if lotta.letto then a.allenatore = lotta.allenatore or 0 end
  return a
end
local function firma_attivita(a)
  if not a.lotta then return "-" end
  return tostring(a.specie) .. ":" .. tostring(a.allenatore) .. ":" .. tostring(a.ps)
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

while true do
  local fc = emu.framecount()
  do
    local ok, tasti = pcall(joypad.get)
    if ok and type(tasti) == "table" then
      for _, v in pairs(tasti) do if v == true then ultimo_input = fc; break end end
    end
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
      local da_mandare = (#coda > 0) or (squadra and fs ~= ultima_firma) or (fb and fb ~= ultima_firma_box)
                         or (APP and fa ~= ultima_attivita) or #coda_app > 0
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
        if squadra and fs ~= ultima_firma then dati.squadra = squadra end
        if fb and fb ~= ultima_firma_box then dati.squadra = squadra; dati.box = box; dati.box_ok = true end
        if #coda > 0 then dati.eventi = coda end
        if CFG.diagnostica then
          dati.diagnostica = { rom = CODICE_ROM, fonte = A.fonte, base = A.base, zona = diag.zona, zona_padre = diag.zona_padre,
            stato_lotta = diag.stato_lotta, in_lotta = lotta.attiva == true, lotta_calibrata = cal_lotta.addr,
            lotta_candidati = n_candidati(), lotte_viste = cal_lotta.lotte, ultimo_nemico = diag.nemico, ultimo_allenatore = diag.allenatore,
            medaglie = diag.medaglie, squadra = squadra and #squadra or 0, pc = box_ok and #box or -1,
            pc_calibrato = box_ancora ~= nil, rom_nome = gameinfo.getromname(), run_rom = run_rom }
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
