"""Parti principali della nuova interfaccia: barra in alto, obiettivo, luogo attuale, coppie, ospite del gioco."""
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .stile import ACC, COLORI_GIOCATORI, COLORI_TIPI, KO, OK, ORO, SPENTO, TENUE, TESTO, WARN, alfa, colori_giocatori


def logo(lato):
    """Il logo dell'app (i due anelli) come immagine."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    l = QLabel()
    l.setFixedSize(lato, lato)
    png = base / "risorse" / "icona.png"
    if png.exists():
        pm = QPixmap(str(png)).scaled(lato * 2, lato * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(2)
        l.setPixmap(pm)
    else:
        l.setPixmap(QIcon(str(base / "risorse" / "icona.ico")).pixmap(lato, lato))
    return l


def ombra(w, raggio=24, alfa_=140, dy=6):
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(raggio)
    e.setOffset(0, dy)
    e.setColor(QColor(0, 0, 0, alfa_))
    w.setGraphicsEffect(e)


class Avatar(QLabel):
    """Cerchio con l'iniziale del giocatore, nel suo colore."""

    def __init__(self, lato=30):
        super().__init__()
        self.lato = lato
        self.setFixedSize(lato, lato)
        self.setAlignment(Qt.AlignCenter)

    def imposta(self, nome_g, colore, attivo=True):
        self.setText((nome_g or "?")[:1].upper())
        c2 = colore if attivo else SPENTO
        self.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c2}, stop:1 {alfa(c2, 0.55)});"
                           f"border-radius: {self.lato // 2}px; color: white; font-weight: 700; font-size: {max(8, self.lato // 3)}pt;")


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


def paragrafi(righe, spazio=6):
    """Righe di testo ricco ben distanziate (con <br> sarebbero tutte attaccate)."""
    return "".join(f"<p style='margin:0 0 {spazio}px 0'>{r}</p>" for r in righe)


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
    def __init__(self, lato=10):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2 if lato < 8 else 3)
        self.lato = lato
        self.punti = []
        for _ in range(8):
            l = QLabel()
            l.setFixedSize(lato, lato)
            h.addWidget(l)
            self.punti.append(l)
        self.imposta(0)

    def imposta(self, n):
        for i, l in enumerate(self.punti):
            if i < n:
                sfondo = "qradialgradient(cx:0.35, cy:0.3, radius:0.8, fx:0.35, fy:0.3, stop:0 #fff3c4, stop:0.5 #ffd166, stop:1 #d99a1e)"
            else:
                sfondo = "rgba(255,255,255,0.09)"
            l.setStyleSheet(f"background:{sfondo};border-radius:{self.lato // 2}px;")
        self.setToolTip(f"{n} medaglie su 8")


class Elisa(QLabel):
    """Testo semplice su una riga che, se non ci sta, finisce con «…» invece di essere tagliato."""

    def __init__(self, testo=""):
        super().__init__(testo)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        r = self.contentsRect()
        p.drawText(r, int(Qt.AlignLeft | Qt.AlignVCenter), self.fontMetrics().elidedText(self.text(), Qt.ElideRight, r.width()))


def pill(testo, colore):
    """Etichetta colorata dentro un testo ricco (QLabel non ha il padding sugli span: si usano spazi fissi)."""
    return (f"<span style='background:{alfa(colore, 0.18)};color:{colore};font-size:8pt;font-weight:700;'>"
            f"&nbsp;{testo}&nbsp;</span>")


def stato_giocatore(x):
    """(etichetta, colore, cosa, sotto) di un giocatore adesso. In lotta «cosa» è contro chi combatte e «sotto»
    il luogo; in giro «cosa» è il luogo e «sotto» il prossimo obiettivo. Testo semplice, accorciato con «…»."""
    if not x.get("online"):
        return "OFFLINE", TENUE, "non connesso", ""
    if not x.get("emulatore"):
        return "IN ATTESA", TENUE, "gioco chiuso", ""
    luogo = x.get("zona_nome") or ""
    dove = f"📍 {luogo}" if luogo else ""
    a = x.get("attivita") or {}
    if a.get("lotta"):
        sp = a.get("nome_specie") or "?"
        lv = f" Lv.{a['livello']}" if a.get("livello") else ""
        all_ = a.get("allenatore")
        if a.get("nome_allenatore"):
            return "BOSS", KO, a["nome_allenatore"], dove
        if all_ == 0:
            return "SELVATICO", WARN, f"{sp}{lv}", dove
        if all_:
            return "ALLENATORE", WARN, a.get("chi_allenatore") or f"{sp}{lv}", dove
        return "IN LOTTA", WARN, f"{sp}{lv}", dove
    pross = (x.get("prossimo") or {}).get("nome")
    if luogo:
        return "IN GIRO", OK, luogo, f"prossimo: {pross}" if pross else ""
    return "IN GIOCO", OK, "schermata iniziale", ""


