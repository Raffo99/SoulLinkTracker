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


# nature: (nome, statistica aumentata, statistica diminuita) con le statistiche nell'ordine att, dif, vel, att.sp, dif.sp
NOMI_NATURE = ["Ardita", "Schiva", "Audace", "Decisa", "Birbona", "Sicura", "Docile", "Placida", "Scaltra", "Fiacca",
               "Timida", "Lesta", "Seria", "Allegra", "Ingenua", "Modesta", "Mite", "Quieta", "Ritrosa", "Ardente",
               "Calma", "Gentile", "Vivace", "Cauta", "Furba"]
NOMI_STAT = ["Att", "Dif", "Vel", "Att.Sp", "Dif.Sp"]
NOMI_STAT_LUNGHI = ["Attacco", "Difesa", "Velocità", "Attacco Speciale", "Difesa Speciale"]


def natura(n):
    """(nome, indice aumentata, indice diminuita) o None; aumentata == diminuita vuol dire neutra."""
    if n is None or not 0 <= n < 25:
        return None
    return NOMI_NATURE[n], n // 5, n % 5


def html_statistiche(ps_max, stat, nat=None, stadi=None, sep=" · "):
    """«PS 41 · Att 22▲ · Dif 18 ...»: verde la statistica aumentata dalla natura, rossa quella diminuita;
    tra parentesi le modifiche in lotta (+1, -2...)."""
    if not stat:
        return ""
    nn = natura(nat)
    pezzi = [f"<span style='color:{TENUE}'>PS</span> <b>{ps_max}</b>"] if ps_max else []
    ordine = [0, 1, 3, 4, 2]                         # come nel gioco: Att, Dif, Att.Sp, Dif.Sp, Vel
    for i in ordine:
        if i >= len(stat):
            continue
        col = TESTO
        if nn and nn[1] != nn[2]:
            col = OK if i == nn[1] else KO if i == nn[2] else TESTO
        extra = ""
        if stadi and i < len(stadi) and stadi[i] not in (None, 6):
            d = stadi[i] - 6
            extra = f" <b style='color:{OK if d > 0 else KO}'>({'+' if d > 0 else ''}{d})</b>"
        pezzi.append(f"<span style='color:{TENUE}'>{NOMI_STAT[i]}</span> <b style='color:{col}'>{stat[i]}</b>{extra}")
    testo = sep.join(pezzi)
    if nn:
        testo += f"{sep}<span style='color:{TENUE}'>natura</span> {nn[0]}"
    return testo


def riassunto_impara(lista, livello):
    """{"totale": mosse imparate salendo di livello, "tra": livelli alla prossima (None se finite), "lv": livello della prossima}."""
    from . import rom as R
    if not lista:
        return None
    p = R.prossime(lista, livello or 0)
    return {"totale": p["totale"], "tra": p["tra"], "lv": p["prossima"][0] if p["prossima"] else None}


def html_impara(d):
    """«Impara 9 mosse in tutto · la prossima tra 3 livelli (Lv.24)»: quale mossa non si dice."""
    if not d:
        return ""
    testo = f"<span style='color:{TENUE}'>Impara</span> <b>{d['totale']}</b> <span style='color:{TENUE}'>mosse in tutto</span>"
    if d.get("tra"):
        tra = "al prossimo livello" if d["tra"] == 1 else f"tra&nbsp;{d['tra']}&nbsp;livelli"
        testo += (f" · <span style='color:{TENUE}'>la prossima</span> <b style='color:#b9a8ff'>{tra}</b>"
                  f" <span style='color:{TENUE}'>(Lv.{d['lv']})</span>")
    else:
        testo += f" · <span style='color:{TENUE}'>le ha già imparate tutte</span>"
    return testo


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


def scrivi_molt(x) -> str:
    """×3, ×1,5, ×0,75… (virgola italiana, senza zeri inutili)."""
    if x == int(x):
        return f"×{int(x)}"
    return "×" + f"{x:.3f}".rstrip("0").rstrip(".").replace(".", ",")


