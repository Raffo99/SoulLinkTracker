"""Lettura di dati dalla ROM randomizzata (file .nds): le mosse che ogni Pokémon impara salendo di livello
e i luoghi dove si incontrano Pokémon selvatici. Si leggono dalla ROM vera perché il randomizer può averli cambiati."""
import struct
from pathlib import Path

PERCORSO_MOSSE = "a/0/1/8"          # Nero 2 / Bianco 2 (e Nero / Bianco): mosse imparate per livello
PERCORSO_MAPPE = "a/0/1/2"          # intestazioni delle zone (48 byte ciascuna)
PERCORSO_SELVATICI = "a/1/2/7"      # tabelle degli incontri selvatici di Nero 2 / Bianco 2
_cache = {}


class ErroreRom(Exception):
    pass


def _file_nds(f, percorso: str) -> bytes:
    """Contenuto di un file del filesystem NitroROM (tabella dei nomi FNT + tabella delle posizioni FAT).
    Legge solo le parti che servono: la ROM di Nero 2 è grande 512 MB."""
    f.seek(0)
    testa = f.read(0x200)
    if len(testa) < 0x50:
        raise ErroreRom("file troppo corto")
    fnt_off, fnt_dim, fat_off, fat_dim = struct.unpack_from("<IIII", testa, 0x40)
    if not (0 < fnt_dim < 0x1000000 and 0 < fat_dim < 0x1000000):
        raise ErroreRom("intestazione della ROM non valida")
    f.seek(fnt_off)
    fnt = f.read(fnt_dim)
    f.seek(fat_off)
    fat = f.read(fat_dim)

    def cartella(id_cartella):
        sub_off, primo_file, _ = struct.unpack_from("<IHH", fnt, (id_cartella & 0xFFF) * 8)
        p = sub_off
        file_id = primo_file
        voci = {}
        while True:
            t = fnt[p]
            p += 1
            if t == 0:
                break
            lung = t & 0x7F
            nome = fnt[p:p + lung].decode("latin-1")
            p += lung
            if t & 0x80:
                sub_id = struct.unpack_from("<H", fnt, p)[0]
                p += 2
                voci[nome] = ("cartella", sub_id)
            else:
                voci[nome] = ("file", file_id)
                file_id += 1
        return voci

    id_corrente = 0xF000
    pezzi = percorso.strip("/").split("/")
    for i, nome in enumerate(pezzi):
        voci = cartella(id_corrente)
        if nome not in voci:
            raise ErroreRom(f"nella ROM manca {percorso}")
        tipo, n = voci[nome]
        if i == len(pezzi) - 1:
            if tipo != "file":
                raise ErroreRom(f"{percorso} non è un file")
            inizio, fine = struct.unpack_from("<II", fat, n * 8)
            f.seek(inizio)
            return f.read(fine - inizio)
        if tipo != "cartella":
            raise ErroreRom(f"{percorso}: {nome} non è una cartella")
        id_corrente = n
    raise ErroreRom(percorso)


def _narc(dati: bytes) -> list:
    """File contenuti in un archivio NARC."""
    if dati[:4] != b"NARC":
        raise ErroreRom("archivio NARC non valido")
    p = struct.unpack_from("<H", dati, 0x0C)[0]                 # dimensione dell'intestazione
    if dati[p:p + 4] != b"BTAF":
        raise ErroreRom("NARC senza BTAF")
    dim_btaf, n = struct.unpack_from("<IH", dati, p + 4)
    voci = [struct.unpack_from("<II", dati, p + 12 + i * 8) for i in range(n)]
    p += dim_btaf
    if dati[p:p + 4] != b"BTNF":
        raise ErroreRom("NARC senza BTNF")
    p += struct.unpack_from("<I", dati, p + 4)[0]
    if dati[p:p + 4] != b"GMIF":
        raise ErroreRom("NARC senza GMIF")
    base = p + 8
    return [dati[base + a:base + b] for a, b in voci]


def mosse_per_livello(rom) -> dict:
    """{specie: [(livello, mossa), ...]} dalla ROM; in cache finché il file non cambia."""
    rom = Path(rom)
    chiave = ("mosse", str(rom), rom.stat().st_mtime, rom.stat().st_size)
    if chiave in _cache:
        return _cache[chiave]
    with open(rom, "rb") as f:
        file = _narc(_file_nds(f, PERCORSO_MOSSE))
    out = {}
    for specie in range(1, min(len(file), 650)):
        f = file[specie]
        lista = []
        for i in range(0, len(f) - 3, 4):
            mossa, livello = struct.unpack_from("<HH", f, i)
            if mossa == 0xFFFF and livello == 0xFFFF:
                break
            lista.append((livello, mossa))
        out[specie] = lista
    _metti_in_cache(chiave, out)
    return out


