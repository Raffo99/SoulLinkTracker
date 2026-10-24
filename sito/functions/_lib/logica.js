// =====================================================================
//  LOGICA SOUL LINK - funzioni pure sullo stato della partita
//  (nessuna dipendenza da Cloudflare: testabile con node)
// =====================================================================
import { POKEDEX, LUOGHI, ZONE, ZONE_NOMI_EN } from "./dati.js";

export const LEVEL_CAP = [13, 18, 24, 30, 33, 39, 48, 51, 58, 59];
export const NOMI_CAP = ["Cheren", "Rosy", "Artemisio", "Camelia", "Rafan", "Anisia", "Aristide",
  "Ciprian", "Superquattro", "Iris"];

// obiettivi principali: ID allenatore (Nero 2 / Bianco 2, dal NDS Ironmon Tracker)
export const OBIETTIVI = [
  { id: "rivale1", nome: "Rivale (prima lotta)", tipo: "rivale", ids: [161, 162, 163] },
  { id: "cheren", nome: "Cheren", tipo: "palestra", medaglia: 1, ids: [156] },
  { id: "rivale2", nome: "Rivale (Fattoria di Venturia)", tipo: "rivale", ids: [166, 167, 168] },
  { id: "rosy", nome: "Rosy", tipo: "palestra", medaglia: 2, ids: [157] },
  { id: "artemisio", nome: "Artemisio", tipo: "palestra", medaglia: 3, ids: [154] },
  { id: "camelia", nome: "Camelia", tipo: "palestra", medaglia: 4, ids: [153] },
  { id: "rafan", nome: "Rafan", tipo: "palestra", medaglia: 5, ids: [158] },
  { id: "anisia", nome: "Anisia", tipo: "palestra", medaglia: 6, ids: [155] },
  { id: "rivale3", nome: "Rivale (Fregata Plasma)", tipo: "rivale", ids: [368, 369, 370] },
  { id: "aristide", nome: "Aristide", tipo: "palestra", medaglia: 7, ids: [159] },
  { id: "acromio", nome: "Acromio", tipo: "plasma", ids: [344] },
  { id: "ghecis", nome: "Ghecis", tipo: "plasma", ids: [345] },
  { id: "rivale4", nome: "Rivale (Spiraria)", tipo: "rivale", ids: [378, 379, 380] },
  { id: "ciprian", nome: "Ciprian", tipo: "palestra", medaglia: 8, ids: [160] },
  { id: "rivale5", nome: "Rivale (Via Vittoria)", tipo: "rivale", ids: [684, 685, 686] },
  { id: "antea", nome: "Antea", tipo: "lega", ids: [38] },
  { id: "marzio", nome: "Marzio", tipo: "lega", ids: [39] },
  { id: "mirton", nome: "Mirton", tipo: "lega", ids: [40] },
  { id: "catlina", nome: "Catlina", tipo: "lega", ids: [41] },
  { id: "iris", nome: "Iris (Campionessa)", tipo: "campione", ids: [341] },
];
const OBIETTIVO_DA_ID = new Map(OBIETTIVI.flatMap((o) => o.ids.map((i) => [i, o])));

const info = (s) => POKEDEX[s] || { nome: `#${s}`, tipi: ["?"], famiglia: -s };
export const nomeLuogo = (k) => {
  if (k == null) return "?";
  k = String(k);
  if (k.startsWith("z")) {
    const z = k.slice(1);
    return ZONE_NOMI_EN[z] ? `${ZONE_NOMI_EN[z]} (zona ${z})` : `Zona ${z}`;
  }
  return LUOGHI[k] || `Luogo #${k}`;
};

export function nuovoStato(ora) {
  const s = { run: 1, giocatori: {}, storico: [], tid_vecchi: {}, id_msg: 0, zone_apprese: {},
    regole: { doppioni: true, shiny: true } };
  azzeraRun(s, ora);
  return s;
}

