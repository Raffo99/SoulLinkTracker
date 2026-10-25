"""LOGICA SOUL LINK - funzioni pure sullo stato della partita.

Traduzione fedele della versione JavaScript (verificata confrontando le due su scenari casuali).
Lo stato è un dizionario serializzabile in JSON: le chiavi dei dizionari sono sempre stringhe.
"""
import json
import math
import sys
from pathlib import Path

_base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
_DATI = json.loads((_base / "risorse" / "dati.json").read_text("utf-8"))
POKEDEX, LUOGHI, ZONE, ZONE_NOMI_EN = _DATI["pokedex"], _DATI["luoghi"], _DATI["zone"], _DATI["zone_nomi_en"]

MAX_GIOCATORI = 4
LEVEL_CAP = [13, 18, 24, 30, 33, 39, 48, 51, 58, 59]
NOMI_CAP = ["Cheren", "Rosy", "Artemisio", "Camelia", "Rafan", "Anisia", "Aristide", "Ciprian", "Superquattro", "Iris"]

# obiettivi principali: ID allenatore (Nero 2 / Bianco 2, dal NDS Ironmon Tracker); "asso" = livello del Pokemon più forte
OBIETTIVI = [
    {"id": "rivale1", "nome": "Rivale (prima lotta)", "tipo": "rivale", "ids": [161, 162, 163]},
    {"id": "cheren", "nome": "Cheren", "tipo": "palestra", "medaglia": 1, "ids": [156]},
    {"id": "rivale2", "nome": "Rivale (Fattoria di Venturia)", "tipo": "rivale", "ids": [166, 167, 168]},
    {"id": "rosy", "nome": "Rosy", "tipo": "palestra", "medaglia": 2, "ids": [157]},
    {"id": "artemisio", "nome": "Artemisio", "tipo": "palestra", "medaglia": 3, "ids": [154]},
    {"id": "camelia", "nome": "Camelia", "tipo": "palestra", "medaglia": 4, "ids": [153]},
    {"id": "rafan", "nome": "Rafan", "tipo": "palestra", "medaglia": 5, "ids": [158]},
    {"id": "anisia", "nome": "Anisia", "tipo": "palestra", "medaglia": 6, "ids": [155]},
    {"id": "rivale3", "nome": "Rivale (Fregata Plasma)", "tipo": "rivale", "ids": [368, 369, 370]},
    {"id": "aristide", "nome": "Aristide", "tipo": "palestra", "medaglia": 7, "ids": [159]},
    {"id": "acromio", "nome": "Acromio", "tipo": "plasma", "ids": [344]},
    {"id": "ghecis", "nome": "Ghecis", "tipo": "plasma", "ids": [345]},
    {"id": "rivale4", "nome": "Rivale (Spiraria)", "tipo": "rivale", "ids": [378, 379, 380]},
    {"id": "ciprian", "nome": "Ciprian", "tipo": "palestra", "medaglia": 8, "ids": [160]},
    {"id": "rivale5", "nome": "Rivale (Via Vittoria)", "tipo": "rivale", "ids": [684, 685, 686]},
    {"id": "antea", "nome": "Antea", "tipo": "lega", "ids": [38]},
    {"id": "marzio", "nome": "Marzio", "tipo": "lega", "ids": [39]},
    {"id": "mirton", "nome": "Mirton", "tipo": "lega", "ids": [40]},
    {"id": "catlina", "nome": "Catlina", "tipo": "lega", "ids": [41]},
    {"id": "iris", "nome": "Iris (Campionessa)", "tipo": "campione", "ids": [341]},
]
OBIETTIVO_DA_ID = {i: o for o in OBIETTIVI for i in o["ids"]}

# ---- novita' (tappe, sfide, traguardi). EXTRA = False riporta alle sole regole di base (usato nei test di confronto)
EXTRA = True

# piccole sfide automatiche dentro le tappe
SFIDE = [
    {"id": "cattura2", "nome": "Cattura il primo selvatico", "tipo": "sfida"},
    {"id": "squadra4", "nome": "Squadra di 4 Pokémon", "tipo": "sfida"},
    {"id": "evoluzione", "nome": "Fai evolvere un Pokémon", "tipo": "sfida"},
    {"id": "squadra6", "nome": "Squadra al completo (6)", "tipo": "sfida"},
]
TAPPE = [
    {"id": "t1", "nome": "Si parte!", "luogo": "Alisopoli", "voci": ["rivale1", "cattura2", "cheren"]},
    {"id": "t2", "nome": "Verso Zondopoli", "luogo": "Zondopoli", "voci": ["rivale2", "rosy"]},
    {"id": "t3", "nome": "La grande città", "luogo": "Austropoli", "voci": ["squadra4", "artemisio"]},
    {"id": "t4", "nome": "Luci di Sciroccopoli", "luogo": "Sciroccopoli", "voci": ["evoluzione", "camelia"]},
    {"id": "t5", "nome": "Il porto", "luogo": "Libecciopoli", "voci": ["squadra6", "rafan"]},
    {"id": "t6", "nome": "In volo", "luogo": "Ponentopoli", "voci": ["anisia", "rivale3"]},
    {"id": "t7", "nome": "Contro il Team Plasma", "luogo": "Boreduopoli", "voci": ["aristide", "acromio", "ghecis"]},
    {"id": "t8", "nome": "Verso il mare", "luogo": "Grecalopoli", "voci": ["rivale4", "ciprian"]},
    {"id": "t9", "nome": "La Lega Pokémon", "luogo": "Lega Pokémon", "voci": ["rivale5", "antea", "marzio", "mirton", "catlina", "iris"]},
]
TRAGUARDI = [
    {"id": "primo_legame", "nome": "Primo legame", "desc": "Forma il primo legame con un compagno"},
    {"id": "collezionista", "nome": "Collezionista", "desc": "10 catture valide"},
    {"id": "esploratore", "nome": "Esploratore", "desc": "Primo incontro in 12 luoghi diversi"},
    {"id": "fortuna", "nome": "Colpo di fortuna", "desc": "Incontra un Pokémon shiny"},
    {"id": "impeccabile", "nome": "Palestra impeccabile", "desc": "Vinci una medaglia senza aver perso nessuno dalla precedente"},
    {"id": "disciplina", "nome": "Disciplina", "desc": "Vinci una medaglia con tutta la squadra entro il level cap"},
    {"id": "compagno", "nome": "Fedele compagno", "desc": "Arriva alla 4ª medaglia con lo starter ancora vivo"},
    {"id": "intoccabili", "nome": "Intoccabili", "desc": "Arriva all'8ª medaglia perdendo al massimo 3 Pokémon"},
]
VOCI = {o["id"]: o for o in OBIETTIVI + SFIDE}
for _t in TAPPE:
    for _v in _t["voci"]:
        VOCI[_v] = dict(VOCI[_v], tappa=_t["id"])


