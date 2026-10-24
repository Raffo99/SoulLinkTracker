"""Finestra principale: BizHawk incastrato a sinistra, pannelli a destra, comandi in basso."""
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QWindow
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QSplitter, QStatusBar, QTabWidget, QVBoxLayout, QWidget)

from . import VERSIONE
from .config import Config, StatoLocale, cartella_app
from .emulatore import Emulatore, adatta, togli_bordi
from .impostazioni import Impostazioni
from .pannelli import (PannelloCimitero, PannelloDiagnostica, PannelloDiario, PannelloObiettivi, PannelloPercorsi,
                       PannelloSquadre)
from .ponte import Ponte
from .run import GestoreRun, run_della_rom
from .sincro import Sincro
from .sprite import Sprite
from .stile import ACC, KO, OK, ORO, TENUE, WARN


def risorsa(nome: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "risorse" / nome


class Pallino(QLabel):
    def __init__(self, testo):
        super().__init__()
        self.testo = testo
        self.imposta(None)

    def imposta(self, ok, dettaglio=""):
        col = OK if ok else (TENUE if ok is None else KO)
        self.setText(f"<span style='color:{col}'>●</span> {self.testo}{(' · ' + dettaglio) if dettaglio else ''}")


class Finestra(QMainWindow):
    _avvia_richiesto = Signal()
    _randomizzato = Signal(int, object, str)
    _avviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.cfg = Config()
        self.locale = StatoLocale()
        self.sprite = Sprite()
        self.run_mgr = GestoreRun(self.cfg)
        self.emu = Emulatore()
        self.ponte = Ponte(self._risposta_script)
        self.sincro = Sincro(self.cfg)
        self.run_desiderata = self.locale.get("ultima_run", 1)
        self.stato_run = None
        self._occupato = False
        self._popup_visto = None
        self._cont = None
        self._qwin = None
        self._avvisi_lua = []
        self._lock = threading.Lock()
        self._ultimo_stato = None

        self.setWindowTitle(f"Soul Link Tracker {VERSIONE}")
        self.resize(1500, 900)
        self._costruisci()
        self._collega()
        QTimer.singleShot(200, self._avvio)

    # ================================================================ interfaccia
    def _costruisci(self):
        radice = QWidget()
        radice.setObjectName("radice")
        self.setCentralWidget(radice)
        v = QVBoxLayout(radice)
        v.setContentsMargins(10, 10, 10, 6)

        # intestazione
        testa = QHBoxLayout()
        t = QLabel("Soul Link <span style='color:%s'>Tracker</span>" % ACC)
        t.setObjectName("titolo")
        testa.addWidget(t)
        self.l_run = QLabel("Run #–")
        self.l_run.setObjectName("pill")
        testa.addWidget(self.l_run)
        testa.addSpacing(16)
        self.l_giocatori = QLabel("")
        self.l_giocatori.setObjectName("tenue")
        testa.addWidget(self.l_giocatori, 1)
        v.addLayout(testa)

        split = QSplitter(Qt.Horizontal)
        v.addWidget(split, 1)

        # area del gioco
        self.area_gioco = QWidget()
        self.area_gioco.setObjectName("pannello")
        self.area_gioco.setMinimumWidth(420)
        ag = QVBoxLayout(self.area_gioco)
        ag.setContentsMargins(4, 4, 4, 4)
        self.segnaposto = QLabel("Avvio…")
        self.segnaposto.setAlignment(Qt.AlignCenter)
        self.segnaposto.setWordWrap(True)
        self.segnaposto.setObjectName("tenue")
        ag.addWidget(self.segnaposto)
        self.b_riavvia_centro = QPushButton("Avvia il gioco")
        self.b_riavvia_centro.setObjectName("primario")
        self.b_riavvia_centro.clicked.connect(self._riavvia_gioco)
        self.b_riavvia_centro.hide()
        ag.addWidget(self.b_riavvia_centro, 0, Qt.AlignHCenter)
        split.addWidget(self.area_gioco)

        # pannelli
        destra = QWidget()
        dv = QVBoxLayout(destra)
        dv.setContentsMargins(0, 0, 0, 0)
        self.l_avvisi = QLabel("")
        self.l_avvisi.setObjectName("avvisi")
        self.l_avvisi.setWordWrap(True)
        self.l_avvisi.hide()
        dv.addWidget(self.l_avvisi)
        self.tabs = QTabWidget()
        self.p_squadre = PannelloSquadre(self.sprite)
        self.p_percorsi = PannelloPercorsi(self._azione, self.sprite)
        self.p_obiettivi = PannelloObiettivi(self._azione)
        self.p_cimitero = PannelloCimitero(self.sprite)
        self.p_diario = PannelloDiario()
        self.p_registro = QListWidget()
        self.p_diag = PannelloDiagnostica()
        for w, n in ((self.p_squadre, "Squadre"), (self.p_percorsi, "Percorsi"), (self.p_obiettivi, "Obiettivi"),
                     (self.p_cimitero, "Cimitero"), (self.p_diario, "Diario"), (self.p_registro, "Registro app"),
                     (self.p_diag, "Diagnostica")):
            self.tabs.addTab(w, n)
        dv.addWidget(self.tabs, 1)
        split.addWidget(destra)
        split.setSizes([820, 680])

        # barra in basso
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.i_gioco = Pallino("BizHawk")
        self.i_script = Pallino("Script")
        self.i_sito = Pallino("Sito")
        for w in (self.i_gioco, self.i_script, self.i_sito):
            sb.addWidget(w)
        self.l_stato = QLabel("")
        self.l_stato.setObjectName("tenue")
        sb.addWidget(self.l_stato, 1)
        self.b_nuova = QPushButton("Nuova run")
        self.b_nuova.setObjectName("primario")
        self.b_riavvia = QPushButton("Riavvia gioco")
        self.b_console = QPushButton("Console Lua")
        self.b_console.setCheckable(True)
        self.b_web = QPushButton("Dashboard web")
        self.b_imp = QPushButton("Impostazioni")
        for b in (self.b_nuova, self.b_riavvia, self.b_console, self.b_web, self.b_imp):
            sb.addPermanentWidget(b)

    def _collega(self):
        self.b_nuova.clicked.connect(self._nuova_run)
        self.b_riavvia.clicked.connect(self._riavvia_gioco)
        self.b_console.toggled.connect(self.emu.mostra_console)
        self.b_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.cfg.server)) if self.cfg.server else None)
        self.b_imp.clicked.connect(self._impostazioni)
        self.emu.finestra_pronta.connect(self._incastra)
        self.emu.terminato.connect(self._emu_terminato)
        self.emu.errore.connect(lambda m: self._log(m, KO))
        self.ponte.collegato.connect(self._script_collegato)
        self.ponte.payload.connect(self._payload)
        self.sincro.stato_server.connect(self._stato_server)
        self.sincro.connessione.connect(lambda ok, err: self.i_sito.imposta(ok, "" if ok else "non raggiungibile"))
        self.sincro.messaggio.connect(lambda t: self._log(t, ORO))
        self.sincro.run_cambiata.connect(self._run_cambiata)
        self.sincro.ignorato.connect(lambda t: self._log("Il sito non registra i dati: " + t, WARN))
        self.sprite.aggiornato.connect(self._sprite_pronti)
        self._avvia_richiesto.connect(self._dopo_arresto)
        self._randomizzato.connect(self._fine_randomizzazione)
        self._avviso.connect(lambda t: self._log(t, ORO))
        self._t_adatta = QTimer(self)
        self._t_adatta.timeout.connect(self._adatta)
        self._t_adatta.start(700)

    # ================================================================ avvio e run
    def _avvio(self):
        manca = self.cfg.mancanti()
        if manca:
            Impostazioni(self.cfg, self, manca).exec()
        self._aggiorna_locale()
        self._log(f"Ponte per BizHawk in ascolto sulla porta {self.ponte.porta}")
        if self.cfg.mancanti():
            self.segnaposto.setText("Completa le impostazioni per avviare il gioco.")
            return
        # aspettiamo un attimo il sito per sapere la run; se non risponde partiamo con l'ultima nota
        QTimer.singleShot(2500, self.assicura_gioco)

    def _run_cambiata(self, run, stato):
        prima = self.run_desiderata
        self.run_desiderata, self.stato_run = run, stato
        if run != prima:
            self._log(f"Run attuale: #{run}")
        self.assicura_gioco()

    def assicura_gioco(self):
        """Fa in modo che BizHawk giri con la ROM della run attuale (generandola se serve)."""
        if self._occupato or self.cfg.mancanti():
            return
        run = self.run_desiderata
        rom = self.run_mgr.rom_per_run(run)
        if self.cfg["randomizza"] and not rom.exists():
            self._occupato = True
            self._stato(f"Genero la ROM randomizzata della run #{run}…")
            self.segnaposto.setText(f"Genero la ROM randomizzata della run #{run}…\nCi vuole qualche secondo.")

            def lavoro():
                out, msg = self.run_mgr.randomizza(run)
                self._randomizzato.emit(run, out, msg)
            threading.Thread(target=lavoro, daemon=True).start()
            return
        if self.emu.in_esecuzione:
            if self.emu.rom and Path(self.emu.rom) == rom:
                return
            self._occupato = True
            self._stato(f"Passo alla ROM della run #{run}: chiudo BizHawk…")
            self._log(f"Cambio ROM: run #{run}")
            self.emu.ferma(alla_fine=self._avvia_richiesto.emit)
            return
        self._avvia(rom, run)

    def _fine_randomizzazione(self, run, out, msg):
        self._occupato = False
        if out is None:
            self._log(msg, KO)
            self.segnaposto.setText("Non sono riuscito a generare la ROM:\n\n" + msg)
            self.b_riavvia_centro.setText("Riprova")
            self.b_riavvia_centro.show()
            QMessageBox.warning(self, "Randomizer", msg)
            return
        self._log(f"ROM della run #{run} pronta: {Path(out).name}", OK)
        self.assicura_gioco()

    def _avvia(self, rom: Path, run: int):
        if not rom.exists():
            self.segnaposto.setText(f"Non trovo la ROM:\n{rom}")
            return
        m = self.run_mgr.prepara_salvataggio(rom)
        if m:
            self._log(m, OK)
            with self._lock:
                self._avvisi_lua.append(m)
        lua = cartella_app() / "soullink.lua"
        try:
            shutil.copyfile(risorsa("soullink.lua"), lua)
        except Exception as e:
            self._log(f"Script Lua non copiato: {e}", KO)
        self.sincro.imposta_run_rom(run_della_rom(rom) if self.cfg["randomizza"] else None)
        if self.emu.avvia(self.cfg["bizhawk"], rom, self.ponte.porta, lua):
            self._log(f"Avvio BizHawk con {rom.name}")
            self.segnaposto.setText("Avvio BizHawk…")
            self.b_riavvia_centro.hide()
            self.i_gioco.imposta(True, "avvio")
            self.locale.update(ultima_run=run)
            self.locale.salva()
        else:
            self.b_riavvia_centro.setText("Riprova")
            self.b_riavvia_centro.show()
        self._aggiorna_locale()

    def _dopo_arresto(self):
        self._occupato = False
        self._togli_contenitore()
        self.assicura_gioco()

    def _riavvia_gioco(self):
        if self.emu.in_esecuzione:
            if QMessageBox.question(self, "Riavvia", "Riavviare BizHawk? Salva prima in gioco se serve.") != QMessageBox.Yes:
                return
            self._occupato = True
            self.emu.ferma(alla_fine=self._avvia_richiesto.emit)
        else:
            self.assicura_gioco()

    def _emu_terminato(self, codice):
        self._togli_contenitore()
        self.i_gioco.imposta(False, "chiuso")
        if not self._occupato:
            self._log("BizHawk è stato chiuso.", WARN)
            self.segnaposto.setText("BizHawk è stato chiuso.")
            self.b_riavvia_centro.setText("Avvia il gioco")
            self.b_riavvia_centro.show()

    # ================================================================ incastro della finestra
    def _incastra(self, hwnd):
        self._togli_contenitore()
        togli_bordi(hwnd)
        self._qwin = QWindow.fromWinId(hwnd)
        self._cont = QWidget.createWindowContainer(self._qwin, self.area_gioco)
        self._cont.setFocusPolicy(Qt.StrongFocus)
        self.segnaposto.hide()
        self.b_riavvia_centro.hide()
        self.area_gioco.layout().addWidget(self._cont, 1)
        self._cont.setFocus()
        self.i_gioco.imposta(True, Path(self.emu.rom).stem if self.emu.rom else "")
        self._log("BizHawk incastrato nella finestra")

    def _adatta(self):
        if self._cont and self.emu.hwnd:
            r = self._cont.devicePixelRatioF()
            adatta(self.emu.hwnd, 0, 0, int(self._cont.width() * r), int(self._cont.height() * r))

    def _togli_contenitore(self):
        if self._cont is not None:
            self._cont.setParent(None)
            self._cont.deleteLater()
            self._cont, self._qwin = None, None
        self.segnaposto.show()

    # ================================================================ script (thread del ponte!)
    def _risposta_script(self, dati: dict) -> str:
        if dati.get("salva_base"):
            m = self.run_mgr.cattura_base(dati.get("salva_base"))
            if m:
                self._avviso.emit(m)
                with self._lock:
                    self._avvisi_lua.append(m)
        pacchetto = {k: v for k, v in dati.items() if k != "salva_base"}
        # la run della ROM che ha prodotto QUESTI dati (non quella che verra' caricata dopo)
        rom = self.emu.rom
        pacchetto["run_rom"] = run_della_rom(rom) if (self.cfg["randomizza"] and rom) else None
        self.sincro.accoda(pacchetto)
        righe = ["OK"]
        if self.sincro.run is not None:
            righe.append(f"RUN {self.sincro.run} {self.sincro.stato or 'in_corso'}")
        righe += self.sincro.messaggi_per_lua()
        with self._lock:
            righe += [f"AVVISO {a}" for a in self._avvisi_lua]
            self._avvisi_lua.clear()
        righe.append(f"DIAG {1 if self.cfg['diagnostica'] else 0}")
        return "\n".join(righe) + "\n"

    def _script_collegato(self, ok):
        self.i_script.imposta(ok, "collegato" if ok else "")
        self.sincro.imposta_emulatore(ok)
        if ok:
            self._log("Lo script di BizHawk è collegato all'app", OK)

    def _payload(self, dati):
        pass

    # ================================================================ stato dal sito
    def _stato_server(self, st):
        self._ultimo_stato = st
        self.stato_run = st["stato"]
        testo_run = f"Run #{st['run']}" + ("" if st["stato"] == "in_corso" else " · VINTA!" if st["stato"] == "vinta" else " · GAME OVER")
        col = KO if st["stato"] == "game_over" else (ORO if st["stato"] == "vinta" else OK)
        self.l_run.setText(testo_run)
        self.l_run.setStyleSheet(f"background:{col}22;color:{col};")
        parti = []
        for g, x in st["giocatori"].items():
            pal = f"<span style='color:{OK if x.get('online') else TENUE}'>●</span>"
            dove = f" · {x['zona_nome']}" if x.get("zona_nome") else ""
            parti.append(f"{pal} <b style='color:#e8e9f0'>{g}</b>{dove} · {x.get('medaglie', 0)} medaglie · cap <b style='color:{WARN}'>{x.get('cap')}</b>")
        self.l_giocatori.setText("&nbsp;&nbsp;&nbsp;&nbsp;".join(parti) or "Nessun giocatore collegato")
        if st["avvisi"]:
            self.l_avvisi.setText("⚠  " + "\n⚠  ".join(st["avvisi"]))
            self.l_avvisi.show()
        else:
            self.l_avvisi.hide()
        for p in (self.p_squadre, self.p_percorsi, self.p_obiettivi, self.p_cimitero, self.p_diario):
            p.aggiorna(st)
        self.p_diag.aggiorna(st)
        # schermate di fine run (una volta per run)
        chiave = (st["run"], st["stato"])
        if st["stato"] in ("game_over", "vinta") and self._popup_visto != chiave:
            self._popup_visto = chiave
            QTimer.singleShot(100, lambda: self._fine_run(st))

    def _fine_run(self, st):
        if st["stato"] == "vinta":
            titolo, testo = "RUN VINTA!", f"Complimenti! {st.get('motivo', '')}\n\nVuoi iniziare una nuova run?"
        else:
            titolo, testo = "GAME OVER", f"{st.get('motivo', '')}\n\nVuoi iniziare una nuova run? Verranno generate nuove ROM."
        if QMessageBox.question(self, titolo, testo, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._azione({"azione": "nuova_run"})

    def _sprite_pronti(self):
        for p in (self.p_squadre, self.p_percorsi, self.p_cimitero):
            p.forza()
        if self._ultimo_stato:
            QTimer.singleShot(300, lambda: self._stato_server(self._ultimo_stato))

    # ================================================================ comandi
    def _azione(self, dati):
        def fine(r):
            if r.get("errore"):
                self._avviso.emit("Errore: " + r["errore"])
        self.sincro.azione(dati, fine)

    def _nuova_run(self):
        domanda = "Abbandonare la run attuale e iniziarne una nuova?" if self.stato_run == "in_corso" else "Iniziare una nuova run?"
        if QMessageBox.question(self, "Nuova run", domanda + "\nVerranno generate nuove ROM per tutti e due.") == QMessageBox.Yes:
            self._azione({"azione": "nuova_run"})
            self._log("Nuova run richiesta…")

    def _impostazioni(self):
        if Impostazioni(self.cfg, self).exec():
            self._log("Impostazioni salvate")
            self.sincro.aggiorna_ora()
            self._aggiorna_locale()
            if not self.emu.in_esecuzione:
                self.assicura_gioco()

    # ================================================================ varie
    def _log(self, testo, colore=None):
        it = QListWidgetItem(f"{datetime.now().strftime('%H:%M:%S')}   {testo}")
        if colore:
            from PySide6.QtGui import QColor
            it.setForeground(QColor(colore))
        self.p_registro.insertItem(0, it)
        while self.p_registro.count() > 300:
            self.p_registro.takeItem(self.p_registro.count() - 1)
        self._stato(testo)

    def _stato(self, testo):
        self.l_stato.setText(testo)

    def _aggiorna_locale(self):
        self.p_diag.locale = {
            "versione app": VERSIONE, "porta ponte": self.ponte.porta, "BizHawk": self.cfg["bizhawk"],
            "ROM in uso": str(self.emu.rom) if self.emu.rom else "-",
            "cartella ROM": str(self.run_mgr.cartella_rom), "salvataggi BizHawk": str(self.run_mgr.cartella_saveram()),
            "salvataggio di partenza": "presente" if self.run_mgr.file_base.exists() else "non ancora creato",
        }

    def closeEvent(self, ev):
        if self.emu.in_esecuzione:
            r = QMessageBox.question(self, "Chiudi", "Chiudere anche BizHawk?\nRicordati di salvare in gioco prima.",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                ev.ignore()
                return
            if r == QMessageBox.Yes:
                fatto = threading.Event()
                self._occupato = True
                self.emu.ferma(alla_fine=fatto.set)
                fine = time.time() + 16
                while not fatto.is_set() and time.time() < fine:
                    QApplication.processEvents()
                    time.sleep(0.05)
        self.sincro.ferma()
        self.ponte.chiudi()
        ev.accept()