function azzeraRun(s, ora) {
  Object.assign(s, {
    stato: "in_corso", motivo: "", iniziata: ora, lega: false,
    pokemon: {}, incontri: [], eventi: [], messaggi: {}, ordine: 0, avvisi_inviati: [], obiettivi: {},
  });
  for (const g of Object.values(s.giocatori)) { g.medaglie = 0; g.box_ok = false; }
}

// ---------- utilità ----------
const vivo = (p) => p.stato === "squadra" || p.stato === "box";
const nome = (p) => p.soprannome || info(p.specie).nome;
const altro = (s, g) => Object.keys(s.giocatori).find((x) => x !== g) || null;

function evento(s, ora, testo, tipo = "info") {
  s.eventi.push({ t: ora, testo, tipo });
  if (s.eventi.length > 250) s.eventi.splice(0, s.eventi.length - 250);
}
function msg(s, g, testo) {
  s.id_msg += 1;
  (s.messaggi[g] ||= []).push({ id: s.id_msg, testo });
  if (s.messaggi[g].length > 40) s.messaggi[g].splice(0, s.messaggi[g].length - 40);
}
const msgTutti = (s, testo) => Object.keys(s.giocatori).forEach((g) => msg(s, g, testo));
function avvisoUnico(s, g, chiave, testo) {
  if (s.avvisi_inviati.includes(chiave)) return;
  s.avvisi_inviati.push(chiave);
  if (s.avvisi_inviati.length > 500) s.avvisi_inviati.splice(0, 100);
  msg(s, g, testo);
}

// luogo (chiave stringa) di un incontro: appreso dalle catture > tabella statica > zona grezza
export function luogoIncontro(s, e) {
  if (e.luogo != null) return String(e.luogo);
  if (s.zone_apprese[e.zona] != null) return String(s.zone_apprese[e.zona]);
  if (ZONE[e.zona] != null) return String(ZONE[e.zona]);
  return "z" + e.zona;
}

// primo incontro valido di un giocatore in un luogo
function primoIncontro(s, g, luogo) {
  return s.incontri.find((e) => e.g === g && !e.ignorato && e.esito !== "annullato" && luogoIncontro(s, e) === luogo) || null;
}

function catturaDi(s, g, luogo) {
  let best = null;
  for (const [k, p] of Object.entries(s.pokemon)) {
    if (p.giocatore === g && String(p.luogo) === luogo && !p.irregolare && (!best || p.ordine < s.pokemon[best].ordine)) best = k;
  }
  return best;
}

export function partner(s, chiave) {
  const p = s.pokemon[chiave];
  if (!p || p.irregolare) return null;
  const a = altro(s, p.giocatore);
  if (!a) return null;
  const luogo = String(p.luogo);
  if (fallito(s, a, luogo)) return null;
  return catturaDi(s, a, luogo);
}

function fallito(s, g, luogo) {
  const e = primoIncontro(s, g, luogo);
  return !!(e && e.esito === "fallito");
}

// ---------- morti e game over ----------
function morte(s, ora, chiave, causa, propaga = true) {
  const p = s.pokemon[chiave];
  if (!p || !vivo(p)) return;
  Object.assign(p, { stato: "morto", causa, morto: ora });
  const g = p.giocatore;
  evento(s, ora, `${g}: ${nome(p)} è morto (${causa})`, "morte");
  msg(s, g, `${nome(p)} e' morto. Riposa in pace.`);
  if (!propaga) return;
  const k = partner(s, chiave);
  if (k && vivo(s.pokemon[k])) {
    const q = s.pokemon[k];
    morte(s, ora, k, `legame con ${nome(p)} di ${g}`, false);
    s.avvisi_inviati.push(`rianimato:${k}`);
    msg(s, q.giocatore, `${nome(p)} di ${g} e' morto: muore anche il tuo ${nome(q)}! Mettilo nel box.`);
  }
}