def info(sp):
    return POKEDEX.get(str(sp)) or {"nome": f"#{sp}", "tipi": ["?"], "famiglia": -(sp or 0)}


def _s(v):
    """String() di JavaScript per i valori che usiamo (interi, stringhe, None)."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def nome_luogo(k):
    if k is None:
        return "?"
    k = _s(k)
    if k.startswith("z"):
        z = k[1:]
        return f"{ZONE_NOMI_EN[z]} (zona {z})" if z in ZONE_NOMI_EN else f"Zona {z}"
    return LUOGHI.get(k) or f"Luogo #{k}"


def nuovo_stato(ora):
    s = {"run": 1, "giocatori": {}, "storico": [], "tid_vecchi": {}, "id_msg": 0, "zone_apprese": {},
         "regole": {"doppioni": True, "shiny": True, "tutorial": True}, "edizione": _nuova_edizione()}
    _azzera_run(s, ora)
    return s


def _nuova_edizione():
    import secrets
    return secrets.token_hex(3)


def _azzera_run(s, ora):
    s.update({"stato": "in_corso", "motivo": "", "iniziata": ora, "lega": False, "pokemon": {}, "incontri": [],
              "eventi": [], "messaggi": {}, "ordine": 0, "avvisi_inviati": [], "obiettivi": {}})
    if EXTRA:
        s.update({"traguardi": {}, "medaglie_t": {}})
    for g in s["giocatori"].values():
        g["medaglie"] = 0
        g["box_ok"] = False


# ---------- utilita' ----------
def vivo(p):
    return p["stato"] in ("squadra", "box")


def nome(p):
    return p.get("soprannome") or info(p["specie"])["nome"]


def altri(s, g):
    return [x for x in s["giocatori"] if x != g]


def _evento(s, ora, testo, tipo="info"):
    s["eventi"].append({"t": ora, "testo": testo, "tipo": tipo})
    if len(s["eventi"]) > 250:
        del s["eventi"][: len(s["eventi"]) - 250]


def _msg(s, g, testo):
    s["id_msg"] += 1
    s["messaggi"].setdefault(g, []).append({"id": s["id_msg"], "testo": testo})
    if len(s["messaggi"][g]) > 40:
        del s["messaggi"][g][: len(s["messaggi"][g]) - 40]


def _msg_tutti(s, testo):
    for g in list(s["giocatori"]):
        _msg(s, g, testo)


def _avviso_unico(s, g, chiave, testo):
    if chiave in s["avvisi_inviati"]:
        return
    s["avvisi_inviati"].append(chiave)
    if len(s["avvisi_inviati"]) > 500:
        del s["avvisi_inviati"][:100]
    _msg(s, g, testo)


def luogo_incontro(s, e):
    if e.get("luogo") is not None:
        return _s(e["luogo"])
    z = _s(e.get("zona"))
    if s["zone_apprese"].get(z) is not None:
        return _s(s["zone_apprese"][z])
    if ZONE.get(z) is not None:
        return _s(ZONE[z])
    return "z" + z


def _primo_incontro(s, g, luogo):
    return next((e for e in s["incontri"] if e["g"] == g and not e.get("ignorato") and e["esito"] != "annullato"
                 and luogo_incontro(s, e) == luogo), None)


def _cattura_di(s, g, luogo):
    best = None
    for k, p in s["pokemon"].items():
        if p["giocatore"] == g and _s(p["luogo"]) == luogo and not p["irregolare"] and (best is None or p["ordine"] < s["pokemon"][best]["ordine"]):
            best = k
    return best


def partners(s, chiave):
    """Gli altri membri del gruppo legato (stesso luogo). Se anche uno solo ha fallito l'incontro, il gruppo è rotto."""
    p = s["pokemon"].get(chiave)
    if not p or p["irregolare"]:
        return []
    luogo = _s(p["luogo"])
    A = altri(s, p["giocatore"])
    if any(_fallito(s, x, luogo) for x in [p["giocatore"]] + A):
        return []
    return [k for k in (_cattura_di(s, a, luogo) for a in A) if k]


