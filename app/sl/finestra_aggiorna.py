"""Finestra "È disponibile una nuova versione": novità, scaricamento con barra di avanzamento, riavvio."""
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout

from . import VERSIONE, aggiorna
from .riepilogo import logo


class _Ponte(QObject):
    avanzamento = Signal(int, int)
    finito = Signal(object, str)


class DialogoAggiornamento(QDialog):
    """Al termine: self.scelta = "aggiorna" (con self.nuovo = exe scaricato), "salta" o None."""

    def __init__(self, parent, info):
        super().__init__(parent)
        self.info, self.scelta, self.nuovo = info, None, None
        self._annulla = False
        self._ponte = _Ponte()
        self._ponte.avanzamento.connect(self._avanza)
        self._ponte.finito.connect(self._finito)
        self.setWindowTitle("Aggiornamento")
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 18)
        v.setSpacing(12)
        testa = QHBoxLayout()
        testa.setSpacing(14)
        testa.addWidget(logo(46), 0, Qt.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(3)
        t = QLabel(f"È disponibile la versione {info['versione']}")
        t.setObjectName("dialogoTitolo")
        tv.addWidget(t)
        mb = (info.get("dimensione") or 0) / 1048576
        s = QLabel(f"Tu hai la {VERSIONE}. L'app scarica il nuovo programma ({mb:.0f} MB), fa un backup della partita, "
                   "chiude BizHawk e si riavvia da sola.")
        s.setObjectName("dialogoTesto")
        s.setWordWrap(True)
        tv.addWidget(s)
        testa.addLayout(tv, 1)
        v.addLayout(testa)
        note = aggiorna.note_brevi(info.get("note"), 20)
        if note:
            v.addWidget(QLabel("<b>Novità</b>"))
            box = QPlainTextEdit(note)
            box.setReadOnly(True)
            box.setStyleSheet("font-size: 9pt;")
            box.setMinimumHeight(140)
            v.addWidget(box, 1)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.hide()
        self.l_stato = QLabel("")
        self.l_stato.setObjectName("piccolo")
        self.l_stato.hide()
        v.addWidget(self.barra)
        v.addWidget(self.l_stato)
        r = QHBoxLayout()
        r.setSpacing(8)
        self.b_salta = QPushButton("Salta questa versione")
        self.b_salta.clicked.connect(self._salta)
        r.addWidget(self.b_salta)
        r.addStretch()
        self.b_dopo = QPushButton("Più tardi")
        self.b_dopo.clicked.connect(self.reject)
        self.b_ok = QPushButton("Aggiorna e riavvia")
        self.b_ok.setObjectName("primario")
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self._scarica)
        r.addWidget(self.b_dopo)
        r.addWidget(self.b_ok)
        v.addLayout(r)

    def _salta(self):
        self.scelta = "salta"
        self.accept()

    def _scarica(self):
        self.b_ok.setEnabled(False)
        self.b_salta.setEnabled(False)
        self.b_dopo.setText("Annulla")
        self.barra.show()
        self.l_stato.show()
        self.l_stato.setText("Scarico…")

        def lavoro():
            try:
                p = aggiorna.scarica(self.info, lambda a, b: self._ponte.avanzamento.emit(a, b), fermo=lambda: self._annulla)
                self._ponte.finito.emit(p, "")
            except Exception as e:
                self._ponte.finito.emit(None, str(e))
        threading.Thread(target=lavoro, daemon=True).start()

    def _avanza(self, letti, totale):
        if totale:
            self.barra.setRange(0, totale)
            self.barra.setValue(letti)
            self.l_stato.setText(f"Scarico… {letti / 1048576:.1f} di {totale / 1048576:.1f} MB")
        else:
            self.barra.setRange(0, 0)
            self.l_stato.setText(f"Scarico… {letti / 1048576:.1f} MB")

    def _finito(self, percorso, errore):
        if errore:
            self.l_stato.setText(errore)
            self.l_stato.setStyleSheet("color: #ff5c6c;")
            self.b_ok.setEnabled(True)
            self.b_ok.setText("Riprova")
            self.b_salta.setEnabled(True)
            self.b_dopo.setText("Più tardi")
            return
        self.nuovo = percorso
        self.scelta = "aggiorna"
        self.l_stato.setText("Fatto: riavvio l'app…")
        self.accept()

    def reject(self):
        self._annulla = True                  # se sta scaricando, si ferma
        super().reject()