export function gameOver(s, ora, motivo) {
  if (s.stato !== "in_corso") return;
  s.stato = "game_over";
  s.motivo = motivo;
  evento(s, ora, `GAME OVER: ${motivo}`, "gameover");
  msgTutti(s, `GAME OVER! ${motivo}`);
  const pk = Object.values(s.pokemon);
  s.storico.push({
    run: s.run, motivo, inizio: s.iniziata, fine: ora,
    medaglie: Math.max(0, ...Object.values(s.giocatori).map((g) => g.medaglie || 0)),
    catture: pk.length, morti: pk.filter((p) => p.stato === "morto").length,
  });
}

function controllaEstinzione(s, ora) {
  for (const g of Object.keys(s.giocatori)) {
    const suoi = Object.values(s.pokemon).filter((p) => p.giocatore === g && !p.irregolare);
    if (suoi.length && !suoi.some(vivo)) gameOver(s, ora, `${g} non ha piu' Pokemon vivi`);
  }
}

export function nuovaRun(s, ora) {
  if (s.stato === "in_corso") gameOver(s, ora, "run abbandonata");
  for (const p of Object.values(s.pokemon)) {
    if (p.tid == null) continue;
    const l = (s.tid_vecchi[p.giocatore] ||= []);
    if (!l.includes(p.tid)) l.push(p.tid);
  }
  s.run += 1;
  azzeraRun(s, ora);
  evento(s, ora, `Inizia la run #${s.run}! Le nuove ROM vengono generate in automatico.`);
  msgTutti(s, `Run #${s.run}: genero la nuova ROM randomizzata...`);
}

// ---------- obiettivi ----------
function completaObiettivo(s, ora, g, o, come) {
  s.obiettivi ||= {};
  const mio = (s.obiettivi[g] ||= {});
  if (mio[o.id]) return;
  mio[o.id] = { t: ora, come };
  evento(s, ora, `${g} ha battuto ${o.nome}!`, "obiettivo");
  msgTutti(s, `${g} ha battuto ${o.nome}!`);
  // Superquattro battuti: level cap di Iris
  if (o.tipo === "lega" && OBIETTIVI.filter((x) => x.tipo === "lega").every((x) => mio[x.id])) {
    msg(s, g, `Superquattro battuti! Level cap: ${LEVEL_CAP[9]}`);
  }
  // campionessa battuta da tutti e due: run vinta
  if (o.tipo === "campione") {
    const G = Object.keys(s.giocatori);
    if (G.length && G.every((x) => s.obiettivi[x] && s.obiettivi[x].iris) && s.stato === "in_corso") {
      s.stato = "vinta";
      s.motivo = "Tutti e due avete battuto Iris!";
      evento(s, ora, "RUN VINTA! Tutti e due avete battuto Iris!", "obiettivo");
      msgTutti(s, "RUN VINTA! Complimenti!");
      const pk = Object.values(s.pokemon);
      s.storico.push({ run: s.run, motivo: "VINTA", inizio: s.iniziata, fine: ora, medaglie: 8,
        catture: pk.length, morti: pk.filter((p) => p.stato === "morto").length, vinta: true });
    } else {
      msg(s, g, "Hai battuto la Campionessa! Aspetta che ce la faccia anche l'altro.");
    }
  }
}

