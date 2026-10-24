"""Parti principali della nuova interfaccia: barra in alto, obiettivo, luogo attuale, coppie, ospite del gioco."""
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from .stile import ACC, COLORI_TIPI, KO, OK, ORO, TENUE, WARN, alfa


def nome(p):
    return (p or {}).get("soprannome") or (p or {}).get("nome_specie") or "?"


def etichetta(testo="", ogg=None, stile=None, a_capo=False):
    l = QLabel(testo)
    if ogg:
        l.setObjectName(ogg)
    if stile:
        l.setStyleSheet(stile)
    l.setWordWrap(a_capo)
    return l


def durata(sec):
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"


def pulisci(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget():
            it.widget().deleteLater()
        elif it.layout():
            pulisci(it.layout())


# ----------------------------------------------------------------------------------------------
class Medaglie(QWidget):
    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(3)
        self.punti = []
        for _ in range(8):
            l = QLabel()
            l.setFixedSize(9, 9)
            h.addWidget(l)
            self.punti.append(l)
        self.imposta(0)

    def imposta(self, n):
        for i, l in enumerate(self.punti):
            col = ORO if i < n else "#343849"
            l.setStyleSheet(f"background:{col};border-radius:4px;")


class CartaGiocatore(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("giocatore")
        g = QGridLayout(self)
        g.setContentsMargins(12, 6, 12, 6)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(2)
        self.l_nome = etichetta("")
        self.medaglie = Medaglie()
        self.l_info = etichetta("", "tenue")
        g.addWidget(self.l_nome, 0, 0)
        g.addWidget(self.medaglie, 0, 1, Qt.AlignRight)
        g.addWidget(self.l_info, 1, 0, 1, 2)

    def imposta(self, g, x, io=False):
        col = OK if x.get("online") else TENUE
        tu = " <span style='color:%s;font-size:8pt'>(tu)</span>" % TENUE if io else ""
        self.l_nome.setText(f"<span style='color:{col}'>●</span> <b>{g}</b>{tu}")
        self.medaglie.imposta(x.get("medaglie") or 0)
        dove = x.get("zona_nome") or ("in gioco" if x.get("emulatore") else "offline" if not x.get("online") else "senza partita")
        self.l_info.setText(f"{dove} · cap <b style='color:{WARN}'>{x.get('cap', '?')}</b>")


class BarraSuperiore(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("barra")
        self.setFixedHeight(66)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 6, 10, 6)
        h.setSpacing(14)
        h.addWidget(etichetta(f"Soul Link <span style='color:{ACC}'>Tracker</span>", "titolo"))
        self.l_run = etichetta("Run #–", "pill")
        h.addWidget(self.l_run, 0, Qt.AlignVCenter)
        self.l_tempo = etichetta("0:00:00", "numero")
        self.l_tempo.setToolTip("Durata della run")
        h.addWidget(self.l_tempo, 0, Qt.AlignVCenter)
        self.chips = {}
        for k, t in (("catture", "catture"), ("coppie", "coppie vive"), ("morti", "morti")):
            l = etichetta("", "chip")
            self.chips[k] = (l, t)
            h.addWidget(l, 0, Qt.AlignVCenter)
        h.addStretch()
        self.carte = [CartaGiocatore(), CartaGiocatore()]
        for c in self.carte:
            h.addWidget(c)
            c.hide()
        self.inizio = None
        self.fermo = False

    def aggiorna(self, st, io):
        stato = st["stato"]
        col = KO if stato == "game_over" else ORO if stato == "vinta" else OK
        testo = {"in_corso": "in corso", "game_over": "GAME OVER", "vinta": "VINTA!"}.get(stato, stato)
        self.l_run.setText(f"Run #{st['run']} · {testo}")
        self.l_run.setStyleSheet(f"background:{alfa(col, 0.14)};color:{col};")
        self.inizio = st.get("iniziata")
        self.fermo = stato != "in_corso"
        P = list(st["pokemon"].values())
        validi = [p for p in P if not p.get("irregolare")]
        coppie = sum(1 for r in st["percorsi"] if r["stato"] == "attiva")
        morti = sum(1 for p in P if p["stato"] == "morto")
        for k, v in (("catture", len(validi)), ("coppie", coppie), ("morti", morti)):
            l, t = self.chips[k]
            colore = KO if k == "morti" and v else "#e8e9f0"
            l.setText(f"<b style='color:{colore}'>{v}</b> <span style='color:{TENUE}'>{t}</span>")
        G = list(st["giocatori"])
        ordine = sorted(G, key=lambda g: g != io)
        for i, c in enumerate(self.carte):
            if i < len(ordine):
                c.imposta(ordine[i], st["giocatori"][ordine[i]], ordine[i] == io)
                c.show()
            else:
                c.hide()

    def tic(self, fine=None):
        if self.inizio and not self.fermo:
            self.l_tempo.setText(durata(time.time() - self.inizio))


# ----------------------------------------------------------------------------------------------
class Carta(QFrame):
    def __init__(self, titolo):
        super().__init__()
        self.setObjectName("carta")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(14, 10, 14, 12)
        self.v.setSpacing(4)
        self.v.addWidget(etichetta(titolo, "sezione"))


TIPI_OB = {"palestra": "Capopalestra", "rivale": "Rivale", "plasma": "Team Plasma", "lega": "Superquattro", "campione": "Campionessa"}


class CartaObiettivo(Carta):
    def __init__(self):
        super().__init__("PROSSIMO OBIETTIVO")
        self.l_nome = etichetta("—", "grande")
        self.l_tipo = etichetta("", "tenue")
        self.l_cap = etichetta("")
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setStyleSheet(f"QProgressBar::chunk{{background:{ACC};}}")
        self.l_prog = etichetta("", "tenue")
        self.l_altro = etichetta("", "tenue", a_capo=True)
        for w in (self.l_nome, self.l_tipo, self.l_cap, self.barra, self.l_prog, self.l_altro):
            self.v.addWidget(w)
        self.v.addStretch()

    def aggiorna(self, st, io):
        x = st["giocatori"].get(io) or {}
        o = x.get("prossimo")
        tot = len(st.get("obiettivi", []))
        fatti = len((st.get("fatti") or {}).get(io, {}))
        if o:
            self.l_nome.setText(o["nome"])
            self.l_tipo.setText(TIPI_OB.get(o["tipo"], o["tipo"]) + (f" · medaglia {o['medaglia']}" if o.get("medaglia") else ""))
        else:
            self.l_nome.setText("Tutto completato!")
            self.l_tipo.setText("")
        self.l_cap.setText(f"Livello massimo adesso: <b style='color:{WARN};font-size:12pt'>{x.get('cap', '?')}</b>")
        self.barra.setRange(0, max(1, tot))
        self.barra.setValue(fatti)
        self.l_prog.setText(f"{fatti} di {tot} obiettivi")
        altri = [(g, y) for g, y in st["giocatori"].items() if g != io]
        if altri:
            g, y = altri[0]
            po = y.get("prossimo")
            nf = len((st.get("fatti") or {}).get(g, {}))
            self.l_altro.setText(f"{g}: {po['nome'] if po else 'tutto completato'} · {nf}/{tot}")
        else:
            self.l_altro.setText("")


class CartaLuogo(Carta):
    def __init__(self):
        super().__init__("DOVE SEI")
        self.l_luogo = etichetta("—", "grande")
        self.l_io = etichetta("", a_capo=True)
        self.l_altro = etichetta("", a_capo=True)
        self.l_nota = etichetta("", "tenue", a_capo=True)
        for w in (self.l_luogo, self.l_io, self.l_altro, self.l_nota):
            self.v.addWidget(w)
        self.v.addStretch()

    @staticmethod
    def situazione(riga, g):
        """(testo, colore) dello stato di un giocatore in un luogo."""
        x = (riga or {}).get("giocatori", {}).get(g) or {}
        cat, inc = x.get("cattura"), x.get("incontro")
        if cat:
            stato = {"morto": "morto", "box": "nel box", "liberato": "liberato"}.get(cat["stato"], "in squadra")
            return f"Catturato: <b>{nome(cat)}</b> ({stato})", KO if cat["stato"] == "morto" else OK
        if inc:
            if inc["esito"] == "in_corso":
                return f"In lotta con <b>{inc.get('nome_specie', '?')}</b>", WARN
            if inc["esito"] == "fallito":
                return f"Incontro usato: fallito ({inc.get('nome_specie', '?')})", KO
            if inc["esito"] == "incerto":
                return f"Da confermare: {inc.get('nome_specie', '?')}", WARN
        return "Incontro disponibile", OK

    def aggiorna(self, st, io):
        x = st["giocatori"].get(io) or {}
        luogo = x.get("luogo_attuale")
        self.l_luogo.setText(x.get("zona_nome") or "—")
        riga = next((r for r in st["percorsi"] if r["luogo"] == luogo), None) if luogo else None
        if not luogo:
            self.l_io.setText(f"<span style='color:{TENUE}'>Il gioco non è ancora partito</span>")
            self.l_altro.setText("")
            self.l_nota.setText("")
            return
        t, c = self.situazione(riga, io)
        self.l_io.setText(f"<span style='color:{c}'>●</span> Tu: {t}")
        altri = [g for g in st["giocatori"] if g != io]
        nota = ""
        if altri:
            g = altri[0]
            t2, c2 = self.situazione(riga, g)
            self.l_altro.setText(f"<span style='color:{c2}'>●</span> {g}: {t2}")
            xa = ((riga or {}).get("giocatori", {}).get(g) or {})
            if xa.get("incontro") and xa["incontro"]["esito"] == "fallito":
                nota = f"{g} ha fallito qui: un'eventuale cattura tua andrà nel box."
        else:
            self.l_altro.setText("")
        self.l_nota.setText(nota)


# ----------------------------------------------------------------------------------------------
class MiniPokemon(QWidget):
    def __init__(self, p, sprite, allinea_destra=False):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        img = QLabel()
        img.setFixedSize(52, 52)
        img.setAlignment(Qt.AlignCenter)
        if p:
            pm = sprite.pixmap(p["specie"], 52)
            if pm:
                img.setPixmap(pm)
        col = QVBoxLayout()
        col.setSpacing(1)
        if p:
            stato = "" if p["stato"] == "squadra" else f" <span style='color:{KO if p['stato'] == 'morto' else WARN}'>· {p['stato']}</span>"
            col.addWidget(etichetta(f"<b>{nome(p)}</b> <span style='color:{TENUE}'>Lv.{p.get('livello') or '?'}</span>{stato}"))
            tipi = " ".join(f"<span style='color:{COLORI_TIPI.get(t, '#888')}'>{t}</span>" for t in p.get("tipi", []))
            col.addWidget(etichetta(f"<span style='color:{TENUE}'>{p.get('nome_specie', '')}</span> · {tipi}"))
            if p.get("ps_max"):
                b = QProgressBar()
                b.setTextVisible(False)
                b.setRange(0, p["ps_max"])
                b.setValue(p.get("ps") or 0)
                perc = (p.get("ps") or 0) / p["ps_max"]
                c = OK if perc > 0.5 else WARN if perc > 0.2 else KO
                b.setStyleSheet(f"QProgressBar::chunk{{background:{c};}}")
                b.setToolTip(f"PS {p.get('ps')}/{p['ps_max']}")
                col.addWidget(b)
        else:
            col.addWidget(etichetta("nessun partner", "tenue"))
        if allinea_destra:
            h.addLayout(col, 1)
            h.addWidget(img)
        else:
            h.addWidget(img)
            h.addLayout(col, 1)


COLORI_EVENTI = {"morte": KO, "gameover": KO, "legame": "#b9a8ff", "cattura": OK, "allarme": WARN,
                 "incontro": "#8fc7ff", "obiettivo": ORO}


class PannelloCoppie(QScrollArea):
    def __init__(self, sprite):
        super().__init__()
        self.sprite = sprite
        self.setWidgetResizable(True)
        w = QWidget()
        w.setObjectName("interno")
        self.v = QVBoxLayout(w)
        self.v.setContentsMargins(10, 10, 10, 10)
        self.v.setSpacing(8)
        self.setWidget(w)
        self._firma = None

    def forza(self):
        self._firma = None

    def _eventi(self, st):
        ev = st.get("eventi", [])[:6]
        if not ev:
            return
        self.v.addWidget(etichetta("ULTIMI EVENTI", "sezione"))
        for e in ev:
            ora = time.strftime("%H:%M", time.localtime(e["t"]))
            self.v.addWidget(etichetta(f"<span style='color:{TENUE}'>{ora}</span>&nbsp;&nbsp;<span style='color:{COLORI_EVENTI.get(e.get('tipo'), '#d8d9e3')}'>{e['testo']}</span>", a_capo=True))

    def aggiorna(self, st, io):
        P = st["pokemon"]
        firma = repr(sorted((k, p["stato"], p.get("ps"), p.get("livello"), p.get("specie"), p.get("partner")) for k, p in P.items())) + io + repr(st["eventi"][:6])
        if firma == self._firma:
            return
        self._firma = firma
        pulisci(self.v)
        G = list(st["giocatori"])
        altro = next((g for g in G if g != io), None)
        miei = sorted([p for p in P.values() if p["giocatore"] == io and p["stato"] == "squadra"], key=lambda p: p.get("slot", 0))
        self.v.addWidget(etichetta(f"LA TUA SQUADRA E I LEGAMI{' CON ' + altro.upper() if altro else ''}", "sezione"))
        usati = set()
        for p in miei:
            q = P.get(p.get("partner")) if p.get("partner") else None
            if q:
                usati.add(q["chiave"])
            riga = QFrame()
            riga.setObjectName("coppia")
            if q and q["stato"] != "squadra":
                riga.setProperty("allarme", True)
            h = QHBoxLayout(riga)
            h.setContentsMargins(10, 6, 10, 6)
            h.addWidget(MiniPokemon(p, self.sprite), 1)
            catena = etichetta("⛓", stile=f"color:{ACC if q else '#3a3e52'};font-size:16pt;")
            catena.setAlignment(Qt.AlignCenter)
            catena.setFixedWidth(30)
            h.addWidget(catena)
            h.addWidget(MiniPokemon(q, self.sprite, allinea_destra=True), 1)
            if q and q["stato"] == "box":
                riga.setToolTip(f"{nome(q)} è nel box di {altro}: dovresti mettere nel box anche {nome(p)}")
            self.v.addWidget(riga)
        if not miei:
            self.v.addWidget(etichetta("Ancora nessun Pokémon in squadra.", "tenue"))
        if altro:
            loro = [p for p in P.values() if p["giocatore"] == altro and p["stato"] == "squadra" and p["chiave"] not in usati]
            if loro:
                self.v.addWidget(etichetta(f"IN SQUADRA DA {altro.upper()} (IL LORO PARTNER NON È NELLA TUA SQUADRA)", "sezione"))
                gr = QGridLayout()
                for i, p in enumerate(sorted(loro, key=lambda p: p.get("slot", 0))):
                    gr.addWidget(MiniPokemon(p, self.sprite), i // 2, i % 2)
                self.v.addLayout(gr)
        self._eventi(st)
        box_vivi = [p for p in P.values() if p["giocatore"] == io and p["stato"] == "box"]
        if box_vivi:
            nomi = ", ".join(nome(p) for p in box_vivi[:12]) + ("…" if len(box_vivi) > 12 else "")
            self.v.addWidget(etichetta(f"NEL TUO BOX ({len(box_vivi)})", "sezione"))
            self.v.addWidget(etichetta(nomi, "tenue", a_capo=True))
        self.v.addStretch()


# ----------------------------------------------------------------------------------------------
class OspiteGioco(QWidget):
    """Riquadro nativo che ospita la finestra di BizHawk (le coordinate sono relative a questo riquadro)."""
    ridimensionato = Signal()

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:#0b0c10;")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.ridimensionato.emit()

    def dimensioni_fisiche(self):
        r = self.devicePixelRatioF()
        return int(self.width() * r), int(self.height() * r)
