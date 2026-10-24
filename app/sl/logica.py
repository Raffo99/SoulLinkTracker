"""LOGICA SOUL LINK - funzioni pure sullo stato della partita.

Traduzione fedele della versione JavaScript (verificata confrontando le due su scenari casuali).
Lo stato e' un dizionario serializzabile in JSON: le chiavi dei dizionari sono sempre stringhe.
"""
import json
import math
import sys
from pathlib import Path

_base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
_DATI = json.loads((_base / "risorse" / "dati.json").read_text("utf-8"))
POKEDEX, LUOGHI, ZONE, ZONE_NOMI_EN = _DATI["pokedex"], _DATI["luoghi"], _DATI["zone"], _DATI["zone_nomi_en"]

LEVEL_CAP = [13, 18, 24, 30, 33, 39, 48, 51, 58, 59]
NOMI_CAP = ["Cheren", "Rosy", "Artemisio", "Camelia", "Rafan", "Anisia", "Aristide", "Ciprian", "Superquattro", "Iris"]

# obiettivi principali: ID allenatore (Nero 2 / Bianco 2, dal NDS Ironmon Tracker); "asso" = livello del Pokemon piu' forte
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
         "regole": {"doppioni": True, "shiny": True, "tutorial": True}}
    _azzera_run(s, ora)
    return s


def _azzera_run(s, ora):
    s.update({"stato": "in_corso", "motivo": "", "iniziata": ora, "lega": False, "pokemon": {}, "incontri": [],
              "eventi": [], "messaggi": {}, "ordine": 0, "avvisi_inviati": [], "obiettivi": {}})
    for g in s["giocatori"].values():
        g["medaglie"] = 0
        g["box_ok"] = False


# ---------- utilita' ----------
def vivo(p):
    return p["stato"] in ("squadra", "box")


def nome(p):
    return p.get("soprannome") or info(p["specie"])["nome"]


def altro(s, g):
    return next((x for x in s["giocatori"] if x != g), None)


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


def partner(s, chiave):
    p = s["pokemon"].get(chiave)
    if not p or p["irregolare"]:
        return None
    a = altro(s, p["giocatore"])
    if not a:
        return None
    luogo = _s(p["luogo"])
    if _fallito(s, a, luogo):
        return None
    return _cattura_di(s, a, luogo)


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
    _evento(s, ora, f"{g}: {nome(p)} è morto ({causa})", "morte")
    _msg(s, g, f"{nome(p)} e' morto. Riposa in pace.")
    if not propaga:
        return
    k = partner(s, chiave)
    if k and vivo(s["pokemon"][k]):
        q = s["pokemon"][k]
        _morte(s, ora, k, f"legame con {nome(p)} di {g}", False)
        s["avvisi_inviati"].append(f"rianimato:{k}")
        _msg(s, q["giocatore"], f"{nome(p)} di {g} e' morto: muore anche il tuo {nome(q)}! Mettilo nel box.")


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
            game_over(s, ora, f"{g} non ha piu' Pokemon vivi")


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
    _evento(s, ora, f"Inizia la run #{s['run']}! Le nuove ROM vengono generate in automatico.")
    _msg_tutti(s, f"Run #{s['run']}: genero la nuova ROM randomizzata...")


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
            _evento(s, ora, "RUN VINTA! Tutti e due avete battuto Iris!", "obiettivo")
            _msg_tutti(s, "RUN VINTA! Complimenti!")
            pk = list(s["pokemon"].values())
            s["storico"].append({"run": s["run"], "motivo": "VINTA", "inizio": s["iniziata"], "fine": ora, "medaglie": 8,
                                 "catture": len(pk), "morti": sum(1 for p in pk if p["stato"] == "morto"), "vinta": True})
        else:
            _msg(s, g, "Hai battuto la Campionessa! Aspetta che ce la faccia anche l'altro.")


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
        _msg(s, g, f"Regola: hai gia' una cattura a {nome_luogo(luogo)}. {nome(p)} non vale.")
    else:
        _evento(s, ora, f"{g} ha catturato {descr} a {nome_luogo(luogo)}", "cattura")
        a = altro(s, g)
        kq = _cattura_di(s, a, luogo) if a else None
        if kq and not _fallito(s, a, luogo):
            q = s["pokemon"][kq]
            _msg_tutti(s, f"Nuovo legame a {nome_luogo(luogo)}: {nome(p)} <-> {nome(q)}")
            _evento(s, ora, f"Legame creato: {nome(p)} ({g}) ↔ {nome(q)} ({a})", "legame")
            if not vivo(q):
                _morte(s, ora, chiave, f"il partner {nome(q)} era gia' morto", False)
        elif a and _fallito(s, a, luogo):
            _msg(s, g, f"{a} ha fallito l'incontro a {nome_luogo(luogo)}: {nome(p)} va nel box o liberato.")
    return p