// ---------- catture ----------
function nuovaCattura(s, ora, g, chiave, m) {
  s.ordine += 1;
  const luogo = String(m.luogo);
  const p = {
    giocatore: g, pid: m.pid, specie: m.specie, soprannome: m.soprannome || "", luogo: m.luogo,
    livello: m.livello || 0, ps: m.ps ?? null, ps_max: m.ps_max ?? null, stato: m.box ? "box" : "squadra",
    ordine: s.ordine, catturato: ora, irregolare: false, causa: "", tid: m.id_allenatore ?? null, slot: m.slot || 0,
  };
  const prima = catturaDi(s, g, luogo);
  s.pokemon[chiave] = p;
  const sp = info(m.specie).nome;
  const descr = p.soprannome && p.soprannome !== sp ? `${p.soprannome} (${sp})` : sp;
  const pi = primoIncontro(s, g, luogo);
  if (pi && pi.esito === "fallito") {
    p.irregolare = true;
    evento(s, ora, `${g} ha catturato ${descr} a ${nomeLuogo(luogo)}, ma lì il primo incontro era fallito!`, "allarme");
    msg(s, g, `Regola: a ${nomeLuogo(luogo)} il primo incontro era fallito. ${nome(p)} non vale: liberalo.`);
  } else if (prima) {
    p.irregolare = true;
    evento(s, ora, `${g} ha un secondo Pokémon da ${nomeLuogo(luogo)}: ${descr} (fuori regola)`, "allarme");
    msg(s, g, `Regola: hai gia' una cattura a ${nomeLuogo(luogo)}. ${nome(p)} non vale.`);
  } else {
    evento(s, ora, `${g} ha catturato ${descr} a ${nomeLuogo(luogo)}`, "cattura");
    const a = altro(s, g);
    const kq = a ? catturaDi(s, a, luogo) : null;
    if (kq && !fallito(s, a, luogo)) {
      const q = s.pokemon[kq];
      msgTutti(s, `Nuovo legame a ${nomeLuogo(luogo)}: ${nome(p)} <-> ${nome(q)}`);
      evento(s, ora, `Legame creato: ${nome(p)} (${g}) ↔ ${nome(q)} (${a})`, "legame");
      if (!vivo(q)) morte(s, ora, chiave, `il partner ${nome(q)} era gia' morto`, false);
    } else if (a && fallito(s, a, luogo)) {
      msg(s, g, `${a} ha fallito l'incontro a ${nomeLuogo(luogo)}: ${nome(p)} va nel box o liberato.`);
    }
  }
  return p;
}

function aggiornaPokemon(s, ora, g, m, inSquadra) {
  const chiave = `${g}:${m.pid}`;
  let p = s.pokemon[chiave];
  if (!p) p = nuovaCattura(s, ora, g, chiave, m);
  if (p.specie !== m.specie && p.specie) {
    evento(s, ora, `${g}: ${nome(p)} si è evoluto in ${info(m.specie).nome}!`);
  }
  p.specie = m.specie;
  if (m.soprannome) p.soprannome = m.soprannome;
  if (inSquadra) {
    Object.assign(p, { livello: m.livello, ps: m.ps, ps_max: m.ps_max, slot: m.slot || 0 });
    if (p.stato === "box" || p.stato === "liberato") p.stato = "squadra";
  } else if (p.stato === "squadra" || p.stato === "liberato") {
    p.stato = "box";
  }
  return chiave;
}

