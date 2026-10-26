"""Le tappe della storia di Nero 2, in ordine, con il luogo di ognuna: i posti dove bisogna andare (per esempio il
Pokéwood per la nave) e le lotte importanti. Servono a capire cosa fare dopo, non contano per la run.
Una tappa «vai» è fatta quando ci sei stato (o quando hai già battuto un obiettivo che viene dopo)."""
from . import logica as L

# (id, testo, luoghi, obiettivo collegato). Luoghi = indici dei nomi dei luoghi del gioco.
TAPPE = [
    ("starter", "Ricevi lo starter e lotta col rivale", [117], "rivale1"),
    ("p19", "Percorso 19", [124], None),
    ("venturia", "Venturia", [122], None),
    ("p20", "Percorso 20", [125], None),
    ("fattoria", "Fattoria di Venturia: ritrova l'Herdier scomparso", [130], None),
    ("rivale2", "Rivale alla Fattoria di Venturia", [130], "rivale2"),
    ("komor", "Torna ad Alisopoli: palestra di Komor", [117], "cheren"),
    ("zondopoli", "Zondopoli", [118, 145], None),
    ("cantiere", "Cantiere Zondopoli: ferma il Team Plasma", [131], None),
    ("velia", "Palestra di Velia", [118], "rosy"),
    ("pokewood", "Pokéwood: gira il primo film (serve per la nave)", [120], None),
    ("austropoli", "In nave fino ad Austropoli", [8, 109], None),
    ("fogne", "Fogne di Austropoli con il rivale", [129], None),
    ("artemisio", "Palestra di Artemisio", [8], "artemisio"),
    ("galleria", "Galleria Solidarietà", [121], None),
    ("p4", "Percorso 4", [17], None),
    ("sciroccopoli", "Sciroccopoli: lotta in coppia alla stazione", [9, 76, 110], None),
    ("camelia", "Palestra di Camelia", [9], "camelia"),
    ("p5", "Percorso 5", [18, 93], None),
    ("ponte_lib", "Ponte Libecciopoli: il Team Plasma", [65, 89], None),
    ("libecciopoli", "Libecciopoli", [10, 77], None),
    ("rafan", "Palestra di Rafan", [10], "rafan"),
    ("pwt", "PWT: il torneo obbligatorio", [36], "rivale3"),
    ("fregata1", "Fregata Plasma al porto di Libecciopoli", [135], None),
    ("p6", "Percorso 6 (qui ricevi Surf)", [19, 94], None),
    ("pietrelettrica", "Cava Pietrelettrica", [37, 85], None),
    ("ponentopoli", "Ponentopoli", [11, 78], None),
    ("p7", "Percorso 7", [20, 95], None),
    ("torre_cielo", "Torre Cielo", [56], None),
    ("anemone", "Palestra di Anemone", [11], "anisia"),
    ("poggiovento", "Poggiovento (in aereo da Ponentopoli)", [123], None),
    ("antipodi", "Monte Antipodi", [132], None),
    ("spiraria", "Spiraria", [42, 105, 107], None),
    ("rivale4", "Rivale a Spiraria", [42], "rivale4"),
    ("p13", "Percorso 13", [26, 100], None),
    ("fortebrezza", "Fortebrezza: il Team Plasma", [41, 104], None),
    ("p12", "Percorso 12", [25, 99], None),
    ("ponte_vil", "Ponte Villaggio", [67, 91], None),
    ("p11", "Percorso 11", [24, 98], None),
    ("boreduopoli", "Boreduopoli", [13, 80, 111], None),
    ("aristide", "Palestra di Aristide (poi la città congelata dal Team Plasma)", [13], "aristide"),
    ("tunnel_marino", "Tunnel Marino (da Spiraria)", [144], None),
    ("grecalopoli", "Grecalopoli", [119], None),
    ("ciprian", "Palestra di Ciprian", [119], "ciprian"),
    ("p22", "Percorso 22", [127], None),
    ("p21", "Percorso 21", [126], None),
    ("grotta", "Grotta Costiera: trova la Fregata Plasma", [141], None),
    ("acromio", "Fregata Plasma: Acromio", [135], "acromio"),
    ("fossa", "Fossa Gigante", [61, 88], None),
    ("ghecis", "Fossa Gigante: Ghecis", [61], "ghecis"),
    ("p23", "Percorso 23", [128], None),
    ("rivale5", "Via Vittoria: il rivale", [134, 40], "rivale5"),
    ("lega", "Lega Pokémon", [44], None),
    ("antea", "Superquattro: Antemia", [44], "antea"),
    ("mirton", "Superquattro: Mirton", [44], "mirton"),
    ("marzio", "Superquattro: Marzio", [44], "marzio"),
    ("catlina", "Superquattro: Catlina", [44], "catlina"),
    ("iris", "Campionessa Iris", [44], "iris"),
]


def stato_tappe(fatti_g: dict, visitati: set) -> list:
    """[(tappa, fatta)] per un giocatore: fatti_g = obiettivi fatti, visitati = luoghi dove è stato."""
    out = []
    ultimo_obiettivo = -1
    for i, t in enumerate(TAPPE):
        if t[3] and fatti_g.get(t[3]):
            ultimo_obiettivo = i
    for i, (tid, testo, luoghi, ob) in enumerate(TAPPE):
        if ob:
            fatta = bool(fatti_g.get(ob))
        else:
            fatta = any(l in visitati for l in luoghi) or i < ultimo_obiettivo
        out.append(((tid, testo, luoghi, ob), fatta))
    return out


def prossima(fatti_g: dict, visitati: set):
    """La prima tappa non ancora fatta: {"id", "testo", "luogo", "luogo_nome", "obiettivo", "n", "tot"} o None."""
    for n, (t, fatta) in enumerate(stato_tappe(fatti_g, visitati), 1):
        if not fatta:
            return {"id": t[0], "testo": t[1], "luogo": t[2][0], "luogo_nome": L.nome_luogo(t[2][0]), "obiettivo": t[3],
                    "n": n, "tot": len(TAPPE)}
    return None
