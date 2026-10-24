"""Finestra delle impostazioni (si apre da sola al primo avvio)."""
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget)


class CampoFile(QWidget):
    def __init__(self, valore, filtro="", cartella=False):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.e = QLineEdit(valore or "")
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


class Impostazioni(QDialog):
    def __init__(self, cfg, parent=None, mancanti=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Impostazioni – Soul Link Tracker")
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        if mancanti:
            l = QLabel("Benvenuto! Per iniziare compila: " + ", ".join(mancanti) + ".")
            l.setObjectName("avvisi")
            l.setWordWrap(True)
            v.addWidget(l)

        g1 = QGroupBox("GIOCATORE E PARTITA CONDIVISA (SUPABASE)")
        f1 = QFormLayout(g1)
        self.giocatore = QLineEdit(cfg["giocatore"])
        self.giocatore.setPlaceholderText("diverso da quello dell'amico")
        self.sb_url = QLineEdit(cfg.get("supabase_url", ""))
        self.sb_url.setPlaceholderText("https://xxxxxxxx.supabase.co")
        self.sb_chiave = QLineEdit(cfg.get("supabase_chiave", ""))
        self.sb_chiave.setPlaceholderText("sb_publishable_…  (Project Settings → API Keys)")
        self.codice = QLineEdit(cfg["codice"])
        self.codice.setPlaceholderText("una parola segreta uguale per tutti e due, es. pikachu-2026-raffo")
        prova = QPushButton("Prova collegamento")
        prova.clicked.connect(self._prova)
        f1.addRow("Il tuo nome", self.giocatore)
        f1.addRow("Indirizzo Supabase", self.sb_url)
        f1.addRow("Chiave pubblica", self.sb_chiave)
        f1.addRow("Codice della partita", self.codice)
        f1.addRow("", prova)
        v.addWidget(g1)

        g2 = QGroupBox("EMULATORE E RANDOMIZER")
        f2 = QFormLayout(g2)
        self.bizhawk = CampoFile(cfg["bizhawk"], "EmuHawk (EmuHawk.exe)")
        self.randomizza = QCheckBox("Genera da solo una ROM randomizzata a ogni run")
        self.randomizza.setChecked(cfg["randomizza"])
        self.java = QLineEdit(cfg["java"])
        self.jar = CampoFile(cfg["jar"], "Randomizer (*.jar)")
        self.imp = CampoFile(cfg["impostazioni"], "Impostazioni randomizer (*.rnqs)")
        self.rom = CampoFile(cfg["rom_originale"], "ROM Nintendo DS (*.nds)")
        self.rom_manuale = CampoFile(cfg["rom_manuale"], "ROM Nintendo DS (*.nds)")
        f2.addRow("BizHawk", self.bizhawk)
        f2.addRow("", self.randomizza)
        f2.addRow("Java", self.java)
        f2.addRow("Randomizer (.jar)", self.jar)
        f2.addRow("Impostazioni (.rnqs)", self.imp)
        f2.addRow("ROM originale", self.rom)
        f2.addRow("ROM da usare (senza randomizer)", self.rom_manuale)
        v.addWidget(g2)

        g3 = QGroupBox("ALTRO")
        f3 = QFormLayout(g3)
        self.dati = CampoFile(cfg["cartella_dati"], cartella=True)
        self.salta = QCheckBox("Salta l'inizio del gioco (riparti da un salvataggio fatto prima dello starter)")
        self.salta.setChecked(cfg["salta_inizio"])
        self.saveram = CampoFile(cfg["cartella_saveram"], cartella=True)
        self.saveram.e.setPlaceholderText("vuoto = <cartella di BizHawk>/NDS/SaveRAM")
        self.diag = QCheckBox("Diagnostica memoria (dati letti dal gioco, per la verifica)")
        self.diag.setChecked(cfg["diagnostica"])
        f3.addRow("Cartella ROM e salvataggi", self.dati)
        f3.addRow("", self.salta)
        f3.addRow("Salvataggi di BizHawk", self.saveram)
        f3.addRow("", self.diag)
        v.addWidget(g3)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText("Salva")
        bb.button(QDialogButtonBox.Cancel).setText("Annulla")
        bb.accepted.connect(self._salva)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.randomizza.toggled.connect(self._abilita)
        self._abilita()

    def _abilita(self):
        r = self.randomizza.isChecked()
        for w in (self.java, self.jar, self.imp, self.rom):
            w.setEnabled(r)
        self.rom_manuale.setEnabled(not r)

    def _prova(self):
        from .archivio import Archivio, ErroreArchivio
        a = Archivio(self.sb_url.text(), self.sb_chiave.text(), self.codice.text())
        try:
            v = a.versione()
            p = a.presenze()
            if v is None:
                QMessageBox.information(self, "Collegamento", "Funziona! La partita con questo codice non esiste ancora: verrà creata al primo avvio.")
            else:
                QMessageBox.information(self, "Collegamento", f"Funziona! Partita trovata. Giocatori visti: {', '.join(p) or 'nessuno'}.")
        except ErroreArchivio as e:
            QMessageBox.warning(self, "Collegamento", f"Non funziona:\n{e}")

    def _salva(self):
        c = self.cfg
        c.update(giocatore=self.giocatore.text().strip(), supabase_url=self.sb_url.text().strip().rstrip("/"),
                 supabase_chiave=self.sb_chiave.text().strip(), codice=self.codice.text().strip(), bizhawk=self.bizhawk.text(), randomizza=self.randomizza.isChecked(),
                 java=self.java.text().strip() or "java", jar=self.jar.text(), impostazioni=self.imp.text(),
                 rom_originale=self.rom.text(), rom_manuale=self.rom_manuale.text(), cartella_dati=self.dati.text() or c["cartella_dati"],
                 salta_inizio=self.salta.isChecked(), cartella_saveram=self.saveram.text(), diagnostica=self.diag.isChecked())
        c.salva()
        self.accept()