// ---------- aggiornamento dallo script Lua ----------
//  d = { giocatore, run_rom, squadra:[...]|null, box:[...]|null, box_ok, eventi:[...], medaglie, zona, diagnostica }
export function aggiornaDaGioco(s, ora, d) {
  const g = String(d.giocatore || "").slice(0, 24);
  if (!g) return { errore: "manca il nome del giocatore" };
  if (!s.giocatori[g]) {
    if (Object.keys(s.giocatori).length >= 2) return { errore: "Ci sono gia' due giocatori in questa partita." };
    s.giocatori[g] = { entrato: ora, medaglie: 0 };
    evento(s, ora, `${g} si è unito alla partita`);
  }
  const G = s.giocatori[g];
  const prima = G.visto || 0;
  G.visto = ora;
  G.emulatore = !!d.attivo;
  if (d.diagnostica) G.diagnostica = d.diagnostica;
  if (d.zona != null) G.zona = d.zona;
  let cambiato = ora - prima > 30 || !!d.diagnostica;

  // dati di una ROM/salvataggio della run precedente: ignorati
  const runOk = d.run_rom == null || Number(d.run_rom) === s.run;
  if ((G.run_rom ?? null) !== (d.run_rom ?? null)) cambiato = true;
  G.run_rom = d.run_rom ?? null;
  if (!runOk) {
    const motivo = Number(d.run_rom) === -1
      ? "la ROM caricata non e' una ROM del Soul Link"
      : `la ROM caricata e' della run ${d.run_rom}, la run attuale e' la ${s.run}`;
    return { cambiato, ignorato: motivo };
  }
  const vecchi = new Set(d.run_rom == null ? (s.tid_vecchi[g] || []) : []);
  const valido = (m) => !m.uovo && !vecchi.has(m.id_allenatore);

  if (Array.isArray(d.squadra) || Array.isArray(d.eventi)) cambiato = true;
  if (typeof d.medaglie === "number" && d.medaglie !== G.medaglie) {
    if (d.medaglie > (G.medaglie || 0)) {
      evento(s, ora, `${g} ha ottenuto la medaglia n. ${d.medaglie}!`, "cattura");
      const cap = LEVEL_CAP[Math.min(d.medaglie, 8)];
      msg(s, g, `Medaglia ${d.medaglie}! Nuovo level cap: ${cap}`);
    }
    G.medaglie = d.medaglie;
    if (s.stato === "in_corso") {
      for (const o of OBIETTIVI) if (o.medaglia && o.medaglia <= d.medaglie) completaObiettivo(s, ora, g, o, "medaglia");
    }
  }

  // 1) squadra e box
  if (Array.isArray(d.squadra)) {
    const squadra = d.squadra.filter(valido);
    const visti = new Set();
    for (const m of squadra) visti.add(aggiornaPokemon(s, ora, g, m, true));
    if (Array.isArray(d.box) && d.box_ok) {
      G.box_ok = true;
      const pidSquadra = new Set(squadra.map((m) => m.pid));
      for (const m of d.box.filter(valido)) {
        if (!pidSquadra.has(m.pid)) visti.add(aggiornaPokemon(s, ora, g, { ...m, box: true }, false));
      }
    }
    const boxCompleto = Array.isArray(d.box) && d.box_ok;   // abbiamo letto tutto il PC
    for (const [k, p] of Object.entries(s.pokemon)) {
      if (p.giocatore !== g || visti.has(k)) continue;
      if (p.stato === "squadra") p.stato = boxCompleto ? "liberato" : "box";
      else if (p.stato === "box" && boxCompleto) p.stato = "liberato";
    }
    if (s.stato === "in_corso") {
      for (const m of squadra) {
        const k = `${g}:${m.pid}`, p = s.pokemon[k];
        if (m.ps === 0 && vivo(p)) morte(s, ora, k, "KO in lotta");
        else if (m.ps > 0 && !vivo(p) && p.stato !== "liberato") {
          avvisoUnico(s, g, `rianimato:${k}`, `ATTENZIONE: ${nome(p)} e' morto, non puo' stare in squadra! Mettilo nel box.`);
        }
      }
      if (squadra.length && squadra.every((m) => m.ps === 0)) gameOver(s, ora, `${g} è stato sconfitto: tutta la squadra è KO`);
      controllaEstinzione(s, ora);
    }
  }

  // 2) incontri selvatici
  for (const e of d.eventi || []) {
    if (e.tipo === "incontro") registraIncontro(s, ora, g, e);
    else if (e.tipo === "esito") esitoIncontro(s, ora, g, e);
    else if (e.tipo === "fine_allenatore" && e.vinta && s.stato === "in_corso") {
      const o = OBIETTIVO_DA_ID.get(Number(e.allenatore));
      if (o) completaObiettivo(s, ora, g, o, "lotta");
    }
  }

  // 3) legami: partner nel box
  for (const [k, p] of Object.entries(s.pokemon)) {
    if (p.giocatore !== g || p.stato !== "squadra") continue;
    const kp = partner(s, k);
    if (kp && s.pokemon[kp].stato === "box") {
      const q = s.pokemon[kp];
      avvisoUnico(s, g, `box:${k}:${Math.floor(ora / 300)}`, `${nome(q)} di ${q.giocatore} e' nel box: metti nel box anche ${nome(p)}.`);
    }
  }
  return { cambiato: true };
}

function famiglieCatturate(s, g) {
  return new Set(Object.values(s.pokemon).filter((p) => p.giocatore === g && !p.irregolare).map((p) => info(p.specie).famiglia));
}

