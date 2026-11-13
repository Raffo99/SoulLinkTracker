"""Finestra delle impostazioni (si apre da sola al primo avvio).

A sinistra gli argomenti, a destra una pagina per argomento. La pagina «Collegamento» fa scegliere tra il
collegamento diretto tra le app e Supabase con due schede affiancate e uno schema di come viaggiano i dati.
"""
import threading

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
                               QStackedWidget, QVBoxLayout, QWidget)

from .stile import ACC, KO, OK, TENUE, TESTO, WARN

CIANO = "#38c6d9"


class CampoFile(QWidget):
    def __init__(self, valore, filtro="", cartella=False):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.e = QLineEdit(valore or "")
        self.e.setMinimumWidth(120)
        b = QPushButton("Sfoglia…")
        b.clicked.connect(lambda: self._scegli(filtro, cartella))
        h.addWidget(self.e, 1)
        h.addWidget(b)

    def _scegli(self, filtro, cartella):
        if cartella:
            p = QFileDialog.getExistingDirectory(self, "Scegli cartella", self.e.text())
        else:
            p, _ = QFileDialog.getOpenFileName(self, "Scegli file", self.e.text(), filtro)
        if p:
            self.e.setText(p)

    def text(self):
        return self.e.text().strip()


# ---------------------------------------------------------------------------------------------- collegamento
class SchemaCollegamento(QWidget):
    """Disegno di come viaggiano i dati con il collegamento scelto: è la cosa da capire prima di scegliere."""

    def __init__(self):
        super().__init__()
        self.modo = "p2p"
        self.setFixedHeight(132)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def imposta(self, modo):
        self.modo = modo
        self.update()

    def _nodo(self, p, c: QPointF, testo, sotto, colore):
        r = QRectF(c.x() - 56, c.y() - 20, 112, 40)
        p.setPen(QPen(QColor(colore), 1.4))
        sf = QColor(colore)
        sf.setAlpha(34)
        p.setBrush(sf)
        p.drawRoundedRect(r, 10, 10)
        f = QFont(self.font())
        f.setPointSizeF(9)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(TESTO))
        p.drawText(r, Qt.AlignCenter, testo)
        if sotto:
            f.setPointSizeF(8)
            f.setWeight(QFont.Normal)
            p.setFont(f)
            p.setPen(QColor(TENUE))
            p.drawText(QRectF(c.x() - 110, r.bottom() + 5, 220, 16), Qt.AlignCenter, sotto)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawRoundedRect(QRectF(0, 0, w, h), 14, 14)
        sx, dx = QPointF(78, 40), QPointF(w - 78, 40)
        f = QFont(self.font())
        f.setPointSizeF(8)
        if self.modo == "p2p":
            # linea diretta, nei due colori del legame
            g = QLinearGradient(sx, dx)
            g.setColorAt(0, QColor(ACC))
            g.setColorAt(1, QColor(CIANO))
            p.setPen(QPen(g, 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(sx.x() + 56, sx.y()), QPointF(dx.x() - 56, dx.y()))
            p.setFont(f)
            p.setPen(QColor(TESTO))
            p.drawText(QRectF(sx.x() + 56, sx.y() - 22, dx.x() - sx.x() - 112, 18), Qt.AlignCenter, "linea diretta, cifrata")
            # relay: tratteggiato, sotto
            rel = QPointF(w / 2, 92)
            p.setPen(QPen(QColor(TENUE), 1.3, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            for a in (sx, dx):
                via = QPainterPath(QPointF(a.x(), a.y() + 20))
                via.quadTo(QPointF(a.x(), rel.y()), QPointF(rel.x() + (-70 if a is sx else 70), rel.y()))
                p.drawPath(via)
            p.setPen(QPen(QColor(TENUE), 1.2))
            p.setBrush(QColor(255, 255, 255, 14))
            rr = QRectF(rel.x() - 70, rel.y() - 14, 140, 28)
            p.drawRoundedRect(rr, 15, 15)
            p.setPen(QColor("#c3c6d4"))
            p.drawText(rr, Qt.AlignCenter, "relay pubblici")
            self._nodo(p, sx, "Il tuo PC", "", ACC)
            self._nodo(p, dx, "Gli amici", "", CIANO)
            p.setFont(f)
            p.setPen(QColor(TENUE))
            p.drawText(QRectF(0, h - 20, w, 16), Qt.AlignCenter, "servono per trovarsi, e di riserva se la linea diretta è bloccata")
        else:
            db = QPointF(w / 2, 40)
            p.setPen(QPen(QColor(OK), 2.4, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(sx.x() + 56, sx.y()), QPointF(db.x() - 68, db.y()))
            p.drawLine(QPointF(db.x() + 68, db.y()), QPointF(dx.x() - 56, dx.y()))
            r = QRectF(db.x() - 68, db.y() - 22, 136, 44)
            sf = QColor(OK)
            sf.setAlpha(34)
            p.setBrush(sf)
            p.setPen(QPen(QColor(OK), 1.4))
            p.drawRoundedRect(r, 10, 10)
            f2 = QFont(self.font())
            f2.setPointSizeF(9)
            f2.setWeight(QFont.DemiBold)
            p.setFont(f2)
            p.setPen(QColor(TESTO))
            p.drawText(r, Qt.AlignCenter, "Il vostro Supabase")
            self._nodo(p, sx, "Il tuo PC", "", ACC)
            self._nodo(p, dx, "Gli amici", "", CIANO)
            p.setFont(f)
            p.setPen(QColor(TENUE))
            p.drawText(QRectF(0, 80, w, 16), Qt.AlignCenter, "la partita sta nel database di uno di voi")
            p.drawText(QRectF(0, h - 30, w, 16), Qt.AlignCenter, "ogni app legge e scrive lì")
        p.end()


class Opzione(QFrame):
    """Scheda da scegliere (una delle due): titolo, una frase, tre fatti."""
    scelta = Signal(str)

    def __init__(self, chiave, titolo, frase, fatti, colore, etichetta=""):
        super().__init__()
        self.chiave, self.colore = chiave, colore
        self.setObjectName("opzione")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)      # le due schede sempre larghe uguali
        self.setMinimumWidth(220)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)
        testa = QHBoxLayout()
        testa.setSpacing(8)
        self.pallino = QLabel()
        self.pallino.setFixedSize(18, 18)
        testa.addWidget(self.pallino, 0, Qt.AlignVCenter)
        t = QLabel(titolo)
        t.setStyleSheet("font-size: 11.5pt; font-weight: 700;")
        testa.addWidget(t, 0, Qt.AlignVCenter)
        testa.addStretch()
        if etichetta:
            e = QLabel(etichetta)
            e.setStyleSheet(f"background: rgba(139,108,255,0.20); color: #d9d0ff; border-radius: 8px; padding: 2px 8px;"
                            f" font-size: 8pt; font-weight: 600;")
            testa.addWidget(e, 0, Qt.AlignVCenter)
        v.addLayout(testa)
        fr = QLabel(frase)
        fr.setWordWrap(True)
        fr.setStyleSheet("color: #c3c6d4;")
        v.addWidget(fr)
        v.addSpacing(4)
        for segno, testo in fatti:
            col = OK if segno == "+" else WARN
            l = QLabel(f"<span style='color:{col};font-weight:700'>{'✓' if segno == '+' else '!'}</span>&nbsp;&nbsp;{testo}")
            l.setWordWrap(True)
            l.setStyleSheet("font-size: 9pt;")
            v.addWidget(l)
        v.addStretch()
        self.imposta(False)

    def imposta(self, scelta: bool):
        self.setProperty("scelta", "true" if scelta else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        c = self.colore
        if scelta:
            self.pallino.setStyleSheet(f"background: {c}; border: 4px solid #171923; border-radius: 9px;"
                                       f" outline: none;")
            self.setStyleSheet(f"QFrame#opzione {{ border: 2px solid {c}; }}")
        else:
            self.pallino.setStyleSheet("background: transparent; border: 2px solid #4a4f66; border-radius: 9px;")
            self.setStyleSheet("")

    def mousePressEvent(self, ev):
        self.scelta.emit(self.chiave)

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.scelta.emit(self.chiave)
        else:
            super().keyPressEvent(ev)


# ---------------------------------------------------------------------------------------------- finestra
class Impostazioni(QDialog):
    _esito_prova = Signal(str, str)

    PAGINE = [("partita", "Tu e la partita"), ("rete", "Collegamento"), ("gioco", "Gioco"),
              ("salvataggi", "Salvataggi"), ("altro", "Altro")]

    def __init__(self, cfg, parent=None, mancanti=None, pagina=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Impostazioni – Soul Link Tracker")
        self.setSizeGripEnabled(True)
        self.setMinimumSize(640, 420)
        schermo = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        larg, alt = 900, 660
        if schermo:
            larg, alt = min(larg, schermo.width() - 60), min(alt, schermo.height() - 80)
        self.resize(larg, alt)
        self._esito_prova.connect(self._mostra_esito)

        esterno = QVBoxLayout(self)
        esterno.setContentsMargins(0, 0, 0, 0)
        esterno.setSpacing(0)
        corpo = QHBoxLayout()
        corpo.setContentsMargins(0, 0, 0, 0)
        corpo.setSpacing(0)
        esterno.addLayout(corpo, 1)

        # ---- argomenti a sinistra
        fianco = QFrame()
        fianco.setObjectName("fianco")
        fianco.setFixedWidth(196)
        fv = QVBoxLayout(fianco)
        fv.setContentsMargins(12, 18, 12, 14)
        fv.setSpacing(10)
        t = QLabel("Impostazioni")
        t.setStyleSheet("font-size: 13pt; font-weight: 700; padding-left: 8px;")
        fv.addWidget(t)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        fv.addWidget(self.nav, 1)
        corpo.addWidget(fianco)

        self.pile = QStackedWidget()
        corpo.addWidget(self.pile, 1)
        self._voci = {}
        costruttori = {"partita": self._pagina_partita, "rete": self._pagina_rete, "gioco": self._pagina_gioco,
                       "salvataggi": self._pagina_salvataggi, "altro": self._pagina_altro}
        for chiave, nome in self.PAGINE:
            it = QListWidgetItem(nome)
            self.nav.addItem(it)
            self._voci[chiave] = it
            self.pile.addWidget(self._scorrevole(costruttori[chiave]()))
        self.nav.currentRowChanged.connect(self.pile.setCurrentIndex)

        # ---- pulsanti in basso
        piede = QFrame()
        piede.setObjectName("piede")
        ph = QHBoxLayout(piede)
        ph.setContentsMargins(20, 12, 20, 12)
        ph.setSpacing(8)
        self.l_manca = QLabel("")
        self.l_manca.setStyleSheet(f"color: {WARN};")
        ph.addWidget(self.l_manca, 1)
        annulla = QPushButton("Annulla")
        annulla.setMinimumWidth(96)
        annulla.clicked.connect(self.reject)
        salva = QPushButton("Salva")
        salva.setObjectName("primario")
        salva.setMinimumWidth(96)
        salva.setDefault(True)
        salva.clicked.connect(self._salva)
        ph.addWidget(annulla)
        ph.addWidget(salva)
        esterno.addWidget(piede)

        self._segna_mancanti(mancanti)
        self._scegli_rete(self._rete)
        if pagina:
            self.nav.setCurrentRow([c for c, _ in self.PAGINE].index(pagina))

    # ---------------------------------------------------------------- pezzi comuni
    @staticmethod
    def _scorrevole(pagina):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(pagina)
        return area

    @staticmethod
    def _pagina(titolo, sotto):
        w = QWidget()
        w.setObjectName("interno")
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 22, 28, 18)
        v.setSpacing(14)
        t = QLabel(titolo)
        t.setStyleSheet("font-size: 15pt; font-weight: 700; letter-spacing: -0.2px;")
        v.addWidget(t)
        if sotto:
            s = QLabel(sotto)
            s.setWordWrap(True)
            s.setObjectName("tenue")
            v.addWidget(s)
            v.addSpacing(2)
        return w, v

    @staticmethod
    def _campo(v, nome, widget, aiuto=""):
        """Nome sopra, campo, e sotto una riga che spiega (al posto dei suggerimenti nascosti)."""
        blocco = QVBoxLayout()
        blocco.setSpacing(5)
        if nome:
            n = QLabel(nome)
            n.setStyleSheet("font-weight: 600;")
            blocco.addWidget(n)
        blocco.addWidget(widget)
        if aiuto:
            a = QLabel(aiuto)
            a.setWordWrap(True)
            a.setObjectName("piccolo")
            blocco.addWidget(a)
        v.addLayout(blocco)
        return widget

    # ---------------------------------------------------------------- pagine
    def _pagina_partita(self):
        cfg = self.cfg
        w, v = self._pagina("Tu e la partita", "Chi sei e in quale Soul Link giochi.")
        self.giocatore = QLineEdit(cfg["giocatore"])
        self.giocatore.setPlaceholderText("es. Raffaele")
        self.giocatore.setMaximumWidth(320)
        self._campo(v, "Il tuo nome", self.giocatore, "Diverso da quello degli amici: è il nome che vedono nel tracker.")
        riga = QWidget()
        h = QHBoxLayout(riga)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.codice = QLineEdit(cfg["codice"])
        self.codice.setPlaceholderText("es. drago-luna-4821-k7q2xm")
        self.codice.setStyleSheet("font-size: 11pt; font-weight: 600;")
        self.codice.setMinimumHeight(34)
        b_copia = QPushButton("Copia")
        b_copia.setToolTip("Copia il codice per mandarlo agli amici")

        def copia():
            QApplication.clipboard().setText(self.codice.text().strip())
            b_copia.setText("Copiato")
        b_copia.clicked.connect(copia)
        b_nuovo = QPushButton("Nuovo codice")

        def nuovo():
            from .partite import codice_nuovo
            self.codice.setText(codice_nuovo())
            b_copia.setText("Copia")
        b_nuovo.clicked.connect(nuovo)
        h.addWidget(self.codice, 1)
        h.addWidget(b_copia)
        h.addWidget(b_nuovo)
        self._campo(v, "Codice della partita", riga,
                    "Uguale per tutti: chi usa lo stesso codice gioca nello stesso Soul Link. Con il collegamento diretto "
                    "è anche la chiave che cifra i dati, quindi mandalo solo agli amici. "
                    "Per tenere più partite usa «Cambia partita» (clic sul codice in alto).")
        v.addStretch()
        return w

    def _pagina_rete(self):
        cfg = self.cfg
        w, v = self._pagina("Collegamento", "Come si scambiano i dati le vostre app. Tutti i giocatori della stessa "
                                            "partita devono scegliere lo stesso.")
        self._rete = "supabase" if cfg.get("rete") == "supabase" else "p2p"
        riga = QHBoxLayout()
        riga.setSpacing(12)
        self.o_p2p = Opzione("p2p", "Diretto tra le app", "Le app si trovano con il codice della partita e poi parlano tra loro.",
                             [("+", "Niente account, niente da configurare"),
                              ("+", "Basta mandare il codice agli amici"),
                              ("!", "Passa da relay pubblici gratuiti: se non rispondono, la partita si aggiorna appena tornano")],
                             ACC, "Consigliato")
        self.o_sb = Opzione("supabase", "Supabase", "La partita sta in un database gratuito creato da uno di voi.",
                            [("+", "Un posto solo, vostro, sempre raggiungibile"),
                             ("!", "Uno di voi crea il progetto (circa 5 minuti)"),
                             ("!", "Tutti inseriscono indirizzo e chiave")],
                            OK)
        for o in (self.o_p2p, self.o_sb):
            o.scelta.connect(self._scegli_rete)
            riga.addWidget(o, 1)
        v.addLayout(riga)
        self.schema = SchemaCollegamento()
        v.addWidget(self.schema)

        # --- diretto
        self.box_p2p = QWidget()
        bv = QVBoxLayout(self.box_p2p)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(8)
        nota = QLabel("I dati sono cifrati con il codice della partita: i relay vedono solo dati illeggibili. "
                      "Viaggiano solo i dati del tracker, mai ROM o salvataggi.")
        nota.setWordWrap(True)
        nota.setObjectName("tenue")
        bv.addWidget(nota)
        self.l_passaggio = QLabel("Avevate una partita su Supabase? La prima app che entra la porta con sé: "
                                  "lasciate indirizzo e chiave nella scheda Supabase finché non siete entrati tutti.")
        self.l_passaggio.setWordWrap(True)
        self.l_passaggio.setObjectName("avvisi")
        self.l_passaggio.setVisible(bool((cfg.get("supabase_url") or "").strip()))
        bv.addWidget(self.l_passaggio)
        v.addWidget(self.box_p2p)

        # --- Supabase
        self.box_sb = QWidget()
        sv = QVBoxLayout(self.box_sb)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(12)
        self.sb_url = QLineEdit(cfg.get("supabase_url", ""))
        self.sb_url.setPlaceholderText("https://xxxxxxxx.supabase.co")
        self._campo(sv, "Indirizzo del progetto", self.sb_url, "In Supabase: Project Settings → Data API → Project URL.")
        self.sb_chiave = QLineEdit(cfg.get("supabase_chiave", ""))
        self.sb_chiave.setPlaceholderText("sb_publishable_…")
        self._campo(sv, "Chiave pubblica", self.sb_chiave, "In Supabase: Project Settings → API Keys → Publishable key. "
                                                           "Come si crea il progetto è spiegato nella guida (LEGGIMI).")
        v.addWidget(self.box_sb)

        # --- prova
        pr = QHBoxLayout()
        pr.setSpacing(12)
        self.b_prova = QPushButton("Prova il collegamento")
        self.b_prova.clicked.connect(self._prova)
        pr.addWidget(self.b_prova)
        self.l_esito = QLabel("")
        self.l_esito.setWordWrap(True)
        pr.addWidget(self.l_esito, 1)
        v.addLayout(pr)
        v.addStretch()
        return w

    def _pagina_gioco(self):
        cfg = self.cfg
        w, v = self._pagina("Gioco", "L'emulatore, il randomizer e la tua ROM.")
        self.rom = CampoFile(cfg["rom_originale"], "ROM Nintendo DS (*.nds)")
        self._campo(v, "La tua ROM di Nero 2", self.rom, "Il file .nds originale: l'app non lo modifica, ne crea una copia randomizzata per ogni run.")
        self.jar = CampoFile(cfg["jar"], "Randomizer (*.jar)")
        self._campo(v, "Randomizer", self.jar, "Il file PokeRandoZX.jar di Universal Pokémon Randomizer ZX.")
        self.imp = CampoFile(cfg["impostazioni"], "Impostazioni randomizer (*.rnqs)")
        self._campo(v, "Impostazioni del randomizer", self.imp, "Il file .rnqs, uguale per tutti i giocatori.")
        self.java = QLineEdit(cfg["java"])
        self.java.setPlaceholderText("java")
        self._campo(v, "Java", self.java, "Lascia «java» se è installato; altrimenti il percorso di java.exe a 64 bit.")
        self.melon = CampoFile(cfg.get("melonds", ""), "melonDS (melonDS.exe)")
        self.melon.e.setPlaceholderText("la copia dell'app")
        self._campo(v, "melonDS", self.melon, "Lascia vuoto: l'app scarica melonDS da sola e ne usa una copia sua. "
                                              "Indicane uno solo se il download non riesce.")
        v.addStretch()
        return w

    def _pagina_salvataggi(self):
        cfg = self.cfg
        w, v = self._pagina("Salvataggi", "Dove stanno i file della partita e ogni quanto l'app ne fa una copia.")
        self.backup = QComboBox()
        self.backup.setMaximumWidth(260)
        self._minuti = [0, 5, 10, 15, 20, 30, 60]
        for m in self._minuti:
            self.backup.addItem("solo quando chiudi" if m == 0 else f"ogni {m} minuti")
        attuale = int(cfg.get("backup_minuti", 10) or 0)
        self.backup.setCurrentIndex(self._minuti.index(attuale) if attuale in self._minuti else 2)
        self._campo(v, "Backup automatico", self.backup, "L'app salva il punto esatto in cui sei. Alla chiusura lo fa sempre.")
        self.salta = QCheckBox("Salta l'inizio del gioco a ogni nuova run")
        self.salta.setChecked(cfg["salta_inizio"])
        self._campo(v, "", self.salta, "Riparti dal salvataggio di partenza, fatto prima della scena dello starter.")
        self.dati = CampoFile(cfg["cartella_dati"], cartella=True)
        self._campo(v, "Cartella di ROM e salvataggi", self.dati, "Qui finiscono le ROM generate, i backup e gli stati salvati.")
        self.saveram = CampoFile(cfg.get("cartella_salvataggi", ""), cartella=True)
        self.saveram.e.setPlaceholderText("dentro la cartella qui sopra")
        self._campo(v, "Salvataggi del gioco", self.saveram, "Lascia vuoto per tenerli nella cartella qui sopra.")
        v.addStretch()
        return w

    def _pagina_altro(self):
        cfg = self.cfg
        w, v = self._pagina("Altro", "")
        self.agg = QCheckBox("Cerca aggiornamenti all'avvio")
        self.agg.setChecked(cfg.get("aggiorna_auto", True) is not False)
        self._campo(v, "", self.agg, "Se c'è una versione nuova te lo chiede e, se vuoi, si aggiorna da sola.")
        self.diag = QCheckBox("Diagnostica della memoria")
        self.diag.setChecked(cfg["diagnostica"])
        self._campo(v, "", self.diag, "Mostra nella scheda Sistema i dati letti dal gioco. Serve solo per cercare un problema.")
        v.addStretch()
        return w

    # ---------------------------------------------------------------- collegamento
    def _scegli_rete(self, modo):
        self._rete = modo
        self.o_p2p.imposta(modo == "p2p")
        self.o_sb.imposta(modo == "supabase")
        self.schema.imposta(modo)
        self.box_p2p.setVisible(modo == "p2p")
        self.box_sb.setVisible(modo == "supabase")
        self.l_esito.setText("")

    def _prova(self):
        self.b_prova.setEnabled(False)
        self.l_esito.setStyleSheet(f"color: {TENUE};")
        self.l_esito.setText("Provo…")
        modo, codice = self._rete, self.codice.text().strip()
        url, chiave = self.sb_url.text(), self.sb_chiave.text()

        def lavoro():
            try:
                if modo == "supabase":
                    from .archivio import Archivio
                    a = Archivio(url, chiave, codice)
                    ver = a.versione()
                    gioc = ", ".join(a.presenze()) or "nessuno online"
                    self._esito_prova.emit("ok", "Funziona. La partita non esiste ancora: verrà creata al primo avvio."
                                           if ver is None else f"Funziona. Partita trovata ({gioc}).")
                else:
                    import time
                    from .rete.trasporto import Rete
                    r = Rete(codice or "prova", "?", lambda m, v: None, webrtc=False)
                    r.avvia()
                    fine = time.time() + 6
                    while time.time() < fine and not (r.stato()["mqtt"] >= 2 and r.stato()["nostr"] >= 2):
                        time.sleep(0.2)
                    st = r.stato()
                    r.ferma()
                    if st["mqtt"] or st["nostr"]:
                        altri = f" Amici visti ora: {st['altri']}." if st["altri"] else ""
                        self._esito_prova.emit("ok", f"Funziona: rispondono {st['mqtt']} relay su {len(r.broker)} per i dati "
                                                     f"e {st['nostr']} per trovarsi.{altri}")
                    else:
                        self._esito_prova.emit("errore", "Nessun relay risponde. Controlla la connessione a internet o il "
                                                         "firewall; se non si risolve, usate Supabase.")
            except Exception as e:
                self._esito_prova.emit("errore", str(e))
        threading.Thread(target=lavoro, daemon=True).start()

    def _mostra_esito(self, tipo, testo):
        try:
            self.b_prova.setEnabled(True)
            self.l_esito.setStyleSheet(f"color: {OK if tipo == 'ok' else KO};")
            self.l_esito.setText(testo)
        except RuntimeError:
            pass

    # ---------------------------------------------------------------- primo avvio e salvataggio
    def _segna_mancanti(self, mancanti):
        """Al primo avvio: un pallino accanto agli argomenti con qualcosa da compilare, e si apre sul primo."""
        dove = {"nome giocatore": "partita", "codice della partita": "partita", "indirizzo Supabase": "rete",
                "chiave Supabase": "rete", "randomizer": "gioco", "impostazioni .rnqs": "gioco", "la tua ROM": "gioco"}
        pagine = [dove.get(m) for m in (mancanti or []) if dove.get(m)]
        for chiave, nome in self.PAGINE:
            self._voci[chiave].setText(nome + ("   ●" if chiave in pagine else ""))
            if chiave in pagine:
                self._voci[chiave].setForeground(QColor(WARN))
        if mancanti:
            self.l_manca.setText("Per iniziare manca: " + ", ".join(mancanti) + ".")
        prima = next((i for i, (c, _) in enumerate(self.PAGINE) if c in pagine), 0)
        self.nav.setCurrentRow(prima)

    def _salva(self):
        c = self.cfg
        c.update(giocatore=self.giocatore.text().strip(), supabase_url=self.sb_url.text().strip().rstrip("/"),
                 supabase_chiave=self.sb_chiave.text().strip(), codice=self.codice.text().strip(), rete=self._rete,
                 melonds=self.melon.text().strip(), randomizza=True,
                 java=self.java.text().strip() or "java", jar=self.jar.text(), impostazioni=self.imp.text(),
                 rom_originale=self.rom.text(), cartella_dati=self.dati.text() or c["cartella_dati"],
                 salta_inizio=self.salta.isChecked(), cartella_salvataggi=self.saveram.text(), diagnostica=self.diag.isChecked(),
                 backup_minuti=self._minuti[self.backup.currentIndex()], aggiorna_auto=self.agg.isChecked())
        c.salva()
        self.accept()
