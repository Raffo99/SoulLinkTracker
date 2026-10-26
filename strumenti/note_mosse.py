"""Note brevi (effetti secondari, danni particolari) e descrizione lunga per le mosse fino alla 5a generazione.
Fonte: CSV di PokeAPI (cartella data/v2/csv). Scrive la chiave "mosse_note" in risorse/dati.json:
{id: [nota breve o "", descrizione lunga in italiano o ""]}."""
import csv, json, sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pokeapi"
DATI = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/soullink3/app/risorse/dati.json"
MAX_ID = 559


def leggi(nome):
    with open(f"{SRC}/{nome}", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def n(x):
    return int(x) if x not in (None, "") else 0


mosse = {n(r["id"]): r for r in leggi("moves.csv") if n(r["id"]) <= MAX_ID}
meta = {n(r["move_id"]): r for r in leggi("move_meta.csv")}
stat = defaultdict(list)
for r in leggi("move_meta_stat_changes.csv"):
    stat[n(r["move_id"])].append((n(r["stat_id"]), n(r["change"])))
testi = {}
for r in leggi("move_flavor_text.csv"):
    if r["language_id"] == "8" and n(r["move_id"]) <= MAX_ID:
        vg = n(r["version_group_id"])
        mid = n(r["move_id"])
        if mid not in testi or vg < testi[mid][0]:          # la versione più vecchia disponibile (più vicina alla 5a gen.)
            testi[mid] = (vg, " ".join(r["flavor_text"].replace("­\n", "").split()))

STATS = {1: "PS", 2: "Att", 3: "Dif", 4: "Att Sp", 5: "Dif Sp", 6: "Vel", 7: "Precisione", 8: "Elusione"}
MALI = {1: "paralisi", 2: "sonno", 3: "congelamento", 4: "scottatura", 5: "avvelenamento", 6: "confusione",
        7: "infatuazione", 8: "intrappola", 9: "incubo", 12: "attacco di tormento", 13: "blocca una mossa",
        14: "sonnolenza (dorme il turno dopo)", 15: "impedisce le cure", 17: "toglie le immunità di tipo",
        18: "semi che rubano PS ogni turno", 19: "impedisce gli strumenti", 20: "KO di tutti dopo 3 turni",
        21: "radici: recupera PS ogni turno", 24: "impedisce le mosse sonore"}

# danni calcolati in modo particolare o effetti che i dati generali non descrivono
SPECIALI = {
    "seismic-toss": "danno = livello di chi la usa", "night-shade": "danno = livello di chi la usa",
    "dragon-rage": "danno fisso: 40 PS", "sonic-boom": "danno fisso: 20 PS",
    "super-fang": "toglie metà dei PS attuali", "endeavor": "porta i PS del bersaglio pari ai tuoi",
    "psywave": "danno casuale da 0,5 a 1,5 volte il livello", "final-gambit": "danno = i tuoi PS, poi vai KO",
    "counter": "rende il doppio del danno fisico subito", "mirror-coat": "rende il doppio del danno speciale subito",
    "metal-burst": "rende 1,5 volte il danno subito", "bide": "aspetta 2 turni e rende il doppio del danno subito",
    "low-kick": "più forte se il bersaglio pesa di più (20–120)",
    "grass-knot": "più forte se il bersaglio pesa di più (20–120)",
    "heavy-slam": "più forte quanto più pesi del bersaglio", "heat-crash": "più forte quanto più pesi del bersaglio",
    "gyro-ball": "più forte se sei più lento del bersaglio", "electro-ball": "più forte se sei più veloce del bersaglio",
    "eruption": "più debole se hai pochi PS", "water-spout": "più debole se hai pochi PS",
    "flail": "più forte se hai pochi PS (fino a 200)", "reversal": "più forte se hai pochi PS (fino a 200)",
    "wring-out": "più forte se il bersaglio ha molti PS", "crush-grip": "più forte se il bersaglio ha molti PS",
    "return": "più forte con amicizia alta (fino a 102)", "frustration": "più forte con amicizia bassa (fino a 102)",
    "hex": "doppia se il bersaglio ha un problema di stato", "venoshock": "doppia se il bersaglio è avvelenato",
    "facade": "doppia se sei scottato, avvelenato o paralizzato",
    "brine": "doppia se il bersaglio ha meno di metà PS", "acrobatics": "doppia se non tieni strumenti",
    "payback": "doppia se agisci dopo il bersaglio", "avalanche": "doppia se sei stato colpito nel turno",
    "revenge": "doppia se sei stato colpito nel turno",
    "assurance": "doppia se il bersaglio ha già subito danni nel turno",
    "retaliate": "doppia se un compagno è andato KO il turno prima",
    "stored-power": "+20 di potenza per ogni aumento di statistica",
    "punishment": "più forte se il bersaglio ha aumentato statistiche",
    "smelling-salts": "doppia sul bersaglio paralizzato (e lo cura)",
    "wake-up-slap": "doppia su chi dorme (e lo sveglia)", "pursuit": "doppia se il bersaglio sta cambiando",
    "fury-cutter": "raddoppia a ogni uso di fila", "rollout": "5 turni, raddoppia ogni turno",
    "ice-ball": "5 turni, raddoppia ogni turno", "echoed-voice": "più forte a ogni uso di fila",
    "round": "doppia se un compagno l'ha appena usata", "trump-card": "più forte con pochi PP rimasti",
    "magnitude": "potenza casuale da 10 a 150", "present": "a caso: danno (40–120) o cura il bersaglio",
    "natural-gift": "tipo e potenza dipendono dalla bacca tenuta", "fling": "potenza dipende dallo strumento lanciato",
    "hidden-power": "tipo e potenza dipendono dal Pokémon", "weather-ball": "cambia tipo e raddoppia con il meteo",
    "beat-up": "un colpo per ogni compagno in salute", "spit-up": "potenza dipende da Accumulo",
    "foul-play": "usa l'Attacco del bersaglio", "psyshock": "speciale, ma il danno usa la Difesa",
    "psystrike": "speciale, ma il danno usa la Difesa", "secret-sword": "speciale, ma il danno usa la Difesa",
    "false-swipe": "lascia sempre almeno 1 PS", "u-turn": "dopo il colpo torni indietro e cambi",
    "volt-switch": "dopo il colpo torni indietro e cambi", "explosion": "chi la usa va KO",
    "self-destruct": "chi la usa va KO", "memento": "chi la usa va KO; Att e Att Sp del bersaglio −2",
    "solar-beam": "carica un turno (subito con il sole)", "sky-attack": "carica un turno · 30% tentennamento",
    "razor-wind": "carica un turno", "skull-bash": "carica un turno (Dif +1)", "freeze-shock": "carica un turno",
    "ice-burn": "carica un turno", "fly": "due turni: nel primo vola via", "dig": "due turni: nel primo va sottoterra",
    "dive": "due turni: nel primo si immerge", "bounce": "due turni: nel primo salta · 30% paralisi",
    "shadow-force": "due turni: nel primo sparisce (supera Protezione)", "sky-drop": "due turni: porta in aria il bersaglio",
    "outrage": "2–3 turni di fila, poi confusione", "thrash": "2–3 turni di fila, poi confusione",
    "petal-dance": "2–3 turni di fila, poi confusione", "uproar": "3 turni di fila, nessuno può dormire",
    "future-sight": "colpisce dopo 2 turni", "doom-desire": "colpisce dopo 2 turni",
    "focus-punch": "agisce per ultima e fallisce se vieni colpito prima",
    "sucker-punch": "fallisce se il bersaglio non sta attaccando", "fake-out": "solo al primo turno · fa tentennare",
    "dream-eater": "solo su chi dorme · recupera metà del danno", "thief": "ruba lo strumento del bersaglio",
    "covet": "ruba lo strumento del bersaglio", "knock-off": "fa cadere lo strumento del bersaglio",
    "incinerate": "brucia la bacca del bersaglio", "bug-bite": "mangia la bacca del bersaglio",
    "pluck": "mangia la bacca del bersaglio", "rapid-spin": "toglie trappole, Parassiseme e legami",
    "brick-break": "rompe Riflesso e Schermoluce", "feint": "supera Protezione",
    "clear-smog": "azzera le modifiche alle statistiche del bersaglio",
    "chip-away": "ignora le modifiche alle statistiche del bersaglio",
    "sacred-sword": "ignora le modifiche alle statistiche del bersaglio",
    "frost-breath": "sempre brutto colpo", "storm-throw": "sempre brutto colpo",
    "snore": "solo mentre dormi · 30% tentennamento", "sleep-talk": "usa a caso un'altra tua mossa mentre dormi",
    "belly-drum": "perdi metà PS: Attacco al massimo", "pain-split": "divide in parti uguali i PS con il bersaglio",
    "jump-kick": "se manca, perdi PS", "high-jump-kick": "se manca, perdi PS",
    "struggle": "contraccolpo: 1/4 dei tuoi PS", "toxic": "iperavvelenamento (danno che cresce ogni turno)",
    "techno-blast": "il tipo dipende dalla cassetta tenuta", "judgment": "il tipo dipende dalla lastra tenuta",
    "synchronoise": "colpisce solo chi ha un tipo in comune con te", "triple-kick": "3 colpi sempre più forti",
    "curse": "Spettro: perdi metà PS e maledici · altri: Vel −1, Att e Dif +1",
    "rest": "dormi 2 turni e recuperi tutti i PS", "rage": "l'Attacco sale quando vieni colpito",
    "pay-day": "monete a fine lotta", "tri-attack": "20% scottatura, paralisi o congelamento",
    "secret-power": "effetto secondario in base al terreno (30%)", "spit-up": "potenza dipende da Accumulo",
    "focus-energy": "brutti colpi più facili", "stealth-rock": "danno a chi entra (in base al tipo Roccia)",
    "spikes": "danno a chi entra", "toxic-spikes": "avvelena chi entra", "baton-pass": "cambi passando le modifiche",
    "perish-song": "tutti in campo vanno KO dopo 3 turni", "destiny-bond": "se vai KO, va KO anche chi ti ha colpito",
}
RICARICA = {"hyper-beam", "giga-impact", "blast-burn", "hydro-cannon", "frenzy-plant", "roar-of-time", "rock-wrecker"}


def segno(c):
    return f"+{c}" if c > 0 else f"−{-c}"


def nota(mid):
    m, x = mosse[mid], meta.get(mid) or {}
    ident = m["identifier"]
    parti = []
    pri = n(m["priority"])
    if pri > 0:
        parti.append(f"priorità +{pri} (agisce prima)")
    elif pri < 0 and ident != "focus-punch":
        parti.append(f"priorità {segno(pri)} (agisce dopo)")
    if ident in SPECIALI:
        parti.append(SPECIALI[ident])
        if ident in ("toxic", "curse", "memento", "skull-bash", "sky-attack", "bounce", "snore", "tri-attack"):
            return " · ".join(parti)
    if ident in RICARICA:
        parti.append("il turno dopo devi ricaricarti")
    cat, mal = n(x.get("meta_category_id")), n(x.get("meta_ailment_id"))
    if cat == 9:
        parti.append("KO in un colpo (precisione 30%)")
    lo, hi = n(x.get("min_hits")), n(x.get("max_hits"))
    if hi > 1 and ident != "triple-kick":
        parti.append(f"colpisce {lo}–{hi} volte" if lo != hi else f"colpisce {hi} volte")
    if mal > 0 and ident not in SPECIALI:
        nome = MALI.get(mal, "")
        ch = n(x.get("ailment_chance"))
        if mal == 8:
            t1, t2 = n(x.get("min_turns")), n(x.get("max_turns"))
            nome = f"intrappola {t1}–{t2} turni" if t2 else "intrappola"
        if nome:
            parti.append(f"{ch}% {nome}" if 0 < ch < 100 else nome)
    fl = n(x.get("flinch_chance"))
    if fl and ident not in SPECIALI:
        parti.append(f"{fl}% tentennamento")
    cambi = stat.get(mid) or []
    if cambi and ident not in ("curse", "memento", "skull-bash"):
        if cat == 7:
            chi = "tu"
        elif cat == 6:
            chi = "bersaglio"
        elif cat == 5:
            chi = "bersaglio"
        else:
            chi = "tu" if any(c > 0 for _, c in cambi) else "bersaglio"
        if m["target_id"] == "7":                               # mosse che agiscono su chi le usa
            chi = "tu"
        sc = n(x.get("stat_chance"))
        tutti = len(cambi) == 5 and len({c for _, c in cambi}) == 1 and {s for s, _ in cambi} == {2, 3, 4, 5, 6}
        testo = (f"tutte le statistiche {segno(cambi[0][1])}" if tutti
                 else ", ".join(f"{STATS[s]} {segno(c)}" for s, c in cambi))
        testo += " (tue)" if chi == "tu" else " (bersaglio)"
        parti.append(f"{sc}% {testo}" if 0 < sc < 100 else testo)
    dr = n(x.get("drain"))
    if dr > 0:
        parti.append(f"recupera il {dr}% del danno")
    elif dr < 0 and ident != "struggle":
        parti.append(f"contraccolpo: {-dr}% del danno")
    he = n(x.get("healing"))
    if he > 0 and ident != "rest":
        parti.append(f"cura il {he}% dei PS")
    if n(x.get("crit_rate")) >= 1 and ident not in ("frost-breath", "storm-throw", "focus-energy"):
        parti.append("brutti colpi più facili")
    out = []
    for p in parti:                                             # niente doppioni
        if p not in out:
            out.append(p)
    return " · ".join(out)


note = {}
for mid in sorted(mosse):
    breve = nota(mid)
    lunga = testi.get(mid, (0, ""))[1]
    if breve or lunga:
        note[str(mid)] = [breve, lunga]

d = json.load(open(DATI, encoding="utf-8"))
d["mosse_note"] = note
json.dump(d, open(DATI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(note), "mosse con note;", sum(1 for v in note.values() if v[0]), "con nota breve")
for k in ("7", "14", "52", "53", "69", "82", "85", "92", "98", "136", "141", "162", "207", "244", "248", "252", "315",
          "370", "369", "389", "447", "473", "506", "57", "94", "63", "33", "76", "200", "130"):
    print(k, mosse[int(k)]["identifier"], "→", note.get(k, ["", ""])[0])