function registraIncontro(s, ora, g, e) {
  if (s.incontri.some((x) => x.g === g && x.pid === e.pid && x.zona === e.zona)) return; // doppione dello stesso evento
  const inc = { id: s.incontri.length + 1, g, zona: e.zona, specie: e.specie, livello: e.livello, pid: e.pid,
    shiny: !!e.shiny, esito: "in_corso", t: ora, fonte: "auto", ignorato: null };
  const luogo = luogoIncontro(s, inc);
  const giaPrimo = primoIncontro(s, g, luogo);
  const sp = info(e.specie).nome;
  if (!giaPrimo) {
    if (catturaDi(s, g, luogo)) inc.ignorato = "luogo_usato";      // hai gia' un Pokemon da qui (regalo, uovo...)
    else if (s.regole.shiny && inc.shiny) inc.ignorato = "shiny";
    else if (s.regole.doppioni && famiglieCatturate(s, g).has(info(e.specie).famiglia)) inc.ignorato = "doppione";
  }
  s.incontri.push(inc);
  if (s.incontri.length > 600) s.incontri.splice(0, s.incontri.length - 600);
  if (inc.ignorato === "shiny") {
    msg(s, g, `SHINY! ${sp} non conta come incontro: puoi catturarlo!`);
    evento(s, ora, `${g}: ${sp} SHINY a ${nomeLuogo(luogo)}!`, "legame");
  } else if (inc.ignorato === "luogo_usato") {
    avvisoUnico(s, g, `usato:${g}:${luogo}`, `${nomeLuogo(luogo)}: hai gia' una cattura qui, non catturare.`);
  } else if (inc.ignorato === "doppione") {
    msg(s, g, `${sp}: hai gia' questa famiglia, non conta (clausola doppioni).`);
  } else if (!giaPrimo) {
    msg(s, g, `Primo incontro a ${nomeLuogo(luogo)}: ${sp} Lv.${e.livello}. Catturalo!`);
    evento(s, ora, `${g}: primo incontro a ${nomeLuogo(luogo)} → ${sp} Lv.${e.livello}`, "incontro");
  } else {
    avvisoUnico(s, g, `usato:${g}:${luogo}`, `${nomeLuogo(luogo)}: incontro gia' usato, non catturare.`);
  }
}

function esitoIncontro(s, ora, g, e) {
  const inc = [...s.incontri].reverse().find((x) => x.g === g && x.pid === e.pid && x.esito === "in_corso");
  if (!inc) return;
  inc.esito = e.esito === "catturato" ? "catturato" : e.esito === "incerto" ? "incerto" : "fallito";
  let luogo = luogoIncontro(s, inc);
  // impara la zona dalla cattura: il luogo vero e' quello salvato nel Pokemon
  if (inc.esito === "catturato" && inc.zona != null) {
    const p = s.pokemon[`${g}:${inc.pid}`];
    if (p && p.luogo != null) s.zone_apprese[inc.zona] = p.luogo;
  }
  luogo = luogoIncontro(s, inc);
  const primo = primoIncontro(s, g, luogo);
  if (primo !== inc) return;
  const sp = info(inc.specie).nome;
  if (inc.esito === "fallito") {
    evento(s, ora, `${g}: incontro fallito a ${nomeLuogo(luogo)} (${sp})`, "allarme");
    msg(s, g, `Incontro fallito a ${nomeLuogo(luogo)}.`);
    const a = altro(s, g);
    const kq = a ? catturaDi(s, a, luogo) : null;
    if (kq) {
      const q = s.pokemon[kq];
      msg(s, a, `${g} ha fallito a ${nomeLuogo(luogo)}: il tuo ${nome(q)} va nel box o liberato.`);
    }
  } else if (inc.esito === "incerto") {
    evento(s, ora, `${g}: non so se ${sp} a ${nomeLuogo(luogo)} è stato catturato. Conferma sulla dashboard.`, "allarme");
  }
}