def partner(s, chiave):
    l = partners(s, chiave)
    return l[0] if l else None


def _fallito(s, g, luogo):
    e = _primo_incontro(s, g, luogo)
    return bool(e and e["esito"] == "fallito")


# ---------- morti e game over ----------
def _morte(s, ora, chiave, causa, propaga=True):
    p = s["pokemon"].get(chiave)
    if not p or not vivo(p):
        return
    p.update(stato="morto", causa=causa, morto=ora)
    g = p["giocatore"]
    _evento(s, ora, f"{nome(p)} di {g} è morto ({causa})", "morte")
    _msg(s, g, f"{nome(p)} è morto. Riposa in pace.")
    if not propaga:
        return
    for k in partners(s, chiave):
        if not vivo(s["pokemon"][k]):
            continue
        q = s["pokemon"][k]
        _morte(s, ora, k, f"legato a {nome(p)} di {g}", False)
        s["avvisi_inviati"].append(f"rianimato:{k}")
        _msg(s, q["giocatore"], f"{nome(p)} di {g} è morto: muore anche il tuo {nome(q)}. Mettilo nel box.")


def _allinea_legami(s, ora):
    """Un gruppo può ricomporsi (incontro annullato, luogo imparato meglio): chi è legato a un morto muore anche lui."""
    if s["stato"] != "in_corso":
        return
    for k, p in list(s["pokemon"].items()):
        if not vivo(p) or p["irregolare"]:
            continue
        morto = next((s["pokemon"][x] for x in partners(s, k) if s["pokemon"][x]["stato"] == "morto"), None)
        if morto:
            _morte(s, ora, k, f"legato a {nome(morto)} di {morto['giocatore']}", False)
            _msg(s, p["giocatore"], f"{nome(morto)} di {morto['giocatore']} è morto: muore anche il tuo {nome(p)}. Mettilo nel box.")
    _controlla_estinzione(s, ora)


def game_over(s, ora, motivo):
    if s["stato"] != "in_corso":
        return
    s["stato"] = "game_over"
    s["motivo"] = motivo
    _evento(s, ora, f"GAME OVER: {motivo}", "gameover")
    _msg_tutti(s, f"GAME OVER! {motivo}")
    pk = list(s["pokemon"].values())
    s["storico"].append({"run": s["run"], "motivo": motivo, "inizio": s["iniziata"], "fine": ora,
                         "medaglie": max([0] + [g.get("medaglie") or 0 for g in s["giocatori"].values()]),
                         "catture": len(pk), "morti": sum(1 for p in pk if p["stato"] == "morto")})


def _controlla_estinzione(s, ora):
    for g in list(s["giocatori"]):
        suoi = [p for p in s["pokemon"].values() if p["giocatore"] == g and not p["irregolare"]]
        if suoi and not any(vivo(p) for p in suoi):
            game_over(s, ora, f"{g} non ha più Pokémon vivi")


def nuova_run(s, ora):
    if s["stato"] == "in_corso":
        game_over(s, ora, "run abbandonata")
    for p in s["pokemon"].values():
        if p.get("tid") is None:
            continue
        l = s["tid_vecchi"].setdefault(p["giocatore"], [])
        if p["tid"] not in l:
            l.append(p["tid"])
    s["run"] += 1
    _azzera_run(s, ora)
    _evento(s, ora, f"Inizia la run #{s['run']}: nuove ROM per tutti.")
    _msg_tutti(s, f"Run #{s['run']}: preparo le nuove ROM…")


# ---------- obiettivi ----------
def _completa_obiettivo(s, ora, g, o, come):
    s.setdefault("obiettivi", {})
    mio = s["obiettivi"].setdefault(g, {})
    if mio.get(o["id"]):
        return
    mio[o["id"]] = {"t": ora, "come": come}
    _evento(s, ora, f"{g} ha battuto {o['nome']}!", "obiettivo")
    _msg_tutti(s, f"{g} ha battuto {o['nome']}!")
    if o["tipo"] == "lega" and all(mio.get(x["id"]) for x in OBIETTIVI if x["tipo"] == "lega"):
        _msg(s, g, f"Superquattro battuti! Level cap: {LEVEL_CAP[9]}")
    if o["tipo"] == "campione":
        G = list(s["giocatori"])
        if G and all(s["obiettivi"].get(x) and s["obiettivi"][x].get("iris") for x in G) and s["stato"] == "in_corso":
            s["stato"] = "vinta"
            s["motivo"] = "Tutti e due avete battuto Iris!"
            _evento(s, ora, "RUN VINTA! Tutti hanno battuto Iris!", "obiettivo")
            _msg_tutti(s, "RUN VINTA! Complimenti!")
            pk = list(s["pokemon"].values())
            s["storico"].append({"run": s["run"], "motivo": "VINTA", "inizio": s["iniziata"], "fine": ora, "medaglie": 8,
                                 "catture": len(pk), "morti": sum(1 for p in pk if p["stato"] == "morto"), "vinta": True})
        else:
            _msg(s, g, "Hai battuto la Campionessa! Ora tocca agli altri.")


# ---------- sfide e traguardi ----------
def _completa_sfida(s, ora, g, voce):
    mio = s.setdefault("obiettivi", {}).setdefault(g, {})
    if mio.get(voce["id"]):
        return
    mio[voce["id"]] = {"t": ora, "come": "auto"}
    _evento(s, ora, f"{g} ha completato «{voce['nome']}»", "obiettivo")
    _msg(s, g, f"Obiettivo completato: {voce['nome']}")


