"""Tracker della lotta: mosse dei tuoi Pokémon contro l'avversario (efficacia, STAB, PP) e viceversa."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from . import logica as L
from .stile import ACC, COLORI_TIPI, KO, OK, ORO, SPENTO, TENUE, TESTO, WARN, alfa

# tabella dei tipi della 5ª generazione (niente Folletto; l'Acciaio resiste a Spettro e Buio)
_SUPER, _POCO, _NULLA = 2.0, 0.5, 0.0
TABELLA = {
    "Normale": {"Roccia": _POCO, "Acciaio": _POCO, "Spettro": _NULLA},
    "Fuoco": {"Erba": _SUPER, "Ghiaccio": _SUPER, "Coleottero": _SUPER, "Acciaio": _SUPER,
              "Fuoco": _POCO, "Acqua": _POCO, "Roccia": _POCO, "Drago": _POCO},
    "Acqua": {"Fuoco": _SUPER, "Terra": _SUPER, "Roccia": _SUPER, "Acqua": _POCO, "Erba": _POCO, "Drago": _POCO},
    "Elettro": {"Acqua": _SUPER, "Volante": _SUPER, "Elettro": _POCO, "Erba": _POCO, "Drago": _POCO, "Terra": _NULLA},
    "Erba": {"Acqua": _SUPER, "Terra": _SUPER, "Roccia": _SUPER, "Fuoco": _POCO, "Erba": _POCO, "Veleno": _POCO,
             "Volante": _POCO, "Coleottero": _POCO, "Drago": _POCO, "Acciaio": _POCO},
    "Ghiaccio": {"Erba": _SUPER, "Terra": _SUPER, "Volante": _SUPER, "Drago": _SUPER, "Fuoco": _POCO, "Acqua": _POCO,
                 "Ghiaccio": _POCO, "Acciaio": _POCO},
    "Lotta": {"Normale": _SUPER, "Ghiaccio": _SUPER, "Roccia": _SUPER, "Buio": _SUPER, "Acciaio": _SUPER,
              "Veleno": _POCO, "Volante": _POCO, "Psico": _POCO, "Coleottero": _POCO, "Spettro": _NULLA},
    "Veleno": {"Erba": _SUPER, "Veleno": _POCO, "Terra": _POCO, "Roccia": _POCO, "Spettro": _POCO, "Acciaio": _NULLA},
    "Terra": {"Fuoco": _SUPER, "Elettro": _SUPER, "Veleno": _SUPER, "Roccia": _SUPER, "Acciaio": _SUPER,
              "Erba": _POCO, "Coleottero": _POCO, "Volante": _NULLA},
    "Volante": {"Erba": _SUPER, "Lotta": _SUPER, "Coleottero": _SUPER, "Elettro": _POCO, "Roccia": _POCO, "Acciaio": _POCO},
    "Psico": {"Lotta": _SUPER, "Veleno": _SUPER, "Psico": _POCO, "Acciaio": _POCO, "Buio": _NULLA},
    "Coleottero": {"Erba": _SUPER, "Psico": _SUPER, "Buio": _SUPER, "Fuoco": _POCO, "Lotta": _POCO, "Veleno": _POCO,
                   "Volante": _POCO, "Spettro": _POCO, "Acciaio": _POCO},
    "Roccia": {"Fuoco": _SUPER, "Ghiaccio": _SUPER, "Volante": _SUPER, "Coleottero": _SUPER, "Lotta": _POCO,
               "Terra": _POCO, "Acciaio": _POCO},
    "Spettro": {"Psico": _SUPER, "Spettro": _SUPER, "Buio": _POCO, "Acciaio": _POCO, "Normale": _NULLA},
    "Drago": {"Drago": _SUPER, "Acciaio": _POCO},
    "Buio": {"Psico": _SUPER, "Spettro": _SUPER, "Lotta": _POCO, "Buio": _POCO, "Acciaio": _POCO},
    "Acciaio": {"Ghiaccio": _SUPER, "Roccia": _SUPER, "Fuoco": _POCO, "Acqua": _POCO, "Elettro": _POCO, "Acciaio": _POCO},
}
STATI = {1: "SON", 2: "SON", 3: "SON", 4: "SON", 5: "SON", 6: "SON", 7: "SON"}


def stato_alterato(v):
    v = v or 0
    if v & 0x07:
        return "SON", "#9aa0b8"
    if v & 0x80:
        return "IPV", "#c27cff"
    if v & 0x08:
        return "VEL", "#c27cff"
    if v & 0x10:
        return "SCO", "#ff8a4c"
    if v & 0x20:
        return "CON", "#7fd1ff"
    if v & 0x40:
        return "PAR", "#f7d02c"
    return "", ""


def efficacia(tipo_mossa, tipi_difesa) -> float:
    m = 1.0
    for t in tipi_difesa or []:
        m *= TABELLA.get(tipo_mossa, {}).get(t, 1.0)
    return m


def mossa(i):
    v = (L._DATI.get("mosse") or {}).get(str(i))
    if not v:
        return None
    nome, tipo, pot, prec, pp, classe = v
    return {"id": i, "nome": nome, "tipo": tipo, "potenza": pot, "precisione": prec, "pp": pp, "classe": classe}


def tipi_di(specie):
    return L.info(specie).get("tipi") or []


def testo_molt(m):
    if m == 0:
        return "×0", SPENTO, "nessun effetto"
    if m >= 4:
        return "×4", OK, "superefficace ×4"
    if m >= 2:
        return "×2", OK, "superefficace"
    if m <= 0.25:
        return "×¼", KO, "poco efficace ×¼"
    if m < 1:
        return "×½", WARN, "poco efficace"
    return "×1", TENUE, "normale"


def migliore(mosse, tipi_attaccante, tipi_difesa):
    """(moltiplicatore, mossa) della mossa d'attacco migliore (efficacia × STAB × potenza)."""
    best = None
    for i in mosse or []:
        mo = mossa(i) if i else None
        if not mo or mo["classe"] == 0 or not mo["potenza"]:
            continue
        e = efficacia(mo["tipo"], tipi_difesa)
        stab = 1.5 if mo["tipo"] in (tipi_attaccante or []) else 1.0
        punteggio = e * stab * mo["potenza"]
        if not best or punteggio > best[2]:
            best = (e, mo, punteggio)
    return best