def _metti_in_cache(chiave, valore):
    for k in [k for k in _cache if k[0] == chiave[0]]:
        del _cache[k]
    _cache[chiave] = valore


# tipi di incontro di una tabella (Gen 5): erba/grotta, erba doppia, erba che si muove, surf, increspature, pesca, increspature
_QUANTI = (12, 12, 12, 5, 5, 5, 5)
_TERRA = (0, 1, 2)


def incontri(rom) -> dict:
    """Dove si incontrano Pokémon selvatici: {"luoghi": {id_luogo: tipo}, "zone": {zona: tipo}},
    con tipo "terra" (erba, grotte, erba che si muove) oppure "acqua" (solo Surf e pesca)."""
    rom = Path(rom)
    chiave = ("incontri", str(rom), rom.stat().st_mtime, rom.stat().st_size)
    if chiave in _cache:
        return _cache[chiave]
    with open(rom, "rb") as f:
        mappe = _narc(_file_nds(f, PERCORSO_MAPPE))[0]
        tabelle = _narc(_file_nds(f, PERCORSO_SELVATICI))

    def tipo_tabella(t):
        terra = acqua = False
        for inizio in range(0, max(len(t), 1), 232):          # 1 o 4 stagioni
            blocco = t[inizio:inizio + 232]
            if len(blocco) < 232:
                break
            off = 8
            for i, n in enumerate(_QUANTI):
                if blocco[i] and any(struct.unpack_from("<H", blocco, off + j * 4)[0] & 0x7FF for j in range(n)):
                    if i in _TERRA:
                        terra = True
                    else:
                        acqua = True
                off += n * 4
        return "terra" if terra else "acqua" if acqua else None

    tipi_tab = {}
    luoghi, zone, zona_luogo = {}, {}, {}
    for zona in range(len(mappe) // 48):
        base = zona * 48
        zona_luogo[zona] = mappe[base + 26]                    # indice del nome del luogo
        tab = mappe[base + 20]                                 # Nero 2 / Bianco 2: un byte, 255 = nessuna tabella
        if tab == 255 or tab >= len(tabelle):
            continue
        if tab not in tipi_tab:
            tipi_tab[tab] = tipo_tabella(tabelle[tab])
        t = tipi_tab[tab]
        if not t:
            continue
        luogo = mappe[base + 26]
        zone[zona] = t
        if luoghi.get(luogo) != "terra":
            luoghi[luogo] = t
    out = {"luoghi": luoghi, "zone": zone, "zona_luogo": zona_luogo}
    _metti_in_cache(chiave, out)
    return out


# ---------- testi del gioco (nomi dei luoghi e degli allenatori) ----------
PERCORSO_TESTI = "a/0/0/2"
PERCORSO_ALLENATORI = "a/0/9/1"
TESTO_LUOGHI, TESTO_ALLENATORI, TESTO_CLASSI = 109, 382, 383      # Nero 2 / Bianco 2, in tutte le lingue
_SIMBOLI = {0x2467: "×", 0x2468: "÷", 0x246C: "…", 0x246D: "♂", 0x246E: "♀", 0x2473: "★", 0x2479: "♪", 0xFFFE: " "}


def _testi(dati: bytes) -> list:
    """Stringhe di un file di testo della quinta generazione (cifrate carattere per carattere)."""
    n_sez, n_voci = struct.unpack_from("<HH", dati, 0)
    if n_sez < 1:
        return []
    sez = struct.unpack_from("<I", dati, 12)[0]
    out = []
    for j in range(n_voci):
        off, n_car = struct.unpack_from("<IH", dati, sez + 4 + j * 8)
        car = list(struct.unpack_from(f"<{n_car}H", dati, sez + off)) if n_car else []
        if car:
            chiave = car[-1] ^ 0xFFFF
            for k in range(n_car - 1, -1, -1):
                car[k] ^= chiave
                chiave = ((chiave >> 3) | (chiave << 13)) & 0xFFFF
        if car and car[0] == 0xF100:                 # testo compresso: non serve per i nomi
            out.append("")
            continue
        t = []
        for c in car:
            if c == 0xFFFF:
                break
            if c in _SIMBOLI:
                t.append(_SIMBOLI[c])
            elif 0x20 <= c < 0xD800:
                t.append(chr(c))
        out.append(" ".join("".join(t).split()))
    return out


def nomi(rom) -> dict:
    """{"luoghi": [nome per indice], "allenatori": {id: "Classe Nome"}} letti dai testi della ROM."""
    rom = Path(rom)
    chiave = ("nomi", str(rom), rom.stat().st_mtime, rom.stat().st_size)
    if chiave in _cache:
        return _cache[chiave]
    with open(rom, "rb") as f:
        testi = _narc(_file_nds(f, PERCORSO_TESTI))
        allenatori = _narc(_file_nds(f, PERCORSO_ALLENATORI))
    luoghi = _testi(testi[TESTO_LUOGHI])
    nomi_all = _testi(testi[TESTO_ALLENATORI])
    classi = _testi(testi[TESTO_CLASSI])
    chi = {}
    for i in range(1, min(len(allenatori), len(nomi_all))):
        d = allenatori[i]
        if len(d) < 2 or not nomi_all[i]:
            continue
        classe = classi[d[1]] if d[1] < len(classi) else ""
        chi[i] = f"{classe} {nomi_all[i]}".strip()
    out = {"luoghi": luoghi, "allenatori": chi}
    _metti_in_cache(chiave, out)
    return out


def prossime(mosse: list, livello: int) -> dict:
    """Riassunto per il tracker: quante mosse impara in tutto salendo di livello e qual è la prossima."""
    per_livello = [(l, m) for l, m in mosse if l > 1]
    future = sorted((l, m) for l, m in per_livello if l > (livello or 0))
    prossima = future[0] if future else None
    return {"totale": len({m for _, m in mosse}), "mancano": len(future),
            "prossima": prossima, "tra": (prossima[0] - livello) if prossima else None}


# ---------- allenatori e strumenti di ogni zona (oggetti della mappa) ----------
PERCORSO_ENTITA = "a/1/2/6"          # Nero 2 / Bianco 2: NPC, strumenti, teletrasporti di ogni zona (CTRMap: FIELD_ZONE_ENTITIES)
TIPO_STRUMENTO = 4                   # tipo di evento delle Poké Ball con uno strumento a terra (in alcune zone)
SCRIPT_STRUMENTI = range(7000, 8000)  # script delle Poké Ball a terra (7000 + numero dello strumento nella lista del gioco)


def entita(rom) -> dict:
    """{"zone": {zona: {"npc": [(sprite, tipo, flag, script), ...]}}, "luogo": {zona: indice del nome del luogo},
        "sprite_strumento": sprite delle Poké Ball a terra}."""
    rom = Path(rom)
    chiave = ("entita", str(rom), rom.stat().st_mtime, rom.stat().st_size)
    if chiave in _cache:
        return _cache[chiave]
    with open(rom, "rb") as f:
        mappe = _narc(_file_nds(f, PERCORSO_MAPPE))[0]
        file = _narc(_file_nds(f, PERCORSO_ENTITA))
    zone, luogo, letti = {}, {}, {}
    conta_sprite = {}
    for zona in range(len(mappe) // 48):
        base = zona * 48
        idx = struct.unpack_from("<H", mappe, base + 0x16)[0]
        luogo[zona] = mappe[base + 26]
        if idx >= len(file):
            continue
        if idx not in letti:
            d = file[idx]
            npc = []
            if len(d) >= 8:
                n_mob, n_npc = d[4], d[5]
                p = 8 + n_mob * 0x14
                for i in range(n_npc):
                    if p + 0x24 > len(d):
                        break
                    sprite, _mov, tipo, flag, scr = struct.unpack_from("<HHHHH", d, p + 2)
                    npc.append((sprite, tipo, flag, scr))
                    if scr in SCRIPT_STRUMENTI:
                        conta_sprite[sprite] = conta_sprite.get(sprite, 0) + 1
                    p += 0x24
            letti[idx] = {"npc": npc, "file": idx}
        zone[zona] = letti[idx]
    sprite_str = max(conta_sprite, key=conta_sprite.get) if conta_sprite else None
    out = {"zone": zone, "luogo": luogo, "sprite_strumento": sprite_str}
    _metti_in_cache(chiave, out)
    return out


def per_luogo(ent: dict, luogo: int, scarto: int, n_allenatori: int) -> dict:
    """Allenatori e strumenti di tutte le zone con quel nome di luogo.
    allenatori: {id: flag di comparsa}; strumenti: [flag]. Un allenatore = NPC con script = scarto + id;
    uno strumento = Poké Ball a terra (tipo 4 o lo sprite delle Poké Ball) con il suo flag (acceso = raccolto)."""
    allenatori, strumenti = {}, set()
    sp = ent.get("sprite_strumento")
    for z, l in ent["luogo"].items():
        if l != luogo or z not in ent["zone"]:
            continue
        for sprite, tipo, flag, scr in ent["zone"][z]["npc"]:
            if tipo == TIPO_STRUMENTO or scr in SCRIPT_STRUMENTI or (sp is not None and sprite == sp and flag):
                if flag:
                    strumenti.add(flag)
                continue
            t = scr - scarto
            if 0 < t < n_allenatori and t not in allenatori:
                allenatori[t] = flag
    return {"allenatori": allenatori, "strumenti": sorted(strumenti)}
