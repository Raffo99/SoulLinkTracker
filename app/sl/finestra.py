"""Finestra principale: barra in alto, BizHawk a sinistra, riepilogo e dettagli a destra, comandi in basso."""
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMenu,
                               QMessageBox, QPushButton, QSplitter, QStackedLayout, QStatusBar, QTabWidget,
                               QVBoxLayout, QWidget)

from . import VERSIONE
from .config import Config, StatoLocale, cartella_app
from .emulatore import Emulatore, adatta, incastra
from .impostazioni import Impostazioni
from .pannelli import PannelloCimitero, PannelloDiagnostica, PannelloDiario, PannelloObiettivi, PannelloPercorsi
from .ponte import Ponte
from .riepilogo import BarraSuperiore, CartaLuogo, CartaObiettivo, OspiteGioco, PannelloCoppie
from .run import GestoreRun, run_della_rom
from .sincro import Sincro
from .sprite import Sprite
from .stile import KO, OK, ORO, TENUE, WARN, alfa


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
    _avviso = Signal(str, str)

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
        self._avvisi_lua = []
        self._comandi_lua = []
        self._lock = threading.Lock()
        self._ultimo_stato = None

        self.setWindowTitle(f"Soul Link Tracker {VERSIONE}")
        self.resize(1560, 920)
        self._costruisci()
        self._collega()
        QTimer.singleShot(200, self._avvio)

    # ================================================================ interfaccia
    def _costruisci(self):
        radice = QWidget()
        radice.setObjectName("radice")
        self.setCentralWidget(radice)
        v = QVBoxLayout(radice)
        v.setContentsMargins(10, 8, 10, 4)
        v.setSpacing(8)

        self.barra = BarraSuperiore()
        v.addWidget(self.barra)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        v.addWidget(split, 1)

        # ---- area del gioco: segnaposto oppure BizHawk incastrato
        self.area_gioco = QWidget()
        self.area_gioco.setObjectName("pannello")
        self.area_gioco.setMinimumWidth(480)
        self.pile = QStackedLayout(self.area_gioco)
        pag = QWidget()
        pv = QVBoxLayout(pag)
        pv.addStretch()
        self.segnaposto = QLabel("Avvio…")
        self.segnaposto.setAlignment(Qt.AlignCenter)
        self.segnaposto.setWordWrap(True)
        self.segnaposto.setObjectName("tenue")
        pv.addWidget(self.segnaposto)
        self.b_avvia_centro = QPushButton("Avvia il gioco")
        self.b_avvia_centro.setObjectName("primario")
        self.b_avvia_centro.clicked.connect(self._riavvia_gioco)
        self.b_avvia_centro.hide()
        pv.addWidget(self.b_avvia_centro, 0, Qt.AlignHCenter)
        pv.addStretch()
        self.pile.addWidget(pag)
        self.ospite = OspiteGioco()
        self.pile.addWidget(self.ospite)
        split.addWidget(self.area_gioco)

        # ---- colonna destra
        destra = QWidget()
        destra.setMinimumWidth(500)
        dv = QVBoxLayout(destra)
        dv.setContentsMargins(0, 0, 0, 0)
        dv.setSpacing(8)
        riga = QHBoxLayout()
        riga.setSpacing(8)
        self.c_obiettivo = CartaObiettivo()
        self.c_luogo = CartaLuogo()
        riga.addWidget(self.c_obiettivo, 1)
        riga.addWidget(self.c_luogo, 1)
        dv.addLayout(riga)
        self.l_avvisi = QLabel("")
        self.l_avvisi.setObjectName("avvisi")
        self.l_avvisi.setWordWrap(True)
        self.l_avvisi.hide()
        dv.addWidget(self.l_avvisi)
        self.tabs = QTabWidget()
        self.p_coppie = PannelloCoppie(self.sprite)
        self.p_percorsi = PannelloPercorsi(self._azione, self.sprite)
        self.p_obiettivi = PannelloObiettivi(self._azione)
        self.p_cimitero = PannelloCimitero(self.sprite)
        self.p_diario = PannelloDiario()
        self.p_registro = QListWidget()
        self.p_diag = PannelloDiagnostica()
        for w, n in ((self.p_coppie, "Coppie"), (self.p_percorsi, "Percorsi"), (self.p_obiettivi, "Obiettivi"),
                     (self.p_cimitero, "Cimitero"), (self.p_diario, "Diario"), (self.p_registro, "Registro"),
                     (self.p_diag, "Diagnostica")):
            self.tabs.addTab(w, n)
        dv.addWidget(self.tabs, 1)
        split.addWidget(destra)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([900, 640])

        # ---- barra in basso
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)
        self.i_gioco = Pallino("BizHawk")
        self.i_script = Pallino("Script")
        self.i_sito = Pallino("Supabase")
        for w in (self.i_gioco, self.i_script, self.i_sito):
            sb.addWidget(w)
        self.l_stato = QLabel("")
        self.l_stato.setObjectName("tenue")
        sb.addWidget(self.l_stato, 1)
        self.b_nuova = QPushButton("Nuova run")
        self.b_nuova.setObjectName("primario")
        self.b_riavvia = QPushButton("Riavvia gioco")
        self.b_partenza = QPushButton("Salvataggio di partenza ▾")
        self.b_regole = QPushButton("Regole ▾")
        self.b_console = QPushButton("Console Lua")
        self.b_console.setCheckable(True)
        self.b_imp = QPushButton("Impostazioni")
        for b in (self.b_nuova, self.b_riavvia, self.b_partenza, self.b_regole, self.b_console, self.b_imp):
            sb.addPermanentWidget(b)
        menu = QMenu(self)
        menu.addAction("Usa il salvataggio attuale come partenza…", self._imposta_partenza)
        menu.addAction("Cancella il salvataggio di partenza", self._cancella_partenza)
        self.b_partenza.setMenu(menu)
        self.m_regole = QMenu(self)
        self.a_regole = {}
        for k, t in (("tutorial", "Il primo selvatico (tutorial) non conta"), ("doppioni", "Clausola doppioni (stessa famiglia non conta)"),
                     ("shiny", "Clausola shiny (gli shiny non contano)")):
            a = self.m_regole.addAction(t)
            a.setCheckable(True)
            a.triggered.connect(lambda v, k=k: self._azione({"azione": "regole", "regole": {k: v}}))
            self.a_regole[k] = a
        self.m_regole.addSeparator()
        self.m_regole.addAction("Fai contare il mio ultimo incontro ignorato…", self._conta_ignorato)
        self.a_lega = self.m_regole.addAction("Superquattro battuti (level cap di Iris)")
        self.a_lega.setCheckable(True)
        self.a_lega.triggered.connect(lambda v: self._azione({"azione": "lega", "valore": v}))
        self.b_regole.setMenu(self.m_regole)

    def _collega(self):
        self.b_nuova.clicked.connect(self._nuova_run)
        self.b_riavvia.clicked.connect(self._riavvia_gioco)
        self.b_console.toggled.connect(self.emu.mostra_console)
        self.b_imp.clicked.connect(self._impostazioni)
        self.emu.finestra_pronta.connect(self._incastra)
        self.emu.terminato.connect(self._emu_terminato)
        self.emu.errore.connect(lambda m: self._log(m, KO))
        self.ponte.collegato.connect(self._script_collegato)
        self.sincro.stato_server.connect(self._stato_server)
        self.sincro.connessione.connect(self._connessione)
        self.sincro.messaggio.connect(lambda t: self._log(t, ORO))
        self.sincro.run_cambiata.connect(self._run_cambiata)
        self.sincro.ignorato.connect(lambda t: self._log("Dati non registrati: " + t, WARN))
        self.sprite.aggiornato.connect(self._sprite_pronti)
        self._avvia_richiesto.connect(self._dopo_arresto)
        self._randomizzato.connect(self._fine_randomizzazione)
        self._avviso.connect(self._log)
        self.ospite.ridimensionato.connect(self._adatta)
        self._t_adatta = QTimer(self)
        self._t_adatta.timeout.connect(self._adatta)
        self._t_adatta.start(1000)
        self._t_tempo = QTimer(self)
        self._t_tempo.timeout.connect(self.barra.tic)
        self._t_tempo.start(1000)

    # ================================================================ avvio e run
    def _avvio(self):
        manca = self.cfg.mancanti()
        if manca:
            if Impostazioni(self.cfg, self, manca).exec():
                self.sincro.riconfigura()
        self._aggiorna_locale()
        self._log(f"Ponte per BizHawk in ascolto sulla porta {self.ponte.porta}")
        if self.cfg.mancanti():
            self.segnaposto.setText("Completa le impostazioni per avviare il gioco.")
            self.b_avvia_centro.setText("Apri le impostazioni")
            self.b_avvia_centro.show()
            return
        QTimer.singleShot(2500, self.assicura_gioco)

    def _connessione(self, ok, err):
        self.i_sito.imposta(ok, "" if ok else "errore")
        self.i_sito.setToolTip(err or "")
        if not ok and err and err != getattr(self, "_ultimo_err", None):
            self._ultimo_err = err
            self._log("Supabase: " + err, KO)

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
            self.pile.setCurrentIndex(0)

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
            self.b_avvia_centro.setText("Riprova")
            self.b_avvia_centro.show()
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
            self.b_avvia_centro.hide()
            self.i_gioco.imposta(True, "avvio")
            self.locale.update(ultima_run=run)
            self.locale.salva()
        else:
            self.b_avvia_centro.setText("Riprova")
            self.b_avvia_centro.show()
        self._aggiorna_locale()

    def _dopo_arresto(self):
        self._occupato = False
        self.pile.setCurrentIndex(0)
        self.assicura_gioco()

    def _riavvia_gioco(self):
        if self.cfg.mancanti():
            self._impostazioni()
            return
        if self.emu.in_esecuzione:
            if QMessageBox.question(self, "Riavvia", "Riavviare BizHawk? Salva prima in gioco se serve.") != QMessageBox.Yes:
                return
            self._occupato = True
            self.emu.ferma(alla_fine=self._avvia_richiesto.emit)
        else:
            self.assicura_gioco()

    def _emu_terminato(self, codice):
        self.pile.setCurrentIndex(0)
        self.i_gioco.imposta(False, "chiuso")
        if not self._occupato:
            self._log("BizHawk è stato chiuso.", WARN)
            self.segnaposto.setText("BizHawk è stato chiuso.")
            self.b_avvia_centro.setText("Avvia il gioco")
            self.b_avvia_centro.show()

    # ================================================================ BizHawk dentro la finestra
    def _incastra(self, hwnd):
        self.pile.setCurrentIndex(1)
        w, h = self.ospite.dimensioni_fisiche()
        incastra(hwnd, int(self.ospite.winId()), w, h)
        self.i_gioco.imposta(True, Path(self.emu.rom).stem if self.emu.rom else "")
        self._log("BizHawk incastrato nella finestra")

    def _adatta(self):
        if self.emu.hwnd and self.pile.currentIndex() == 1:
            adatta(self.emu.hwnd, *self.ospite.dimensioni_fisiche())

    # ================================================================ script (thread del ponte!)
    def _risposta_script(self, dati: dict) -> str:
        nome_rom = dati.pop("salva_base", None)
        manuale = dati.pop("salva_base_manuale", False)
        n_squadra = dati.pop("salva_base_squadra", 0) or 0
        if nome_rom:
            if manuale and n_squadra > 0:
                m = ("Nel salvataggio attuale hai già lo starter: carica o fai un salvataggio prima della scena "
                     "dello starter e riprova.")
            else:
                m = self.run_mgr.cattura_base(nome_rom, forza=manuale)
            if m:
                self._avviso.emit(m, ORO)
                with self._lock:
                    self._avvisi_lua.append(m)
                QTimer.singleShot(0, self._aggiorna_locale)
        rom = self.emu.rom
        dati["run_rom"] = run_della_rom(rom) if (self.cfg["randomizza"] and rom) else None
        self.sincro.accoda(dati)
        righe = ["OK"]
        if self.sincro.run is not None:
            righe.append(f"RUN {self.sincro.run} {self.sincro.stato or 'in_corso'}")
        righe += self.sincro.messaggi_per_lua()
        with self._lock:
            righe += [f"AVVISO {a}" for a in self._avvisi_lua]
            righe += self._comandi_lua
            self._avvisi_lua.clear()
            self._comandi_lua.clear()
        righe.append(f"DIAG {1 if self.cfg['diagnostica'] else 0}")
        return "\n".join(righe) + "\n"

    def _script_collegato(self, ok):
        self.i_script.imposta(ok, "collegato" if ok else "")
        self.sincro.imposta_presenza(emulatore=ok)
        if ok:
            self._log("Lo script di BizHawk è collegato all'app", OK)

    # ================================================================ stato condiviso
    def _stato_server(self, st):
        self._ultimo_stato = st
        self.stato_run = st["stato"]
        io = self.cfg["giocatore"]
        self.barra.aggiorna(st, io)
        self.barra.tic()
        self.c_obiettivo.aggiorna(st, io)
        self.c_luogo.aggiorna(st, io)
        if st["avvisi"]:
            self.l_avvisi.setText("⚠  " + "\n⚠  ".join(st["avvisi"]))
            self.l_avvisi.show()
        else:
            self.l_avvisi.hide()
        for k, a in self.a_regole.items():
            a.setChecked(st["regole"].get(k, True) is not False)
        self.a_lega.setChecked(bool(st.get("lega")))
        self.p_coppie.aggiorna(st, io)
        for p in (self.p_percorsi, self.p_obiettivi, self.p_cimitero, self.p_diario):
            p.aggiorna(st)
        self.p_diag.aggiorna(st)
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
        for p in (self.p_coppie, self.p_percorsi, self.p_cimitero):
            p.forza()
        if self._ultimo_stato:
            QTimer.singleShot(300, lambda: self._stato_server(self._ultimo_stato))

    # ================================================================ comandi
    def _azione(self, dati):
        def fine(r):
            if r.get("errore"):
                self._avviso.emit("Errore: " + r["errore"], KO)
        self.sincro.azione(dati, fine)

    def _nuova_run(self):
        domanda = "Abbandonare la run attuale e iniziarne una nuova?" if self.stato_run == "in_corso" else "Iniziare una nuova run?"
        if QMessageBox.question(self, "Nuova run", domanda + "\nVerranno generate nuove ROM per tutti e due.") == QMessageBox.Yes:
            self._azione({"azione": "nuova_run"})
            self._log("Nuova run richiesta…")

    def _imposta_partenza(self):
        if not self.ponte.attivo:
            QMessageBox.information(self, "Salvataggio di partenza", "Avvia prima il gioco: lo script deve essere collegato.")
            return
        r = QMessageBox.question(self, "Salvataggio di partenza",
                                 "Prima salva nel gioco (menu → Salva) il più vicino possibile alla Vedetta di Alisopoli, "
                                 "PRIMA della scena in cui ricevi lo starter.\n\nFatto? Premi Sì e userò quel salvataggio "
                                 "come partenza per le prossime run.")
        if r == QMessageBox.Yes:
            with self._lock:
                self._comandi_lua.append("SALVABASE")
            self._log("Chiedo allo script il salvataggio attuale…")

    def _conta_ignorato(self):
        st = self._ultimo_stato or {}
        io = self.cfg["giocatore"]
        inc = next((e for e in st.get("incontri", []) if e["g"] == io and e.get("ignorato")), None)
        if not inc:
            QMessageBox.information(self, "Regole", "Non hai incontri ignorati.")
            return
        motivi = {"tutorial": "tutorial", "shiny": "shiny", "doppione": "clausola doppioni", "luogo_usato": "luogo già usato"}
        if QMessageBox.question(self, "Regole", f"Far contare l'incontro con {inc['nome_specie']} a {inc['luogo_nome']} "
                                f"(ignorato: {motivi.get(inc['ignorato'], inc['ignorato'])})?") == QMessageBox.Yes:
            self._azione({"azione": "conta_incontro", "id": inc["id"]})

    def _cancella_partenza(self):
        f = self.run_mgr.file_base
        if not f.exists():
            QMessageBox.information(self, "Salvataggio di partenza", "Non c'è nessun salvataggio di partenza.")
            return
        if QMessageBox.question(self, "Salvataggio di partenza", "Cancellare il salvataggio di partenza?") == QMessageBox.Yes:
            f.unlink()
            self._log("Salvataggio di partenza cancellato")
            self._aggiorna_locale()

    def _impostazioni(self):
        if Impostazioni(self.cfg, self).exec():
            self._log("Impostazioni salvate")
            self.sincro.riconfigura()
            self._aggiorna_locale()
            if not self.emu.in_esecuzione:
                self.assicura_gioco()

    # ================================================================ varie
    def _log(self, testo, colore=None):
        it = QListWidgetItem(f"{datetime.now().strftime('%H:%M:%S')}   {testo}")
        if colore:
            it.setForeground(QColor(colore))
        self.p_registro.insertItem(0, it)
        while self.p_registro.count() > 300:
            self.p_registro.takeItem(self.p_registro.count() - 1)
        self._stato(testo)

    def _stato(self, testo):
        self.l_stato.setText(testo[:140])

    def _aggiorna_locale(self):
        self.p_diag.locale = {
            "versione app": VERSIONE, "porta ponte": self.ponte.porta, "BizHawk": self.cfg["bizhawk"],
            "ROM in uso": str(self.emu.rom) if self.emu.rom else "-",
            "cartella ROM": str(self.run_mgr.cartella_rom), "salvataggi BizHawk": str(self.run_mgr.cartella_saveram()),
            "salvataggio di partenza": "presente" if self.run_mgr.file_base.exists() else "non ancora creato",
            "dati scaricati da Supabase": f"{self.sincro.archivio.byte_scaricati // 1024} KB",
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
