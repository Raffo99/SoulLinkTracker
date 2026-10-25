"""Correzioni a mano dei Pokémon del tracker e controllo con quello che c'è davvero nel gioco
(utile se un salvataggio è andato perso, se hai ricaricato un backup o se qualcosa è stato letto male)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from . import dialoghi
from . import logica as L
from .riepilogo import nome
from .stile import ACC, COLORI_TIPI, KO, OK, ORO, TENUE, WARN, alfa

STATI = [("squadra", "In squadra"), ("box", "Nel box"), ("morto", "Morto"), ("liberato", "Liberato")]
COLORE_STATO = {"squadra": OK, "box": ACC, "morto": KO, "liberato": TENUE}


def _testa(sprite, p, lato=64):
    h = QHBoxLayout()
    h.setSpacing(14)
    img = QLabel()
    img.setFixedSize(lato, lato)
    img.setAlignment(Qt.AlignCenter)
    tc = COLORI_TIPI.get((p.get("tipi") or ["?"])[0], "#888888")
    img.setStyleSheet(f"background:{alfa(tc, 0.18)}; border-radius:{lato // 2}px;")
    pm = sprite.pixmap(p["specie"], lato - 6) if sprite else None
    if pm:
        img.setPixmap(pm)
    h.addWidget(img, 0, Qt.AlignTop)
    v = QVBoxLayout()
    v.setSpacing(3)
    c = COLORE_STATO.get(p["stato"], TENUE)
    t = QLabel(f"<b style='font-size:12.5pt'>{nome(p)}</b> <span style='color:{TENUE}'>{p.get('nome_specie', '')} · Lv.{p.get('livello') or '?'}</span>")
    v.addWidget(t)
    st = dict(STATI).get(p["stato"], p["stato"])
    v.addWidget(QLabel(f"di <b>{p['giocatore']}</b> · <span style='color:{c};font-weight:600'>{st}</span>"
                       + (f" <span style='color:{WARN}'>· fuori regola</span>" if p.get("irregolare") else "")
                       + (f"<br><span style='color:{TENUE}'>{p.get('causa')}</span>" if p.get("causa") else "")))
    v.addWidget(QLabel(f"<span style='color:{TENUE}'>Catturato a</span> {p.get('luogo_nome') or L.nome_luogo(p.get('luogo'))}"))
    h.addLayout(v, 1)
    return h


class DialogoPokemon(QDialog):
    def __init__(self, finestra, chiave):
        super().__init__(finestra)
        self.f = finestra
        st = finestra._ultimo_stato or {}
        self.P = st.get("pokemon") or {}
        self.k = chiave
        p = self.P.get(chiave)
        self.setWindowTitle("Modifica Pokémon")
        self.setMinimumWidth(500)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        if not p:
            v.addWidget(QLabel("Questo Pokémon non è più nel tracker."))
            return
        v.addLayout(_testa(finestra.sprite, p))
        legati = [self.P[x] for x in p.get("partners") or [] if x in self.P]
        if legati:
            v.addWidget(QLabel(f"<span style='color:{TENUE}'>Legato a:</span> " + ", ".join(
                f"{nome(q)} di {q['giocatore']} <span style='color:{COLORE_STATO.get(q['stato'], TENUE)}'>({dict(STATI).get(q['stato'], q['stato'])})</span>"
                for q in legati)))

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(10)
        self.c_stato = QComboBox()
        for k, t in STATI:
            self.c_stato.addItem(t, k)
        self.c_stato.setCurrentIndex([k for k, _ in STATI].index(p["stato"]) if p["stato"] in dict(STATI) else 0)
        b_stato = QPushButton("Cambia stato")
        b_stato.clicked.connect(self._stato)
        g.addWidget(QLabel("Stato"), 0, 0)
        g.addWidget(self.c_stato, 0, 1)
        g.addWidget(b_stato, 0, 2)
        self.c_luogo = QComboBox()
        luoghi = sorted(((k, n) for k, n in (L.LUOGHI or {}).items()), key=lambda x: x[1])
        for k, n in luoghi:
            self.c_luogo.addItem(n, k)
        i = self.c_luogo.findData(L._s(p.get("luogo")))
        if i < 0:
            self.c_luogo.insertItem(0, L.nome_luogo(p.get("luogo")), L._s(p.get("luogo")))
            i = 0
        self.c_luogo.setCurrentIndex(i)
        b_luogo = QPushButton("Cambia luogo")
        b_luogo.setToolTip("Il legame dipende dal luogo: cambiandolo, il Pokémon si lega a chi ha catturato lì")
        b_luogo.clicked.connect(self._luogo)
        g.addWidget(QLabel("Luogo"), 1, 0)
        g.addWidget(self.c_luogo, 1, 1)
        g.addWidget(b_luogo, 1, 2)
        g.setColumnStretch(1, 1)
        v.addLayout(g)

        r = QHBoxLayout()
        r.setSpacing(8)
        if p["stato"] == "morto":
            b = QPushButton("Riporta in vita" + (" con i suoi legati" if legati else ""))
            b.setObjectName("primario")
            b.setToolTip("Per esempio se hai ricaricato un salvataggio di prima della morte")
            b.clicked.connect(self._rianima)
            r.addWidget(b)
        if p.get("irregolare"):
            b = QPushButton("Conta come cattura valida")
            b.clicked.connect(lambda: self._fai({"azione": "stato_pokemon", "chiave": self.k, "stato": "valido"}))
            r.addWidget(b)
        r.addStretch()
        b_via = QPushButton("Togli dal tracker")
        b_via.setObjectName("pericolo")
        b_via.clicked.connect(self._togli)
        r.addWidget(b_via)
        v.addLayout(r)
        nota = QLabel("Se il gioco dice altro (per esempio il Pokémon è ancora in squadra), alla prossima lettura il tracker "
                      "si riallinea da solo.")
        nota.setObjectName("piccolo")
        nota.setWordWrap(True)
        v.addWidget(nota)
        chiudi = QPushButton("Chiudi")
        chiudi.clicked.connect(self.accept)
        rr = QHBoxLayout()
        rr.addStretch()
        rr.addWidget(chiudi)
        v.addLayout(rr)

    def _fai(self, dati):
        self.f._azione(dati)
        self.accept()

    def _stato(self):
        st = self.c_stato.currentData()
        p = self.P[self.k]
        if st == p["stato"]:
            return
        if st == "morto":
            if dialoghi.chiedi(self, f"Segnare {nome(p)} come morto?", "Muoiono anche i Pokémon legati a lui.",
                               si="Segna morto", no="Annulla", pericolo=True):
                self._fai({"azione": "stato_pokemon", "chiave": self.k, "stato": "morto"})
        elif p["stato"] == "morto":
            self._rianima()
        else:
            self._fai({"azione": "stato_pokemon", "chiave": self.k, "stato": st})

    def _rianima(self):
        p = self.P[self.k]
        if dialoghi.chiedi(self, f"Riportare in vita {nome(p)}?",
                           "Torna nel box insieme ai suoi legati morti. Usalo solo per correggere un errore "
                           "(per esempio un salvataggio ricaricato): resta scritto nel diario.", si="Riporta in vita", no="Annulla"):
            self._fai({"azione": "rianima", "chiave": self.k, "gruppo": True})

    def _luogo(self):
        nuovo = self.c_luogo.currentData()
        try:
            nuovo = int(nuovo)
        except (TypeError, ValueError):
            pass
        self._fai({"azione": "modifica_pokemon", "chiave": self.k, "luogo": nuovo})

    def _togli(self):
        p = self.P[self.k]
        if dialoghi.chiedi(self, f"Togliere {nome(p)} dal tracker?",
                           "Sparisce dalle coppie e dai percorsi. Se è ancora nel gioco, alla prossima lettura torna.",
                           si="Togli", no="Annulla", pericolo=True):
            self._fai({"azione": "elimina_pokemon", "chiave": self.k})


def differenze(st, io, squadra, box):
    """Confronto tra il tracker (solo i tuoi Pokémon) e la squadra/il PC letti dal gioco."""
    out = []
    P = st.get("pokemon") or {}
    nel_gioco = {}
    for m in squadra or []:
        if not m.get("uovo"):
            nel_gioco[m["pid"]] = ("squadra", m)
    for m in box or []:
        if not m.get("uovo") and m["pid"] not in nel_gioco:
            nel_gioco[m["pid"]] = ("box", m)
    for k, p in P.items():
        if p["giocatore"] != io:
            continue
        dove, m = nel_gioco.get(p["pid"], (None, None))
        if p["stato"] == "morto" and dove == "squadra" and (m.get("ps") or 0) > 0:
            out.append({"tipo": "vivo", "chiave": k, "p": p,
                        "testo": f"<b>{nome(p)}</b> è morto nel tracker ma nel gioco è in squadra con {m.get('ps')} PS"})
        elif p["stato"] == "liberato" and dove:
            out.append({"tipo": "ricomparso", "chiave": k, "p": p,
                        "testo": f"<b>{nome(p)}</b> risulta liberato ma nel gioco è {'in squadra' if dove == 'squadra' else 'nel PC'}"})
        elif p["stato"] in ("squadra", "box") and dove is None and squadra is not None:
            out.append({"tipo": "sparito", "chiave": k, "p": p,
                        "testo": f"<b>{nome(p)}</b> nel tracker è {'in squadra' if p['stato'] == 'squadra' else 'nel box'}, "
                                 f"ma nel gioco non lo trovo" + ("" if box else " (il PC non è stato letto)")})
    return out


class DialogoControllo(QDialog):
    def __init__(self, finestra, automatico=False):
        super().__init__(finestra)
        self.f = finestra
        self.setWindowTitle("Controllo con il gioco")
        self.resize(660, 440)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        t = QLabel("Il tracker e il gioco coincidono?")
        t.setObjectName("grande")
        v.addWidget(t)
        s = QLabel(("Ho trovato delle differenze tra il tracker e il gioco (forse un salvataggio ricaricato). "
                    if automatico else "") + "Confronto i tuoi Pokémon nel tracker con la squadra e il PC letti adesso "
                   "dalla memoria del gioco.")
        s.setWordWrap(True)
        s.setObjectName("tenue")
        v.addWidget(s)
        self.area = QVBoxLayout()
        self.area.setSpacing(8)
        cont = QWidget()
        cont.setObjectName("interno")
        cont.setLayout(self.area)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(cont)
        v.addWidget(sc, 1)
        r = QHBoxLayout()
        r.addStretch()
        b = QPushButton("Chiudi")
        b.setObjectName("primario")
        b.clicked.connect(self.accept)
        r.addWidget(b)
        v.addLayout(r)
        self._riempi()

    def _riempi(self):
        while self.area.count():
            it = self.area.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        f = self.f
        st = f._ultimo_stato or {}
        if not f._squadra_gioco:
            self.area.addWidget(QLabel(f"<span style='color:{TENUE}'>Avvia il gioco: mi serve la squadra letta dalla memoria.</span>"))
            self.area.addStretch()
            return
        diffs = differenze(st, f.cfg["giocatore"], f._squadra_gioco, f._box_gioco)
        if not diffs:
            l = QLabel(f"<span style='color:{OK};font-weight:600'>✓ Tutto torna:</span> il tracker coincide con la squadra"
                       + (" e il PC" if f._box_gioco else "") + " del gioco.")
            l.setWordWrap(True)
            self.area.addWidget(l)
        for d in diffs:
            riga = QFrame()
            riga.setObjectName("coppia")
            h = QHBoxLayout(riga)
            h.setContentsMargins(14, 10, 14, 10)
            l = QLabel(d["testo"])
            l.setWordWrap(True)
            h.addWidget(l, 1)
            if d["tipo"] == "vivo":
                b = QPushButton("Riporta in vita")
                b.setObjectName("primario")
                b.clicked.connect(lambda _=False, k=d["chiave"]: self._fai({"azione": "rianima", "chiave": k, "gruppo": True}))
                h.addWidget(b)
                b2 = QPushButton("Resta morto")
                b2.setToolTip("Il Pokémon va messo nel box: per la regola è morto")
                b2.clicked.connect(lambda _=False, r=riga: r.hide())
                h.addWidget(b2)
            b3 = QPushButton("Modifica…")
            b3.clicked.connect(lambda _=False, k=d["chiave"]: (DialogoPokemon(self.f, k).exec(), self._riempi()))
            h.addWidget(b3)
            self.area.addWidget(riga)
        self.area.addStretch()

    def _fai(self, dati):
        self.f._azione(dati)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, self._riempi)
