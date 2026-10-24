"""Pannelli laterali: squadre, percorsi, obiettivi, cimitero, diario, diagnostica."""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar,
                               QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .stile import ACC, COLORI_TIPI, KO, OK, ORO, TENUE, WARN


def ora(t):
    return datetime.fromtimestamp(t).strftime("%H:%M") if t else ""


def nome(p):
    return p.get("soprannome") or p.get("nome_specie") or "?"


def pulisci(layout):
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w:
            w.deleteLater()
        elif it.layout():
            pulisci(it.layout())


# ----------------------------------------------------------------------
class CartaPokemon(QFrame):
    def __init__(self, p, partner, sprite):
        super().__init__()
        self.setObjectName("pk")
        self.setProperty("ko", p.get("ps") == 0)
        self.setFixedWidth(150)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 8)
        v.setSpacing(2)
        top = QHBoxLayout()
        top.addStretch()
        lv = QLabel(f"Lv.{p.get('livello', '?')}")
        lv.setObjectName("tenue")
        top.addWidget(lv)
        v.addLayout(top)
        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        img.setFixedHeight(64)
        pm = sprite.pixmap(p["specie"])
        if pm:
            img.setPixmap(pm)
        v.addWidget(img)
        n = QLabel(f"<b>{nome(p)}</b>")
        n.setAlignment(Qt.AlignCenter)
        v.addWidget(n)
        s = QLabel(f"{p.get('nome_specie', '')} · {p.get('luogo_nome', '')}")
        s.setObjectName("tenue")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        v.addWidget(s)
        hp = QProgressBar()
        hp.setTextVisible(False)
        mx = p.get("ps_max") or 1
        hp.setRange(0, mx)
        hp.setValue(p.get("ps") or 0)
        perc = (p.get("ps") or 0) / mx
        col = OK if perc > 0.5 else WARN if perc > 0.2 else KO
        hp.setStyleSheet(f"QProgressBar::chunk{{background:{col};}}")
        v.addWidget(hp)
        tipi = QHBoxLayout()
        tipi.addStretch()
        for t in p.get("tipi", []):
            l = QLabel(t)
            l.setStyleSheet(f"background:{COLORI_TIPI.get(t, '#666')};color:white;border-radius:8px;padding:1px 7px;font-size:8pt;font-weight:600;")
            tipi.addWidget(l)
        tipi.addStretch()
        v.addLayout(tipi)
        pt = QLabel(f"⛓ {nome(partner)} ({partner['giocatore']})" if partner else "nessun partner")
        pt.setObjectName("tenue")
        pt.setAlignment(Qt.AlignCenter)
        pt.setWordWrap(True)
        v.addWidget(pt)