def _sblocca(s, ora, g, tid):
    mio = s.setdefault("traguardi", {}).setdefault(g, {})
    if mio.get(tid):
        return
    t = next(x for x in TRAGUARDI if x["id"] == tid)
    mio[tid] = {"t": ora}
    _evento(s, ora, f"{g} ha sbloccato il traguardo «{t['nome']}»", "traguardo")
    _msg(s, g, f"Traguardo sbloccato: {t['nome']}")


def _controlla_extra(s, ora, g, medaglie_prima, livelli_prima):
    suoi = [p for p in s["pokemon"].values() if p["giocatore"] == g and not p["irregolare"]]
    in_squadra = [p for p in suoi if p["stato"] == "squadra"]
    morti = [p for p in suoi if p["stato"] == "morto"]
    sfide = {x["id"]: x for x in SFIDE}
    if len(suoi) >= 2:
        _completa_sfida(s, ora, g, sfide["cattura2"])
    if len(in_squadra) >= 4:
        _completa_sfida(s, ora, g, sfide["squadra4"])
    if len(in_squadra) >= 6:
        _completa_sfida(s, ora, g, sfide["squadra6"])
    if any(p.get("evoluto") for p in suoi):
        _completa_sfida(s, ora, g, sfide["evoluzione"])
    chiavi = [k for k, p in s["pokemon"].items() if p["giocatore"] == g and not p["irregolare"]]
    if len(s["giocatori"]) >= 2 and any(partners(s, k) for k in chiavi):
        _sblocca(s, ora, g, "primo_legame")
    if len(suoi) >= 10:
        _sblocca(s, ora, g, "collezionista")
    luoghi = {luogo_incontro(s, e) for e in s["incontri"] if e["g"] == g and e.get("fonte") == "auto" and not e.get("ignorato")}
    if len(luoghi) >= 12:
        _sblocca(s, ora, g, "esploratore")
    if any(e["g"] == g and e.get("shiny") for e in s["incontri"]):
        _sblocca(s, ora, g, "fortuna")
    nuove = s["giocatori"][g].get("medaglie") or 0
    if nuove > medaglie_prima:
        dal = s.setdefault("medaglie_t", {}).get(g, s["iniziata"])
        if not any((p.get("morto") or 0) > dal for p in morti):
            _sblocca(s, ora, g, "impeccabile")
        if livelli_prima and max(livelli_prima) <= LEVEL_CAP[min(medaglie_prima, 8)]:
            _sblocca(s, ora, g, "disciplina")
        if nuove >= 4 and suoi:
            starter = min(suoi, key=lambda p: p["ordine"])
            if vivo(starter):
                _sblocca(s, ora, g, "compagno")
        if nuove >= 8 and len(morti) <= 3:
            _sblocca(s, ora, g, "intoccabili")
        s["medaglie_t"][g] = ora


# ---------- catture ----------
def _nuova_cattura(s, ora, g, chiave, m):
    s["ordine"] += 1
    luogo = _s(m["luogo"])
    p = {"giocatore": g, "pid": m["pid"], "specie": m["specie"], "soprannome": m.get("soprannome") or "", "luogo": m["luogo"],
         "livello": m.get("livello") or 0, "ps": m.get("ps"), "ps_max": m.get("ps_max"),
         "stato": "box" if m.get("box") else "squadra", "ordine": s["ordine"], "catturato": ora, "irregolare": False,
         "causa": "", "tid": m.get("id_allenatore"), "slot": m.get("slot") or 0}
    prima = _cattura_di(s, g, luogo)
    s["pokemon"][chiave] = p
    sp = info(m["specie"])["nome"]
    descr = f"{p['soprannome']} ({sp})" if p["soprannome"] and p["soprannome"] != sp else sp
    pi = _primo_incontro(s, g, luogo)
    if pi and pi["esito"] == "fallito":
        p["irregolare"] = True
        _evento(s, ora, f"{g} ha catturato {descr} a {nome_luogo(luogo)}, ma lì il primo incontro era fallito!", "allarme")
        _msg(s, g, f"Regola: a {nome_luogo(luogo)} il primo incontro era fallito. {nome(p)} non vale: liberalo.")
    elif prima:
        p["irregolare"] = True
        _evento(s, ora, f"{g} ha un secondo Pokémon da {nome_luogo(luogo)}: {descr} (fuori regola)", "allarme")
        _msg(s, g, f"Regola: hai già una cattura a {nome_luogo(luogo)}. {nome(p)} non vale.")
    else:
        _evento(s, ora, f"{g} ha catturato {descr} a {nome_luogo(luogo)}", "cattura")
        A = altri(s, g)
        falliti = [a for a in A if _fallito(s, a, luogo)]
        membri = [(a, _cattura_di(s, a, luogo)) for a in A]
        membri = [(a, k) for a, k in membri if k]
        if membri and not falliti:
            qs = [s["pokemon"][k] for _, k in membri]
            _msg_tutti(s, f"Nuovo legame a {nome_luogo(luogo)}: " + " ↔ ".join(nome(x) for x in [p] + qs))
            _evento(s, ora, f"Nuovo legame a {nome_luogo(luogo)}: " + " ↔ ".join(f"{nome(x)} ({x['giocatore']})" for x in [p] + qs), "legame")
            morto = next((q for q in qs if not vivo(q)), None)
            if morto:
                _morte(s, ora, chiave, f"il compagno {nome(morto)} era già morto", False)
        elif falliti:
            _msg(s, g, f"{falliti[0]} ha fallito l'incontro a {nome_luogo(luogo)}: {nome(p)} va messo nel box o liberato.")
    return p


