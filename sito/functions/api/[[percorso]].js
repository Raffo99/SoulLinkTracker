// =====================================================================
//  API del Soul Link Tracker - Cloudflare Pages Functions + D1
//
//  GET  /api/stato    -> stato completo per la dashboard (sola lettura)
//  POST /api/gioco    -> aggiornamento dallo script Lua di BizHawk (risposta in testo semplice)
//  POST /api/azione   -> azioni dalla dashboard
//
//  Binding richiesti: D1 "DB". Variabile/segreto: CODICE (parola segreta condivisa).
// =====================================================================
import { nuovoStato, aggiornaDaGioco, azione, vista, messaggiDa } from "../_lib/logica.js";

let tabellaPronta = false;

async function preparaTabella(db) {
  if (tabellaPronta) return;
  await db.prepare(
    "CREATE TABLE IF NOT EXISTS partita (id TEXT PRIMARY KEY, stato TEXT NOT NULL, versione INTEGER NOT NULL, aggiornato INTEGER NOT NULL)"
  ).run();
  tabellaPronta = true;
}

async function carica(db, id, ora) {
  const r = await db.prepare("SELECT stato, versione FROM partita WHERE id = ?").bind(id).first();
  if (r) return { s: JSON.parse(r.stato), versione: r.versione };
  const s = nuovoStato(ora);
  await db.prepare("INSERT OR IGNORE INTO partita (id, stato, versione, aggiornato) VALUES (?, ?, 0, ?)")
    .bind(id, JSON.stringify(s), ora).run();
  const r2 = await db.prepare("SELECT stato, versione FROM partita WHERE id = ?").bind(id).first();
  return { s: JSON.parse(r2.stato), versione: r2.versione };
}

// legge, modifica, scrive solo se nessun altro ha scritto nel frattempo (altrimenti riprova)
async function modifica(db, id, fn) {
  for (let tentativo = 0; tentativo < 6; tentativo++) {
    const ora = Date.now() / 1000;
    const { s, versione } = await carica(db, id, ora);
    const esito = fn(s, ora);
    if (!esito || !esito.salva) return { s, esito };
    const r = await db.prepare("UPDATE partita SET stato = ?, versione = versione + 1, aggiornato = ? WHERE id = ? AND versione = ?")
      .bind(JSON.stringify(s), Math.floor(ora), id, versione).run();
    if (r.meta && r.meta.changes === 1) return { s, esito };
    await new Promise((res) => setTimeout(res, 30 + Math.random() * 80));
  }
  throw new Error("troppi aggiornamenti contemporanei, riprova");
}

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
});
const testo = (t, status = 200) => new Response(t, {
  status, headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
});

async function leggiCorpo(request) {
  const tipo = request.headers.get("Content-Type") || "";
  if (tipo.includes("application/x-www-form-urlencoded") || tipo.includes("multipart/form-data")) {
    const f = await request.formData();           // BizHawk manda payload=<json>
    return JSON.parse(f.get("payload") || "{}");
  }
  const t = await request.text();
  return JSON.parse(t || "{}");
}

export async function onRequest(context) {
  const { request, env, params } = context;
  const percorso = (params.percorso || []).join("/");
  const db = env.DB;
  if (!db) return json({ errore: "Database D1 non collegato: aggiungi il binding DB nelle impostazioni del progetto Pages." }, 500);
  const idPartita = env.PARTITA_ID || "principale";
  const codice = env.CODICE || "cambiami";

  try {
    await preparaTabella(db);

    if (request.method === "GET" && percorso === "stato") {
      const ora = Date.now() / 1000;
      const { s } = await carica(db, idPartita, ora);
      return json(vista(s, ora));
    }

    if (request.method !== "POST") return json({ errore: "metodo non permesso" }, 405);
    let d;
    try { d = await leggiCorpo(request); } catch { return json({ errore: "richiesta non valida" }, 400); }
    if (d.codice !== codice) {
      return percorso === "gioco" ? testo("ERR codice sbagliato (controlla config.lua)\n") : json({ errore: "codice sbagliato" }, 403);
    }

    if (percorso === "gioco") {
      const { s, esito } = await modifica(db, idPartita, (s, ora) => {
        const r = aggiornaDaGioco(s, ora, d);
        return { ...r, salva: !!r.cambiato && !r.errore };
      });
      if (esito.errore) return testo(`ERR ${esito.errore}\n`);
      const righe = [`RUN ${s.run} ${s.stato}`];
      if (esito.ignorato) righe.push(`IGNORATO ${esito.ignorato}`);
      if (Number(d.ultimo_msg) === -1) {
        righe.push(`ULTIMO ${s.id_msg}`);          // script appena avviato: non ripetere i vecchi messaggi
      } else {
        for (const m of messaggiDa(s, String(d.giocatore), Number(d.ultimo_msg) || 0)) {
          righe.push(`MSG ${m.id} ${m.testo.replace(/[\r\n]+/g, " ")}`);
        }
      }
      return testo(righe.join("\n") + "\n");
    }

    if (percorso === "azione") {
      const { esito } = await modifica(db, idPartita, (s, ora) => {
        const r = azione(s, ora, d);
        return { ...r, salva: !r.errore };
      });
      return json(esito.errore ? { errore: esito.errore } : { ok: true });
    }

    return json({ errore: "non trovato" }, 404);
  } catch (e) {
    return percorso === "gioco" ? testo(`ERR ${e.message}\n`, 500) : json({ errore: e.message }, 500);
  }
}
