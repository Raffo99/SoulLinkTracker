"""Finestra dei backup della run in corso: farne uno subito, riprendere da un backup, aprire la cartella."""
from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from . import dialoghi
from .backup import TIPI
from .riepilogo import logo
from .stile import ACC, OK, ORO, TENUE, WARN, alfa

COLORI = {"auto": ACC, "chiusura": OK, "cambio": OK, "manuale": ORO}


def quando(t):
    d = datetime.fromtimestamp(t)
    oggi = datetime.now().date()
    if d.date() == oggi:
        return "oggi alle " + d.strftime("%H:%M")
    if (oggi - d.date()).days == 1:
        return "ieri alle " + d.strftime("%H:%M")
    return d.strftime("%d/%m alle %H:%M")


class RigaBackup(QFrame):
    def __init__(self, b):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(12)
        col = COLORI.get(b["tipo"], ACC)
        punto = QLabel()
        punto.setFixedSize(10, 10)
        punto.setStyleSheet(f"background:{col}; border-radius:5px;")
        h.addWidget(punto, 0, Qt.AlignVCenter)
        v = QVBoxLayout()
        v.setSpacing(2)
        t = QLabel(f"<b>{quando(b['quando'])}</b>")
        sotto = QLabel(f"<span style='color:{col}'>{TIPI.get(b['tipo'], b['tipo'])}</span>"
                       f"<span style='color:{TENUE}'> · {b['byte'] / 1048576:.1f} MB"
                       f"{'' if b['saveram'] else ' · senza salvataggio del gioco'}</span>")
        v.addWidget(t)
        v.addWidget(sotto)
        h.addLayout(v, 1)


class DialogoBackup(QDialog):
    def __init__(self, finestra):
        super().__init__(finestra)
        self.f = finestra
        self.setWindowTitle("Backup e ripristino")
        self.resize(560, 540)
        self.setMinimumSize(460, 400)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        testa = QHBoxLayout()
        testa.setSpacing(14)
        testa.addWidget(logo(42), 0, Qt.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(3)
        t = QLabel("Backup della run")
        t.setObjectName("grande")
        tv.addWidget(t)
        minuti = int(finestra.cfg.get("backup_minuti", 10) or 0)
        ogni = f"ogni {minuti} minuti e " if minuti else ""
        s = QLabel(f"L'app salva il punto in cui sei {ogni}ogni volta che chiudi, cambi partita o riavvii il gioco. "
                   "Il tracker non torna indietro: morti e catture già registrate restano.")
        s.setWordWrap(True)
        s.setObjectName("tenue")
        tv.addWidget(s)
        testa.addLayout(tv, 1)
        v.addLayout(testa)

        self.lista = QListWidget()
        self.lista.setObjectName("partite")
        self.lista.setSpacing(2)
        self.lista.itemDoubleClicked.connect(lambda _: self._riprendi())
        self.lista.currentItemChanged.connect(lambda *_: self._pulsanti())
        v.addWidget(self.lista, 1)
        self.vuota = QLabel("Ancora nessun backup per questa run.")
        self.vuota.setAlignment(Qt.AlignCenter)
        self.vuota.setObjectName("tenue")
        self.vuota.setStyleSheet("background: rgba(255,255,255,0.025); border: 1px dashed rgba(255,255,255,0.10); border-radius: 14px;")
        v.addWidget(self.vuota, 1)

        r = QHBoxLayout()
        r.setSpacing(8)
        self.b_ora = QPushButton("Fai un backup adesso")
        self.b_ora.clicked.connect(self._adesso)
        self.b_cartella = QPushButton("Apri la cartella")
        self.b_cartella.clicked.connect(self._cartella)
        r.addWidget(self.b_ora)
        r.addWidget(self.b_cartella)
        r.addStretch()
        v.addLayout(r)

        r2 = QHBoxLayout()
        r2.setSpacing(8)
        self.b_saveram = QPushButton("Rimetti solo il salvataggio del gioco")
        self.b_saveram.setToolTip("Chiude BizHawk, rimette il salvataggio del gioco di quel momento e riapre il gioco")
        self.b_saveram.clicked.connect(self._saveram)
        r2.addWidget(self.b_saveram)
        r2.addStretch()
        chiudi = QPushButton("Chiudi")
        chiudi.clicked.connect(self.reject)
        self.b_riprendi = QPushButton("Riprendi da qui")
        self.b_riprendi.setObjectName("primario")
        self.b_riprendi.clicked.connect(self._riprendi)
        r2.addWidget(chiudi)
        r2.addWidget(self.b_riprendi)
        v.addLayout(r2)
        self._riempi()

    def _run(self):
        return self.f._run_in_gioco() or self.f.run_desiderata

    def _riempi(self):
        self.lista.clear()
        self.elenco = self.f.backup.elenco(self._run())
        for b in self.elenco:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, b)
            riga = RigaBackup(b)
            it.setSizeHint(QSize(100, riga.sizeHint().height() + 4))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, riga)
        self.lista.setVisible(bool(self.elenco))
        self.vuota.setVisible(not self.elenco)
        if self.elenco:
            self.lista.setCurrentRow(0)
        self._pulsanti()

    def _scelto(self):
        it = self.lista.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _pulsanti(self):
        b = self._scelto()
        gioco = self.f.emu.in_esecuzione and self.f.ponte.attivo
        self.b_riprendi.setEnabled(bool(b) and gioco)
        self.b_saveram.setEnabled(bool(b and b["saveram"]))
        self.b_ora.setEnabled(gioco)
        self.b_riprendi.setToolTip("" if gioco else "Avvia prima il gioco")

    def _adesso(self):
        self.b_ora.setEnabled(False)
        self.b_ora.setText("Salvo…")

        def fatto(ok):
            try:
                self.b_ora.setText("Fai un backup adesso")
                self._riempi()
                if not ok:
                    dialoghi.avviso(self, "Backup non riuscito", "Lo script di BizHawk non ha risposto. Riprova tra qualche secondo.")
            except RuntimeError:
                pass
        self.f._chiedi_backup("manuale", fatto)

    def _riprendi(self):
        b = self._scelto()
        if not b or not self.b_riprendi.isEnabled():
            return
        if dialoghi.chiedi(self, "Riprendere da questo backup?",
                           f"Il gioco torna a {quando(b['quando'])}. Quello che hai fatto dopo, se non lo hai salvato, va perso.\n\n"
                           "Il tracker non torna indietro: morti e catture già registrate restano.",
                           si="Riprendi da qui", no="Annulla"):
            self.f._carica_backup(b)
            self.accept()

    def _saveram(self):
        b = self._scelto()
        if not b or not b["saveram"]:
            return
        if dialoghi.chiedi(self, "Rimettere il salvataggio del gioco?",
                           f"BizHawk verrà chiuso e riaperto con il salvataggio del gioco di {quando(b['quando'])}. "
                           "Il salvataggio attuale viene tenuto da parte nella cartella di BizHawk.",
                           si="Rimetti il salvataggio", no="Annulla", pericolo=True):
            self.f._ripristina_saveram(b)
            self.accept()

    def _cartella(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.f.backup.cartella(self._run()))))