// ---------- azioni dalla dashboard ----------
export function azione(s, ora, d) {
  const a = d.azione;
  if (a === "esito_incontro") {
    const inc = s.incontri.find((x) => x.id === Number(d.id));
    if (!inc) return { errore: "incontro non trovato" };
    if (d.esito === "annullato") { inc.esito = "annullato"; evento(s, ora, `${inc.g}: incontro a ${nomeLuogo(luogoIncontro(s, inc))} annullato`); }
    else { inc.esito = "in_corso"; esitoIncontro(s, ora, inc.g, { pid: inc.pid, esito: d.esito }); }
  } else if (a === "fallito") {
    // incontro fallito segnato a mano (es. lo script era spento)
    const luogo = String(d.luogo);
    s.incontri.push({ id: s.incontri.length + 1, g: d.giocatore, zona: null, luogo, specie: 0, livello: 0, pid: -s.incontri.length - 1,
      shiny: false, esito: "in_corso", t: ora, fonte: "manuale", ignorato: null });
    esitoIncontro(s, ora, d.giocatore, { pid: -s.incontri.length, esito: "fallito" });
  } else if (a === "regole") {
    s.regole = { ...s.regole, ...d.regole };
  } else if (a === "obiettivo") {
    const o = OBIETTIVI.find((x) => x.id === d.id);
    if (!o) return { errore: "obiettivo sconosciuto" };
    if (d.valore) completaObiettivo(s, ora, d.giocatore, o, "a mano");
    else if (s.obiettivi?.[d.giocatore]) delete s.obiettivi[d.giocatore][o.id];
  } else if (a === "lega") {
    s.lega = !!d.valore;
  } else if (a === "stato_pokemon") {
    const p = s.pokemon[d.chiave];
    if (!p) return { errore: "pokemon non trovato" };
    if (d.stato === "morto") { morte(s, ora, d.chiave, "segnato a mano", d.propaga !== false); controllaEstinzione(s, ora); }
    else if (["squadra", "box", "liberato"].includes(d.stato)) {
      Object.assign(p, { stato: d.stato, causa: "" });
      evento(s, ora, `${p.giocatore}: ${nome(p)} segnato come '${d.stato}'`);
    } else if (d.stato === "valido") { p.irregolare = false; }
  } else if (a === "game_over") {
    gameOver(s, ora, d.motivo || "game over dichiarato a mano");
  } else if (a === "nuova_run") {
    nuovaRun(s, ora);
  } else if (a === "rimuovi_giocatore") {
    delete s.giocatori[d.giocatore];
  } else return { errore: "azione sconosciuta" };
  return { ok: true };
}

// ---------- vista per la dashboard ----------
export function capDi(s, g) {
  const G = s.giocatori[g] || {};
  const mio = (s.obiettivi || {})[g] || {};
  const lega = s.lega || OBIETTIVI.filter((x) => x.tipo === "lega").every((x) => mio[x.id]);
  return LEVEL_CAP[lega ? 9 : Math.min(G.medaglie || 0, 8)];
}