def _aggiorna_pokemon(s, ora, g, m, in_squadra):
    chiave = f"{g}:{_s(m['pid'])}"
    p = s["pokemon"].get(chiave)
    if not p:
        p = _nuova_cattura(s, ora, g, chiave, m)
    if p["specie"] != m["specie"] and p["specie"]:
        _evento(s, ora, f"{g}: {nome(p)} si è evoluto in {info(m['specie'])['nome']}!")
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
        if len(s["giocatori"]) >= 2:
            return {"errore": "Ci sono gia' due giocatori in questa partita."}
        s["giocatori"][g] = {"entrato": ora, "medaglie": 0}
        _evento(s, ora, f"{g} si è unito alla partita")
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
        motivo = ("la ROM caricata non e' una ROM del Soul Link" if run_rom == -1
                  else f"la ROM caricata e' della run {_s(run_rom)}, la run attuale e' la {s['run']}")
        return {"cambiato": cambiato, "ignorato": motivo}
    vecchi = set(s["tid_vecchi"].get(g, []) if run_rom is None else [])

    def valido(m):
        return not m.get("uovo") and m.get("id_allenatore") not in vecchi

    if isinstance(d.get("squadra"), list) or isinstance(d.get("eventi"), list):
        cambiato = True
    med = d.get("medaglie")
    if _numero(med) and med != G.get("medaglie"):
        if med > (G.get("medaglie") or 0):
            _evento(s, ora, f"{g} ha ottenuto la medaglia n. {_s(med)}!", "cattura")
            cap = LEVEL_CAP[min(int(med), 8)]
            _msg(s, g, f"Medaglia {_s(med)}! Nuovo level cap: {cap}")
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
                    _avviso_unico(s, g, f"rianimato:{k}", f"ATTENZIONE: {nome(p)} e' morto, non puo' stare in squadra! Mettilo nel box.")
            if squadra and all(m.get("ps") == 0 for m in squadra):
                game_over(s, ora, f"{g} è stato sconfitto: tutta la squadra è KO")
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

    # 3) legami: partner nel box
    for k, p in s["pokemon"].items():
        if p["giocatore"] != g or p["stato"] != "squadra":
            continue
        kp = partner(s, k)
        if kp and s["pokemon"][kp]["stato"] == "box":
            q = s["pokemon"][kp]
            _avviso_unico(s, g, f"box:{k}:{math.floor(ora / 300)}", f"{nome(q)} di {q['giocatore']} e' nel box: metti nel box anche {nome(p)}.")
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
        _msg(s, g, f"{sp}: e' l'incontro del tutorial, non conta.")
        _evento(s, ora, f"{g}: incontro del tutorial ({sp}), non conta", "info")
    elif ig == "shiny":
        _msg(s, g, f"SHINY! {sp} non conta come incontro: puoi catturarlo!")
        _evento(s, ora, f"{g}: {sp} SHINY a {nome_luogo(luogo)}!", "legame")
    elif ig == "luogo_usato":
        _avviso_unico(s, g, f"usato:{g}:{luogo}", f"{nome_luogo(luogo)}: hai gia' una cattura qui, non catturare.")
    elif ig == "doppione":
        _msg(s, g, f"{sp}: hai gia' questa famiglia, non conta (clausola doppioni).")
    elif not gia_primo:
        _msg(s, g, f"Primo incontro a {nome_luogo(luogo)}: {sp} Lv.{_s(e.get('livello'))}. Catturalo!")
        _evento(s, ora, f"{g}: primo incontro a {nome_luogo(luogo)} → {sp} Lv.{_s(e.get('livello'))}", "incontro")
    else:
        _avviso_unico(s, g, f"usato:{g}:{luogo}", f"{nome_luogo(luogo)}: incontro gia' usato, non catturare.")


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
        _evento(s, ora, f"{g}: incontro fallito a {nome_luogo(luogo)} ({sp})", "allarme")
        _msg(s, g, f"Incontro fallito a {nome_luogo(luogo)}.")
        a = altro(s, g)
        kq = _cattura_di(s, a, luogo) if a else None
        if kq:
            q = s["pokemon"][kq]
            _msg(s, a, f"{g} ha fallito a {nome_luogo(luogo)}: il tuo {nome(q)} va nel box o liberato.")
    elif inc["esito"] == "incerto":
        _evento(s, ora, f"{g}: non so se {sp} a {nome_luogo(luogo)} è stato catturato. Conferma sulla dashboard.", "allarme")