def _aggiorna_pokemon(s, ora, g, m, in_squadra):
    chiave = f"{g}:{_s(m['pid'])}"
    p = s["pokemon"].get(chiave)
    if not p:
        p = _nuova_cattura(s, ora, g, chiave, m)
    if p["specie"] != m["specie"] and p["specie"]:
        _evento(s, ora, f"{nome(p)} di {g} si è evoluto in {info(m['specie'])['nome']}!")
        if EXTRA:
            p["evoluto"] = True
    p["specie"] = m["specie"]
    if m.get("soprannome"):
        p["soprannome"] = m["soprannome"]
    if in_squadra:
        p.update(livello=m.get("livello"), ps=m.get("ps"), ps_max=m.get("ps_max"), slot=m.get("slot") or 0)
        if p["stato"] in ("box", "liberato"):
            p["stato"] = "squadra"
    elif p["stato"] in ("squadra", "liberato"):
        p["stato"] = "box"
    return chiave


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---------- aggiornamento dallo script Lua ----------
def aggiorna_da_gioco(s, ora, d):
    g = str(d.get("giocatore") or "")[:24]
    if not g:
        return {"errore": "manca il nome del giocatore"}
    if g not in s["giocatori"]:
        if len(s["giocatori"]) >= MAX_GIOCATORI:
            return {"errore": f"La partita è già piena ({MAX_GIOCATORI} giocatori)."}
        s["giocatori"][g] = {"entrato": ora, "medaglie": 0}
        _evento(s, ora, f"{g} è entrato nella partita")
    G = s["giocatori"][g]
    prima = G.get("visto") or 0
    G["visto"] = ora
    G["emulatore"] = bool(d.get("attivo"))
    if d.get("diagnostica"):
        G["diagnostica"] = d["diagnostica"]
    if d.get("zona") is not None:
        G["zona"] = d["zona"]
    cambiato = ora - prima > 30 or bool(d.get("diagnostica"))

    run_rom = d.get("run_rom")
    run_ok = run_rom is None or (_numero(run_rom) and run_rom == s["run"])
    if G.get("run_rom") != run_rom:
        cambiato = True
    G["run_rom"] = run_rom
    if not run_ok:
        motivo = ("la ROM caricata non è una ROM del Soul Link" if run_rom == -1
                  else f"la ROM caricata è della run {_s(run_rom)}, mentre la run attuale è la {s['run']}")
        return {"cambiato": cambiato, "ignorato": motivo}
    vecchi = set(s["tid_vecchi"].get(g, []) if run_rom is None else [])
    medaglie_prima = G.get("medaglie") or 0
    livelli_prima = [p.get("livello") or 0 for p in s["pokemon"].values() if p["giocatore"] == g and p["stato"] == "squadra" and not p["irregolare"]]

    def valido(m):
        return not m.get("uovo") and m.get("id_allenatore") not in vecchi

    if isinstance(d.get("squadra"), list) or isinstance(d.get("eventi"), list):
        cambiato = True
    med = d.get("medaglie")
    if _numero(med) and med != G.get("medaglie"):
        if med > (G.get("medaglie") or 0):
            _evento(s, ora, f"{g} ha conquistato la {_s(med)}ª medaglia!", "obiettivo")
            cap = LEVEL_CAP[min(int(med), 8)]
            _msg(s, g, f"{_s(med)}ª medaglia! Nuovo level cap: {cap}")
        G["medaglie"] = med
        if s["stato"] == "in_corso":
            for o in OBIETTIVI:
                if o.get("medaglia") and o["medaglia"] <= med:
                    _completa_obiettivo(s, ora, g, o, "medaglia")

    # 1) squadra e box
    if isinstance(d.get("squadra"), list):
        squadra = [m for m in d["squadra"] if valido(m)]
        visti = set()
        for m in squadra:
            visti.add(_aggiorna_pokemon(s, ora, g, m, True))
        if isinstance(d.get("box"), list) and d.get("box_ok"):
            G["box_ok"] = True
            pid_squadra = {m["pid"] for m in squadra}
            for m in d["box"]:
                if valido(m) and m["pid"] not in pid_squadra:
                    visti.add(_aggiorna_pokemon(s, ora, g, dict(m, box=True), False))
        box_completo = isinstance(d.get("box"), list) and bool(d.get("box_ok"))
        for k, p in s["pokemon"].items():
            if p["giocatore"] != g or k in visti:
                continue
            if p["stato"] == "squadra":
                p["stato"] = "liberato" if box_completo else "box"
            elif p["stato"] == "box" and box_completo:
                p["stato"] = "liberato"
        if s["stato"] == "in_corso":
            for m in squadra:
                k = f"{g}:{_s(m['pid'])}"
                p = s["pokemon"][k]
                if m.get("ps") == 0 and vivo(p):
                    _morte(s, ora, k, "KO in lotta")
                elif (m.get("ps") or 0) > 0 and not vivo(p) and p["stato"] != "liberato":
                    _avviso_unico(s, g, f"rianimato:{k}", f"Attenzione: {nome(p)} è morto e non può stare in squadra. Mettilo nel box.")
            if squadra and all(m.get("ps") == 0 for m in squadra):
                game_over(s, ora, f"{g} ha perso tutta la squadra")
            _controlla_estinzione(s, ora)

    # 2) incontri selvatici e lotte con allenatori
    for e in d.get("eventi") or []:
        if e.get("tipo") == "incontro":
            _registra_incontro(s, ora, g, e)
        elif e.get("tipo") == "esito":
            _esito_incontro(s, ora, g, e)
        elif e.get("tipo") == "fine_allenatore" and e.get("vinta") and s["stato"] == "in_corso":
            try:
                o = OBIETTIVO_DA_ID.get(int(e.get("allenatore")))
            except (TypeError, ValueError):
                o = None
            if o:
                _completa_obiettivo(s, ora, g, o, "lotta")

    _allinea_legami(s, ora)
    if EXTRA and s["stato"] == "in_corso":
        _controlla_extra(s, ora, g, medaglie_prima, livelli_prima)

    # 3) legami: partner nel box
    for k, p in s["pokemon"].items():
        if p["giocatore"] != g or p["stato"] != "squadra":
            continue
        kp = next((x for x in partners(s, k) if s["pokemon"][x]["stato"] == "box"), None)
        if kp:
            q = s["pokemon"][kp]
            _avviso_unico(s, g, f"box:{k}:{math.floor(ora / 300)}", f"{nome(q)} di {q['giocatore']} è nel box: metti nel box anche {nome(p)}.")
    return {"cambiato": True}