class PannelloSquadre(QScrollArea):
    def __init__(self, sprite):
        super().__init__()
        self.sprite = sprite
        self.setWidgetResizable(True)
        w = QWidget()
        w.setObjectName("interno")
        self.v = QVBoxLayout(w)
        self.v.setSpacing(10)
        self.setWidget(w)
        self._firma = None

    def aggiorna(self, st):
        P = st["pokemon"]
        firma = repr([(k, p["stato"], p.get("ps"), p.get("livello"), p.get("specie"), p.get("partner")) for k, p in sorted(P.items())]) + repr(list(st["giocatori"]))
        if firma == self._firma:
            return
        self._firma = firma
        pulisci(self.v)
        for g in st["giocatori"]:
            sq = sorted([p for p in P.values() if p["giocatore"] == g and p["stato"] == "squadra"], key=lambda p: p.get("slot", 0))
            nbox = sum(1 for p in P.values() if p["giocatore"] == g and p["stato"] == "box")
            box = QGroupBox(f"SQUADRA DI {g.upper()} · {nbox} NEL BOX")
            gr = QGridLayout(box)
            gr.setSpacing(8)
            gr.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            for i, p in enumerate(sq):
                partner = P.get(p.get("partner")) if p.get("partner") else None
                gr.addWidget(CartaPokemon(p, partner, self.sprite), i // 3, i % 3)
            if not sq:
                l = QLabel("Nessun Pokémon in squadra")
                l.setObjectName("tenue")
                gr.addWidget(l, 0, 0)
            self.v.addWidget(box)
        self.v.addStretch()

    def forza(self):
        self._firma = None


# ----------------------------------------------------------------------
ETICHETTE_ESITO = {"catturato": "catturato", "fallito": "fallito", "incerto": "da confermare", "in_corso": "in lotta"}
COLORI_ESITO = {"catturato": OK, "fallito": KO, "incerto": WARN, "in_corso": WARN}
STATI_COPPIA = {"attiva": ("Legati", OK), "morta": ("Morti", KO), "rotta": ("Incontro fallito", WARN),
                "in_attesa": ("In attesa", TENUE), "in_lotta": ("In lotta…", TENUE)}


class PannelloPercorsi(QTableWidget):
    def __init__(self, azione, sprite):
        super().__init__()
        self.azione, self.sprite = azione, sprite
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setIconSize(self.iconSize().expandedTo(self.iconSize().__class__(40, 40)))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self._righe = []
        self._G = []
        self._firma = None

    def aggiorna(self, st):
        G = list(st["giocatori"])
        firma = repr(st["percorsi"]) + repr(G)
        if firma == self._firma:
            return
        self._firma = firma
        self._G, self._righe = G, st["percorsi"]
        self.setColumnCount(len(G) + 2)
        self.setHorizontalHeaderLabels(["Luogo"] + G + ["Coppia"])
        self.setRowCount(len(self._righe))
        for r, riga in enumerate(self._righe):
            self.setItem(r, 0, QTableWidgetItem(riga["luogo_nome"]))
            for c, g in enumerate(G):
                x = riga["giocatori"].get(g, {})
                cat, inc = x.get("cattura"), x.get("incontro")
                righe_txt, specie, colore = [], None, None
                if cat:
                    specie = cat["specie"]
                    righe_txt.append(f"{nome(cat)}  [{cat['stato']}]" + ("  fuori regola" if cat.get("irregolare") else ""))
                if inc and not (cat and inc.get("esito") == "catturato" and inc.get("pid") == cat.get("pid")):
                    specie = specie or inc.get("specie")
                    righe_txt.append(f"incontro: {inc.get('nome_specie', '—')} · {ETICHETTE_ESITO.get(inc['esito'], inc['esito'])}")
                    colore = COLORI_ESITO.get(inc["esito"])
                if cat and cat["stato"] == "morto":
                    colore = KO
                it = QTableWidgetItem("\n".join(righe_txt) or "—")
                if specie:
                    pm = self.sprite.pixmap(specie, 40)
                    if pm:
                        it.setIcon(QIcon(pm))
                if colore:
                    it.setForeground(QColor(colore))
                self.setItem(r, c + 1, it)
            testo, col = STATI_COPPIA.get(riga["stato"], (riga["stato"], TENUE))
            it = QTableWidgetItem(testo)
            it.setForeground(QColor(col))
            self.setItem(r, len(G) + 1, it)
        self.resizeRowsToContents()
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in range(1, len(G) + 1):
            h.setSectionResizeMode(c, QHeaderView.Stretch)
        h.setSectionResizeMode(len(G) + 1, QHeaderView.ResizeToContents)

    def forza(self):
        self._firma = None

    def _menu(self, pos):
        idx = self.indexAt(pos)
        if not idx.isValid() or idx.column() < 1 or idx.column() > len(self._G):
            return
        riga = self._righe[idx.row()]
        g = self._G[idx.column() - 1]
        x = riga["giocatori"].get(g, {})
        m = QMenu(self)
        cat, inc = x.get("cattura"), x.get("incontro")
        if cat:
            m.addSection(f"{nome(cat)} ({g})")
            for st in ("squadra", "box", "morto", "liberato"):
                m.addAction(f"Segna come {st}", lambda st=st: self._conferma(f"Segnare {nome(cat)} come {st}?",
                            {"azione": "stato_pokemon", "chiave": cat["chiave"], "stato": st}))
            if cat.get("irregolare"):
                m.addAction("Conta come cattura valida", lambda: self.azione({"azione": "stato_pokemon", "chiave": cat["chiave"], "stato": "valido"}))
        if inc:
            m.addSection(f"Incontro: {inc.get('nome_specie', '—')}")
            if inc["esito"] in ("incerto", "in_corso", "fallito", "catturato"):
                m.addAction("È stato catturato", lambda: self.azione({"azione": "esito_incontro", "id": inc["id"], "esito": "catturato"}))
                m.addAction("È fallito", lambda: self.azione({"azione": "esito_incontro", "id": inc["id"], "esito": "fallito"}))
            m.addAction("Annulla questo incontro", lambda: self._conferma("Annullare l'incontro?", {"azione": "esito_incontro", "id": inc["id"], "esito": "annullato"}))
        if not cat and not inc:
            m.addAction(f"Segna incontro fallito per {g}", lambda: self._conferma(
                f"Segnare fallito l'incontro di {g} a {riga['luogo_nome']}?", {"azione": "fallito", "giocatore": g, "luogo": riga["luogo"]}))
        m.exec(self.viewport().mapToGlobal(pos))

    def _conferma(self, domanda, dati):
        if QMessageBox.question(self, "Soul Link", domanda) == QMessageBox.Yes:
            self.azione(dati)


# ----------------------------------------------------------------------
TIPI_OB = {"palestra": "palestra", "rivale": "rivale", "plasma": "team plasma", "lega": "superquattro", "campione": "campionessa"}


class PannelloObiettivi(QTableWidget):
    def __init__(self, azione):
        super().__init__()
        self.azione = azione
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.cellDoubleClicked.connect(self._doppio)
        self._ob, self._G, self._fatti, self._firma = [], [], {}, None

    def aggiorna(self, st):
        firma = repr(st.get("fatti")) + repr(list(st["giocatori"]))
        if firma == self._firma:
            return
        self._firma = firma
        self._ob, self._G, self._fatti = st.get("obiettivi", []), list(st["giocatori"]), st.get("fatti", {})
        self.setColumnCount(len(self._G) + 1)
        intest = ["Obiettivo"]
        for g in self._G:
            n = len(self._fatti.get(g, {}))
            intest.append(f"{g}  {n}/{len(self._ob)}")
        self.setHorizontalHeaderLabels(intest)
        self.setRowCount(len(self._ob))
        for r, o in enumerate(self._ob):
            it = QTableWidgetItem(f"{o['nome']}   ·  {TIPI_OB.get(o['tipo'], o['tipo'])}")
            self.setItem(r, 0, it)
            for c, g in enumerate(self._G):
                f = self._fatti.get(g, {}).get(o["id"])
                it = QTableWidgetItem(f"✓  {ora(f['t'])}" if f else "—")
                it.setForeground(QColor(OK if f else TENUE))
                it.setTextAlignment(Qt.AlignCenter)
                it.setToolTip("Doppio clic per correggere a mano")
                self.setItem(r, c + 1, it)
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, len(self._G) + 1):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)

    def _doppio(self, r, c):
        if c < 1:
            return
        o, g = self._ob[r], self._G[c - 1]
        fatto = bool(self._fatti.get(g, {}).get(o["id"]))
        if QMessageBox.question(self, "Obiettivi", f"{'Annullare' if fatto else 'Segnare'} «{o['nome']}» per {g}?") == QMessageBox.Yes:
            self.azione({"azione": "obiettivo", "id": o["id"], "giocatore": g, "valore": not fatto})