# ---------- azioni dall'interfaccia ----------
def azione(s, ora, d):
    a = d.get("azione")
    if a == "esito_incontro":
        inc = next((x for x in s["incontri"] if x["id"] == int(d.get("id", -1))), None)
        if not inc:
            return {"errore": "incontro non trovato"}
        if d.get("esito") == "annullato":
            inc["esito"] = "annullato"
            _evento(s, ora, f"{inc['g']}: incontro a {nome_luogo(luogo_incontro(s, inc))} annullato")
        else:
            inc["esito"] = "in_corso"
            _esito_incontro(s, ora, inc["g"], {"pid": inc["pid"], "esito": d.get("esito")})
    elif a == "conta_incontro":
        inc = next((x for x in s["incontri"] if x["id"] == int(d.get("id", -1))), None)
        if not inc:
            return {"errore": "incontro non trovato"}
        inc["ignorato"] = None
        _evento(s, ora, f"{inc['g']}: l'incontro con {info(inc['specie'])['nome']} ora conta")
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
            return {"errore": "pokemon non trovato"}
        st = d.get("stato")
        if st == "morto":
            _morte(s, ora, d["chiave"], "segnato a mano", d.get("propaga") is not False)
            _controlla_estinzione(s, ora)
        elif st in ("squadra", "box", "liberato"):
            p.update(stato=st, causa="")
            _evento(s, ora, f"{p['giocatore']}: {nome(p)} segnato come '{st}'")
        elif st == "valido":
            p["irregolare"] = False
    elif a == "game_over":
        game_over(s, ora, d.get("motivo") or "game over dichiarato a mano")
    elif a == "nuova_run":
        nuova_run(s, ora)
    elif a == "rimuovi_giocatore":
        s["giocatori"].pop(d.get("giocatore"), None)
    else:
        return {"errore": "azione sconosciuta"}
    return {"ok": True}


# ---------- vista per l'interfaccia ----------
def cap_di(s, g):
    G = s["giocatori"].get(g) or {}
    mio = (s.get("obiettivi") or {}).get(g) or {}
    lega = s.get("lega") or all(mio.get(x["id"]) for x in OBIETTIVI if x["tipo"] == "lega")
    return LEVEL_CAP[9 if lega else min(G.get("medaglie") or 0, 8)]


def prossimo_obiettivo(s, g):
    mio = (s.get("obiettivi") or {}).get(g) or {}
    return next((o for o in OBIETTIVI if not mio.get(o["id"])), None)


def vista(s, ora):
    G = list(s["giocatori"])
    pk = {}
    for k, p in s["pokemon"].items():
        i = info(p["specie"])
        pk[k] = {**p, "chiave": k, "nome_specie": i["nome"], "tipi": i["tipi"], "luogo_nome": nome_luogo(p["luogo"]),
                 "partner": partner(s, k)}
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
        elif len(G) == 2 and all(m["cattura"] for m in membri):
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
        if p["partner"] and pk[p["partner"]]["stato"] == "box":
            avvisi.append(f"{p['giocatore']}: {nome(p)} è in squadra ma il partner è nel box")
    for t, l in per_tipo.items():
        if len(l) > 1:
            avvisi.append(f"Tipo primario {t} ripetuto in squadra: {', '.join(nome_luogo(x) for x in l)}")
    for p in pk.values():
        if p["stato"] == "squadra" and p["irregolare"]:
            avvisi.append(f"{p['giocatore']}: {nome(p)} è una cattura fuori regola")
    for p in pk.values():
        if p["stato"] != "squadra" or p["irregolare"]:
            continue
        a = altro(s, p["giocatore"])
        if a and _fallito(s, a, _s(p["luogo"])):
            avvisi.append(f"{p['giocatore']}: {nome(p)} va nel box, {a} ha fallito l'incontro a {nome_luogo(p['luogo'])}")
    for g in G:
        x = s["giocatori"][g]
        if x.get("run_rom") is not None and x["run_rom"] != s["run"] and ora - (x.get("visto") or 0) < 60:
            avvisi.append(f"{g}: i suoi dati vengono ignorati, " + ("la ROM caricata non è una ROM del Soul Link" if x["run_rom"] == -1 else f"la ROM è della run {_s(x['run_rom'])}"))
    for e in s["incontri"]:
        if e["esito"] == "incerto":
            avvisi.append(f"{e['g']}: conferma se {info(e['specie'])['nome']} ({nome_luogo(luogo_incontro(s, e))}) è stato catturato")

    return {
        "run": s["run"], "stato": s["stato"], "motivo": s["motivo"], "iniziata": s["iniziata"], "lega": s.get("lega"),
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
    }


def messaggi_da(s, g, dopo):
    return [m for m in s["messaggi"].get(g, []) if m["id"] > dopo]