def totale(e, stab) -> float:
    """Moltiplicatore complessivo: efficacia del tipo × 1,5 se la mossa è dello stesso tipo del Pokémon."""
    return e * (1.5 if stab else 1.0)


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
            best = (e, mo, punteggio, totale(e, stab > 1))
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
        self._idx_nem, self._ko_da = None, None
        self.impara = {}                      # specie -> [(livello, mossa)] letti dalla ROM randomizzata
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 14, 18, 14)
        self.v.setSpacing(8)

    def _pulisci(self):
        while self.v.count():
            it = self.v.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif it.layout():
                _svuota(it.layout())

    def aggiorna(self, det, squadra):
        cambio_lotta = (det or {}).get("allenatore") != (self.det or {}).get("allenatore") or not self.det
        attivo_prima = ((self.det or {}).get("mio") or {}).get("pid")
        attivo_ora = ((det or {}).get("mio") or {}).get("pid")
        if attivo_ora and attivo_ora != attivo_prima:
            self.sel_mio = None                    # hai cambiato Pokémon nel gioco: il tracker lo segue
        self.det = det
        self.squadra = [p for p in (squadra or []) if not p.get("uovo")]
        if cambio_lotta:
            self.sel_mio = self.sel_nemico = None
            self._idx_nem, self._ko_da = None, None
        self._disegna()

    # ---------- scelte predefinite: il primo Pokémon vivo, l'avversario in campo ----------
    def _mio(self):
        vivi = [p for p in self.squadra if (p.get("ps") or 0) > 0] or self.squadra
        attivo = ((self.det or {}).get("mio") or {}).get("pid")
        for pid in (self.sel_mio, attivo):
            if pid is not None:
                for p in self.squadra:
                    if p.get("pid") == pid:
                        return p
        return vivi[0] if vivi else None

    def _live(self, mio):
        """PS, PP e modifiche alle statistiche in tempo reale, se è il Pokémon in campo."""
        m = (self.det or {}).get("mio") or {}
        return m if mio and m.get("pid") == mio.get("pid") else {}

    def _nemico(self):
        """L'avversario in campo. Quando va KO si continua a mostrarlo per qualche secondo: il successivo
        compare solo dopo, quando l'allenatore lo manda in campo (così il tracker non anticipa niente)."""
        import time
        from PySide6.QtCore import QTimer
        nemici = (self.det or {}).get("nemici") or []
        if not nemici:
            return None, None
        in_campo = [k for k, n in enumerate(nemici) if n.get("in_campo")]
        if in_campo:                                # il gioco dice chi è in campo: niente supposizioni
            i = self.sel_nemico if self.sel_nemico in in_campo else in_campo[0]
            self._idx_nem, self._ko_da = i, None
            return i, nemici[i]
        i = self._idx_nem if self._idx_nem is not None and self._idx_nem < len(nemici) else 0
        if (nemici[i].get("ps") or 0) == 0:
            if self._ko_da is None:
                self._ko_da = time.time()
                QTimer.singleShot(4200, self._disegna)
            elif time.time() - self._ko_da >= 4:
                dopo = next((k for k in range(i + 1, len(nemici)) if (nemici[k].get("ps") or 0) > 0), None)
                if dopo is not None:
                    i, self._ko_da = dopo, None
        else:
            self._ko_da = None
        self._idx_nem = i
        return i, nemici[i]

    def _disegna(self):
        self._pulisci()
        det = self.det or {}
        nemici = det.get("nemici") or []
        o = L.OBIETTIVO_DA_ID.get(det.get("allenatore") or -1)
        _, nem = self._nemico()
        mio = self._mio()

        # --- titolo: contro chi (solo quello che si vede anche nel gioco)
        testa = QHBoxLayout()
        if det.get("allenatore"):
            chi = o["nome"] if o else L.NOMI_ALLENATORI.get(det.get("allenatore"))
            titolo = f"LOTTA CONTRO {chi.upper()}" if chi else "LOTTA CONTRO UN ALLENATORE"
        else:
            titolo = "LOTTA CON UN SELVATICO"
        t = QLabel(titolo)
        t.setObjectName("sezione")
        t.setStyleSheet(f"color:{KO if o else WARN};")
        testa.addWidget(t)
        if det.get("allenatore") and nemici:
            # dell'allenatore si sa solo quanti Pokémon ha (come le Poké Ball del gioco), non quali
            palle = QHBoxLayout()
            palle.setSpacing(3)
            for n in nemici:
                pb = QLabel()
                pb.setFixedSize(11, 11)
                if (n.get("ps") or 0) > 0:
                    pb.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5c6c, stop:0.46 #ff5c6c,"
                                     " stop:0.47 #1b1d29, stop:0.56 #1b1d29, stop:0.57 #eceef4, stop:1 #eceef4); border-radius: 5px;")
                else:
                    pb.setStyleSheet("background: #3a3e52; border-radius: 5px;")
                palle.addWidget(pb)
            box = QWidget()
            box.setLayout(palle)
            box.setToolTip(f"L'allenatore ha {len(nemici)} Pokémon")
            palle.setContentsMargins(8, 0, 0, 0)
            testa.addWidget(box)
        testa.addStretch()
        if nem:
            testa.addWidget(QLabel(f"<span style='color:{TENUE}'>contro</span> <b>{L.info(nem['specie'])['nome']}</b> "
                                   f"<span style='color:{TENUE}'>Lv.{nem['livello']}</span>"))
        self.v.addLayout(testa)
        if not nem:
            self.v.addWidget(QLabel(f"<span style='color:{TENUE}'>Leggo l'avversario…</span>"))
            self.v.addStretch()
            return
        tipi_nem = tipi_di(nem["specie"])

        # --- la tua squadra: scegli chi è in campo (ognuno con il miglior moltiplicatore)
        riga = QHBoxLayout()
        riga.setSpacing(4)
        for p in self.squadra:
            best = migliore(p.get("mosse"), tipi_di(p["specie"]), tipi_nem)
            _, c, _ = testo_molt(best[0]) if best else ("", TENUE, "")
            tx = scrivi_molt(best[3]) if best else ""
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
        tipi_mio = tipi_di(mio["specie"])

        # --- il tuo Pokémon: nome, tipi, PS, stato, abilità
        live = self._live(mio)
        nome_mio = mio.get("soprannome") or L.info(mio["specie"])["nome"]
        st, cst = stato_alterato(mio.get("stato_alt"))
        righe = [f"<b style='font-size:11pt'>{nome_mio}</b> <span style='color:{TENUE}'>Lv.{mio.get('livello')}</span>"
                 f"&nbsp; {' '.join(pillola_tipo(x) for x in tipi_mio)}"
                 f"&nbsp; <span style='color:{TENUE}'>PS {live.get('ps', mio.get('ps'))}/{mio.get('ps_max')}</span>"
                 + (f"&nbsp; <b style='color:{cst};font-size:8pt'>{st}</b>" if st else "")]
        ab = (L._DATI.get("abilita") or {}).get(str(mio.get("abilita") or 0))
        if ab:
            righe.append(f"<span style='color:{TENUE}'>Abilità:</span> <b>{ab[0]}</b>"
                         + (f" <span style='color:{TENUE}'>— {ab[1]}</span>" if ab[1] else ""))
        riga_imp = self._riga_impara(mio)
        if riga_imp:
            righe.append(riga_imp)
        righe.append(html_statistiche(mio.get("ps_max"), mio.get("stat"), mio.get("natura"), live.get("stadi")))
        info = QLabel("<br>".join(righe))
        info.setWordWrap(True)
        self.v.addWidget(info)

        # --- le sue mosse: nome verde se superefficace, stella dorata se STAB, moltiplicatore e PP vicini
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(4)
        g.setContentsMargins(0, 4, 0, 0)
        for k, mid in enumerate(mio.get("mosse") or []):
            mo = mossa(mid) if mid else None
            if not mo:
                continue
            stab = mo["tipo"] in tipi_mio and mo["classe"] != 0
            if mo["classe"] == 0:
                colore_nome, tx, c, desc = TESTO, "—", TENUE, "mossa di stato"
            else:
                e = efficacia(mo["tipo"], tipi_nem)
                _, c, desc = testo_molt(e)
                tx = scrivi_molt(totale(e, stab))
                if stab and e > 0:
                    desc = f"{desc} {scrivi_molt(e)} · stesso tipo del Pokémon (STAB) ×1,5 = {tx}"
                colore_nome = OK if e >= 2 else KO if 0 < e < 1 else SPENTO if e == 0 else TESTO
            stella = f"&nbsp;<span style='color:{ORO}'>★</span>" if stab else ""
            n = QLabel(f"<b style='color:{colore_nome}'>{mo['nome']}</b>{stella}")
            n.setToolTip(desc)
            tipo = QLabel(pillola_tipo(mo["tipo"]))
            classe = ["stato", "fisica", "speciale"][mo["classe"]]
            pot = QLabel(f"<span style='color:{TENUE}'>{classe}</span>" + (f" <b>{mo['potenza']}</b>" if mo["potenza"] else ""))
            molt = QLabel(f"<b style='color:{c}'>{tx}</b>")
            molt.setToolTip(desc)
            pp_max = mo["pp"] * (5 + ((mio.get("pp_su") or [0, 0, 0, 0])[k] or 0)) // 5 if mo["pp"] else 0
            pp_ora = (live.get("pp") or mio.get("pp") or [0, 0, 0, 0])[k]
            cpp = KO if pp_ora == 0 else WARN if pp_max and pp_ora <= pp_max // 4 else TENUE
            pp = QLabel(f"<span style='color:{cpp}'>PP {pp_ora}/{pp_max}</span>")
            for c_, w in enumerate((n, tipo, pot, molt, pp)):
                g.addWidget(w, k, c_)
        g.setColumnStretch(5, 1)                 # tutto vicino a sinistra
        self.v.addLayout(g)
        if (self.det or {}).get("mio"):
            t_nota = ("Il tracker segue il Pokémon che hai in campo: clicca un altro per vedere come se la caverebbe. "
                      "PS, PP e modifiche alle statistiche (tra parentesi) sono in tempo reale.")
        else:
            t_nota = "Clicca il Pokémon che hai in campo. PS e PP sono quelli di inizio lotta."
        nota = QLabel(f"<span style='color:{SPENTO};font-size:8pt'>{t_nota}</span>")
        nota.setWordWrap(True)
        self.v.addWidget(nota)
        self.v.addStretch()

    def _riga_impara(self, mio):
        lista = self.impara.get(mio.get("specie"))
        return html_impara(riassunto_impara(lista, mio.get("livello"))) if lista else ""

    def imposta_impara(self, dati):
        self.impara = dati or {}
        if self.isVisible() and self.det:
            self._disegna()

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
            it.widget().hide()
            it.widget().setParent(None)
            it.widget().deleteLater()
        elif it.layout():
            _svuota(it.layout())
