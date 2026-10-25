"""Finestra del reset totale."""
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class DialogoReset(QDialog):
    def __init__(self, parent, n_giocatori: int):
        super().__init__(parent)
        self.setWindowTitle("Reset totale")
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.setContentsMargins(20, 18, 20, 18)
        t = QLabel("<b style='font-size:13pt'>Ricominciare da zero</b>")
        v.addWidget(t)
        self.condivisa = QCheckBox("Azzera la partita condivisa: si torna alla run #1, storico e obiettivi cancellati")
        self.condivisa.setChecked(True)
        v.addWidget(self.condivisa)
        if n_giocatori > 1:
            nota = QLabel(f"Vale per tutti i {n_giocatori} giocatori: anche le loro app passano a ROM nuove.")
            nota.setObjectName("tenue")
            nota.setContentsMargins(26, 0, 0, 0)
            v.addWidget(nota)
        self.locale = QCheckBox("Cancella le ROM generate e i salvataggi di BizHawk di questa partita\n(le altre partite non vengono toccate)")
        self.locale.setChecked(True)
        v.addWidget(self.locale)
        self.partenza = QCheckBox("Cancella anche il salvataggio di partenza (vale per tutte le partite)")
        v.addWidget(self.partenza)
        avviso = QLabel("Non si può annullare. Scrivi <b>RESET</b> per confermare:")
        avviso.setObjectName("avvisi")
        avviso.setWordWrap(True)
        v.addWidget(avviso)
        self.conferma = QLineEdit()
        self.conferma.setPlaceholderText("RESET")
        v.addWidget(self.conferma)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok = bb.button(QDialogButtonBox.Ok)
        self.ok.setText("Azzera")
        self.ok.setObjectName("pericolo")
        self.ok.setEnabled(False)
        bb.button(QDialogButtonBox.Cancel).setText("Annulla")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.conferma.textChanged.connect(self._controlla)
        for c in (self.condivisa, self.locale, self.partenza):
            c.toggled.connect(self._controlla)

    def _controlla(self):
        qualcosa = self.condivisa.isChecked() or self.locale.isChecked() or self.partenza.isChecked()
        self.ok.setEnabled(qualcosa and self.conferma.text().strip().upper() == "RESET")