class CartaGiocatore(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("giocatore")
        self.setMinimumWidth(190)
        self.setMaximumWidth(340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # avatar a sinistra accanto a nome e stato; la barra dei PS sotto, su tutta la larghezza
        g = QGridLayout(self)
        g.setContentsMargins(12, 9, 12, 9)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(4)
        self.avatar = Avatar(30)
        g.addWidget(self.avatar, 0, 0, 2, 1, Qt.AlignVCenter)
        r1 = QHBoxLayout()
        r1.setSpacing(8)
        self.l_nome = etichetta("")
        self.l_nome.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.l_nome.setMinimumHeight(18)
        self.medaglie = Medaglie(7)
        r1.addWidget(self.l_nome, 1)
        r1.addWidget(self.medaglie, 0, Qt.AlignVCenter)
        g.addLayout(r1, 0, 1)
        r2 = QHBoxLayout()                                   # etichetta colorata + contro chi (con «…» se non ci sta)
        r2.setSpacing(7)
        self.l_stato = etichetta("")
        self.l_stato.setMinimumHeight(19)
        self.l_cosa = Elisa()
        self.l_cosa.setMinimumHeight(19)
        r2.addWidget(self.l_stato, 0)
        r2.addWidget(self.l_cosa, 1)
        g.addLayout(r2, 1, 1)
        self.l_luogo = Elisa()                               # dov'è, su tutta la larghezza
        self.l_luogo.setMinimumHeight(16)
        g.addWidget(self.l_luogo, 2, 0, 1, 2)
        r3 = QHBoxLayout()
        r3.setSpacing(10)
        r3.setContentsMargins(0, 4, 0, 0)
        self.ps = QProgressBar()
        self.ps.setTextVisible(False)
        self.ps.setFixedHeight(5)
        self.l_lv = etichetta("", "piccolo")
        r3.addWidget(self.ps, 1, Qt.AlignVCenter)
        r3.addWidget(self.l_lv, 0, Qt.AlignVCenter)
        g.addLayout(r3, 3, 0, 1, 2)
        g.setColumnStretch(1, 1)

    def imposta(self, g, x, squadra, io=False, colore=ACC):
        online = bool(x.get("online"))
        self.avatar.imposta(g, colore, online)
        self.l_nome.setText(f"<b style='font-size:10.5pt;color:{TESTO if online else TENUE}'>{g}</b>")
        self.l_nome.setToolTip("sei tu" if io else "")
        self.medaglie.imposta(x.get("medaglie") or 0)
        et, c, cosa, sotto = stato_giocatore(x)
        self.l_stato.setText(pill(et, c))
        self.l_cosa.setText(cosa)
        self.l_cosa.setStyleSheet(f"color:{'#ff8a96' if et == 'BOSS' else TESTO if online else TENUE};"
                                  f" font-weight:{700 if et in ('BOSS', 'ALLENATORE', 'SELVATICO') else 400};")
        self.l_luogo.setText(sotto)
        self.l_luogo.setStyleSheet(f"color:{'#aeb2c4' if online else TENUE}; font-size:8.5pt;")
        in_lotta = bool((x.get("attivita") or {}).get("lotta") and x.get("online") and x.get("emulatore"))
        boss = in_lotta and et == "BOSS"
        if self.property("lotta") != (in_lotta and not boss) or self.property("boss") != boss:
            self.setProperty("lotta", in_lotta and not boss)
            self.setProperty("boss", boss)
            self.style().unpolish(self)
            self.style().polish(self)
        tot = sum(p.get("ps_max") or 0 for p in squadra)
        ora = sum(min(p.get("ps") or 0, p.get("ps_max") or 0) for p in squadra)
        self.ps.setRange(0, max(1, tot))
        self.ps.setValue(ora if tot else 0)
        perc = ora / tot if tot else 0
        cb = OK if perc > 0.5 else WARN if perc > 0.2 else KO
        self.ps.setStyleSheet(f"QProgressBar::chunk{{background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {alfa(cb, 0.7)}, stop:1 {cb});}}")
        lv = max((p.get("livello") or 0 for p in squadra), default=0)
        cap = x.get("cap", "?")
        sopra = isinstance(cap, int) and lv > cap
        self.l_lv.setText(f"Lv <b style='color:{KO if sopra else TESTO}'>{lv or '–'}</b>"
                          f" <span style='color:#5b5f73'>·</span> cap <b style='color:{WARN}'>{cap}</b>")
        self.ps.setToolTip(f"PS della squadra: {ora}/{tot}" if tot else "nessun Pokémon in squadra")
        righe = [f"<b>{g}</b> · {x.get('medaglie') or 0} medaglie · level cap {cap} · {len(squadra)} in squadra",
                 f"{et.capitalize()}: {cosa}" + (f" — {sotto}" if sotto else "")]
        a = x.get("attivita") or {}
        if in_lotta and a.get("ps_max"):
            righe[-1] += f" · PS del nemico {round(100 * (a.get('ps') or 0) / a['ps_max'])}%"
        righe.append("")
        for p in squadra:
            righe.append(f"{nome(p)} Lv.{p.get('livello') or '?'} — PS {p.get('ps') or 0}/{p.get('ps_max') or '?'}")
        if not squadra:
            righe.append("nessun Pokémon in squadra")
        self.setToolTip("<br>".join(righe))


class BarraSuperiore(QFrame):
    cambia_partita = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("barra")
        self.setFixedHeight(122)
        h = QHBoxLayout(self)
        h.setContentsMargins(20, 9, 12, 9)
        h.setSpacing(10)
        h.addWidget(logo(44), 0, Qt.AlignVCenter)
        h.addSpacing(6)
        sx = QVBoxLayout()
        sx.setSpacing(7)
        sx.addStretch()
        r0 = QHBoxLayout()
        r0.setSpacing(12)
        r0.addWidget(etichetta(f"Soul Link <span style='color:#b6a4ff;font-weight:600'>Tracker</span>", "titolo"))
        self.b_partita = QPushButton("partita")
        self.b_partita.setObjectName("partita")
        self.b_partita.setCursor(Qt.PointingHandCursor)
        self.b_partita.setToolTip("Codice della partita in corso: clicca per giocarne un'altra o crearne una nuova")
        self.b_partita.clicked.connect(self.cambia_partita.emit)
        r0.addWidget(self.b_partita, 0, Qt.AlignVCenter)
        r0.addStretch()
        sx.addLayout(r0)
        riga = QHBoxLayout()
        riga.setSpacing(12)
        self.l_run = etichetta("Run #–", "pill")
        riga.addWidget(self.l_run, 0, Qt.AlignVCenter)
        self.l_tempo = etichetta("0:00:00", "numero")
        self.l_tempo.setToolTip("Tempo di gioco della run: conta solo quando almeno un giocatore sta giocando")
        riga.addWidget(self.l_tempo, 0, Qt.AlignVCenter)
        self.l_conti = etichetta("")
        riga.addWidget(self.l_conti, 0, Qt.AlignVCenter)
        riga.addStretch()
        sx.addLayout(riga)
        sx.addStretch()
        h.addLayout(sx)
        h.addSpacing(24)
        self.carte = [CartaGiocatore() for _ in range(4)]
        for c in self.carte:
            h.addWidget(c, 2)
            c.hide()
        self.inizio = None
        self.tempo = self.tempo_vivo = None
        self.fermo = False

    def aggiorna(self, st, io):
        stato = st["stato"]
        col = KO if stato == "game_over" else ORO if stato == "vinta" else OK
        testo = {"in_corso": "in corso", "game_over": "GAME OVER", "vinta": "VINTA!"}.get(stato, stato)
        self.l_run.setText(f"Run #{st['run']} · {testo}")
        self.l_run.setStyleSheet(f"background:{alfa(col, 0.14)};color:{col};border:1px solid {alfa(col, 0.35)};")
        self.inizio = st.get("iniziata")
        self.tempo, self.tempo_vivo = st.get("tempo"), st.get("tempo_vivo")
        self.fermo = stato != "in_corso"
        P = list(st["pokemon"].values())
        validi = [p for p in P if not p.get("irregolare")]
        coppie = sum(1 for r in st["percorsi"] if r["stato"] == "attiva")
        morti = sum(1 for p in P if p["stato"] == "morto")
        sep = f"<span style='color:#4a4e62'>&nbsp;&nbsp;·&nbsp;&nbsp;</span>"
        self.l_conti.setText(sep.join([
            f"<b>{len(validi)}</b> <span style='color:{TENUE}'>catture</span>",
            f"<b>{coppie}</b> <span style='color:{TENUE}'>legami vivi</span>",
            f"<b style='color:{KO if morti else TESTO}'>{morti}</b> <span style='color:{TENUE}'>morti</span>"]
            + ([f"<span style='color:{ORO}'>EXP solo dagli allenatori</span>"] if (st.get("regole") or {}).get("solo_allenatori") else [])
            + ([f"<span style='color:#7fd1ff'>Condividi Esp.</span>"] if (st.get("regole") or {}).get("condividi_esp") else [])))
        G = list(st["giocatori"])
        colori = colori_giocatori(st)
        ordine = sorted(G, key=lambda g: (g != io, st["giocatori"][g].get("entrato") or 0, g))
        for i, c in enumerate(self.carte):
            if i < len(ordine):
                g = ordine[i]
                squadra = sorted((p for p in P if p["giocatore"] == g and p["stato"] == "squadra"), key=lambda p: p.get("slot", 0))
                c.imposta(g, st["giocatori"][g], squadra, g == io, colori.get(g, ACC))
                c.show()
            else:
                c.hide()

    def imposta_partita(self, codice):
        self.b_partita.setText(f"{codice or 'nessuna partita'}  ▾")

    def tic(self, fine=None):
        if self.tempo is not None:
            # tempo di gioco condiviso: avanza solo se qualcuno ha giocato nell'ultimo minuto e mezzo
            t = self.tempo
            dt = time.time() - (self.tempo_vivo or 0)
            if not self.fermo and 0 < dt <= 90:
                t += dt
            self.l_tempo.setText(durata(t))
        elif self.inizio and not self.fermo:
            self.l_tempo.setText(durata(time.time() - self.inizio))


# ----------------------------------------------------------------------------------------------
class Carta(QFrame):
    def __init__(self, titolo):
        super().__init__()
        self.setObjectName("carta")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 14, 18, 16)
        self.v.setSpacing(6)
        self.v.addWidget(etichetta(titolo, "sezione"))
        self.v.addSpacing(2)


TIPI_OB = {"palestra": "Capopalestra", "rivale": "Rivale", "plasma": "Team Plasma", "lega": "Superquattro", "campione": "Campionessa",
           "sfida": "Sfida"}


class CartaObiettivo(Carta):
    apri_mappa = Signal()

    def __init__(self):
        super().__init__("PROSSIMO OBIETTIVO")
        from .mappa import MappaUnima
        self.l_nome = etichetta("—", "grande")
        self.l_tipo = etichetta("", a_capo=True)
        self.l_cap = etichetta("")
        self.mappa = MappaUnima(compatta=True)
        self.mappa.setMinimumHeight(96)
        self.mappa.setToolTip("Clicca per aprire la mappa grande con tutti gli obiettivi")
        self.mappa.setCursor(Qt.PointingHandCursor)
        self.mappa.mouseReleaseEvent = lambda e: self.apri_mappa.emit()
        self.l_altro = etichetta("", "tenue", a_capo=True)
        self.v.addWidget(self.l_nome)
        self.v.addWidget(self.l_tipo)
        self.v.addWidget(self.l_cap)
        self.v.addSpacing(2)
        self.v.addWidget(self.mappa, 1)
        self.v.addSpacing(2)
        self.v.addWidget(self.l_altro)

    def aggiorna(self, st, io):
        x = st["giocatori"].get(io) or {}
        o = x.get("prossimo")
        tot = len(st.get("obiettivi", []))
        fatti = len((st.get("fatti") or {}).get(io, {}))
        if o:
            self.l_nome.setText(o["nome"])
            pezzi = [TIPI_OB.get(o["tipo"], o["tipo"]) + (f" · medaglia {o['medaglia']}" if o.get("medaglia") else "")]
            if o.get("luogo_nome"):
                pezzi.append(f"📍 <b style='color:#e6e8f0'>{o['luogo_nome']}</b>")
            pezzi.append(f"{fatti} di {tot} fatti")
            self.l_tipo.setText(f"<span style='color:{TENUE}'>" + " · ".join(pezzi) + "</span>")
        else:
            self.l_nome.setText("Tutto completato!")
            self.l_tipo.setText(f"<span style='color:{TENUE}'>{fatti} di {tot} obiettivi</span>")
        self.l_cap.setText(f"Livello massimo adesso: <b style='color:{WARN};font-size:12pt'>{x.get('cap', '?')}</b>")
        self.mappa.imposta(st, io)
        righe = []
        colori = colori_giocatori(st)
        for g, y in st["giocatori"].items():
            if g == io:
                continue
            po = y.get("prossimo")
            nf = len((st.get("fatti") or {}).get(g, {}))
            righe.append(f"<span style='color:{colori.get(g, ACC)}'>●</span> <b style='color:#c9cbd6'>{g}</b>&nbsp; "
                         f"{po['nome'] if po else 'tutto completato'} <span style='color:#6f7389'>· {nf}/{tot}</span>")
        self.l_altro.setText(paragrafi(righe, 4))
        self.l_altro.setVisible(bool(righe))


class CartaLuogo(Carta):
    def __init__(self):
        super().__init__("DOVE SEI")
        self.l_luogo = etichetta("—", "grande")
        self.l_io = etichetta("", a_capo=True)
        self.l_altro = etichetta("", a_capo=True)
        self.l_nota = etichetta("", "tenue", a_capo=True)
        self.l_conti = etichetta("", a_capo=True)
        self.l_conti.hide()
        self.v.addWidget(self.l_luogo)
        self.v.addWidget(self.l_conti)
        self.v.addSpacing(4)
        self.v.addWidget(self.l_io)
        self.v.addSpacing(2)
        self.v.addWidget(self.l_altro)
        self.v.addSpacing(4)
        self.v.addWidget(self.l_nota)
        self.v.addStretch()

    def imposta_conteggi(self, c):
        """Allenatori ancora da battere e strumenti ancora da raccogliere nel luogo (letti da ROM e memoria)."""
        if not c or (not c["allenatori"] and not c["strumenti"]):
            self.l_conti.hide()
            return
        pezzi = []
        if c["allenatori"]:
            resta = c["allenatori"] - c["battuti"]
            col = OK if resta == 0 else WARN
            t = (f"<b style='color:{col}'>{resta}</b> <span style='color:{TENUE}'>allenator{'e' if resta == 1 else 'i'} da battere su</span> "
                 f"{c['allenatori']}" if resta else f"<span style='color:{OK}'>allenatori tutti battuti</span> <span style='color:{TENUE}'>({c['allenatori']})</span>")
            pezzi.append(f"<span title=''>👤</span> {t}")
        if c["strumenti"]:
            if c["presi"] is None:
                t = f"{c['strumenti']} <span style='color:{TENUE}'>strumenti a terra</span>"
            else:
                resta = c["strumenti"] - c["presi"]
                col = OK if resta == 0 else "#8fc7ff"
                t = (f"<b style='color:{col}'>{resta}</b> <span style='color:{TENUE}'>strument{'o' if resta == 1 else 'i'} da raccogliere su</span> "
                     f"{c['strumenti']}" if resta else f"<span style='color:{OK}'>strumenti tutti raccolti</span> <span style='color:{TENUE}'>({c['strumenti']})</span>")
            pezzi.append(f"🎒 {t}")
        self.l_conti.setText(paragrafi(pezzi, 2))
        self.l_conti.setToolTip("Conteggi letti dalla ROM e dalla memoria del gioco, per tutto il luogo (anche le case e gli edifici "
                                "con lo stesso nome). Strumenti: solo quelli visibili nelle Poké Ball, non quelli nascosti."
                                + ("" if c.get("dal_gioco") else "\nAllenatori battuti: per ora conto le lotte viste dall'app in questa run; "
                                   "dopo un paio di lotte vinte li leggo direttamente dal gioco."))
        self.l_conti.show()

    @staticmethod
    def situazione(riga, g):
        """(testo, colore) dello stato di un giocatore in un luogo."""
        x = (riga or {}).get("giocatori", {}).get(g) or {}
        cat, inc = x.get("cattura"), x.get("incontro")
        if cat:
            stato = {"morto": "morto", "box": "nel box", "liberato": "liberato"}.get(cat["stato"])
            extra = f" <span style='color:{KO if cat['stato'] == 'morto' else TENUE}'>· {stato}</span>" if stato else ""
            return f"ha preso <b>{nome(cat)}</b>{extra}", KO if cat["stato"] == "morto" else OK
        if inc:
            if inc["esito"] == "in_corso":
                return f"in lotta con <b>{inc.get('nome_specie', '?')}</b>", WARN
            if inc["esito"] == "fallito":
                return f"incontro fallito <span style='color:{TENUE}'>({inc.get('nome_specie', '?')})</span>", KO
            if inc["esito"] == "incerto":
                return f"da confermare: {inc.get('nome_specie', '?')} catturato?", WARN
        return f"<span style='color:{TENUE}'>incontro ancora libero</span>", OK

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
        self.l_io.setText(f"<span style='color:{c}'>●</span>&nbsp; <b>Tu</b> — {t}")
        righe, nota = [], ""
        for g in st["giocatori"]:
            if g == io:
                continue
            t2, c2 = self.situazione(riga, g)
            righe.append(f"<span style='color:{c2}'>●</span>&nbsp; <b style='color:#c9cbd6'>{g}</b> — {t2}")
            xa = ((riga or {}).get("giocatori", {}).get(g) or {})
            if xa.get("incontro") and xa["incontro"]["esito"] == "fallito":
                nota = f"{g} ha fallito qui: un'eventuale cattura tua andrà nel box."
        self.l_altro.setText(paragrafi(righe, 5))
        self.l_altro.setVisible(bool(righe))
        self.l_nota.setText(nota)
        self.l_nota.setVisible(bool(nota))


# ----------------------------------------------------------------------------------------------
class MiniPokemon(QWidget):
    apri = None            # funzione chiamata con la chiave del Pokémon al clic (la imposta la finestra)

    def __init__(self, p, sprite, allinea_destra=False, giocatore=None, colore_g=ACC):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.chiave = (p or {}).get("chiave")
        if self.chiave:
            self.setToolTip("Clicca per la scheda: statistiche, mosse, abilità")
            self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        img = QLabel()
        img.setFixedSize(54, 54)
        img.setAlignment(Qt.AlignCenter)
        if p:
            tc = COLORI_TIPI.get((p.get("tipi") or ["?"])[0], "#888888")
            if p["stato"] == "morto":
                tc = "#555a6e"
            img.setStyleSheet(f"background: qradialgradient(cx:0.5, cy:0.55, radius:0.6, fx:0.5, fy:0.55, stop:0 {alfa(tc, 0.32)},"
                              f" stop:1 {alfa(tc, 0.06)}); border-radius: 27px;")
            pm = sprite.pixmap(p["specie"], 50)
            if pm:
                img.setPixmap(pm)
        else:
            img.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 27px;")
        col = QVBoxLayout()
        col.setSpacing(1)
        if p:
            stato = "" if p["stato"] == "squadra" else f" <span style='color:{KO if p['stato'] == 'morto' else WARN}'>· {p['stato']}</span>"
            chi = f"<span style='color:{colore_g};font-weight:600'>{giocatore}</span>&nbsp;&nbsp;" if giocatore else ""
            col.addWidget(etichetta(f"{chi}<b>{nome(p)}</b> <span style='color:{TENUE}'>Lv.{p.get('livello') or '?'}</span>{stato}"))
            tipi = " ".join(f"<span style='color:{COLORI_TIPI.get(t, '#888')}'>{t}</span>" for t in p.get("tipi", []))
            col.addWidget(etichetta(f"<span style='color:{TENUE}'>{p.get('nome_specie', '')}</span> · {tipi}"))
            if p.get("ps_max"):
                b = QProgressBar()
                b.setTextVisible(False)
                b.setRange(0, p["ps_max"])
                b.setValue(p.get("ps") or 0)
                perc = (p.get("ps") or 0) / p["ps_max"]
                c = OK if perc > 0.5 else WARN if perc > 0.2 else KO
                b.setStyleSheet(f"QProgressBar::chunk{{background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {alfa(c, 0.7)}, stop:1 {c});}}")
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


def _clic(self, ev):
    if ev.button() == Qt.LeftButton and self.chiave and MiniPokemon.apri and self.rect().contains(ev.position().toPoint()):
        MiniPokemon.apri(self.chiave)


MiniPokemon.mouseReleaseEvent = _clic


COLORI_EVENTI = {"morte": KO, "gameover": KO, "legame": "#b9a8ff", "cattura": OK, "allarme": WARN,
                 "incontro": "#8fc7ff", "obiettivo": ORO, "premio": ORO}


class PannelloCoppie(QScrollArea):
    def __init__(self, sprite):
        super().__init__()
        self.sprite = sprite
        self.setWidgetResizable(True)
        w = QWidget()
        w.setObjectName("interno")
        self.v = QVBoxLayout(w)
        self.v.setContentsMargins(4, 6, 8, 6)
        self.v.setSpacing(10)
        self.setWidget(w)
        self._firma = None

    def forza(self):
        self._firma = None

    def _eventi(self, st):
        ev = st.get("eventi", [])[:6]
        if not ev:
            return
        self.v.addSpacing(8)
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
        colori = colori_giocatori(st)
        altri = [g for g in G if g != io]
        miei = sorted([p for p in P.values() if p["giocatore"] == io and p["stato"] == "squadra"], key=lambda p: p.get("slot", 0))
        titolo = "LA TUA SQUADRA E I LEGAMI" + (f" CON {', '.join(altri).upper()}" if altri else "")
        self.v.addWidget(etichetta(titolo, "sezione"))
        usati = set()
        for p in miei:
            gruppo = [P[x] for x in p.get("partners", []) if x in P]
            usati.update(q["chiave"] for q in gruppo)
            riga = QFrame()
            riga.setObjectName("coppia")
            if any(q["stato"] != "squadra" for q in gruppo):
                riga.setProperty("allarme", True)
            h = QHBoxLayout(riga)
            h.setContentsMargins(16, 12, 16, 12)
            h.setSpacing(12)
            h.addWidget(MiniPokemon(p, self.sprite), 1, Qt.AlignVCenter)
            catena = etichetta("⛓", stile=f"color:{'#b08cff' if gruppo else '#343850'};font-size:15pt;background:transparent;")
            catena.setToolTip("legati" if gruppo else "nessun legame")
            catena.setAlignment(Qt.AlignCenter)
            catena.setFixedWidth(28)
            h.addWidget(catena)
            destra = QVBoxLayout()
            destra.setSpacing(6)
            for q in gruppo or [None]:
                destra.addWidget(MiniPokemon(q, self.sprite, allinea_destra=True, giocatore=q["giocatore"] if q and len(altri) > 1 else None,
                                             colore_g=colori.get(q["giocatore"], ACC) if q else ACC))
            h.addLayout(destra, 1)
            nel_box = [q for q in gruppo if q["stato"] == "box"]
            if nel_box:
                riga.setToolTip(f"{nome(nel_box[0])} è nel box di {nel_box[0]['giocatore']}: dovresti mettere nel box anche {nome(p)}")
            self.v.addWidget(riga)
        if not miei:
            self.v.addWidget(etichetta("Ancora nessun Pokémon in squadra.", "tenue"))
        for g in altri:
            loro = [p for p in P.values() if p["giocatore"] == g and p["stato"] == "squadra" and p["chiave"] not in usati]
            if loro:
                self.v.addSpacing(6)
                self.v.addWidget(etichetta(f"<span style='color:{colori.get(g, ACC)}'>●</span>&nbsp; IN SQUADRA DA {g.upper()}, SENZA LEGAME CON LA TUA",
                                           "sezione"))
                gr = QGridLayout()
                gr.setHorizontalSpacing(16)
                gr.setVerticalSpacing(8)
                for i, p in enumerate(sorted(loro, key=lambda p: p.get("slot", 0))):
                    gr.addWidget(MiniPokemon(p, self.sprite), i // 2, i % 2)
                self.v.addLayout(gr)
        self._eventi(st)
        box_vivi = [p for p in P.values() if p["giocatore"] == io and p["stato"] == "box"]
        if box_vivi:
            nomi = ", ".join(nome(p) for p in box_vivi[:12]) + ("…" if len(box_vivi) > 12 else "")
            self.v.addSpacing(8)
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


# ----------------------------------------------------------------------------------------------
class Notifiche(QWidget):
    """Notifiche a comparsa in basso a destra (sopra i pannelli, non sopra il gioco)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(8)
        self.v.addStretch()
        self.setFixedWidth(360)
        self.attive = []

    def mostra(self, testo, colore=None, secondi=6):
        from PySide6.QtCore import QTimer
        t = testo.lower()
        if colore is None:
            colore = (KO if ("morto" in t or "game over" in t) else
                      ORO if any(x in t for x in ("traguardo", "battuto", "obiettivo", "medaglia", "vinta")) else
                      "#b9a8ff" if ("legame" in t or "shiny" in t) else
                      WARN if any(x in t for x in ("fallito", "attenzione", "regola", "box")) else
                      OK if "primo incontro" in t else "#c9cbd6")
        f = QFrame()
        f.setObjectName("notifica")
        ombra(f, 28, 160, 8)
        h = QHBoxLayout(f)
        h.setContentsMargins(12, 10, 14, 10)
        h.setSpacing(10)
        barra = QLabel()
        barra.setFixedWidth(4)
        barra.setStyleSheet(f"background:{colore};border-radius:2px;")
        h.addWidget(barra)
        l = etichetta(testo, a_capo=True)
        h.addWidget(l, 1)
        self._aggiungi(f, secondi)

    def grande(self, titolo, testo="", colore=OK, simbolo="!", secondi=12):
        """Notifica importante: più grande, colorata e più lunga; se l'app non è in primo piano
        fa lampeggiare la sua icona nella barra delle applicazioni."""
        from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect
        f = QFrame()
        f.setObjectName("notificaGrande")
        f.grande = True
        def misto(a, b, t):                       # colore pieno (non trasparente: sotto c'è altro testo)
            ca, cb = QColor(a), QColor(b)
            return QColor(round(ca.red() * t + cb.red() * (1 - t)), round(ca.green() * t + cb.green() * (1 - t)),
                          round(ca.blue() * t + cb.blue() * (1 - t))).name()
        f.setStyleSheet(f"QFrame#notificaGrande {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {misto(colore, '#262a3c', 0.22)},"
                        f" stop:0.6 #262a3c, stop:1 #222536); border: 1px solid {misto(colore, '#262a3c', 0.7)}; border-radius: 14px; }}")
        e = QGraphicsDropShadowEffect(f)
        e.setBlurRadius(34)
        e.setOffset(0, 6)
        c = QColor(colore)
        c.setAlpha(150)
        e.setColor(c)
        f.setGraphicsEffect(e)
        h = QHBoxLayout(f)
        h.setContentsMargins(14, 14, 16, 14)
        h.setSpacing(14)
        tondo = QLabel(simbolo)
        tondo.setFixedSize(38, 38)
        tondo.setAlignment(Qt.AlignCenter)
        tondo.setStyleSheet(f"background:{colore}; color:#14151d; border-radius:19px; font-weight:800;"
                            f" font-size:{15 if len(simbolo) == 1 else 10}pt;")
        h.addWidget(tondo, 0, Qt.AlignTop)
        v = QVBoxLayout()
        v.setSpacing(4)
        t = etichetta(titolo, a_capo=True, stile=f"color:{colore}; font-size:12.5pt; font-weight:800; background:transparent;")
        v.addWidget(t)
        if testo:
            v.addWidget(etichetta(testo, a_capo=True, stile="color:#e6e8f0; font-size:10pt; background:transparent;"))
        h.addLayout(v, 1)
        self._aggiungi(f, secondi)
        finestra = self.window()
        if finestra and not finestra.isActiveWindow():
            QApplication.alert(finestra, 0)

    def _aggiungi(self, f, secondi):
        from PySide6.QtCore import QTimer
        self.v.addWidget(f)
        self.attive.append(f)
        while len(self.attive) > 3:                    # tolgo prima le notifiche normali, poi le importanti
            vecchia = next((x for x in self.attive if not getattr(x, "grande", False)), self.attive[0])
            self.attive.remove(vecchia)
            vecchia.hide()
            self.v.removeWidget(vecchia)
            vecchia.deleteLater()
        self.riposiziona()
        self.show()
        self.raise_()

        def togli():
            if f in self.attive:
                self.attive.remove(f)
                f.hide()
                self.v.removeWidget(f)
                f.deleteLater()
            QTimer.singleShot(50, self.riposiziona)
        QTimer.singleShot(int(secondi * 1000), togli)

    def riposiziona(self):
        p = self.parentWidget()
        if not p:
            return
        h = min(p.height() - 24, 420)          # il riquadro è trasparente: le notifiche stanno in fondo
        self.setGeometry(p.width() - self.width() - 14, p.height() - h - 12, self.width(), h)