export function vista(s, ora) {
  const G = Object.keys(s.giocatori);
  const pk = {};
  for (const [k, p] of Object.entries(s.pokemon)) {
    const i = info(p.specie);
    pk[k] = { ...p, chiave: k, nome_specie: i.nome, tipi: i.tipi, luogo_nome: nomeLuogo(p.luogo), partner: partner(s, k) };
  }
  // tutti i luoghi toccati da catture o incontri
  const luoghi = new Map();
  const tocca = (l, t) => { if (!luoghi.has(l) || luoghi.get(l) > t) luoghi.set(l, t); };
  for (const p of Object.values(s.pokemon)) tocca(String(p.luogo), p.catturato);
  for (const e of s.incontri) if (e.esito !== "annullato") tocca(luogoIncontro(s, e), e.t);
  const percorsi = [...luoghi.entries()].sort((a, b) => a[1] - b[1]).map(([l]) => {
    const r = { luogo: l, luogo_nome: nomeLuogo(l), giocatori: {} };
    for (const g of G) {
      const e = primoIncontro(s, g, l);
      const kc = catturaDi(s, g, l);
      r.giocatori[g] = { incontro: e ? { ...e, nome_specie: e.specie ? info(e.specie).nome : "—" } : null, cattura: kc ? pk[kc] : null };
    }
    const membri = G.map((g) => r.giocatori[g]);
    if (membri.some((m) => m.incontro && m.incontro.esito === "fallito")) r.stato = "rotta";
    else if (membri.some((m) => m.cattura && !vivo(m.cattura))) r.stato = "morta";
    else if (G.length === 2 && membri.every((m) => m.cattura)) r.stato = "attiva";
    else if (membri.some((m) => m.incontro && m.incontro.esito === "in_corso")) r.stato = "in_lotta";
    else r.stato = "in_attesa";
    return r;
  });

  const avvisi = [];
  const perTipo = {};
  for (const p of Object.values(pk)) {
    if (p.stato !== "squadra" || p.irregolare) continue;
    const cap = capDi(s, p.giocatore);
    if (p.livello > cap) avvisi.push(`${p.giocatore}: ${nome(p)} è al livello ${p.livello}, sopra il cap ${cap}`);
    (perTipo[p.tipi[0]] ||= new Set()).add(String(p.luogo));
    if (p.partner && pk[p.partner].stato === "box") avvisi.push(`${p.giocatore}: ${nome(p)} è in squadra ma il partner è nel box`);
  }
  for (const [t, l] of Object.entries(perTipo)) if (l.size > 1) avvisi.push(`Tipo primario ${t} ripetuto in squadra: ${[...l].map(nomeLuogo).join(", ")}`);
  for (const p of Object.values(pk)) if (p.stato === "squadra" && p.irregolare) avvisi.push(`${p.giocatore}: ${nome(p)} è una cattura fuori regola`);
  for (const p of Object.values(pk)) {
    if (p.stato !== "squadra" || p.irregolare) continue;
    const a = altro(s, p.giocatore);
    if (a && fallito(s, a, String(p.luogo))) avvisi.push(`${p.giocatore}: ${nome(p)} va nel box, ${a} ha fallito l'incontro a ${nomeLuogo(p.luogo)}`);
  }
  for (const g of G) {
    const x = s.giocatori[g];
    if (x.run_rom != null && Number(x.run_rom) !== s.run && ora - (x.visto || 0) < 60) {
      avvisi.push(`${g}: i suoi dati vengono ignorati, ${Number(x.run_rom) === -1 ? "la ROM caricata non è una ROM del Soul Link" : "la ROM è della run " + x.run_rom}`);
    }
  }
  for (const e of s.incontri) if (e.esito === "incerto") avvisi.push(`${e.g}: conferma se ${info(e.specie).nome} (${nomeLuogo(luogoIncontro(s, e))}) è stato catturato`);

  return {
    run: s.run, stato: s.stato, motivo: s.motivo, iniziata: s.iniziata, lega: s.lega, regole: s.regole,
    level_cap: LEVEL_CAP, nomi_cap: NOMI_CAP,
    giocatori: Object.fromEntries(G.map((g) => [g, { ...s.giocatori[g], online: ora - (s.giocatori[g].visto || 0) < 45,
      cap: capDi(s, g), zona_nome: s.giocatori[g].zona != null ? nomeLuogo(luogoIncontro(s, { zona: s.giocatori[g].zona })) : null }])),
    pokemon: pk, percorsi, avvisi,
    incontri: s.incontri.slice(-80).reverse().map((e) => ({ ...e, nome_specie: e.specie ? info(e.specie).nome : "—", luogo_nome: nomeLuogo(luogoIncontro(s, e)) })),
    eventi: s.eventi.slice(-80).reverse(), storico: s.storico, luoghi: LUOGHI,
    obiettivi: OBIETTIVI.map(({ id, nome, tipo, medaglia }) => ({ id, nome, tipo, medaglia })), fatti: s.obiettivi || {},
  };
}

export function messaggiDa(s, g, dopo) {
  return (s.messaggi[g] || []).filter((m) => m.id > dopo);
}
