"""Finestre di dialogo dell'app (domande, avvisi, scelte), in italiano e con lo stile dell'interfaccia.
Sostituiscono QMessageBox, che ha i pulsanti in inglese e si impagina male con il foglio di stile."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from .stile import ACC, KO, OK, WARN, alfa

TIPI = {
    "domanda": ("?", ACC),
    "info": ("i", ACC),
    "ok": ("✓", OK),
    "avviso": ("!", WARN),
    "errore": ("✕", KO),
}

# per i test automatici: se impostata, le domande non si aprono e rispondono così
RISPOSTA_AUTOMATICA = None


class Dialogo(QDialog):
    def __init__(self, parent, titolo, testo, tipo="info", pulsanti=(("ok", "OK", "primario"),), dettagli=None,
                 predefinito=None, annulla=None):
        super().__init__(parent)
        self.setWindowTitle(titolo)
        self.setObjectName("dialogo")
        self.setModal(True)
        self.scelta = annulla
        self._annulla = annulla
        self.setMinimumWidth(460)
        self.setMaximumWidth(620)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 18)
        v.setSpacing(16)
        corpo = QHBoxLayout()
        corpo.setSpacing(16)
        segno, colore = TIPI.get(tipo, TIPI["info"])
        icona = QLabel(segno)
        icona.setFixedSize(40, 40)
        icona.setAlignment(Qt.AlignCenter)
        icona.setStyleSheet(f"background:{alfa(colore, 0.16)}; color:{colore}; border:1px solid {alfa(colore, 0.4)};"
                            f"border-radius:20px; font-size:15pt; font-weight:700;")
        corpo.addWidget(icona, 0, Qt.AlignTop)
        testi = QVBoxLayout()
        testi.setSpacing(6)
        t = QLabel(titolo)
        t.setObjectName("dialogoTitolo")
        t.setWordWrap(True)
        testi.addWidget(t)
        if testo:
            l = QLabel(testo)
            l.setObjectName("dialogoTesto")
            l.setWordWrap(True)
            l.setTextFormat(Qt.RichText if "<" in testo and ">" in testo else Qt.PlainText)
            l.setTextInteractionFlags(Qt.TextSelectableByMouse)
            l.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            l.setMinimumWidth(300)
            testi.addWidget(l)
        corpo.addLayout(testi, 1)
        v.addLayout(corpo)

        if dettagli:
            self.b_dettagli = QPushButton("Mostra i dettagli")
            self.b_dettagli.setObjectName("collegamento")
            self.b_dettagli.setCursor(Qt.PointingHandCursor)
            self.dett = QPlainTextEdit(dettagli)
            self.dett.setReadOnly(True)
            self.dett.setObjectName("dettagli")
            self.dett.setFixedHeight(140)
            self.dett.hide()

            def apri():
                vis = not self.dett.isVisible()
                self.dett.setVisible(vis)
                self.b_dettagli.setText("Nascondi i dettagli" if vis else "Mostra i dettagli")
                self.adjustSize()
            self.b_dettagli.clicked.connect(apri)
            riga = QHBoxLayout()
            riga.addSpacing(56)
            riga.addWidget(self.b_dettagli)
            riga.addStretch()
            v.addLayout(riga)
            v.addWidget(self.dett)

        r = QHBoxLayout()
        r.setSpacing(8)
        r.addStretch()
        primo = None
        for chiave, etichetta, stile in pulsanti:
            b = QPushButton(etichetta)
            if stile:
                b.setObjectName(stile)
            b.setMinimumWidth(92)
            b.setAutoDefault(False)
            b.clicked.connect(lambda _=False, k=chiave: self._scegli(k))
            r.addWidget(b)
            if chiave == predefinito or (predefinito is None and stile == "primario" and primo is None):
                primo = b
        if primo:
            primo.setDefault(True)
            primo.setFocus()
        v.addLayout(r)
        self.adjustSize()

    def _scegli(self, k):
        self.scelta = k
        self.accept()

    def reject(self):
        self.scelta = self._annulla
        super().reject()

    def esegui(self):
        self.exec()
        return self.scelta


def _genitore(parent):
    if isinstance(parent, QWidget):
        return parent
    return QApplication.activeWindow()


def chiedi(parent, titolo, testo="", si="Sì", no="No", pericolo=False, tipo="domanda", dettagli=None) -> bool:
    """Domanda sì/no. Esc o chiusura della finestra = no."""
    if RISPOSTA_AUTOMATICA is not None:
        return bool(RISPOSTA_AUTOMATICA)
    d = Dialogo(_genitore(parent), titolo, testo, tipo,
                (("no", no, None), ("si", si, "pericolo" if pericolo else "primario")), dettagli,
                predefinito="no" if pericolo else "si", annulla="no")
    return d.esegui() == "si"


def scegli(parent, titolo, testo, opzioni, tipo="domanda", annulla="annulla"):
    """opzioni: [(chiave, etichetta, stile)], stile = "primario" / "pericolo" / None. Restituisce la chiave (o annulla)."""
    if RISPOSTA_AUTOMATICA is not None:
        return opzioni[-1][0] if RISPOSTA_AUTOMATICA else annulla
    return Dialogo(_genitore(parent), titolo, testo, tipo, opzioni, annulla=annulla).esegui()


def avviso(parent, titolo, testo="", tipo="avviso", dettagli=None):
    """Messaggio con un solo pulsante (tipo: info, ok, avviso, errore)."""
    if RISPOSTA_AUTOMATICA is not None:
        print(f"  [{tipo}] {titolo}: {testo[:120]}")
        return
    Dialogo(_genitore(parent), titolo, testo, tipo, (("ok", "OK", "primario"),), dettagli).esegui()


def installa_traduzione(app):
    """Testi standard di Qt (menu dei campi di testo, finestre per scegliere i file…) in italiano."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    QLocale.setDefault(QLocale(QLocale.Italian, QLocale.Italy))
    tr = QTranslator(app)
    if tr.load(QLocale(QLocale.Italian), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
        app._traduzione = tr
        return True
    return False