def _famiglie_catturate(s, g):
    return {info(p["specie"])["famiglia"] for p in s["pokemon"].values() if p["giocatore"] == g and not p["irregolare"]}


def _registra_incontro(s, ora, g, e):
    if any(x["g"] == g and x["pid"] == e.get("pid") and x.get("zona") == e.get("zona") for x in s["incontri"]):
        return
    inc = {"id": len(s["incontri"]) + 1, "g": g, "zona": e.get("zona"), "specie": e.get("specie"), "livello": e.get("livello"),
           "pid": e.get("pid"), "shiny": bool(e.get("shiny")), "esito": "in_corso", "t": ora, "fonte": "auto", "ignorato": None}
    luogo = luogo_incontro(s, inc)
    gia_primo = _primo_incontro(s, g, luogo)
    sp = info(e.get("specie"))["nome"]
    primo_in_assoluto = not any(x["g"] == g and x.get("fonte") == "auto" for x in s["incontri"])
    if s["regole"].get("tutorial") is not False and primo_in_assoluto:
        inc["ignorato"] = "tutorial"
    elif not gia_primo:
        if _cattura_di(s, g, luogo):
            inc["ignorato"] = "luogo_usato"
        elif s["regole"].get("shiny") and inc["shiny"]:
            inc["ignorato"] = "shiny"
        elif s["regole"].get("doppioni") and info(e.get("specie"))["famiglia"] in _famiglie_catturate(s, g):
            inc["ignorato"] = "doppione"
    s["incontri"].append(inc)
    if len(s["incontri"]) > 600:
        del s["incontri"][: len(s["incontri"]) - 600]
    ig = inc["ignorato"]
    if ig == "tutorial":
        _msg(s, g, f"{sp} è l'incontro del tutorial: non conta.")
        _evento(s, ora, f"Incontro del tutorial di {g} ({sp}): non conta", "info")
    elif ig == "shiny":
        _msg(s, g, f"{sp} shiny! Non conta come incontro: puoi catturarlo.")
        _evento(s, ora, f"{g} ha incontrato un {sp} shiny a {nome_luogo(luogo)}!", "legame")
    elif ig == "luogo_usato":
        _avviso_unico(s, g, f"usato:{g}:{luogo}", f"{nome_luogo(luogo)}: hai già una cattura qui, non catturare.")
    elif ig == "doppione":
        _msg(s, g, f"{sp}: hai già questa famiglia evolutiva, non conta (clausola doppioni).")
    elif not gia_primo:
        _msg(s, g, f"Primo incontro a {nome_luogo(luogo)}: {sp} Lv.{_s(e.get('livello'))}. Catturalo!")
        _evento(s, ora, f"Primo incontro di {g} a {nome_luogo(luogo)}: {sp} Lv.{_s(e.get('livello'))}", "incontro")
    else:
        _avviso_unico(s, g, f"usato:{g}:{luogo}", f"{nome_luogo(luogo)}: incontro già usato, non catturare.")


def _esito_incontro(s, ora, g, e):
    inc = next((x for x in reversed(s["incontri"]) if x["g"] == g and x["pid"] == e.get("pid") and x["esito"] == "in_corso"), None)
    if not inc:
        return
    es = e.get("esito")
    inc["esito"] = "catturato" if es == "catturato" else "incerto" if es == "incerto" else "fallito"
    if inc["esito"] == "catturato" and inc.get("zona") is not None:
        p = s["pokemon"].get(f"{g}:{_s(inc['pid'])}")
        if p and p.get("luogo") is not None:
            s["zone_apprese"][_s(inc["zona"])] = p["luogo"]
    luogo = luogo_incontro(s, inc)
    primo = _primo_incontro(s, g, luogo)
    if primo is not inc:
        return
    sp = info(inc["specie"])["nome"]
    if inc["esito"] == "fallito":
        _evento(s, ora, f"{g} ha fallito il primo incontro a {nome_luogo(luogo)} ({sp})", "allarme")
        _msg(s, g, f"Incontro fallito a {nome_luogo(luogo)}.")
        for a in altri(s, g):
            kq = _cattura_di(s, a, luogo)
            if kq:
                q = s["pokemon"][kq]
                _msg(s, a, f"{g} ha fallito a {nome_luogo(luogo)}: il tuo {nome(q)} va messo nel box o liberato.")
    elif inc["esito"] == "incerto":
        _evento(s, ora, f"Non so se {g} ha catturato {sp} a {nome_luogo(luogo)}: conferma nella scheda Percorsi.", "allarme")


