"""Scheda di un Pokémon (tuo o di un amico): statistiche, natura, abilità, mosse ed esperienza.
Si apre cliccando un Pokémon nelle Coppie e si aggiorna da sola mentre si gioca."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
                               QWidget)

from . import logica as L
from .correzioni import COLORE_STATO, STATI
from .lotta import NOMI_STAT_LUNGHI, html_impara, mossa, natura, pillola_tipo, stato_alterato
from .riepilogo import nome
from .stile import ACC, COLORI_TIPI, KO, OK, ORO, SPENTO, TENUE, TESTO, WARN, alfa

ORDINE_STAT = [0, 1, 3, 4, 2]          # come nel gioco: Attacco, Difesa, Att. Sp., Dif. Sp., Velocità


def dettagli_di(finestra, p):
    """Dati completi (mosse, statistiche…) del Pokémon p del tracker, se è in squadra: i miei li leggo dal gioco,
    quelli degli amici arrivano dalla loro app."""
    if not p:
        return None
    io = finestra.cfg["giocatore"]
    if p["giocatore"] == io:                         # la versione pubblicata ha anche le mosse da imparare
        lista = finestra.sincro._presenza.get("squadra") or finestra._squadra_gioco
    else:
        x = ((finestra._ultimo_stato or {}).get("giocatori") or {}).get(p["giocatore"]) or {}
        lista = x.get("squadra_dett") or []
    return next((m for m in lista or [] if m.get("pid") == p.get("pid")), None)


def _svuota(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget():
            it.widget().hide()
            it.widget().setParent(None)
            it.widget().deleteLater()
        elif it.layout():
            _svuota(it.layout())


class SchedaPokemon(QDialog):
    aperte = []

    def __init__(self, finestra, chiave):
        super().__init__(finestra)
        self.f = finestra
        self.k = chiave
        self.setWindowTitle("Scheda Pokémon")
        self.setObjectName("dialogo")
        self.setMinimumWidth(520)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 20, 22, 18)
        self.v.setSpacing(12)
        self._firma = None
        SchedaPokemon.aperte.append(self)
        self.destroyed.connect(lambda *_: SchedaPokemon.aperte.remove(self) if self in SchedaPokemon.aperte else None)
        self.aggiorna()

    @classmethod
    def aggiorna_tutte(cls):
        for s in list(cls.aperte):
            try:
                s.aggiorna()
            except RuntimeError:
                pass

    def aggiorna(self):
        st = self.f._ultimo_stato or {}
        p = (st.get("pokemon") or {}).get(self.k)
        d = dettagli_di(self.f, p)
        x = ((st.get("giocatori") or {}).get(p["giocatore"]) or {}) if p else {}
        firma = repr((p, d, x.get("online")))
        if firma == self._firma:
            return
        self._firma = firma
        _svuota(self.v)
        if not p:
            self.v.addWidget(QLabel("Questo Pokémon non è più nel tracker."))
            return
        self._testa(p, d)
        if d and d.get("stat"):
            self._statistiche(d)
            self._mosse(d)
        elif p["stato"] in ("squadra", "box"):
            spiega = ("Le statistiche e le mosse si vedono per i Pokémon in squadra." if p["stato"] == "box" else
                      f"Le statistiche arrivano dall'app di {p['giocatore']} quando è in gioco"
                      f"{'' if x.get('online') else ' (adesso è offline)'}.")
            l = QLabel(f"<span style='color:{TENUE}'>{spiega}</span>")
            l.setWordWrap(True)
            self.v.addWidget(l)
        legati = [st["pokemon"][q] for q in p.get("partners") or [] if q in st["pokemon"]]
        if legati:
            self.v.addWidget(QLabel(f"<span style='color:{TENUE}'>Legato a</span> "
                                    + ", ".join(f"<b>{nome(q)}</b> di {q['giocatore']}" for q in legati)))
        basso = QHBoxLayout()
        nota = QLabel(f"<span style='color:{SPENTO};font-size:8pt'>Si aggiorna da sola mentre giocate.</span>")
        basso.addWidget(nota, 1)
        b_corr = QPushButton("Correggi…")
        b_corr.setToolTip("Cambia lo stato, il luogo o i legami di questo Pokémon nel tracker")
        b_corr.clicked.connect(lambda: self.f._apri_pokemon(self.k))
        b_chiudi = QPushButton("Chiudi")
        b_chiudi.setObjectName("primario")
        b_chiudi.clicked.connect(self.close)
        basso.addWidget(b_corr)
        basso.addWidget(b_chiudi)
        self.v.addLayout(basso)
        self.adjustSize()

    # ---------- parti ----------
    def _testa(self, p, d):
        h = QHBoxLayout()
        h.setSpacing(14)
        img = QLabel()
        img.setFixedSize(76, 76)
        img.setAlignment(Qt.AlignCenter)
        tc = COLORI_TIPI.get((p.get("tipi") or ["?"])[0], "#888888")
        if p["stato"] == "morto":
            tc = "#555a6e"
        img.setStyleSheet(f"background: qradialgradient(cx:0.5, cy:0.55, radius:0.6, fx:0.5, fy:0.55, stop:0 {alfa(tc, 0.35)},"
                          f" stop:1 {alfa(tc, 0.06)}); border-radius: 38px;")
        pm = self.f.sprite.pixmap(p["specie"], 70)
        if pm:
            img.setPixmap(pm)
        h.addWidget(img, 0, Qt.AlignTop)
        v = QVBoxLayout()
        v.setSpacing(4)
        lv = (d or {}).get("livello") or p.get("livello") or "?"
        v.addWidget(QLabel(f"<b style='font-size:13pt'>{nome(p)}</b> <span style='color:{TENUE}'>{p.get('nome_specie', '')}"
                           f" · Lv.{lv}</span>&nbsp; " + " ".join(pillola_tipo(t) for t in p.get("tipi") or [])))
        c = COLORE_STATO.get(p["stato"], TENUE)
        riga = (f"di <b>{p['giocatore']}</b> · <span style='color:{c};font-weight:600'>{dict(STATI).get(p['stato'], p['stato'])}</span>"
                f" · <span style='color:{TENUE}'>catturato a</span> {p.get('luogo_nome') or L.nome_luogo(p.get('luogo'))}")
        v.addWidget(QLabel(riga))
        if d:
            ps, mx = d.get("ps") or 0, d.get("ps_max") or 0
            st, cst = stato_alterato(d.get("stato_alt"))
            barra = QHBoxLayout()
            barra.setSpacing(8)
            pb = QProgressBar()
            pb.setTextVisible(False)
            pb.setFixedHeight(7)
            pb.setRange(0, max(1, mx))
            pb.setValue(ps)
            perc = ps / mx if mx else 0
            cb = OK if perc > 0.5 else WARN if perc > 0.2 else KO
            pb.setStyleSheet(f"QProgressBar::chunk{{background:{cb}; border-radius:3px;}}")
            barra.addWidget(pb, 1)
            barra.addWidget(QLabel(f"<b>{ps}</b><span style='color:{TENUE}'>/{mx} PS</span>"
                                   + (f"&nbsp; <b style='color:{cst};font-size:8pt'>{st}</b>" if st else "")))
            v.addLayout(barra)
            v.addWidget(self._esperienza(p, d))
        h.addLayout(v, 1)
        self.v.addLayout(h)
        ab = (L._DATI.get("abilita") or {}).get(str((d or {}).get("abilita") or 0))
        righe = []
        if ab:
            righe.append(f"<span style='color:{TENUE}'>Abilità:</span> <b>{ab[0]}</b>"
                         + (f" <span style='color:{TENUE}'>— {ab[1]}</span>" if ab[1] else ""))
        nn = natura((d or {}).get("natura"))
        if nn:
            if nn[1] == nn[2]:
                righe.append(f"<span style='color:{TENUE}'>Natura:</span> <b>{nn[0]}</b> <span style='color:{TENUE}'>(neutra)</span>")
            else:
                righe.append(f"<span style='color:{TENUE}'>Natura:</span> <b>{nn[0]}</b> <span style='color:{TENUE}'>—</span> "
                             f"<span style='color:{OK}'>+{NOMI_STAT_LUNGHI[nn[1]]}</span>, "
                             f"<span style='color:{KO}'>−{NOMI_STAT_LUNGHI[nn[2]]}</span>")
        if d and d.get("impara"):
            righe.append(html_impara(d["impara"]))
        if righe:
            l = QLabel("<br>".join(righe))
            l.setWordWrap(True)
            self.v.addWidget(l)

    def _esperienza(self, p, d):
        from . import esperienza as E
        w = QLabel()
        lv, esp = d.get("livello") or 0, d.get("esperienza")
        if not lv or esp is None or lv >= 100:
            return w
        curva = E.curva_di(p["specie"], lv, esp)
        da, a = E.esp_per_livello(curva, lv), E.esp_per_livello(curva, lv + 1)
        manca = max(0, a - esp)
        w.setText(f"<span style='color:{TENUE}'>Esperienza per il Lv.{lv + 1}:</span> mancano <b>{manca}</b> "
                  f"<span style='color:{TENUE}'>({round(100 * (esp - da) / max(1, a - da))}% del livello)</span>")
        return w

    def _statistiche(self, d):
        box = QFrame()
        box.setObjectName("carta")
        g = QGridLayout(box)
        g.setContentsMargins(14, 10, 14, 10)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        nn = natura(d.get("natura"))
        valori = [("PS", d.get("ps_max") or 0, TESTO)]
        for i in ORDINE_STAT:
            col = TESTO
            if nn and nn[1] != nn[2]:
                col = OK if i == nn[1] else KO if i == nn[2] else TESTO
            valori.append((NOMI_STAT_LUNGHI[i], (d.get("stat") or [0] * 5)[i], col))
        massimo = max(1, max(v for _, v, _ in valori))
        for r, (n, val, col) in enumerate(valori):
            g.addWidget(QLabel(f"<span style='color:{TENUE}'>{n}</span>"), r, 0)
            g.addWidget(QLabel(f"<b style='color:{col}'>{val}</b>"), r, 1, Qt.AlignRight)
            pb = QProgressBar()
            pb.setTextVisible(False)
            pb.setFixedHeight(6)
            pb.setRange(0, massimo)
            pb.setValue(val)
            cb = OK if col == OK else KO if col == KO else ACC
            pb.setStyleSheet(f"QProgressBar::chunk{{background:{alfa(cb, 0.85)}; border-radius:3px;}}")
            g.addWidget(pb, r, 2)
        tot = sum(v for _, v, _ in valori)
        g.addWidget(QLabel(f"<span style='color:{TENUE}'>Totale</span>"), len(valori), 0)
        g.addWidget(QLabel(f"<b>{tot}</b>"), len(valori), 1, Qt.AlignRight)
        g.setColumnStretch(2, 1)
        self.v.addWidget(box)

    def _mosse(self, d):
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(5)
        intest = ["Mossa", "Tipo", "Categoria", "Potenza", "Precisione", "PP"]
        for c, t in enumerate(intest):
            g.addWidget(QLabel(f"<span style='color:{SPENTO};font-size:8pt'>{t.upper()}</span>"), 0, c)
        r = 1
        for k, mid in enumerate(d.get("mosse") or []):
            mo = mossa(mid) if mid else None
            if not mo:
                continue
            stab = mo["tipo"] in (L.info(d["specie"]).get("tipi") or []) and mo["classe"] != 0
            g.addWidget(QLabel(f"<b>{mo['nome']}</b>" + (f"&nbsp;<span style='color:{ORO}'>★</span>" if stab else "")), r, 0)
            g.addWidget(QLabel(pillola_tipo(mo["tipo"])), r, 1)
            g.addWidget(QLabel(f"<span style='color:{TENUE}'>{['stato', 'fisica', 'speciale'][mo['classe']]}</span>"), r, 2)
            g.addWidget(QLabel(f"<b>{mo['potenza']}</b>" if mo["potenza"] else f"<span style='color:{SPENTO}'>—</span>"), r, 3)
            prec = mo.get("precisione")
            g.addWidget(QLabel(f"{prec}%" if prec else f"<span style='color:{SPENTO}'>—</span>"), r, 4)
            pp_max = mo["pp"] * (5 + ((d.get("pp_su") or [0, 0, 0, 0])[k] or 0)) // 5 if mo["pp"] else 0
            pp_ora = (d.get("pp") or [0, 0, 0, 0])[k]
            cpp = KO if pp_ora == 0 else WARN if pp_max and pp_ora <= pp_max // 4 else TESTO
            g.addWidget(QLabel(f"<span style='color:{cpp}'>{pp_ora}/{pp_max}</span>"), r, 5)
            r += 1
        g.setColumnStretch(6, 1)
        w = QWidget()
        w.setLayout(g)
        self.v.addWidget(w)
        if any(m for m in d.get("mosse") or []):
            spiega = QLabel(f"<span style='color:{SPENTO};font-size:8pt'><span style='color:{ORO}'>★</span> = stesso tipo del "
                            "Pokémon (STAB, ×1,5)</span>")
            self.v.addWidget(spiega)
