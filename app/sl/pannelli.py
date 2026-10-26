"""Pannelli laterali: squadre, percorsi, obiettivi, cimitero, diario, diagnostica."""
import time
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

from . import dialoghi
from .stile import ACC, COLORI_TIPI, KO, OK, ORO, TENUE, WARN, colori_giocatori


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
ETICHETTE_ESITO = {"catturato": "catturato", "fallito": "fallito", "incerto": "da confermare?", "in_corso": "in lotta"}
COLORI_ESITO = {"catturato": OK, "fallito": KO, "incerto": WARN, "in_corso": WARN}
STATI_COPPIA = {"attiva": ("Legati", OK), "morta": ("Morti", KO), "rotta": ("Fallito", WARN),
                "in_attesa": ("In attesa", TENUE), "in_lotta": ("In lotta…", TENUE)}
STATI_BREVI = {"squadra": "vivo", "box": "nel box", "morto": "morto", "liberato": "liberato"}


def corto(t, n=11):
    return t if len(t) <= n else t[:n - 1] + "…"


class PannelloPercorsi(QTableWidget):
    def __init__(self, azione, sprite):
        super().__init__()
        self.apri_pokemon = None
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setFrameShape(QFrame.NoFrame)
        self.verticalHeader().setDefaultSectionSize(40)
        self.horizontalHeader().setHighlightSections(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.azione, self.sprite = azione, sprite
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setIconSize(self.iconSize().expandedTo(self.iconSize().__class__(32, 32)))
        self.setTextElideMode(Qt.ElideNone)
        self.setWordWrap(False)
        self.setStyleSheet("QTableWidget::item { padding: 4px 4px; }")
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
        colori = colori_giocatori(st)
        for i, nome_c in enumerate(["Luogo"] + G + ["Coppia"]):
            hi = self.horizontalHeaderItem(i)
            if hi:
                hi.setForeground(QColor(colori.get(nome_c, "#7c8199")))
        self.setRowCount(len(self._righe))
        for r, riga in enumerate(self._righe):
            self.setItem(r, 0, QTableWidgetItem(riga["luogo_nome"]))
            for c, g in enumerate(G):
                x = riga["giocatori"].get(g, {})
                cat, inc = x.get("cattura"), x.get("incontro")
                righe_txt, dettagli, specie, colore = [], [], None, None
                if cat:
                    specie = cat["specie"]
                    righe_txt += [corto(nome(cat)), "fuori regola" if cat.get("irregolare") else STATI_BREVI.get(cat["stato"], cat["stato"])]
                    dettagli.append(f"{nome(cat)} ({cat.get('nome_specie', '')}) · {cat['stato']}" + (" · fuori regola" if cat.get("irregolare") else ""))
                    colore = OK if cat["stato"] == "squadra" else None
                if inc and not (cat and inc.get("esito") == "catturato" and inc.get("pid") == cat.get("pid")):
                    specie = specie or inc.get("specie")
                    esito = ETICHETTE_ESITO.get(inc["esito"], inc["esito"])
                    if not cat:
                        righe_txt += [corto(inc.get("nome_specie", "—")), esito]
                    dettagli.append(f"primo incontro: {inc.get('nome_specie', '—')} · {esito}")
                    colore = COLORI_ESITO.get(inc["esito"])
                if cat and cat["stato"] == "morto":
                    colore = KO
                it = QTableWidgetItem("\n".join(righe_txt) or "—")
                it.setToolTip("\n".join(dettagli))
                if specie:
                    pm = self.sprite.pixmap(specie, 32)
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
        for r in range(self.rowCount()):
            self.setRowHeight(r, max(48, self.rowHeight(r) + 12))
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in range(1, len(G) + 1):
            h.setSectionResizeMode(c, QHeaderView.Stretch)
        h.setSectionResizeMode(len(G) + 1, QHeaderView.ResizeToContents)
        h.setMinimumSectionSize(60)

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
            if self.apri_pokemon:
                m.addAction("Modifica…", lambda: self.apri_pokemon(cat["chiave"]))
            for st, t in (("squadra", "in squadra"), ("box", "nel box"), ("morto", "morto"), ("liberato", "liberato")):
                m.addAction(f"Segna come {t}", lambda st=st, t=t: self._conferma(f"Segnare {nome(cat)} come «{t}»?",
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
        if dialoghi.chiedi(self, domanda, "", si="Conferma", no="Annulla"):
            self.azione(dati)


# ----------------------------------------------------------------------
TIPI_OB = {"palestra": "capopalestra", "rivale": "rivale", "plasma": "team plasma", "lega": "superquattro",
           "campione": "campionessa", "sfida": "sfida"}


def durata_breve(sec):
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    return f"{h}:{r // 60:02d}" if h else f"{r // 60}m"


class PannelloObiettivi(QWidget):
    """Gli obiettivi veri del gioco, in ordine di storia, con chi li ha già fatti (doppio clic su una casella per
    segnarlo o toglierlo a mano). La mappa di Unima si apre in una finestra a parte."""

    def __init__(self, azione, io, apri_mappa):
        super().__init__()
        self.azione, self.io = azione, io
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(6)
        testa = QHBoxLayout()
        testa.setContentsMargins(10, 0, 10, 0)
        self.l_info = QLabel("")
        self.l_info.setWordWrap(True)
        testa.addWidget(self.l_info, 1)
        b = QPushButton("Apri la mappa di Unima")
        b.setToolTip("Dove sono gli obiettivi e dove siete adesso")
        b.clicked.connect(apri_mappa)
        testa.addWidget(b)
        v.addLayout(testa)
        self.lista = QTreeWidget()
        self.lista.setRootIsDecorated(False)
        self.lista.setFrameShape(QFrame.NoFrame)
        self.lista.setFocusPolicy(Qt.NoFocus)
        self.lista.itemDoubleClicked.connect(self._doppio)
        v.addWidget(self.lista, 1)
        self._firma = None
        self._G, self._fatti = [], {}

    def aggiorna(self, st):
        io = self.io()
        po = ((st["giocatori"].get(io) or {}).get("prossimo") or {})
        nf = len((st.get("fatti") or {}).get(io, {}))
        self.l_info.setText(f"<span style='color:{TENUE}'>Obiettivi del gioco in ordine di storia · tu ne hai fatti</span> "
                            f"<b>{nf}/{len(st.get('obiettivi') or [])}</b>"
                            + (f" <span style='color:{TENUE}'>· prossimo:</span> <b style='color:#b9a8ff'>{po['nome']}</b>" if po else ""))
        firma = repr(st.get("fatti")) + repr(list(st["giocatori"])) + repr([o["id"] for o in st.get("obiettivi") or []]) + repr(po.get("id"))
        if firma == self._firma:
            return
        self._firma = firma
        self._G, self._fatti = list(st["giocatori"]), st.get("fatti", {})
        inizio = st.get("iniziata") or 0
        L = self.lista
        L.clear()
        L.setColumnCount(len(self._G) + 2)
        L.setHeaderLabels(["Obiettivo", "Dove"] + self._G)
        colori = colori_giocatori(st)
        for i, g in enumerate(self._G):
            L.headerItem().setForeground(i + 2, QColor(colori.get(g, ACC)))
        h = L.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, len(self._G) + 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        from . import logica as LG
        for o in st.get("obiettivi") or []:
            tipo = TIPI_OB.get(o["tipo"], o["tipo"]) + (f" {o['medaglia']}" if o.get("medaglia") else "")
            it = QTreeWidgetItem([f"{o['nome']}   ·  {tipo}", LG.nome_luogo(o["luogo"]) if o.get("luogo") is not None else ""])
            it.setData(0, Qt.UserRole, o["id"])
            it.setForeground(1, QColor(TENUE))
            for c, g in enumerate(self._G, 2):
                x = self._fatti.get(g, {}).get(o["id"])
                it.setText(c, f"✓ +{durata_breve(x['t'] - inizio)}" if x else "—")
                it.setForeground(c, QColor(OK if x else TENUE))
                it.setTextAlignment(c, Qt.AlignCenter)
                it.setToolTip(c, f"Fatto dopo {durata_breve(x['t'] - inizio)} dall'inizio della run" if x else "Doppio clic per segnarlo a mano")
            if po and o["id"] == po.get("id"):
                f = it.font(0)
                f.setBold(True)
                it.setFont(0, f)
                it.setForeground(0, QColor("#b9a8ff"))
            L.addTopLevelItem(it)
        L.setToolTip("Doppio clic su una casella per segnare o togliere un obiettivo a mano")

    def _doppio(self, it, col):
        vid = it.data(0, Qt.UserRole)
        if col < 2 or not vid:
            return
        g = self._G[col - 2]
        fatto = bool(self._fatti.get(g, {}).get(vid))
        nome_v = it.text(0).split("   ·")[0]
        if dialoghi.chiedi(self, f"{'Annullare' if fatto else 'Segnare come fatto'} «{nome_v}» per {g}?", "",
                           si="Annulla obiettivo" if fatto else "Segna fatto", no="Lascia stare"):
            self.azione({"azione": "obiettivo", "id": vid, "giocatore": g, "valore": not fatto})


# ----------------------------------------------------------------------
class PannelloStatistiche(QScrollArea):
    """Numeri della run per ogni giocatore e record tra una run e l'altra."""

    def __init__(self, sprite):
        super().__init__()
        self.sprite = sprite
        self.setWidgetResizable(True)
        w = QWidget()
        w.setObjectName("interno")
        self.v = QVBoxLayout(w)
        self.v.setContentsMargins(14, 10, 14, 10)
        self.v.setSpacing(10)
        self.setWidget(w)
        self._firma = None

    def aggiorna(self, st):
        P = st["pokemon"]
        firma = repr(sorted((k, p["stato"], p.get("livello")) for k, p in P.items())) + repr(st["storico"]) + repr(st.get("fatti")) + repr(st.get("traguardi"))
        if firma == self._firma:
            return
        self._firma = firma
        pulisci(self.v)
        tot_ob = len(st.get("voci") or st.get("obiettivi") or [])
        self.v.addWidget(QLabel("<span style='color:#9498ad;font-size:8pt;font-weight:700;letter-spacing:1px'>QUESTA RUN</span>"))
        griglia = QGridLayout()
        griglia.setHorizontalSpacing(18)
        griglia.setVerticalSpacing(8)
        intest = ["", "Catture", "Persi", "Vivi", "Obiettivi", "Il più forte"]
        for c, t in enumerate(intest):
            l = QLabel(f"<span style='color:{TENUE};font-size:8.5pt;font-weight:600'>{t}</span>")
            griglia.addWidget(l, 0, c)
        for r, (g, x) in enumerate(st["giocatori"].items(), 1):
            suoi = [p for p in P.values() if p["giocatore"] == g and not p.get("irregolare")]
            morti = sum(1 for p in suoi if p["stato"] == "morto")
            vivi = sum(1 for p in suoi if p["stato"] in ("squadra", "box"))
            forte = max((p for p in suoi if p["stato"] in ("squadra", "box")), key=lambda p: p.get("livello") or 0, default=None)
            n_ob = len((st.get("fatti") or {}).get(g, {}))
            n_tr = len((st.get("traguardi") or {}).get(g, {}))
            celle = [f"<span style='color:{colori_giocatori(st).get(g, ACC)}'>●</span>&nbsp; <b>{g}</b>", str(len(suoi)), f"<span style='color:{KO if morti else TENUE}'>{morti}</span>", str(vivi),
                     f"{n_ob}/{tot_ob}",
                     f"{nome(forte)} Lv.{forte.get('livello')}" if forte else "—"]
            for c, t in enumerate(celle):
                griglia.addWidget(QLabel(t), r, c)
        self.v.addLayout(griglia)

        storico = st.get("storico") or []
        self.v.addSpacing(10)
        self.v.addWidget(QLabel("<span style='color:#9498ad;font-size:8pt;font-weight:700;letter-spacing:1px'>RECORD</span>"))
        if storico:
            vinte = [r for r in storico if r.get("vinta")]
            migliore = max(storico, key=lambda r: (r.get("vinta", False), r.get("medaglie", 0), -(r["fine"] - r["inizio"])))
            lunga = max(storico, key=lambda r: r["fine"] - r["inizio"])
            durate = [r["fine"] - r["inizio"] for r in storico]
            righe = [
                f"Run giocate: <b>{len(storico)}</b>   ·   vinte: <b style='color:{ORO}'>{len(vinte)}</b>",
                f"Run migliore: <b>#{migliore['run']}</b> con {migliore.get('medaglie', 0)} medaglie" + (" (vinta!)" if migliore.get("vinta") else ""),
                f"Run più lunga: <b>#{lunga['run']}</b>, {durata_breve(lunga['fine'] - lunga['inizio'])}",
                f"Durata media: <b>{durata_breve(sum(durate) / len(durate))}</b>   ·   Pokémon persi in tutto: <b style='color:{KO}'>{sum(r.get('morti', 0) for r in storico)}</b>",
            ]
            for t in righe:
                self.v.addWidget(QLabel(t))
            self.v.addSpacing(10)
            self.v.addWidget(QLabel("<span style='color:#9498ad;font-size:8pt;font-weight:700;letter-spacing:1px'>RUN PRECEDENTI</span>"))
            for r in reversed(storico[-15:]):
                col = ORO if r.get("vinta") else TENUE
                l = QLabel(f"<b>Run #{r['run']}</b>{' ★' if r.get('vinta') else ''}  ·  {r.get('medaglie', 0)} medaglie  ·  "
                           f"{r.get('catture', 0)} catture  ·  {r.get('morti', 0)} persi  ·  {durata_breve(r['tempo'] if r.get('tempo') is not None else r['fine'] - r['inizio'])}"
                           f"<br><span style='color:{col}'>{r['motivo']}</span>")
                l.setWordWrap(True)
                self.v.addWidget(l)
        else:
            l = QLabel("Ancora nessuna run conclusa: i record compaiono dopo il primo game over (o la prima vittoria).")
            l.setObjectName("tenue")
            l.setWordWrap(True)
            self.v.addWidget(l)
        self.v.addStretch()


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
        if not morti:
            it = QListWidgetItem("Ancora nessun caduto. Che resti così!")
            it.setForeground(QColor(TENUE))
            it.setFlags(Qt.NoItemFlags)
            self.addItem(it)
        for p in morti:
            it = QListWidgetItem(f"{nome(p)}\n{p['giocatore']} · Lv.{p.get('livello', '?')}")
            it.setData(Qt.UserRole, p.get("chiave"))
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
                 "incontro": "#8fc7ff", "obiettivo": ORO, "traguardo": ORO}


class PannelloDiario(QListWidget):
    def __init__(self):
        super().__init__()
        self.setWordWrap(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSpacing(1)
        self._firma = None

    def aggiorna(self, st):
        ev = st.get("eventi", [])
        firma = repr(ev[:3]) + str(len(ev))
        if firma == self._firma:
            return
        self._firma = firma
        self.clear()
        for e in ev:
            it = QListWidgetItem(f"{ora(e['t'])}    {e['testo']}")
            it.setForeground(QColor(COLORI_EVENTI.get(e.get("tipo"), "#d8d9e3")))
            it.setToolTip(time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(e["t"])))
            self.addItem(it)
        if not ev:
            it = QListWidgetItem("Il diario si riempie da solo durante la partita: catture, legami, lotte e morti.")
            it.setForeground(QColor(TENUE))
            it.setFlags(Qt.NoItemFlags)
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
