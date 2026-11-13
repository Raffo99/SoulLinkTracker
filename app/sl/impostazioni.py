"""Finestra delle impostazioni (si apre da sola al primo avvio)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QComboBox,
                               QVBoxLayout, QWidget)


class CampoFile(QWidget):
    def __init__(self, valore, filtro="", cartella=False):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
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


class Impostazioni(QDialog):
    def __init__(self, cfg, parent=None, mancanti=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Impostazioni – Soul Link Tracker")
        self.setSizeGripEnabled(True)
        self.setMinimumSize(380, 260)
        esterno = QVBoxLayout(self)
        esterno.setContentsMargins(0, 0, 0, 12)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        contenuto = QWidget()
        contenuto.setObjectName("interno")
        v = QVBoxLayout(contenuto)
        v.setContentsMargins(18, 14, 18, 8)
        v.setSpacing(6)
        area.setWidget(contenuto)
        esterno.addWidget(area, 1)
        schermo = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        larg, alt = 680, 760
        if schermo:
            larg, alt = min(larg, schermo.width() - 60), min(alt, schermo.height() - 80)
        self.resize(larg, alt)
        if mancanti:
            l = QLabel("Benvenuto! Per iniziare compila: " + ", ".join(mancanti) + ".")
            l.setObjectName("avvisi")
            l.setWordWrap(True)
            v.addWidget(l)

        g1 = QGroupBox("GIOCATORE E PARTITA CONDIVISA")
        f1 = self._form(g1)
        self.giocatore = QLineEdit(cfg["giocatore"])
        self.giocatore.setPlaceholderText("diverso da quello dell'amico")
        self.sb_url = QLineEdit(cfg.get("supabase_url", ""))
        self.sb_url.setPlaceholderText("https://xxxxxxxx.supabase.co")
        self.sb_chiave = QLineEdit(cfg.get("supabase_chiave", ""))
        self.sb_chiave.setPlaceholderText("sb_publishable_…  (Project Settings → API Keys)")
        self.codice = QLineEdit(cfg["codice"])
        self.codice.setPlaceholderText("uguale per tutti i giocatori, es. drago-luna-4821")
        prova = QPushButton("Prova collegamento")
        prova.clicked.connect(self._prova)
        self.rete = QComboBox()
        self.rete.addItem("Diretto tra le app (consigliato: niente account)", "p2p")
        self.rete.addItem("Supabase (database vostro)", "supabase")
        self.rete.setCurrentIndex(0 if (cfg.get("rete") or "p2p") != "supabase" else 1)
        self.rete.setToolTip("Diretto: le app si trovano con il codice della partita tramite relay pubblici e poi parlano "
                             "direttamente (WebRTC); se non si può, i dati passano da un relay MQTT pubblico. Tutto cifrato "
                             "con il codice. Tutti i giocatori della partita devono usare lo stesso collegamento.")
        f1.addRow("Il tuo nome", self.giocatore)
        f1.addRow("Codice della partita", self.codice)
        f1.addRow("Collegamento", self.rete)
        self.l_sb_url, self.l_sb_chiave = QLabel("Indirizzo Supabase"), QLabel("Chiave pubblica")
        f1.addRow(self.l_sb_url, self.sb_url)
        f1.addRow(self.l_sb_chiave, self.sb_chiave)
        self.codice.setToolTip("Il codice della partita (uguale per tutti): è anche la chiave che cifra i dati. "
                               "Per avere più partite usa «Cambia partita» (clic sul codice in alto).")
        f1.addRow("", prova)
        self._prova_b = prova

        def scelta_rete():
            sb = self.rete.currentData() == "supabase"
            for w in (self.l_sb_url, self.sb_url, self.l_sb_chiave, self.sb_chiave, self._prova_b):
                w.setVisible(sb)
        self.rete.currentIndexChanged.connect(lambda *_: scelta_rete())
        scelta_rete()
        v.addWidget(g1)

        g2 = QGroupBox("EMULATORE E RANDOMIZER")
        f2 = self._form(g2)
        self.melon = CampoFile(cfg.get("melonds", ""), "melonDS (melonDS.exe)")
        self.melon.e.setPlaceholderText("vuoto = la copia dell'app (scaricata da sola la prima volta)")
        self.melon.setToolTip("Lascia vuoto: l'app scarica melonDS da GitHub e usa una sua copia, con le impostazioni "
                              "giuste per il tracker. Indica un melonDS solo se l'app non riesce a scaricarlo.")
        self.java = QLineEdit(cfg["java"])
        self.java.setPlaceholderText("java  (oppure il percorso di java.exe a 64 bit)")
        self.jar = CampoFile(cfg["jar"], "Randomizer (*.jar)")
        self.imp = CampoFile(cfg["impostazioni"], "Impostazioni randomizer (*.rnqs)")
        self.rom = CampoFile(cfg["rom_originale"], "ROM Nintendo DS (*.nds)")
        f2.addRow("melonDS", self.melon)
        f2.addRow("Java", self.java)
        f2.addRow("Randomizer (.jar)", self.jar)
        f2.addRow("Impostazioni (.rnqs)", self.imp)
        f2.addRow("La tua ROM di Nero 2", self.rom)
        v.addWidget(g2)

        g3 = QGroupBox("ALTRO")
        f3 = self._form(g3)
        self.dati = CampoFile(cfg["cartella_dati"], cartella=True)
        self.salta = QCheckBox("Salta l'inizio del gioco")
        self.salta.setToolTip("A ogni nuova run riparti dal salvataggio di partenza (fatto prima della scena dello starter)")
        self.salta.setChecked(cfg["salta_inizio"])
        self.saveram = CampoFile(cfg.get("cartella_salvataggi", ""), cartella=True)
        self.saveram.e.setPlaceholderText("vuoto = <cartella ROM e salvataggi>/salvataggi")
        self.diag = QCheckBox("Diagnostica memoria")
        self.diag.setToolTip("Mostra i dati letti dalla memoria del gioco (utile per la verifica iniziale)")
        self.diag.setChecked(cfg["diagnostica"])
        f3.addRow("Cartella ROM e salvataggi", self.dati)
        f3.addRow("", self.salta)
        f3.addRow("Salvataggi del gioco", self.saveram)
        f3.addRow("", self.diag)
        self.backup = QComboBox()
        self._minuti = [0, 5, 10, 15, 20, 30, 60]
        for m in self._minuti:
            self.backup.addItem("mai (solo alla chiusura)" if m == 0 else f"{m} minuti")
        attuale = int(cfg.get("backup_minuti", 10) or 0)
        self.backup.setCurrentIndex(self._minuti.index(attuale) if attuale in self._minuti else 2)
        self.backup.setToolTip("Ogni quanti minuti l'app copia da parte il salvataggio del gioco. "
                               "Alla chiusura lo fa sempre.")
        f3.addRow("Backup automatico ogni", self.backup)
        self.agg = QCheckBox("Cerca aggiornamenti all'avvio")
        self.agg.setToolTip("Se su GitHub c'è una versione nuova te lo chiede e, se vuoi, si aggiorna da sola")
        self.agg.setChecked(cfg.get("aggiorna_auto", True) is not False)
        f3.addRow("", self.agg)
        v.addWidget(g3)

        v.addStretch()
        riga_bb = QHBoxLayout()
        riga_bb.setContentsMargins(18, 0, 18, 0)
        riga_bb.setSpacing(8)
        riga_bb.addStretch()
        annulla = QPushButton("Annulla")
        annulla.setMinimumWidth(92)
        annulla.clicked.connect(self.reject)
        salva = QPushButton("Salva")
        salva.setObjectName("primario")
        salva.setMinimumWidth(92)
        salva.setDefault(True)
        salva.clicked.connect(self._salva)
        riga_bb.addWidget(annulla)
        riga_bb.addWidget(salva)
        esterno.addLayout(riga_bb)

    @staticmethod
    def _form(gruppo):
        f = QFormLayout(gruppo)
        f.setRowWrapPolicy(QFormLayout.WrapLongRows)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        f.setVerticalSpacing(10)
        f.setHorizontalSpacing(14)
        return f

    def _prova(self):
        from . import dialoghi
        from .archivio import Archivio, ErroreArchivio
        a = Archivio(self.sb_url.text(), self.sb_chiave.text(), self.codice.text())
        try:
            v = a.versione()
            p = a.presenze()
            if v is None:
                dialoghi.avviso(self, "Collegamento riuscito", "La partita con questo codice non esiste ancora: verrà creata al primo avvio.", "ok")
            else:
                dialoghi.avviso(self, "Collegamento riuscito", f"Partita trovata. Giocatori: {', '.join(p) or 'nessuno'}.", "ok")
        except ErroreArchivio as e:
            dialoghi.avviso(self, "Il collegamento non funziona", str(e), "errore")

    def _salva(self):
        c = self.cfg
        c.update(giocatore=self.giocatore.text().strip(), supabase_url=self.sb_url.text().strip().rstrip("/"),
                 supabase_chiave=self.sb_chiave.text().strip(), codice=self.codice.text().strip(), rete=self.rete.currentData(), melonds=self.melon.text().strip(), randomizza=True,
                 java=self.java.text().strip() or "java", jar=self.jar.text(), impostazioni=self.imp.text(),
                 rom_originale=self.rom.text(), cartella_dati=self.dati.text() or c["cartella_dati"],
                 salta_inizio=self.salta.isChecked(), cartella_salvataggi=self.saveram.text(), diagnostica=self.diag.isChecked(),
                 backup_minuti=self._minuti[self.backup.currentIndex()], aggiorna_auto=self.agg.isChecked())
        c.salva()
        self.accept()