def pillola_tipo(t):
    c = COLORI_TIPI.get(t, "#888888")
    return f"<span style='background:{alfa(c, 0.25)};color:{c};font-size:8pt;font-weight:700;'>&nbsp;{t}&nbsp;</span>"


class Scelta(QPushButton):
    """Pulsantino con lo sprite di un Pokémon (tuo o avversario) per scegliere chi analizzare."""

    def __init__(self, sprite, specie, testo, colore_badge=None, badge=""):
        super().__init__()
        self.setCheckable(True)
        self.setObjectName("sceltaLotta")
        self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 3, 8, 3)
        h.setSpacing(4)
        img = QLabel()
        img.setFixedSize(30, 30)
        pm = sprite.pixmap(specie, 30) if specie else None
        if pm:
            img.setPixmap(pm)
        h.addWidget(img)
        l = QLabel(testo)
        l.setStyleSheet("font-size: 8pt;")
        h.addWidget(l)
        if badge:
            b = QLabel(badge)
            b.setStyleSheet(f"color:{colore_badge}; font-weight:700; font-size:8pt;")
            h.addWidget(b)
        self.setMinimumHeight(38)
        self.setMinimumWidth(h.sizeHint().width() + 4)      # il pulsante non conosce il suo contenuto


class CartaLotta(QFrame):
    """Compare al posto di «Prossimo obiettivo» e «Dove sei» mentre sei in lotta."""

    def __init__(self, sprite):
        super().__init__()
        self.setObjectName("carta")
        self.sprite = sprite
        self.det, self.squadra = None, []
        self.sel_mio, self.sel_nemico = None, None
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 14, 18, 14)
        self.v.setSpacing(8)

    def _pulisci(self):
        while self.v.count():
            it = self.v.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
            elif it.layout():
                _svuota(it.layout())

    def aggiorna(self, det, squadra):
        cambio_lotta = (det or {}).get("allenatore") != (self.det or {}).get("allenatore") or not self.det
        self.det = det
        self.squadra = [p for p in (squadra or []) if not p.get("uovo")]
        if cambio_lotta:
            self.sel_mio = self.sel_nemico = None
        self._disegna()

    # ---------- scelte predefinite: il primo Pokémon vivo, l'avversario in campo ----------
    def _mio(self):
        vivi = [p for p in self.squadra if (p.get("ps") or 0) > 0] or self.squadra
        if self.sel_mio is not None:
            for p in self.squadra:
                if p.get("pid") == self.sel_mio:
                    return p
        return vivi[0] if vivi else None

    def _nemico(self):
        nemici = (self.det or {}).get("nemici") or []
        if self.sel_nemico is not None and self.sel_nemico < len(nemici):
            return self.sel_nemico, nemici[self.sel_nemico]
        for i, n in enumerate(nemici):
            if (n.get("ps") or 0) > 0:
                return i, n
        return (0, nemici[0]) if nemici else (None, None)

    def _disegna(self):
        self._pulisci()
        det = self.det or {}
        nemici = det.get("nemici") or []
        o = L.OBIETTIVO_DA_ID.get(det.get("allenatore") or -1)
        if det.get("allenatore"):
            titolo = f"LOTTA CONTRO {o['nome'].upper()}" if o else "LOTTA CONTRO UN ALLENATORE"
        else:
            titolo = "LOTTA CON UN POKÉMON SELVATICO"
        t = QLabel(titolo)
        t.setObjectName("sezione")
        t.setStyleSheet(f"color:{KO if o else WARN};")
        self.v.addWidget(t)
        if not nemici:
            self.v.addWidget(QLabel("<span style='color:%s'>Leggo l'avversario…</span>" % TENUE))
            self.v.addStretch()
            return
        i_nem, nem = self._nemico()
        mio = self._mio()
        tipi_nem = tipi_di(nem["specie"])
        tipi_mio = tipi_di(mio["specie"]) if mio else []

        # --- avversario
        r = QHBoxLayout()
        r.setSpacing(12)
        img = QLabel()
        img.setFixedSize(56, 56)
        pm = self.sprite.pixmap(nem["specie"], 56)
        if pm:
            img.setPixmap(pm)
        img.setStyleSheet(f"background: {alfa(COLORI_TIPI.get((tipi_nem or ['?'])[0], '#888888'), 0.18)}; border-radius: 28px;")
        r.addWidget(img)
        col = QVBoxLayout()
        col.setSpacing(3)
        nome = L.info(nem["specie"])["nome"]
        st, cst = stato_alterato(nem.get("stato_alt"))
        st_html = f"&nbsp;<span style='color:{cst};font-weight:700;font-size:8pt'>{st}</span>" if st else ""
        col.addWidget(QLabel(f"<b style='font-size:11.5pt'>{nome}</b> <span style='color:{TENUE}'>Lv.{nem['livello']}</span>{st_html}"
                             f"&nbsp;&nbsp;{' '.join(pillola_tipo(x) for x in tipi_nem)}"))
        ps = QProgressBar()
        ps.setTextVisible(False)
        ps.setRange(0, max(1, nem.get("ps_max") or 1))
        ps.setValue(nem.get("ps") or 0)
        perc = (nem.get("ps") or 0) / max(1, nem.get("ps_max") or 1)
        cps = OK if perc > 0.5 else WARN if perc > 0.2 else KO
        ps.setStyleSheet(f"QProgressBar::chunk{{background:{cps};}}")
        col.addWidget(ps)
        info = []
        if mio and mio.get("stat") and nem.get("stat"):
            vm, vn = mio["stat"][2], nem["stat"][2]
            if vm > vn:
                info.append(f"<span style='color:{OK}'>{mio.get('soprannome') or L.info(mio['specie'])['nome']} è più veloce</span>")
            elif vm < vn:
                info.append(f"<span style='color:{WARN}'>{nome} è più veloce</span>")
            else:
                info.append(f"<span style='color:{TENUE}'>stessa velocità</span>")
        info.append(f"<span style='color:{TENUE}'>PS {nem.get('ps')}/{nem.get('ps_max')}</span>")
        col.addWidget(QLabel("&nbsp;·&nbsp;".join(info)))
        r.addLayout(col, 1)
        self.v.addLayout(r)

        if len(nemici) > 1:
            riga = QHBoxLayout()
            riga.setSpacing(4)
            for i, n in enumerate(nemici):
                b = Scelta(self.sprite, n["specie"], f"Lv.{n['livello']}")
                b.setChecked(i == i_nem)
                if (n.get("ps") or 0) == 0:
                    b.setEnabled(False)
                b.setToolTip(L.info(n["specie"])["nome"])
                b.clicked.connect(lambda _=False, i=i: self._scegli_nemico(i))
                riga.addWidget(b)
            riga.addStretch()
            self.v.addLayout(riga)

        # --- mosse dell'avversario contro il tuo Pokémon
        if mio:
            pericoli = []
            for k, mid in enumerate(nem.get("mosse") or []):
                mo = mossa(mid) if mid else None
                if not mo:
                    continue
                if mo["classe"] == 0:
                    pericoli.append(f"<span style='color:{TENUE}'>{mo['nome']}</span>")
                    continue
                e = efficacia(mo["tipo"], tipi_mio)
                tx, c, _ = testo_molt(e)
                stab = "★" if mo["tipo"] in tipi_nem else ""
                pericoli.append(f"<span style='color:{COLORI_TIPI.get(mo['tipo'], '#888')}'>{mo['nome']}</span>"
                                f"<b style='color:{c}'>&nbsp;{tx}</b><span style='color:{ORO}'>{stab}</span>")
            if pericoli:
                l = QLabel(f"<span style='color:{TENUE}'>Sue mosse:</span>&nbsp; " + "&nbsp;&nbsp;·&nbsp;&nbsp;".join(pericoli))
                l.setWordWrap(True)
                self.v.addWidget(l)

        linea = QFrame()
        linea.setFixedHeight(1)
        linea.setStyleSheet("background: rgba(255,255,255,0.07);")
        self.v.addWidget(linea)

        # --- i tuoi Pokémon (scegli chi analizzare) con la mossa migliore
        riga = QHBoxLayout()
        riga.setSpacing(4)
        for p in self.squadra:
            best = migliore(p.get("mosse"), tipi_di(p["specie"]), tipi_nem)
            tx, c, _ = testo_molt(best[0]) if best else ("", TENUE, "")
            b = Scelta(self.sprite, p["specie"], f"Lv.{p.get('livello')}", c, tx)
            b.setChecked(mio is not None and p.get("pid") == mio.get("pid"))
            if (p.get("ps") or 0) == 0:
                b.setEnabled(False)
            b.setToolTip(f"{p.get('soprannome') or L.info(p['specie'])['nome']}"
                         + (f" — mossa migliore: {best[1]['nome']} {tx}" if best else ""))
            b.clicked.connect(lambda _=False, pid=p.get("pid"): self._scegli_mio(pid))
            riga.addWidget(b)
        riga.addStretch()
        self.v.addLayout(riga)

        if not mio:
            self.v.addStretch()
            return
        # --- le mosse del tuo Pokémon
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(5)
        for k, mid in enumerate(mio.get("mosse") or []):
            mo = mossa(mid) if mid else None
            if not mo:
                continue
            c_tipo = COLORI_TIPI.get(mo["tipo"], "#888888")
            n = QLabel(f"<b>{mo['nome']}</b>")
            tipo = QLabel(pillola_tipo(mo["tipo"]))
            classe = ["stato", "fisica", "speciale"][mo["classe"]]
            pot = QLabel(f"<span style='color:{TENUE}'>{classe}</span>"
                         + (f" <b>{mo['potenza']}</b>" if mo["potenza"] else ""))
            if mo["classe"] == 0:
                eff = QLabel(f"<span style='color:{TENUE}'>—</span>")
            else:
                e = efficacia(mo["tipo"], tipi_nem)
                tx, c, desc = testo_molt(e)
                stab = mo["tipo"] in tipi_mio
                eff = QLabel(f"<b style='color:{c}'>{tx}</b>"
                             + (f"&nbsp;<span style='background:{alfa(ORO, 0.2)};color:{ORO};font-size:7.5pt;font-weight:700'>&nbsp;STAB&nbsp;</span>" if stab else ""))
                eff.setToolTip(desc + (" · stesso tipo del Pokémon: ×1,5" if stab else ""))
            pp_max = mo["pp"] * (5 + ((mio.get("pp_su") or [0, 0, 0, 0])[k] or 0)) // 5 if mo["pp"] else 0
            pp_ora = (mio.get("pp") or [0, 0, 0, 0])[k]
            cpp = KO if pp_ora == 0 else WARN if pp_max and pp_ora <= pp_max // 4 else TENUE
            pp = QLabel(f"<span style='color:{cpp}'>PP {pp_ora}/{pp_max}</span>")
            for c_, w in enumerate((n, tipo, pot, eff, pp)):
                g.addWidget(w, k, c_)
        g.setColumnStretch(0, 1)
        self.v.addLayout(g)
        nota = QLabel(f"<span style='color:{SPENTO};font-size:8pt'>I PS e i PP dei tuoi Pokémon sono quelli di inizio lotta. "
                      "Clicca un Pokémon per vedere le sue mosse.</span>")
        nota.setWordWrap(True)
        self.v.addWidget(nota)
        self.v.addStretch()

    def _scegli_mio(self, pid):
        self.sel_mio = pid
        self._disegna()

    def _scegli_nemico(self, i):
        self.sel_nemico = i
        self._disegna()


def _svuota(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget():
            it.widget().deleteLater()
        elif it.layout():
            _svuota(it.layout())
