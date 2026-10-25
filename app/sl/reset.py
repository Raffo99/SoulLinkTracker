"""Finestra del reset totale."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from .stile import KO, alfa


class DialogoReset(QDialog):
    def __init__(self, parent, n_giocatori: int):
        super().__init__(parent)
        self.setWindowTitle("Reset totale")
        self.setMinimumWidth(540)
        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(24, 22, 24, 18)

        testa = QHBoxLayout()
        testa.setSpacing(16)
        icona = QLabel("!")
        icona.setFixedSize(40, 40)
        icona.setAlignment(Qt.AlignCenter)
        icona.setStyleSheet(f"background:{alfa(KO, 0.16)}; color:{KO}; border:1px solid {alfa(KO, 0.4)};"
                            "border-radius:20px; font-size:15pt; font-weight:700;")
        testa.addWidget(icona, 0, Qt.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(4)
        t = QLabel("Ricominciare da zero")
        t.setObjectName("dialogoTitolo")
        tv.addWidget(t)
        s = QLabel("Scegli cosa cancellare. Riguarda solo la partita in corso.")
        s.setObjectName("dialogoTesto")
        s.setWordWrap(True)
        tv.addWidget(s)
        testa.addLayout(tv, 1)
        v.addLayout(testa)

        opzioni = QVBoxLayout()
        opzioni.setContentsMargins(56, 4, 0, 0)
        opzioni.setSpacing(10)
        self.condivisa = QCheckBox("Azzera la partita condivisa e torna alla run #1")
        self.condivisa.setChecked(True)
        opzioni.addWidget(self.condivisa)
        if True:
            chi = f" Vale per tutti i {n_giocatori} giocatori: anche le loro app passano a ROM nuove." if n_giocatori > 1 else ""
            nota = QLabel("Storico e obiettivi vengono cancellati." + chi)
            nota.setWordWrap(True)
            nota.setObjectName("piccolo")
            nota.setContentsMargins(26, 0, 0, 0)
            opzioni.addWidget(nota)
        self.locale = QCheckBox("Cancella dal PC le ROM, i salvataggi e i backup di questa partita")
        self.locale.setChecked(True)
        opzioni.addWidget(self.locale)
        self.partenza = QCheckBox("Cancella anche il salvataggio di partenza (vale per tutte le partite)")
        opzioni.addWidget(self.partenza)
        v.addLayout(opzioni)

        v.addSpacing(4)
        avviso = QLabel("Non si può annullare. Scrivi <b>RESET</b> qui sotto per confermare.")
        avviso.setObjectName("avvisi")
        avviso.setWordWrap(True)
        v.addWidget(avviso)
        self.conferma = QLineEdit()
        self.conferma.setPlaceholderText("scrivi RESET")
        v.addWidget(self.conferma)

        r = QHBoxLayout()
        r.setSpacing(8)
        r.addStretch()
        annulla = QPushButton("Annulla")
        annulla.setMinimumWidth(92)
        annulla.clicked.connect(self.reject)
        self.ok = QPushButton("Azzera tutto")
        self.ok.setObjectName("pericolo")
        self.ok.setMinimumWidth(110)
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self.accept)
        r.addWidget(annulla)
        r.addWidget(self.ok)
        v.addLayout(r)
        self.conferma.textChanged.connect(self._controlla)
        for c in (self.condivisa, self.locale, self.partenza):
            c.toggled.connect(self._controlla)

    def _controlla(self):
        qualcosa = self.condivisa.isChecked() or self.locale.isChecked() or self.partenza.isChecked()
        self.ok.setEnabled(qualcosa and self.conferma.text().strip().upper() == "RESET")