# ----------------------------------------------------------------------
class PannelloCimitero(QListWidget):
    def __init__(self, sprite):
        super().__init__()
        self.sprite = sprite
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(self.iconSize().__class__(56, 56))
        self.setResizeMode(QListWidget.Adjust)
        self.setSpacing(10)
        self.setWordWrap(True)
        self._firma = None

    def aggiorna(self, st):
        morti = sorted([p for p in st["pokemon"].values() if p["stato"] == "morto"], key=lambda p: p.get("morto") or 0)
        firma = repr([(p["chiave"], p.get("causa")) for p in morti])
        if firma == self._firma:
            return
        self._firma = firma
        self.clear()
        for p in morti:
            it = QListWidgetItem(f"{nome(p)}\n{p['giocatore']} · Lv.{p.get('livello', '?')}")
            it.setToolTip(p.get("causa", ""))
            pm = self.sprite.pixmap(p["specie"], 56)
            if pm:
                it.setIcon(QIcon(pm))
            it.setForeground(QColor(TENUE))
            self.addItem(it)
        if not morti:
            self.addItem(QListWidgetItem("Nessuna vittima. Per ora."))

    def forza(self):
        self._firma = None


COLORI_EVENTI = {"morte": KO, "gameover": KO, "legame": "#b9a8ff", "cattura": OK, "allarme": WARN,
                 "incontro": "#8fc7ff", "obiettivo": ORO}


class PannelloDiario(QListWidget):
    def __init__(self):
        super().__init__()
        self._firma = None

    def aggiorna(self, st):
        ev = st.get("eventi", [])
        firma = repr(ev[:3]) + str(len(ev))
        if firma == self._firma:
            return
        self._firma = firma
        self.clear()
        for e in ev:
            it = QListWidgetItem(f"{ora(e['t'])}   {e['testo']}")
            it.setForeground(QColor(COLORI_EVENTI.get(e.get("tipo"), "#d8d9e3")))
            self.addItem(it)


class PannelloDiagnostica(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        self.locale = {}

    def aggiorna(self, st, ultimo_payload=None):
        righe = ["== Questa app =="]
        righe += [f"{k}: {v}" for k, v in self.locale.items()]
        for g, x in st.get("giocatori", {}).items():
            d = x.get("diagnostica")
            righe.append("")
            righe.append(f"== {g} ({'online' if x.get('online') else 'offline'}) ==")
            righe.append(f"zona: {x.get('zona_nome')}   medaglie: {x.get('medaglie')}   cap: {x.get('cap')}")
            if d:
                for k in ("rom", "rom_nome", "fonte", "base", "squadra", "zona", "zona_padre", "stato_lotta", "in_lotta",
                          "lotta_calibrata", "lotta_candidati", "lotte_viste", "ultimo_nemico", "ultimo_allenatore",
                          "medaglie", "pc", "pc_calibrato", "run_rom"):
                    v = d.get(k)
                    if k in ("base", "lotta_calibrata") and isinstance(v, int):
                        v = hex(v)
                    righe.append(f"  {k}: {v}")
            else:
                righe.append("  (attiva 'Diagnostica' nelle impostazioni per vedere i dati letti dalla memoria)")
        testo = "\n".join(righe)
        if testo != self.toPlainText():
            self.setPlainText(testo)