# ---------- azioni dall'interfaccia ----------
def azione(s, ora, d):
    a = d.get("azione")
    if a == "esito_incontro":
        inc = next((x for x in s["incontri"] if x["id"] == int(d.get("id", -1))), None)
        if not inc:
            return {"errore": "incontro non trovato"}
        if d.get("esito") == "annullato":
            inc["esito"] = "annullato"
            _evento(s, ora, f"Incontro di {inc['g']} a {nome_luogo(luogo_incontro(s, inc))} annullato")
        else:
            inc["esito"] = "in_corso"
            _esito_incontro(s, ora, inc["g"], {"pid": inc["pid"], "esito": d.get("esito")})
    elif a == "conta_incontro":
        inc = next((x for x in s["incontri"] if x["id"] == int(d.get("id", -1))), None)
        if not inc:
            return {"errore": "incontro non trovato"}
        inc["ignorato"] = None
        _evento(s, ora, f"L'incontro di {inc['g']} con {info(inc['specie'])['nome']} ora conta")
    elif a == "fallito":
        luogo = _s(d.get("luogo"))
        s["incontri"].append({"id": len(s["incontri"]) + 1, "g": d.get("giocatore"), "zona": None, "luogo": luogo, "specie": 0,
                              "livello": 0, "pid": -len(s["incontri"]) - 1, "shiny": False, "esito": "in_corso", "t": ora,
                              "fonte": "manuale", "ignorato": None})
        _esito_incontro(s, ora, d.get("giocatore"), {"pid": -len(s["incontri"]), "esito": "fallito"})
    elif a == "regole":
        s["regole"] = {**s["regole"], **(d.get("regole") or {})}
    elif a == "obiettivo":
        o = next((x for x in OBIETTIVI if x["id"] == d.get("id")), None)
        if not o:
            return {"errore": "obiettivo sconosciuto"}
        if d.get("valore"):
            _completa_obiettivo(s, ora, d.get("giocatore"), o, "a mano")
        elif s.get("obiettivi", {}).get(d.get("giocatore")) is not None:
            s["obiettivi"][d["giocatore"]].pop(o["id"], None)
    elif a == "lega":
        s["lega"] = bool(d.get("valore"))
    elif a == "stato_pokemon":
        p = s["pokemon"].get(d.get("chiave"))
        if not p:
            return {"errore": "Pokémon non trovato"}
        st = d.get("stato")
        if st == "morto":
            _morte(s, ora, d["chiave"], "segnato a mano", d.get("propaga") is not False)
            _controlla_estinzione(s, ora)
        elif st in ("squadra", "box", "liberato"):
            p.update(stato=st, causa="")
            _evento(s, ora, f"{nome(p)} di {p['giocatore']} segnato a mano come «{ {'squadra': 'in squadra', 'box': 'nel box', 'valido': 'cattura valida'}.get(st, st) }»")
        elif st == "valido":
            p["irregolare"] = False
    elif a == "game_over":
        game_over(s, ora, d.get("motivo") or "game over dichiarato a mano")
    elif a == "nuova_run":
        nuova_run(s, ora)
    elif a == "reset_partita":
        giocatori = {g: {"entrato": x.get("entrato", ora), "medaglie": 0} for g, x in s["giocatori"].items()}
        id_msg = s.get("id_msg", 0)
        s.clear()
        s.update(nuovo_stato(ora))
        s["giocatori"], s["id_msg"] = giocatori, id_msg
        _evento(s, ora, f"Partita azzerata da {d.get('giocatore', '?')}: si riparte dalla run #1", "allarme")
        _msg_tutti(s, f"{d.get('giocatore', '?')} ha azzerato la partita: si riparte dalla run #1.")
    elif a == "rimuovi_giocatore":
        s["giocatori"].pop(d.get("giocatore"), None)
    else:
        return {"errore": "azione sconosciuta"}
    _allinea_legami(s, ora)
    return {"ok": True}


# ---------- vista per l'interfaccia ----------
def cap_di(s, g):
    G = s["giocatori"].get(g) or {}
    mio = (s.get("obiettivi") or {}).get(g) or {}
    lega = s.get("lega") or all(mio.get(x["id"]) for x in OBIETTIVI if x["tipo"] == "lega")
    return LEVEL_CAP[9 if lega else min(G.get("medaglie") or 0, 8)]


def prossimo_obiettivo(s, g):
    mio = (s.get("obiettivi") or {}).get(g) or {}
    if not EXTRA:
        return next((o for o in OBIETTIVI if not mio.get(o["id"])), None)
    for i, t in enumerate(TAPPE):
        mancanti = [v for v in t["voci"] if not mio.get(v)]
        if mancanti:
            v = VOCI[mancanti[0]]
            return {**{k: v[k] for k in ("id", "nome", "tipo", "medaglia") if k in v}, "tappa": t["nome"], "tappa_n": i + 1,
                    "tappe": len(TAPPE), "tappa_fatte": len(t["voci"]) - len(mancanti), "tappa_voci": len(t["voci"]), "luogo": t["luogo"]}
    return None


def vista(s, ora):
    G = list(s["giocatori"])
    pk = {}
    for k, p in s["pokemon"].items():
        i = info(p["specie"])
        gr = partners(s, k)
        pk[k] = {**p, "chiave": k, "nome_specie": i["nome"], "tipi": i["tipi"], "luogo_nome": nome_luogo(p["luogo"]),
                 "partner": gr[0] if gr else None, "partners": gr}
    luoghi = {}

    def tocca(l, t):
        if l not in luoghi or luoghi[l] > t:
            luoghi[l] = t
    for p in s["pokemon"].values():
        tocca(_s(p["luogo"]), p["catturato"])
    for e in s["incontri"]:
        if e["esito"] != "annullato":
            tocca(luogo_incontro(s, e), e["t"])
    percorsi = []
    for l, _t in sorted(luoghi.items(), key=lambda x: x[1]):
        r = {"luogo": l, "luogo_nome": nome_luogo(l), "giocatori": {}}
        for g in G:
            e = _primo_incontro(s, g, l)
            kc = _cattura_di(s, g, l)
            r["giocatori"][g] = {"incontro": ({**e, "nome_specie": info(e["specie"])["nome"] if e["specie"] else "—"} if e else None),
                                 "cattura": pk[kc] if kc else None}
        membri = [r["giocatori"][g] for g in G]
        if any(m["incontro"] and m["incontro"]["esito"] == "fallito" for m in membri):
            r["stato"] = "rotta"
        elif any(m["cattura"] and not vivo(m["cattura"]) for m in membri):
            r["stato"] = "morta"
        elif len(G) >= 2 and all(m["cattura"] for m in membri):
            r["stato"] = "attiva"
        elif any(m["incontro"] and m["incontro"]["esito"] == "in_corso" for m in membri):
            r["stato"] = "in_lotta"
        else:
            r["stato"] = "in_attesa"
        percorsi.append(r)

    avvisi = []
    per_tipo = {}
    for p in pk.values():
        if p["stato"] != "squadra" or p["irregolare"]:
            continue
        cap = cap_di(s, p["giocatore"])
        if (p.get("livello") or 0) > cap:
            avvisi.append(f"{p['giocatore']}: {nome(p)} è al livello {p['livello']}, sopra il cap {cap}")
        lista = per_tipo.setdefault(p["tipi"][0], [])
        if _s(p["luogo"]) not in lista:
            lista.append(_s(p["luogo"]))
        if any(pk[x]["stato"] == "box" for x in p["partners"]):
            avvisi.append(f"{p['giocatore']}: {nome(p)} è in squadra ma il suo compagno è nel box")
    for t, l in per_tipo.items():
        if len(l) > 1:
            avvisi.append(f"Tipo primario {t} ripetuto in squadra: {', '.join(nome_luogo(x) for x in l)}")
    for p in pk.values():
        if p["stato"] == "squadra" and p["irregolare"]:
            avvisi.append(f"{p['giocatore']}: {nome(p)} è una cattura fuori regola")
    for p in pk.values():
        if p["stato"] != "squadra" or p["irregolare"]:
            continue
        a = next((x for x in altri(s, p["giocatore"]) if _fallito(s, x, _s(p["luogo"]))), None)
        if a:
            avvisi.append(f"{p['giocatore']}: {nome(p)} va nel box, {a} ha fallito l'incontro a {nome_luogo(p['luogo'])}")
    for g in G:
        x = s["giocatori"][g]
        if x.get("run_rom") is not None and x["run_rom"] != s["run"] and ora - (x.get("visto") or 0) < 60:
            avvisi.append(f"{g}: i suoi dati vengono ignorati, " + ("la ROM caricata non è una ROM del Soul Link" if x["run_rom"] == -1 else f"la ROM è della run {_s(x['run_rom'])}"))
    for e in s["incontri"]:
        if e["esito"] == "incerto":
            avvisi.append(f"{e['g']}: conferma se {info(e['specie'])['nome']} ({nome_luogo(luogo_incontro(s, e))}) è stato catturato")

    return {
        "run": s["run"], "edizione": s.get("edizione", ""), "stato": s["stato"], "motivo": s["motivo"], "iniziata": s["iniziata"], "lega": s.get("lega"),
        "regole": s["regole"], "level_cap": LEVEL_CAP, "nomi_cap": NOMI_CAP,
        "giocatori": {g: {**s["giocatori"][g], "online": ora - (s["giocatori"][g].get("visto") or 0) < 45, "cap": cap_di(s, g),
                          "zona_nome": nome_luogo(luogo_incontro(s, {"zona": s["giocatori"][g]["zona"]})) if s["giocatori"][g].get("zona") is not None else None}
                      for g in G},
        "pokemon": pk, "percorsi": percorsi, "avvisi": avvisi,
        "incontri": [{**e, "nome_specie": info(e["specie"])["nome"] if e["specie"] else "—", "luogo_nome": nome_luogo(luogo_incontro(s, e))}
                     for e in list(reversed(s["incontri"][-80:]))],
        "eventi": list(reversed(s["eventi"][-80:])), "storico": s["storico"], "luoghi": LUOGHI,
        "obiettivi": [{k: o[k] for k in ("id", "nome", "tipo", "medaglia") if k in o} for o in OBIETTIVI],
        "fatti": s.get("obiettivi") or {},
        **({"tappe": TAPPE, "voci": VOCI, "traguardi_def": TRAGUARDI, "traguardi": s.get("traguardi") or {}} if EXTRA else {}),
    }


def messaggi_da(s, g, dopo):
    return [m for m in s["messaggi"].get(g, []) if m["id"] > dopo]
