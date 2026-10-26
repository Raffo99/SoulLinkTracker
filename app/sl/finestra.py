"""Finestra principale: barra in alto, BizHawk a sinistra, riepilogo e dettagli a destra, comandi in basso."""
import html
import unicodedata
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QSizePolicy, QSplitter, QStackedLayout, QTabWidget, QVBoxLayout,
                               QWidget)

from . import VERSIONE
from .config import Config, StatoLocale, cartella_app
from .emulatore import Emulatore, adatta, incastra
from .impostazioni import Impostazioni
from .pannelli import (PannelloCimitero, PannelloDiagnostica, PannelloDiario, PannelloObiettivi, PannelloPercorsi,
                       PannelloStatistiche)
from .ponte import Ponte
from .riepilogo import BarraSuperiore, CartaLuogo, CartaObiettivo, MiniPokemon, Notifiche, OspiteGioco, PannelloCoppie, logo, paragrafi
from . import aggiorna, dialoghi
from . import logica as L
from .backup import TIPI as TIPI_BACKUP, GestoreBackup
from .lotta import CartaLotta
from .partite import DialogoPartite
from .reset import DialogoReset
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
        col = OK if ok else ("#5b6075" if ok is None else KO)
        det = f" <span style='color:#7c8199'>· {dettaglio}</span>" if dettaglio else ""
        self.setText(f"<span style='color:{col};font-size:11pt'>●</span>&nbsp;<span style='color:#c9cbd6'>{self.testo}</span>{det}")


_SOSTITUZIONI_OVERLAY = {"è": "e'", "é": "e'", "à": "a'", "ì": "i'", "ò": "o'", "ù": "u'", "È": "E'",
                         "↔": "<->", "→": "->", "«": '"', "»": '"', "ª": "a", "…": "...", "·": "-",
                         "–": "-", "—": "-", "’": "'", "★": "*", "✓": "v", "⚔": "", "📍": ""}


def per_overlay(testo: str) -> str:
    """Il testo disegnato da BizHawk sopra il gioco non ha gli accenti: si usa la grafia con l'apostrofo."""
    testo = testo.replace("Pokémon", "Pokemon").replace("Pokédex", "Pokedex")
    out = "".join(_SOSTITUZIONI_OVERLAY.get(c, c) for c in testo)
    out = unicodedata.normalize("NFKD", out).encode("ascii", "ignore").decode("ascii")
    return out


class Finestra(QMainWindow):
    _avvia_richiesto = Signal()
    _randomizzato = Signal(int, object, str)
    _avviso = Signal(str, str)
    _per_reset = Signal()
    _per_cambio = Signal()
    _risposte = Signal(object)        # risposte dello script ai comandi (backup fatto, stato caricato)
    _in_gui = Signal(object)          # funzione da eseguire nel thread dell'interfaccia
    _dettagli = Signal(object)        # dettagli della lotta in corso (o None a lotta finita)
    _aggiornamento = Signal(object, str, bool)   # info sulla nuova versione (o None), errore, controllo chiesto a mano

    def __init__(self):
        super().__init__()
        self.cfg = Config()
        self.stato_locale = StatoLocale()
        self.locale = self.stato_locale.partita(self.cfg.get("codice"))
        self.sprite = Sprite()
        self.run_mgr = GestoreRun(self.cfg)
        self.backup = GestoreBackup(self.run_mgr)
        self._richieste = {}              # id -> backup/caricamento chiesto allo script
        self._id_richiesta = 0
        self._ultimo_backup = time.time()
        self._gioco_attivo = False
        self._ripresa_chiesta = set()
        self._chiusura_pronta = False
        self._in_chiusura = False
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

        self.setWindowTitle(f"Soul Link Tracker {VERSIONE}" + (f" — {self.cfg['codice']}" if self.cfg.get("codice") else ""))
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
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

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
        pv.setSpacing(14)
        pv.addStretch()
        pv.addWidget(logo(88), 0, Qt.AlignHCenter)
        t = QLabel("Soul Link")
        t.setStyleSheet("font-size: 18pt; font-weight: 700; color: #d9dbe6;")
        t.setAlignment(Qt.AlignCenter)
        pv.addWidget(t)
        self.segnaposto = QLabel("Avvio…")
        self.segnaposto.setAlignment(Qt.AlignCenter)
        self.segnaposto.setWordWrap(True)
        self.segnaposto.setObjectName("segnaposto")
        pv.addWidget(self.segnaposto)
        pv.addSpacing(4)
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
        dv.setSpacing(12)
        riga = QHBoxLayout()
        riga.setSpacing(12)
        self.c_obiettivo = CartaObiettivo()
        self.c_luogo = CartaLuogo()
        riga.addWidget(self.c_obiettivo, 1)
        riga.addWidget(self.c_luogo, 1)
        self.c_lotta = CartaLotta(self.sprite)          # durante la lotta prende il posto delle due carte
        from PySide6.QtWidgets import QScrollArea
        self.s_lotta = QScrollArea()                    # se lo schermo è basso il riquadro scorre invece di allungare la finestra
        self.s_lotta.setWidgetResizable(True)
        self.s_lotta.setFrameShape(QFrame.NoFrame)
        self.s_lotta.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.s_lotta.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self.s_lotta.setWidget(self.c_lotta)
        self.s_lotta.setMinimumHeight(260)
        riga.addWidget(self.s_lotta, 2)
        self.s_lotta.hide()
        dv.addLayout(riga)
        self._dv, self._riga = dv, riga
        self.l_avvisi = QLabel("")
        self.l_avvisi.setObjectName("avvisi")
        self.l_avvisi.setWordWrap(True)
        self.l_avvisi.hide()
        dv.addWidget(self.l_avvisi)
        self.tabs = QTabWidget()
        self.p_coppie = PannelloCoppie(self.sprite)
        self.p_percorsi = PannelloPercorsi(self._azione, self.sprite)
        self.p_obiettivi = PannelloObiettivi(self._azione, lambda: self.cfg["giocatore"], self._apri_mappa)
        self.c_obiettivo.apri_mappa.connect(self._apri_mappa)
        self._mappa = None
        self.p_cimitero = PannelloCimitero(self.sprite)
        self.p_diario = PannelloDiario()
        self.p_stat = PannelloStatistiche(self.sprite)
        self.p_registro = QListWidget()
        self.p_registro.setWordWrap(True)
        self.p_registro.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.p_diag = PannelloDiagnostica()
        sistema = QSplitter(Qt.Vertical)
        sistema.addWidget(self.p_registro)
        sistema.addWidget(self.p_diag)
        sistema.setSizes([300, 300])
        for w, n in ((self.p_coppie, "Coppie"), (self.p_percorsi, "Percorsi"), (self.p_obiettivi, "Obiettivi"),
                     (self.p_cimitero, "Cimitero"), (self.p_stat, "Statistiche"), (self.p_diario, "Diario"),
                     (sistema, "Sistema")):
            self.tabs.addTab(w, n)
        self.tabs.setMinimumHeight(170)       # le schede si stringono; i riquadri sopra no
        dv.addWidget(self.tabs, 1)
        split.addWidget(destra)
        self.destra = destra
        self.notifiche = Notifiche(destra)
        destra.installEventFilter(self)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([900, 640])

        # ---- barra dei comandi in basso
        basso = QFrame()
        basso.setObjectName("barraBasso")
        basso.setFixedHeight(56)
        hb = QHBoxLayout(basso)
        hb.setContentsMargins(18, 8, 10, 8)
        hb.setSpacing(8)
        self.i_gioco = Pallino("BizHawk")
        self.i_script = Pallino("Script")
        self.i_sito = Pallino("Supabase")
        for i, w in enumerate((self.i_gioco, self.i_script, self.i_sito)):
            if i:
                hb.addSpacing(10)
            hb.addWidget(w)
        hb.addSpacing(14)
        sep = QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet("background:#2f3344;")
        hb.addWidget(sep, 0, Qt.AlignVCenter)
        hb.addSpacing(14)
        self.l_stato = QLabel("")
        self.l_stato.setObjectName("tenue")
        self.l_stato.setMinimumWidth(80)
        self.l_stato.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        hb.addWidget(self.l_stato, 1)
        hb.addSpacing(12)
        self.b_nuova = QPushButton("Nuova run")
        self.b_nuova.setObjectName("primario")
        self.b_riavvia = QPushButton("Riavvia gioco")
        self.b_partenza = QPushButton("Partenza")
        self.b_partenza.setToolTip("Salvataggio di partenza: da dove riparte ogni nuova run")
        self.b_regole = QPushButton("Regole")
        self.b_altro = QPushButton("Altro")
        self.b_imp = QPushButton("Impostazioni")
        self.b_vel = QPushButton("")
        self.b_vel.setToolTip("Velocità del gioco (al posto delle scorciatoie di BizHawk). Tab tenuto premuto resta l'avanti veloce.")
        m_vel = QMenu(self)
        for perc, t in ((100, "×1 normale"), (200, "×2"), (300, "×3"), (400, "×4"), (800, "×8"), (6400, "Più veloce possibile")):
            a = m_vel.addAction(t)
            a.setCheckable(True)
            a.setData(perc)
            a.triggered.connect(lambda _=False, perc=perc: self._imposta_velocita(perc))
        self.m_vel = m_vel
        self.b_vel.setMenu(m_vel)
        for b in (self.b_vel, self.b_nuova, self.b_riavvia, self.b_partenza, self.b_regole, self.b_altro, self.b_imp):
            hb.addWidget(b)
        v.addWidget(basso)

        menu = QMenu(self)
        menu.addAction("Usa il salvataggio attuale come partenza…", self._imposta_partenza)
        menu.addAction("Cancella il salvataggio di partenza", self._cancella_partenza)
        self.b_partenza.setMenu(menu)
        self.m_regole = QMenu(self)
        self.a_regole = {}
        self.m_regole.addSection("Incontri")
        for k, t in (("tutorial", "Il primo selvatico (tutorial) non conta"), ("doppioni", "Clausola doppioni (stessa famiglia non conta)"),
                     ("shiny", "Clausola shiny (gli shiny non contano)"),
                     ("tipi", "Tipo primario unico in squadra (avvisa se ripetuto)"),
                     ("level_cap", "Avvisa se un Pokémon supera il level cap")):
            if k == "tipi":
                self.m_regole.addSection("Squadra")
            a = self.m_regole.addAction(t)
            a.setCheckable(True)
            a.triggered.connect(lambda val, k=k: self._azione({"azione": "regole", "regole": {k: val}}))
            self.a_regole[k] = a
        self.m_regole.addSection("Esperienza")
        self.a_condividi = self.m_regole.addAction("Condividi esperienza: tutta la squadra cresce")
        self.a_condividi.setCheckable(True)
        self.a_condividi.triggered.connect(self._condividi_esp)
        self.m_molt = self.m_regole.addMenu("Esperienza con Condividi")
        from PySide6.QtGui import QActionGroup
        gruppo = QActionGroup(self)
        self.a_molt = {}
        for v, t in ((1.0, "×1 (normale)"), (0.5, "×½"), (0.25, "×¼"), (0.125, "×⅛")):
            a = self.m_molt.addAction(t)
            a.setCheckable(True)
            gruppo.addAction(a)
            a.triggered.connect(lambda _=False, v=v: self._azione({"azione": "regole", "regole": {"molt_condividi": v}}))
            self.a_molt[v] = a
        self.a_cap_bloccato = self.m_regole.addAction("Blocca il level cap (sperimentale)…")
        self.a_cap_bloccato.setCheckable(True)
        self.a_cap_bloccato.triggered.connect(self._cap_bloccato)
        self.a_solo_allenatori = self.m_regole.addAction("Esperienza solo dagli allenatori (sperimentale)…")
        self.a_solo_allenatori.setCheckable(True)
        self.a_solo_allenatori.triggered.connect(self._modo_allenatori)
        self.m_regole.addSection("Correzioni a mano")
        self.m_regole.addAction("Fai contare il mio ultimo incontro ignorato…", self._conta_ignorato)
        self.a_lega = self.m_regole.addAction("Superquattro battuti (level cap di Iris)")
        self.a_lega.setCheckable(True)
        self.a_lega.triggered.connect(lambda val: self._azione({"azione": "lega", "valore": val}))
        self.b_regole.setMenu(self.m_regole)
        m_altro = QMenu(self)
        self.a_console = m_altro.addAction("Mostra la console Lua di BizHawk")
        self.a_console.setCheckable(True)
        m_altro.addSeparator()
        m_altro.addAction("Backup e ripristino…", self._apri_backup)
        m_altro.addAction("Controlla il tracker con il gioco…", lambda: self._controllo(False))
        m_altro.addAction("Cambia partita…", self._cambia_partita)
        m_altro.addAction("Cerca aggiornamenti…", lambda: self._cerca_aggiornamenti(True))
        m_altro.addAction("Crea file per la diagnosi…", self._diagnosi)
        m_altro.addSeparator()
        m_altro.addAction("Reset totale…", self._reset_totale)
        self.b_altro.setMenu(m_altro)

    def _collega(self):
        self.b_nuova.clicked.connect(self._nuova_run)
        self.b_riavvia.clicked.connect(self._riavvia_gioco)
        self.a_console.toggled.connect(self.emu.mostra_console)
        self.b_imp.clicked.connect(self._impostazioni)
        self.emu.finestra_pronta.connect(self._incastra)
        self.emu.terminato.connect(self._emu_terminato)
        self.emu.errore.connect(lambda m: self._log(m, KO))
        self.ponte.collegato.connect(self._script_collegato)
        self.sincro.stato_server.connect(self._stato_server)
        self.sincro.connessione.connect(self._connessione)
        if self.sincro.online:                  # collegato prima che il segnale fosse agganciato
            self._connessione(True, "")
        self.sincro.messaggio.connect(self._messaggio)
        self.sincro.run_cambiata.connect(self._run_cambiata)
        self.sincro.ignorato.connect(lambda t: self._log("Dati non registrati: " + t, WARN))
        self.sprite.aggiornato.connect(self._sprite_pronti)
        self._avvia_richiesto.connect(self._dopo_arresto)
        self._randomizzato.connect(self._fine_randomizzazione)
        self._avviso.connect(self._log)
        self._per_reset.connect(self._esegui_dopo_reset)
        self._per_cambio.connect(self._applica_partita)
        self._risposte.connect(self._gestisci_risposte)
        self._in_gui.connect(lambda f: f())
        self._dettagli.connect(self._mostra_lotta)
        self._aggiorna_vel()
        self._aggiornamento.connect(self._esito_aggiornamento)
        self._riavvia_con = None
        aggiorna.pulisci()
        QTimer.singleShot(15000, lambda: self._cerca_aggiornamenti(False))
        if "--aggiornato" in sys.argv:
            QTimer.singleShot(1500, lambda: (self._log(f"Aggiornato alla versione {VERSIONE}", OK),
                                             self.notifiche.mostra(f"Aggiornato alla versione {VERSIONE}", OK, 8)))
        self._squadra_gioco = []
        self._box_gioco = None
        self._det_lotta = None
        self._impara_rom = None
        self._esp = {}                    # controllo dell'esperienza nella lotta in corso
        self._critici = set()             # Pokémon in pericolo già segnalati
        self._entita_rom = None           # allenatori e strumenti di ogni zona, letti dalla ROM
        self._flag_evento = b""
        self._incontri_rom = None         # dove si incontrano selvatici, letto dalla ROM
        self._ultimo_luogo = None
        self._luoghi_avvisati = set()
        self._lotte_avvisate = set()
        self._controllo_visto = None
        MiniPokemon.apri = self._scheda_pokemon
        self.p_percorsi.apri_pokemon = self._apri_pokemon
        self.p_cimitero.itemDoubleClicked.connect(lambda it: it.data(Qt.UserRole) and self._apri_pokemon(it.data(Qt.UserRole)))
        self._in_primo_piano = True
        self._t_focus = QTimer(self)
        self._t_focus.timeout.connect(self._controlla_focus)
        self._t_focus.start(150)
        self._t_battito = QTimer(self)
        self._t_battito.timeout.connect(self._battito)
        self._t_battito.start(60000)
        self._t_backup = QTimer(self)
        self._t_backup.timeout.connect(self._backup_periodico)
        self._t_backup.start(30000)
        self.barra.cambia_partita.connect(self._cambia_partita)
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
                self.locale = self.stato_locale.partita(self.cfg.get("codice"))
                self.sincro.riconfigura()
        self.barra.imposta_partita(self.cfg.get("codice"))
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
        if self.sincro.edizione is not None and self.sincro.edizione != self.locale.get("ultima_edizione") and self.locale.get("ultima_edizione") is not None:
            self._log("La partita è stata azzerata: si riparte con ROM nuove", WARN)
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
        if self.sincro.edizione is None and not self.locale.get("ultima_edizione"):
            self.segnaposto.setText("Carico i dati della partita…")
            self.pile.setCurrentIndex(0)
            return                        # arriveranno con il primo stato da Supabase (run_cambiata)
        rom = self.rom_attesa()
        if self.cfg["randomizza"] and not rom.exists():
            self._occupato = True
            self._stato(f"Genero la ROM randomizzata della run #{run}…")
            self.segnaposto.setText(f"Genero la ROM randomizzata della run #{run}…\nCi vuole qualche secondo.")
            self.pile.setCurrentIndex(0)

            ed = self.edizione()

            def lavoro():
                out, msg = self.run_mgr.randomizza(run, ed)
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

    def edizione(self) -> str:
        if self.sincro.edizione is not None:
            return self.sincro.edizione
        return self.locale.get("ultima_edizione", "")

    def rom_attesa(self) -> Path:
        return self.run_mgr.rom_per_run(self.run_desiderata, self.edizione())

    def _fine_randomizzazione(self, run, out, msg):
        self._occupato = False
        if out is None:
            self._log(msg, KO)
            self.segnaposto.setText("Non sono riuscito a generare la ROM:\n\n" + msg)
            self.b_avvia_centro.setText("Riprova")
            self.b_avvia_centro.show()
            corto, _, lungo = msg.partition("\n")
            dialoghi.avviso(self, "Il randomizer non è riuscito a creare la ROM", corto, "errore", dettagli=lungo.strip() or None)
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
            ed = self.edizione()
            viste = self.locale.get("edizioni", [])
            if ed and ed not in viste:
                viste = viste + [ed]
            self.locale.update(ultima_run=run, ultima_edizione=ed, edizioni=viste, ultimo_accesso=time.time())
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
            if not dialoghi.chiedi(self, "Riavviare il gioco?", "BizHawk verrà chiuso e riaperto. Prima di chiuderlo "
                                   "l'app fa un backup del punto in cui sei.", si="Riavvia", no="Annulla"):
                return
            self._salva_e_ferma("cambio", self._avvia_richiesto.emit)
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
        if not self.cfg["randomizza"]:
            dati["run_rom"] = None
        elif rom and self.sincro.run is not None:
            dati["run_rom"] = self.sincro.run if Path(rom) == self.rom_attesa() else -1   # ROM di un'altra run/edizione
        else:
            dati["run_rom"] = run_della_rom(rom) if rom else -1
        risposte = dati.pop("risposte", None)
        if risposte:
            self._risposte.emit(risposte)
        if isinstance(dati.get("box"), list) and dati.get("box_ok"):
            self._box_gioco = list(dati["box"])
        if dati.get("squadra"):
            self._squadra_gioco = list(dati["squadra"])
            self._in_gui.emit(self._pubblica_squadra)          # siamo nel thread del ponte
            if self._det_lotta:
                self._dettagli.emit(self._det_lotta)
        if "lotta_dettagli" in dati:                     # solo per il tracker della lotta, non per la partita
            self._det_lotta = dati.pop("lotta_dettagli") or None
            self._dettagli.emit(self._det_lotta)
            if self._det_lotta and self._det_lotta.get("allenatore"):
                t, z = self._det_lotta["allenatore"], dati.get("zona")
                self._in_gui.emit(lambda: self._impara_scarto_script(t, z))
        if "flag_evento" in dati:                        # strumenti raccolti, allenatori battuti
            try:
                self._flag_evento = bytes.fromhex(dati.pop("flag_evento") or "")
            except ValueError:
                pass
            self._in_gui.emit(self._aggiorna_conteggi)
        for e in dati.get("eventi") or []:
            if e.get("tipo") == "fine_allenatore" and e.get("vinta") and e.get("allenatore"):
                t = int(e["allenatore"])
                self._in_gui.emit(lambda t=t: self._segna_vinto(t))
        if dati.get("ping"):                             # contatto leggero: solo comandi, niente partita
            return self._righe_per_lua(dati, solo_comandi=True)
        self._gioco_attivo = bool(dati.get("attivo"))
        self.sincro.accoda(dati)
        return self._righe_per_lua(dati)

    def _righe_per_lua(self, dati, solo_comandi=False):
        righe = ["OK"]
        if not solo_comandi:
            if self.sincro.run is not None:
                righe.append(f"RUN {self.sincro.run} {self.sincro.stato or 'in_corso'}")
            righe += [per_overlay(r) for r in self.sincro.messaggi_per_lua()]
        with self._lock:
            if not solo_comandi:
                righe += [f"AVVISO {per_overlay(a)}" for a in self._avvisi_lua]
                self._avvisi_lua.clear()
            righe += self._comandi_lua
            self._comandi_lua.clear()
        self._misura_velocita(dati)
        righe.append(f"VELOCITA {int(self.cfg.get('velocita', 100) or 100)}")
        blocca = self.cfg.get("blocca_input", True) is not False and not self._in_primo_piano
        righe.append(f"FOCUS {0 if blocca else 1}")
        if not solo_comandi:
            righe.append(f"DIAG {1 if self.cfg['diagnostica'] else 0}")
            st = self._ultimo_stato or {}
            reg = st.get("regole") or {}
            righe.append("MODO allenatori" if reg.get("solo_allenatori") else "MODO normale")
            righe.append(f"CONDIVIDI {1 if reg.get('condividi_esp') else 0}")
            righe.append(f"CONTROLLO {1 if self._controllo_esp_attivo(reg) else 0}")
        return "\n".join(righe) + "\n"

    def _imposta_velocita(self, v):
        self.cfg["velocita"] = v
        self.cfg.salva()
        self._aggiorna_vel()

    def _aggiorna_vel(self, reale=None):
        v = int(self.cfg.get("velocita", 100) or 100)
        nome = "max" if v >= 6400 else f"×{v // 100}"
        testo = f"Velocità {nome}"
        if reale is not None and self.emu.in_esecuzione:
            testo += f" ({reale:.1f})".replace(".", ",")
            self.b_vel.setToolTip(f"Velocità scelta: {nome}. Velocità vera del gioco adesso: ×{reale:.1f}".replace(".", ",")
                                  + ". Se resta più bassa di quella scelta, il PC non ce la fa ad andare più veloce. "
                                  "Tab tenuto premuto resta l'avanti veloce di BizHawk.")
        self.b_vel.setText(testo)
        for a in self.m_vel.actions():
            a.setChecked(a.data() == v)

    def _misura_velocita(self, dati):
        """Velocità vera del gioco (fotogrammi al secondo / 60), dai contatti dello script: dice se il PC ce la fa."""
        fc = dati.get("fc")
        if fc is None:
            return
        ora = time.time()
        prima = getattr(self, "_vel_campione", None)
        if prima and ora - prima[1] >= 2 and fc > prima[0]:
            reale = (fc - prima[0]) / (ora - prima[1]) / 60
            self._vel_campione = (fc, ora)
            self._in_gui.emit(lambda r=reale: self._aggiorna_vel(r))
        elif not prima or fc < prima[0] or ora - prima[1] > 10:
            self._vel_campione = (fc, ora)

    def _controlla_focus(self):
        """L'app (con BizHawk dentro) è la finestra in primo piano? Se no, i tasti non devono arrivare al gioco."""
        if sys.platform == "win32":
            try:
                import ctypes
                u = ctypes.windll.user32
                u.GetForegroundWindow.restype = ctypes.c_void_p
                u.GetAncestor.restype = ctypes.c_void_p
                u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                fg = u.GetForegroundWindow()
                radice = u.GetAncestor(fg, 2) if fg else None          # GA_ROOT
                attivo = bool(radice) and int(radice) == int(self.winId())
            except Exception:
                attivo = QApplication.applicationState() == Qt.ApplicationActive
        else:
            attivo = QApplication.applicationState() == Qt.ApplicationActive
        if attivo != self._in_primo_piano:
            self._in_primo_piano = attivo

    def _mostra_lotta(self, det):
        in_lotta = bool(det)
        self.c_obiettivo.setVisible(not in_lotta)
        self.c_luogo.setVisible(not in_lotta)
        self.s_lotta.setVisible(in_lotta)
        self.c_lotta.setVisible(in_lotta)
        self._dv.setStretchFactor(self._riga, 3 if in_lotta else 0)       # in lotta il riquadro prende più spazio delle schede
        self.l_avvisi.setVisible(not in_lotta and bool((self._ultimo_stato or {}).get("avvisi")))
        self._dv.setStretchFactor(self.tabs, 1)
        if in_lotta:
            self._carica_impara()
            self.c_lotta.aggiorna(det, self._squadra_gioco)
            self._avvisa_lotta_importante(det)
            self._controlla_esperienza(det)
            m = det.get("mio") or {}
            nome_m = next((p.get("soprannome") or L.info(p["specie"])["nome"] for p in self._squadra_gioco
                           if p.get("pid") == m.get("pid")), "")
            self._controlla_critico(self.cfg["giocatore"], {**m, "nome": nome_m}, det.get("allenatore"))
        self._pubblica_squadra()
        if self._ultimo_stato:
            self.p_coppie.aggiorna(self._con_dati_vivi(self._ultimo_stato), self.cfg["giocatore"])

    def _aggiorna_storia(self, st, io):
        """Luoghi visitati (miei, dal gioco; degli altri, dalla loro app) e prossima tappa della storia di ognuno."""
        from . import storia
        chiave = str(st.get("run"))
        tutti = dict(self.locale.get("visitati") or {})
        mie = set(tutti.get(chiave, []))
        prima = set(mie)
        x = st["giocatori"].get(io) or {}
        if self._gioco_attivo and str(x.get("luogo_attuale") or "").isdigit():
            mie.add(int(x["luogo_attuale"]))
        for r in st.get("percorsi") or []:                 # dove ho incontrato o catturato qualcosa
            y = (r.get("giocatori") or {}).get(io) or {}
            if (y.get("incontro") or y.get("cattura")) and str(r["luogo"]).isdigit():
                mie.add(int(r["luogo"]))
        if mie != prima:
            self.locale["visitati"] = {chiave: sorted(mie)}          # solo la run attuale
            self.locale.salva()
        if sorted(mie) != self.sincro._presenza.get("visitati"):
            self.sincro.imposta_presenza(visitati=sorted(mie))
        fatti = st.get("fatti") or {}
        for g, y in st["giocatori"].items():
            vis = mie if g == io else set(y.get("visitati") or [])
            y["tappa"] = storia.prossima(fatti.get(g) or {}, vis)
            y["visitati_set"] = sorted(vis)

    def _con_dati_vivi(self, st):
        """Copia dello stato con PS e stato attuali dei Pokémon in squadra (dal gioco per i miei, dalle app degli altri
        per i loro): in lotta sono quelli veri di adesso."""
        io = self.cfg["giocatore"]
        vivi = {}
        for p in self.sincro._presenza.get("squadra") or self._squadra_gioco:
            vivi[(io, p.get("pid"))] = p
        for g, x in (st.get("giocatori") or {}).items():
            if g != io:
                for p in x.get("squadra_dett") or []:
                    vivi[(g, p.get("pid"))] = p
        P = {}
        for k, p in st["pokemon"].items():
            d = vivi.get((p["giocatore"], p.get("pid")))
            if d and p["stato"] == "squadra":
                p = {**p, "ps": d.get("ps", p.get("ps")), "ps_max": d.get("ps_max", p.get("ps_max")),
                     "stato_alt": d.get("stato_alt"), "stato_lotta": d.get("stato_lotta")}
            P[k] = p
        return {**st, "pokemon": P}

    def _controlla_critico(self, g, m, allenatore):
        """Avviso per tutti quando il Pokémon in campo di qualcuno ha pochi PS (20% o meno)."""
        if not m or not m.get("ps_max") or not m.get("pid"):
            return
        chiave = (g, m["pid"])
        critico = 0 < (m.get("ps") or 0) <= m["ps_max"] * 0.2
        if not critico:
            self._critici.discard(chiave)
            return
        if chiave in self._critici:
            return
        self._critici.add(chiave)
        nome_m = m.get("nome") or L.info(m.get("specie") or 0)["nome"]
        if g == self.cfg["giocatore"]:
            self.notifiche.grande(f"{nome_m} è in pericolo!", f"Gli restano <b>{m.get('ps')}/{m['ps_max']}</b> PS. Pensaci bene prima "
                                  "della prossima mossa.", KO, "!", 8)
        else:
            self.notifiche.grande(f"{g}: {nome_m} è in pericolo!", f"Gli restano {m.get('ps')}/{m['ps_max']} PS. Tifate per lui!",
                                  WARN, "!", 7)

    def _avvisa_lotta_importante(self, det):
        """Notifica grande all'inizio della lotta contro un capopalestra, il rivale, il Team Plasma, la Lega."""
        o = L.OBIETTIVO_DA_ID.get(det.get("allenatore") or -1)
        st = self._ultimo_stato
        if not o or not st:
            return
        chiave = (st.get("run"), st.get("edizione"), o["id"])
        if chiave in self._lotte_avvisate:
            return
        self._lotte_avvisate.add(chiave)
        io = self.cfg["giocatore"]
        n = len(det.get("nemici") or [])
        testo = [f"Ha {n} Pokémon." if n else "", "È uno degli obiettivi importanti della run: occhio alle mosse!"]
        cap = (st["giocatori"].get(io) or {}).get("cap")
        if st["regole"].get("level_cap", True) and isinstance(cap, int):
            sopra = [p for p in self._squadra_gioco if not p.get("uovo") and (p.get("livello") or 0) > cap]
            if sopra:
                nomi = ", ".join(f"{p.get('soprannome') or L.info(p['specie'])['nome']} (Lv.{p.get('livello')})" for p in sopra[:3])
                testo.append(f"<b style='color:{WARN}'>Sopra il level cap {cap}:</b> {nomi}")
            else:
                testo.append(f"<span style='color:{TENUE}'>Level cap: {cap}</span>")
        self.notifiche.grande(f"Lotta contro {o['nome']}", "<br>".join(t for t in testo if t), KO, "VS", 10)

    def _carica_impara(self):
        """Legge dalla ROM randomizzata le mosse che ogni Pokémon impara salendo di livello (una volta per ROM)."""
        rom = self.emu.rom
        if not rom or rom == self._impara_rom:
            return
        self._impara_rom = rom
        self._incontri_rom = None

        def lavoro():
            from . import rom as R
            try:
                dati = R.mosse_per_livello(rom)
            except Exception as e:
                dati = {}
                self._avviso.emit(f"Non riesco a leggere le mosse dalla ROM ({e})", WARN)
            try:
                inc = R.incontri(rom)
            except Exception as e:
                inc = False                      # non leggibile: si avvisa in tutti i luoghi con un nome
                self._avviso.emit(f"Non riesco a leggere dalla ROM dove sono i selvatici ({e})", WARN)
            try:
                nomi = R.nomi(rom)
            except Exception as e:
                nomi = {}
                self._avviso.emit(f"Non riesco a leggere dalla ROM i nomi di luoghi e allenatori ({e})", WARN)
            try:
                ent = R.entita(rom)
            except Exception as e:
                ent = None
                self._avviso.emit(f"Non riesco a leggere dalla ROM allenatori e strumenti delle zone ({e})", WARN)

            def fatto():
                if rom == self.emu.rom:
                    L.imposta_dati_rom((inc or {}).get("zona_luogo"), nomi.get("luoghi"), nomi.get("allenatori"))
                    self.c_lotta.imposta_impara(dati)
                    self._incontri_rom = inc
                    self._entita_rom = ent
                    self._pubblica_squadra()
                    self._aggiorna_conteggi()
                    if self._ultimo_stato:
                        self._controlla_luogo(self._ultimo_stato, self.cfg["giocatore"])
            self._in_gui.emit(fatto)
        threading.Thread(target=lavoro, daemon=True).start()

    def _messaggio(self, t):
        """Messaggi della partita: quelli sugli obiettivi importanti diventano notifiche grandi."""
        import re
        self._log(t, ORO)
        io = self.cfg["giocatore"]
        m = re.match(r"^(.+) ha battuto (.+)!$", t)
        nomi_obiettivi = {o["nome"] for o in L.OBIETTIVI}
        if m and m.group(2) in nomi_obiettivi:
            chi, contro = m.group(1), m.group(2)
            if chi == io:
                self.notifiche.grande(f"Hai battuto {contro}!", "Obiettivo importante completato. Bel colpo!", ORO, "★", 12)
            else:
                self.notifiche.grande(f"{chi} ha battuto {contro}!", f"Obiettivo importante completato da {chi}.", "#b9a8ff", "★", 9)
        elif t.startswith("RUN VINTA") or t.startswith("Superquattro battuti") or t.startswith("Hai battuto la Campionessa"):
            self.notifiche.grande(t.split("!")[0] + "!", t.split("!", 1)[1].strip(), ORO, "★", 14)
        else:
            self.notifiche.mostra(t)

    def _controlla_luogo(self, st, io):
        """Notifica grande quando entri in un luogo dove il tuo primo incontro è ancora da fare."""
        x = st["giocatori"].get(io) or {}
        luogo = x.get("luogo_attuale")
        if luogo is None or luogo == self._ultimo_luogo or st["stato"] != "in_corso" or not self._gioco_attivo:
            return
        if self._incontri_rom is None:
            self._carica_impara()
            return                                   # la ROM si sta ancora leggendo: riprovo al prossimo aggiornamento
        self._ultimo_luogo = luogo
        chiave = (st["run"], st.get("edizione"), luogo)
        if chiave in self._luoghi_avvisati:
            return
        riga = next((r for r in st["percorsi"] if r["luogo"] == luogo), None)
        mio = ((riga or {}).get("giocatori") or {}).get(io) or {}
        if mio.get("cattura") or mio.get("incontro"):
            return                                   # qui hai già fatto il tuo incontro
        tipo = None
        if self._incontri_rom:
            if str(luogo).isdigit():
                tipo = self._incontri_rom["luoghi"].get(int(luogo))
            elif x.get("zona") is not None:
                tipo = self._incontri_rom["zone"].get(int(x["zona"]))
            if not tipo:
                return                               # qui non ci sono selvatici
        elif not str(luogo).isdigit():
            return
        self._luoghi_avvisati.add(chiave)
        nome_l = x.get("zona_nome") or L.nome_luogo(luogo)
        falliti = [g for g, y in ((riga or {}).get("giocatori") or {}).items()
                   if g != io and y.get("incontro") and y["incontro"]["esito"] == "fallito"]
        nota = f"<br><span style='color:{WARN}'>{falliti[0]} ha fallito qui: la tua cattura andrà nel box.</span>" if falliti else ""
        if tipo == "acqua":
            self.notifiche.mostra(f"{nome_l}: incontro ancora libero, ma qui i selvatici sono solo in acqua (Surf o pesca).",
                                  "#6cb8ff", 8)
            return
        self.notifiche.grande(f"Cattura da fare: {nome_l}",
                              "Il primo Pokémon selvatico che incontri qui è quello che conta." + nota, OK, "!", 12)

    def _script_collegato(self, ok):
        if not ok:
            self._det_lotta = None
            self._mostra_lotta(None)
        self.i_script.imposta(ok, "collegato" if ok else "")
        self.sincro.imposta_presenza(emulatore=ok)
        if ok:
            self._log("Lo script di BizHawk è collegato all'app", OK)
            self._ultimo_backup = time.time()
            self._carica_impara()
            from .config import cartella_documenti
            d = cartella_documenti() / "diagnosi"
            d.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self._comandi_lua.append(f"DUMPLOTTA {d / 'ultima_lotta.txt'}")
            QTimer.singleShot(1500, self._proponi_ripresa)
            QTimer.singleShot(12000, self._controllo_automatico)

    # ================================================================ stato condiviso
    def _stato_server(self, st):
        self._ultimo_stato = st
        G = st["giocatori"]
        rias = {"run": st["run"], "stato": st["stato"],
                "giocatori": {g: G[g].get("medaglie") or 0 for g in sorted(G, key=lambda g: (G[g].get("entrato") or 0, g))}}
        if self.locale.get("riassunto") != rias:          # per la finestra di scelta della partita, anche senza rete
            self.locale["riassunto"] = rias
            self.locale.salva()
        self.stato_run = st["stato"]
        io = self.cfg["giocatore"]
        self._aggiorna_storia(st, io)
        self.barra.aggiorna(st, io)
        self.barra.tic()
        self.c_obiettivo.aggiorna(st, io)
        self.c_luogo.aggiorna(st, io)
        self._aggiorna_conteggi()
        self._controlla_luogo(st, io)
        from .scheda import SchedaPokemon
        SchedaPokemon.aggiorna_tutte()
        if self._mappa is not None and self._mappa.isVisible():
            self._mappa.imposta(st, io)
        if st["avvisi"]:
            righe = [f"⚠&nbsp;&nbsp;{html.escape(a)}" for a in st["avvisi"][:3]]
            if len(st["avvisi"]) > 3:
                righe.append(f"<span style='color:#b8955a'>… e altri {len(st['avvisi']) - 3}: passa qui sopra col mouse per vederli</span>")
            self.l_avvisi.setText(paragrafi(righe, 5))
            self.l_avvisi.setToolTip("\n".join(st["avvisi"]))
            self.l_avvisi.setVisible(not self._det_lotta)        # in lotta lo spazio va al riquadro della lotta
        else:
            self.l_avvisi.hide()
        for k, a in self.a_regole.items():
            predefinita = k != "tipi"                      # il tipo unico è spento se non scelto
            a.setChecked(bool(st["regole"].get(k, predefinita)))
        self.a_lega.setChecked(bool(st.get("lega")))
        self.a_solo_allenatori.setChecked(bool(st["regole"].get("solo_allenatori")))
        self.a_condividi.setChecked(bool(st["regole"].get("condividi_esp")))
        self.a_cap_bloccato.setChecked(bool(st["regole"].get("cap_bloccato")))
        m = float(st["regole"].get("molt_condividi") or 1)
        for v, a in self.a_molt.items():
            a.setChecked(abs(v - m) < 1e-6)
        self.m_molt.setEnabled(bool(st["regole"].get("condividi_esp")))
        self.p_coppie.aggiorna(self._con_dati_vivi(st), io)
        for g, x in st["giocatori"].items():              # Pokémon in pericolo degli altri
            if g != io:
                a = x.get("attivita") or {}
                if a.get("lotta") and a.get("mio"):
                    self._controlla_critico(g, a["mio"], a.get("allenatore"))
        for p in (self.p_percorsi, self.p_obiettivi, self.p_cimitero, self.p_diario, self.p_stat):
            p.aggiorna(st)
        self.p_diag.aggiorna(st)
        chiave = (st["run"], st["stato"])
        if st["stato"] in ("game_over", "vinta") and self._popup_visto != chiave:
            self._popup_visto = chiave
            QTimer.singleShot(100, lambda: self._fine_run(st))

    def _fine_run(self, st):
        if st["stato"] == "vinta":
            ok = dialoghi.chiedi(self, "Run vinta! Complimenti!", f"{st.get('motivo', '')}\n\nVuoi iniziare una nuova run?",
                                 si="Nuova run", no="Più tardi", tipo="ok")
        else:
            ok = dialoghi.chiedi(self, "Game over", f"{st.get('motivo', '')}\n\nVuoi iniziare subito una nuova run? "
                                 "Verranno generate ROM nuove per tutti.", si="Nuova run", no="Più tardi", tipo="errore")
        if ok:
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
        if dialoghi.chiedi(self, "Nuova run", domanda + "\n\nVerranno generate ROM nuove per tutti i giocatori.",
                           si="Nuova run", no="Annulla", pericolo=self.stato_run == "in_corso"):
            self._azione({"azione": "nuova_run"})
            self._log("Nuova run richiesta…")

    def _imposta_partenza(self):
        if not self.ponte.attivo:
            dialoghi.avviso(self, "Salvataggio di partenza", "Avvia prima il gioco: lo script deve essere collegato.", "info")
            return
        r = dialoghi.chiedi(self, "Usare il salvataggio attuale come partenza?",
                            "Prima salva nel gioco (menu → Salva) il più vicino possibile alla Vedetta di Alisopoli, "
                            "PRIMA della scena in cui ricevi lo starter.\n\nFatto? Userò quel salvataggio "
                            "come partenza per le prossime run.", si="Sì, usalo", no="Annulla")
        if r:
            with self._lock:
                self._comandi_lua.append("SALVABASE")
            self._log("Chiedo allo script il salvataggio attuale…")

    def _condividi_esp(self, val):
        self.a_condividi.setChecked(not val)
        testo = ("Per tutti i giocatori della partita: dopo ogni lotta prende esperienza tutta la squadra, "
                 "anche chi non ha combattuto (come il Condividi Esperienza dei giochi più recenti).\n\n"
                 "Si può usare con o senza «Esperienza solo dagli allenatori»." if val else
                 "Torna l'esperienza normale: la prende solo chi ha partecipato alla lotta.")
        if dialoghi.chiedi(self, "Condividi esperienza?" if val else "Disattivare Condividi esperienza?", testo,
                           si="Attiva" if val else "Disattiva", no="Annulla"):
            self._azione({"azione": "regole", "regole": {"condividi_esp": bool(val)}})
            self.a_condividi.setChecked(bool(val))

    def _cap_bloccato(self, val):
        self.a_cap_bloccato.setChecked(not val)
        if val:
            ok = dialoghi.chiedi(self, "Bloccare il level cap?",
                                 "Modalità sperimentale, per tutti i giocatori della partita: nessun Pokémon può andare oltre "
                                 "il level cap. Se un Pokémon al 12 con cap 13 battendo un avversario salirebbe al 14, si ferma "
                                 "al 13; al cap non prende più esperienza.\n\n"
                                 "Prima di ogni Pokémon battuto l'app calcola quanta esperienza arriverebbe e la riduce quanto "
                                 "serve. Con Condividi esperienza vale per tutta la squadra: il Pokémon più vicino al cap "
                                 "decide per tutti.", si="Blocca il cap", no="Annulla")
        else:
            ok = dialoghi.chiedi(self, "Sbloccare il level cap?", "L'esperienza torna normale.", si="Sblocca", no="Annulla")
        if ok:
            self._azione({"azione": "regole", "regole": {"cap_bloccato": bool(val)}})
            self.a_cap_bloccato.setChecked(bool(val))

    def _modo_allenatori(self, val):
        self.a_solo_allenatori.setChecked(not val)          # cambia solo se confermato (e poi arriva dallo stato)
        if val:
            ok = dialoghi.chiedi(self, "Esperienza solo dagli allenatori?",
                                 "Modalità sperimentale, per tutti i giocatori della partita:\n\n"
                                 "• i Pokémon selvatici non danno esperienza;\n"
                                 "• gli allenatori ne danno quanto basta per portare il tuo primo Pokémon al livello "
                                 "del loro Pokémon più forte, senza superare il level cap (se sei già a quel livello, niente).\n\n"
                                 "Funziona come i codici «moltiplicatore di esperienza»: l'app cambia per un attimo il "
                                 "calcolo dell'esperienza durante la lotta, poi lo rimette com'era.",
                                 si="Attiva", no="Annulla")
        else:
            ok = dialoghi.chiedi(self, "Tornare all'esperienza normale?", "Anche i selvatici torneranno a dare esperienza.",
                                 si="Torna normale", no="Annulla")
        if ok:
            self._azione({"azione": "regole", "regole": {"solo_allenatori": bool(val)}})
            self.a_solo_allenatori.setChecked(bool(val))

    def _conta_ignorato(self):
        st = self._ultimo_stato or {}
        io = self.cfg["giocatore"]
        inc = next((e for e in st.get("incontri", []) if e["g"] == io and e.get("ignorato")), None)
        if not inc:
            dialoghi.avviso(self, "Nessun incontro ignorato", "Non hai incontri ignorati da far contare.", "info")
            return
        motivi = {"tutorial": "tutorial", "shiny": "shiny", "doppione": "clausola doppioni", "luogo_usato": "luogo già usato"}
        if dialoghi.chiedi(self, "Far contare l'incontro?", f"Incontro con {inc['nome_specie']} a {inc['luogo_nome']}, "
                           f"ignorato per: {motivi.get(inc['ignorato'], inc['ignorato'])}.", si="Fallo contare", no="Annulla"):
            self._azione({"azione": "conta_incontro", "id": inc["id"]})

    def _cancella_partenza(self):
        f = self.run_mgr.file_base
        if not f.exists():
            dialoghi.avviso(self, "Salvataggio di partenza", "Non c'è nessun salvataggio di partenza.", "info")
            return
        if dialoghi.chiedi(self, "Cancellare il salvataggio di partenza?", "Le prossime run partiranno dall'inizio del gioco "
                           "finché non ne crei uno nuovo.", si="Cancella", no="Annulla", pericolo=True):
            f.unlink()
            self._log("Salvataggio di partenza cancellato")
            self._aggiorna_locale()

    def _reset_totale(self):
        n = len((self._ultimo_stato or {}).get("giocatori", {}))
        d = DialogoReset(self, n)
        if not d.exec():
            return
        condivisa, locale, partenza = d.condivisa.isChecked(), d.locale.isChecked(), d.partenza.isChecked()
        self._log("Reset in corso…", WARN)

        def dopo_arresto():
            if locale or partenza:
                via = self.run_mgr.cancella_tutto(anche_partenza=partenza, edizioni=self.locale.get("edizioni", [])) if locale else []
                if partenza and not locale and self.run_mgr.file_base.exists():
                    self.run_mgr.file_base.unlink()
                    via.append(self.run_mgr.file_base)
                self._log(f"Cancellati {len(via)} file (ROM, salvataggi e stati di BizHawk)", OK)
            self.locale.update(ultima_run=1)
            self.locale.salva()
            self._aggiorna_locale()
            if condivisa:
                def fine(r):
                    self._avviso.emit("Partita azzerata: si riparte dalla run #1" if not r.get("errore") else "Errore: " + r["errore"],
                                      OK if not r.get("errore") else KO)
                    self._avvia_richiesto.emit()
                self.sincro.azione({"azione": "reset_partita", "giocatore": self.cfg["giocatore"]}, fine)
            else:
                self._avvia_richiesto.emit()

        self._occupato = True
        self._dopo_reset = dopo_arresto          # prima di chiedere la chiusura: BizHawk può chiudersi in fretta
        if self.emu.in_esecuzione:
            self.emu.ferma(alla_fine=self._per_reset.emit)
        else:
            dopo_arresto()

    def _esegui_dopo_reset(self):
        f, self._dopo_reset = getattr(self, "_dopo_reset", None), None
        if f:
            f()

    def _impostazioni(self):
        prima = self.cfg.get("codice")
        if Impostazioni(self.cfg, self).exec():
            self._log("Impostazioni salvate")
            if self.cfg.get("codice") != prima and self.cfg.get("codice"):
                nuovo = self.cfg["codice"]
                self.cfg["codice"] = prima
                self._passa_a_partita(nuovo)
                return
            self.sincro.riconfigura()
            self._aggiorna_locale()
            if not self.emu.in_esecuzione:
                self.assicura_gioco()

    # ================================================================ backup
    def _run_in_gioco(self):
        return run_della_rom(self.emu.rom) if self.emu.rom else None

    def _chiedi_backup(self, tipo, alla_fine=None, attesa=6.0):
        """Chiede allo script uno stato salvato + il salvataggio del gioco. alla_fine(ok) arriva sempre (anche se va male)."""
        run = self._run_in_gioco()
        if not (self.emu.in_esecuzione and self.ponte.attivo and run is not None):
            if alla_fine:
                alla_fine(False)
            return
        self._id_richiesta += 1
        rid = self._id_richiesta
        percorso = self.backup.nuovo(run, tipo)
        self._richieste[rid] = {"tipo": tipo, "percorso": percorso, "rom": self.emu.rom, "run": run, "alla_fine": alla_fine}
        with self._lock:
            self._comandi_lua.append(f"BACKUP {rid} {percorso}")

        def scaduto():
            r = self._richieste.pop(rid, None)
            if r:
                self._log("Backup non riuscito: lo script non ha risposto", WARN)
                if r["alla_fine"]:
                    r["alla_fine"](False)
        QTimer.singleShot(int(attesa * 1000), scaduto)

    def _gestisci_risposte(self, risposte):
        for x in risposte:
            if x.get("tipo") == "dump":
                f, self._dump_attesa = getattr(self, "_dump_attesa", None), None
                if f:
                    f(bool(x.get("ok")), x.get("errore"))
                continue
            if x.get("tipo") == "flag_allenatore":
                self._calibra_flag_allenatori(x)
                continue
            if x.get("tipo") == "allenatore_esp":
                self._esperienza_allenatore(x)
                continue
            if x.get("tipo") == "condividi_sito":
                if x.get("ok"):
                    self._log(f"Condividi esperienza: codice del gioco trovato (0x{x.get('indirizzo', 0):06X})", OK)
                else:
                    self._log("Condividi esperienza: non trovo il punto giusto in questa ROM", KO)
                    dialoghi.avviso(self, "Condividi esperienza non disponibile",
                                    "Non trovo nel gioco il punto in cui si decide chi prende l'esperienza, quindi resta "
                                    "normale. Mandami la scheda Sistema.", "avviso")
                continue
            if x.get("tipo") == "esp_sito":
                if x.get("ok"):
                    self._log(f"Esperienza solo dagli allenatori: codice del gioco trovato (0x{x.get('indirizzo', 0):06X})", OK)
                else:
                    self._log("Esperienza solo dagli allenatori: non trovo il calcolo dell'esperienza in questa ROM", KO)
                    dialoghi.avviso(self, "Modalità non disponibile su questa ROM",
                                    "Non trovo nel gioco il punto in cui si calcola l'esperienza, quindi in questa lotta "
                                    "l'esperienza resta normale. Mandami la scheda Sistema: probabilmente serve "
                                    "l'indirizzo giusto per la tua versione.", "avviso")
                continue
            r = self._richieste.pop(x.get("id"), None)
            if not r:
                continue
            if x.get("tipo") == "backup":
                ok = bool(x.get("ok")) and self.backup.completa(r["percorso"], r["rom"])
                if ok:
                    self.backup.pulisci(r["run"])
                    if r["tipo"] == "auto":
                        self._ultimo_backup = time.time()
                    self._log(f"Backup {TIPI_BACKUP.get(r['tipo'], r['tipo'])} salvato ({r['percorso'].name})", OK)
                else:
                    self._log("Backup non riuscito: BizHawk non ha scritto lo stato salvato", WARN)
                if r["alla_fine"]:
                    r["alla_fine"](ok)
            elif x.get("tipo") == "caricato":
                if x.get("ok"):
                    self._log(f"Ripreso il backup {r['percorso'].name}", OK)
                    self.notifiche.mostra("Ripreso da dove avevi lasciato", OK)
                    QTimer.singleShot(8000, self._controllo_automatico)
                else:
                    self._log("BizHawk non è riuscito a caricare il backup", KO)
                    dialoghi.avviso(self, "Backup non caricato", "BizHawk non è riuscito a caricare lo stato salvato. "
                                    "Puoi riprovare dalla finestra Backup oppure continuare dal salvataggio del gioco.", "errore")
                if r["alla_fine"]:
                    r["alla_fine"](bool(x.get("ok")))

    def _esperienza_allenatore(self, x):
        """Lo script chiede quanta esperienza dare nella lotta con un allenatore appena iniziata."""
        from . import esperienza
        st = self._ultimo_stato or {}
        cap = ((st.get("giocatori") or {}).get(self.cfg["giocatore"]) or {}).get("cap") or 100
        dividi = (x.get("vivi") or 1) if (st.get("regole") or {}).get("condividi_esp") else 1
        r = esperienza.moltiplicatore(x.get("nemici") or [], x.get("primo"), cap, dividi)
        self._esp["n_all"] = r["n"]                    # lo usa il controllo dell'esperienza di ogni Pokémon battuto
        self._esp["n_all_per"] = x.get("allenatore")
        if self._det_lotta:
            self._controlla_esperienza(self._det_lotta)
        o = L.OBIETTIVO_DA_ID.get(x.get("allenatore") or -1)
        chi = o["nome"] if o else "l'allenatore"
        # niente livelli né nomi: non deve far capire com'è la squadra dell'allenatore
        if r["n"] > 0:
            t = f"Lotta con {chi}: esperienza ×{r['n']}"
        elif r.get("obiettivo"):
            t = f"Lotta con {chi}: niente esperienza, sei già al suo livello"
        else:
            t = f"Lotta con {chi}: esperienza normale ({r.get('motivo')})"
        self._log(t, ORO if r["n"] else TENUE)
        self.notifiche.mostra(t, ORO if r["n"] else TENUE, 5)

    @staticmethod
    def _controllo_esp_attivo(reg):
        return bool(reg.get("solo_allenatori") or reg.get("cap_bloccato")
                    or (reg.get("condividi_esp") and float(reg.get("molt_condividi") or 1) < 1))

    def _controlla_esperienza(self, det):
        """Prima di ogni Pokémon battuto decide quanta esperienza dare: niente oltre il level cap (se bloccato), Condividi
        esperienza ridotto, solo allenatori. Lo script cambia il calcolo dell'esperienza del gioco per quel Pokémon."""
        from . import esperienza as E
        st = self._ultimo_stato or {}
        reg = st.get("regole") or {}
        if not det or not self._controllo_esp_attivo(reg):
            return
        nemici = det.get("nemici") or []
        chiave = (det.get("allenatore"), tuple(n.get("specie") for n in nemici))
        if self._esp.get("lotta") != chiave:
            self._esp.update(lotta=chiave, extra={}, previsti={}, contati=set(), ultimo=None)
            if self._esp.get("n_all_per") != det.get("allenatore"):
                self._esp["n_all"] = None
        # i Pokémon avversari appena battuti: la loro esperienza è già arrivata (la squadra si aggiorna solo a fine lotta)
        for i, n in enumerate(nemici):
            if (n.get("ps") or 0) == 0 and i in self._esp["previsti"] and i not in self._esp["contati"]:
                self._esp["contati"].add(i)
                for pid, e in self._esp["previsti"][i].items():
                    attuale = next((p.get("esperienza") or 0 for p in self._squadra_gioco if p.get("pid") == pid), 0)
                    base, somma = self._esp["extra"].get(pid, (attuale, 0))
                    self._esp["extra"][pid] = (base, somma + e)
        attivi = [i for i, n in enumerate(nemici) if n.get("in_campo") and (n.get("ps") or 0) > 0]
        vivi_n = [i for i, n in enumerate(nemici) if (n.get("ps") or 0) > 0]
        idx = (attivi or vivi_n or [None])[0]
        if idx is None:
            return
        live = {m["pid"]: m for m in det.get("squadra") or []}
        squadra = []
        for p in self._squadra_gioco:
            if p.get("uovo"):
                continue
            ps = live.get(p.get("pid"), {}).get("ps", p.get("ps") or 0)
            if ps <= 0:
                continue
            q = dict(p)
            base, extra = self._esp["extra"].get(p.get("pid"), (0, 0))
            if extra and (p.get("esperienza") or 0) > base:   # il gioco ha già aggiornato l'esperienza: niente stime
                self._esp["extra"].pop(p.get("pid"), None)
                extra = 0
            if extra:
                q["esperienza"] = (p.get("esperienza") or 0) + extra
                curva = E.curva_di(p.get("specie"), p.get("livello") or 1, p.get("esperienza"))
                lv = p.get("livello") or 1
                while lv < 100 and E.esp_per_livello(curva, lv + 1) <= q["esperienza"]:
                    lv += 1
                q["livello"] = lv
            squadra.append(q)
        if reg.get("condividi_esp"):
            riceventi = squadra
        else:
            pid_mio = (det.get("mio") or {}).get("pid")
            riceventi = [q for q in squadra if q.get("pid") == pid_mio] or squadra[:1]
        io = self.cfg["giocatore"]
        cap = ((st.get("giocatori") or {}).get(io) or {}).get("cap") or 100
        tid = (self._squadra_gioco[0].get("id_allenatore") if self._squadra_gioco else None)
        codice, prev, perche = E.controllo(nemici[idx], riceventi, bool(det.get("allenatore")), reg, cap,
                                           self._esp.get("n_all"), tid)
        if codice is None:
            return
        self._esp["previsti"][idx] = prev
        if codice != self._esp.get("ultimo"):
            self._esp["ultimo"] = codice
            with self._lock:
                self._comandi_lua.append(f"ESPX {codice}")
            testo = "niente" if codice == 0 else (f"×{codice}" if codice > 0 else f"÷{2 ** -codice}")
            self._log(f"Esperienza per il prossimo Pokémon battuto: {testo}" + (f" ({perche})" if perche else ""), TENUE)

    def _battito(self):
        """Ogni minuto di gioco: il tempo della run avanza (conta solo se almeno un giocatore gioca)."""
        if self.emu.in_esecuzione and self.ponte.attivo and self._gioco_attivo and self.stato_run == "in_corso":
            self.sincro.azione({"azione": "battito"})

    def _backup_periodico(self):
        minuti = int(self.cfg.get("backup_minuti", 10) or 0)
        if minuti <= 0 or self._in_chiusura or self._occupato or not self._gioco_attivo:
            return
        if time.time() - self._ultimo_backup >= minuti * 60:
            self._ultimo_backup = time.time()          # anche se fallisce, si riprova al giro dopo
            self._chiedi_backup("auto")

    def _carica_backup(self, b, alla_fine=None):
        if not (self.emu.in_esecuzione and self.ponte.attivo):
            dialoghi.avviso(self, "Gioco non avviato", "Avvia prima il gioco: lo script deve essere collegato.", "info")
            return
        self._id_richiesta += 1
        rid = self._id_richiesta
        self._richieste[rid] = {"tipo": "carica", "percorso": b["stato"], "rom": self.emu.rom, "run": self._run_in_gioco(),
                                "alla_fine": alla_fine}
        with self._lock:
            self._comandi_lua.append(f"CARICA {rid} {b['stato']}")

    def _ripristina_saveram(self, b):
        """Rimette il salvataggio del gioco di un backup (BizHawk va chiuso e riaperto)."""
        rom = self.emu.rom or self.rom_attesa()
        dest = self.run_mgr.file_saveram(rom)

        def copia():
            try:
                if dest.exists():
                    shutil.copyfile(dest, dest.with_suffix(".prima_del_ripristino"))
                shutil.copyfile(b["saveram"], dest)
                self._log(f"Salvataggio del gioco ripristinato dal backup {b['stato'].name}", OK)
            except OSError as e:
                dialoghi.avviso(self, "Ripristino non riuscito", str(e), "errore")
            self._occupato = False
            self.pile.setCurrentIndex(0)
            self.assicura_gioco()
        if self.emu.in_esecuzione:
            self._occupato = True
            self.emu.ferma(alla_fine=lambda: self._in_gui.emit(copia))
        else:
            copia()

    def _salva_e_ferma(self, tipo, dopo):
        """Backup del momento attuale, poi chiusura di BizHawk (che scrive anche il salvataggio del gioco)."""
        self._occupato = True
        fatto = {"si": False}

        def ferma(ok=False):
            if fatto["si"]:
                return
            fatto["si"] = True
            self.emu.ferma(alla_fine=lambda: self._in_gui.emit(dopo))
        self._chiedi_backup(tipo, ferma)

    def _proponi_ripresa(self):
        """All'avvio del gioco: se l'ultima volta l'app è stata chiusa senza salvare in gioco, propone di riprendere da lì."""
        rom, run = self.emu.rom, self._run_in_gioco()
        if not rom or run is None or str(rom) in self._ripresa_chiesta or not self.ponte.attivo:
            return
        self._ripresa_chiesta.add(str(rom))
        b = self.backup.ultimo_chiusura(run, rom)
        if not b:
            return
        ora = datetime.fromtimestamp(b["quando"]).strftime("%d/%m alle %H:%M")
        if dialoghi.chiedi(self, "Riprendere da dove avevi lasciato?",
                           f"L'ultima volta l'app è stata chiusa il {ora}, dopo il tuo ultimo salvataggio nel gioco. "
                           "Ho un backup di quel momento: vuoi ripartire da lì?",
                           si="Riprendi da lì", no="Usa il salvataggio del gioco"):
            self._carica_backup(b)

    # ---------------------------------------------------------------- allenatori e strumenti del luogo
    def _vinti(self):
        return set((self.locale.get("vinti") or {}).get(str(self.sincro.run), []))

    def _segna_vinto(self, t):
        v = dict(self.locale.get("vinti") or {})
        lista = set(v.get(str(self.sincro.run), []))
        if t not in lista:
            lista.add(t)
            v = {str(self.sincro.run): sorted(lista)}            # solo la run attuale
            self.locale["vinti"] = v
            self.locale.salva()
        self._aggiorna_conteggi()

    def _impara_scarto_script(self, t, zona):
        """Gli allenatori sulla mappa hanno uno script = scarto + numero dell'allenatore (di solito 3000).
        Ogni lotta contro un allenatore conferma lo scarto (o lo trova, se in questa ROM è diverso)."""
        ent = self._entita_rom
        if not ent or zona is None:
            return
        try:
            x = ent["zone"].get(int(zona))
        except (TypeError, ValueError):
            return
        script = [n[3] for n in (x or {}).get("npc") or [] if n[1] != 4]
        if not script:
            return
        cand = {sc - int(t) for sc in script}
        attuale = self.cfg.get("scarto_script_allenatori", 3000)
        if attuale in cand and not self.cfg.get("scarto_confermato"):
            self.cfg["scarto_confermato"] = True              # solo una conferma: lo scarto non si cambia da solo
            self.cfg.salva()

    def _flag_acceso(self, i):
        f = self._flag_evento
        return bool(f) and 0 <= i // 8 < len(f) and (f[i // 8] >> (i % 8)) & 1 == 1

    def _calibra_flag_allenatori(self, x):
        """Dopo una lotta vinta lo script dice quali flag si sono accesi: uno di questi è quello dell'allenatore.
        Il numero del flag meno il numero dell'allenatore è sempre lo stesso: lo si trova incrociando le lotte."""
        t = int(x.get("allenatore") or 0)
        cand = {int(b) - t for b in x.get("nuovi") or []}
        if not cand or self.cfg.get("flag_allenatori") is not None:
            return
        vecchi = set(self.cfg.get("flag_allenatori_cand") or [])
        resto = (vecchi & cand) if vecchi else cand
        if not resto:
            resto = cand
        self.cfg["flag_allenatori_cand"] = sorted(resto)
        if len(resto) == 1:
            self.cfg["flag_allenatori"] = next(iter(resto))
            self._log("Allenatori battuti: ora li leggo direttamente dal gioco", OK)
        self.cfg.salva()
        self._aggiorna_conteggi()

    def _conteggi(self, luogo):
        from . import rom as R
        ent = self._entita_rom
        if not ent or luogo is None or not str(luogo).isdigit():
            return None
        n_all = (max(L.NOMI_ALLENATORI) + 1) if L.NOMI_ALLENATORI else 1000
        d = R.per_luogo(ent, int(luogo), self.cfg.get("scarto_script_allenatori", 3000), n_all)
        base = self.cfg.get("flag_allenatori")
        vinti = self._vinti()
        # allenatori che ci sono davvero: quelli col flag di comparsa acceso non sono (più) sulla mappa
        presenti = [t for t, fl in d["allenatori"].items() if not (fl and self._flag_evento and self._flag_acceso(fl))]
        d["allenatori"] = presenti
        battuti = [t for t in presenti if t in vinti or (base is not None and self._flag_acceso(base + t))]
        presi = [f for f in d["strumenti"] if self._flag_acceso(f)] if self._flag_evento else None
        return {"allenatori": len(d["allenatori"]), "battuti": len(battuti), "strumenti": len(d["strumenti"]),
                "presi": None if presi is None else len(presi), "dal_gioco": base is not None}

    def _aggiorna_conteggi(self):
        st = self._ultimo_stato
        if not st:
            return
        x = st["giocatori"].get(self.cfg["giocatore"]) or {}
        self.c_luogo.imposta_conteggi(self._conteggi(x.get("luogo_attuale")))

    # ---------------------------------------------------------------- diagnosi
    def _diagnosi(self):
        """Un file .zip con quello che serve per capire cosa non va: memoria della lotta e del codice dell'esperienza
        (dallo script), allenatori e strumenti della zona (dalla ROM), registro e impostazioni (senza chiavi)."""
        from .config import cartella_documenti
        cartella = cartella_documenti() / "diagnosi"
        cartella.mkdir(parents=True, exist_ok=True)
        nome = f"diagnosi_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        dump = cartella / f"{nome}_memoria.txt"
        self._log("Preparo il file per la diagnosi…")

        def chiudi(ok_dump, errore=None):
            try:
                zipp = self._scrivi_diagnosi(cartella / f"{nome}.zip", dump if ok_dump and dump.exists() else None, errore)
            except Exception as e:
                dialoghi.avviso(self, "Diagnosi non riuscita", str(e), "errore")
                return
            finally:
                try:
                    dump.unlink()
                except OSError:
                    pass
            self._log(f"File per la diagnosi pronto: {zipp}", OK)
            if dialoghi.chiedi(self, "File per la diagnosi pronto", f"L'ho salvato qui:\n{zipp}\n\nMandamelo così vedo cosa succede "
                               "nel tuo gioco. Il momento migliore è durante o subito dopo una lotta con un allenatore.",
                               si="Apri la cartella", no="Chiudi", tipo="ok"):
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(cartella)))
        if not (self.emu.in_esecuzione and self.ponte.attivo):
            chiudi(False, "gioco non avviato")
            return
        self._dump_attesa = lambda ok, err: chiudi(ok, err)
        with self._lock:
            self._comandi_lua.append(f"DUMP {dump}")

        def scaduto():
            if getattr(self, "_dump_attesa", None):
                self._dump_attesa = None
                chiudi(False, "lo script non ha risposto")
        QTimer.singleShot(10000, scaduto)

    def _scrivi_diagnosi(self, percorso, dump, errore):
        import json
        import zipfile
        from . import rom as R
        st = self._ultimo_stato or {}
        io = self.cfg["giocatore"]
        x = (st.get("giocatori") or {}).get(io) or {}
        cfg = {k: v for k, v in self.cfg.items() if "chiave" not in k and "key" not in k}
        info = {"versione": VERSIONE, "config": cfg, "rom": str(self.emu.rom or ""), "errore_dump": errore,
                "zona": x.get("zona"), "luogo": x.get("luogo_attuale"), "luogo_nome": x.get("zona_nome"),
                "conteggi": self._conteggi(x.get("luogo_attuale")), "lotta": self._det_lotta, "esperienza": {
                    k: (sorted(v) if isinstance(v, set) else v) for k, v in (self._esp or {}).items()},
                "squadra": [{k: p.get(k) for k in ("pid", "specie", "livello", "esperienza", "ps", "ps_max", "stato_alt",
                                                   "strumento", "id_allenatore")} for p in self._squadra_gioco],
                "regole": st.get("regole"), "attivita": x.get("attivita"), "flag_allenatori": self.cfg.get("flag_allenatori"),
                "diagnostica_script": x.get("diagnostica")}
        ent = self._entita_rom
        if ent:
            zona = x.get("zona")
            luogo = x.get("luogo_attuale")
            zone = [z for z, l in ent["luogo"].items() if str(luogo).isdigit() and l == int(luogo)]
            if zona is not None and int(zona) not in zone:
                zone.append(int(zona))
            info["entita"] = {"sprite_strumento": ent.get("sprite_strumento"),
                              "zone": {str(z): ent["zone"].get(z) for z in zone}}
        righe = [self.p_registro.item(i).text() for i in range(self.p_registro.count())]
        with zipfile.ZipFile(percorso, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("info.json", json.dumps(info, ensure_ascii=False, indent=1, default=str))
            z.writestr("registro.txt", "\n".join(righe))
            if dump:
                z.write(dump, "memoria.txt")
            from .config import cartella_documenti
            ul = cartella_documenti() / "diagnosi" / "ultima_lotta.txt"
            if ul.exists():
                z.write(ul, "memoria_ultima_lotta.txt")
        return percorso

    def _apri_mappa(self):
        from .mappa import DialogoMappa
        if self._mappa is None:
            self._mappa = DialogoMappa(self)
        if self._ultimo_stato:
            self._mappa.imposta(self._ultimo_stato, self.cfg["giocatore"])
        self._mappa.show()
        self._mappa.raise_()
        self._mappa.activateWindow()

    def _scheda_pokemon(self, chiave):
        from .scheda import SchedaPokemon
        for s in SchedaPokemon.aperte:              # già aperta: la porto davanti
            if s.k == chiave:
                s.raise_()
                s.activateWindow()
                return
        s = SchedaPokemon(self, chiave)
        s.show()

    def _pubblica_squadra(self):
        """La mia squadra con mosse e statistiche va nella presenza: così gli altri vedono la scheda dei miei Pokémon."""
        from .lotta import riassunto_impara
        campi = ("pid", "specie", "soprannome", "livello", "ps", "ps_max", "mosse", "pp", "pp_su", "stat", "abilita",
                 "natura", "stato_alt", "esperienza")
        imp = self.c_lotta.impara
        lista = []
        vivi = {m["pid"]: m for m in ((self._det_lotta or {}).get("squadra") or [])}
        for p in self._squadra_gioco:
            if p.get("uovo"):
                continue
            d = {k: p.get(k) for k in campi if p.get(k) is not None}
            if p.get("pid") in vivi:                       # in lotta: PS e stato veri di adesso
                d["ps"] = vivi[p["pid"]].get("ps", d.get("ps"))
                d["stato_lotta"] = vivi[p["pid"]].get("stato") or 0
            r = riassunto_impara(imp.get(p.get("specie")), p.get("livello")) if imp else None
            if r:
                d["impara"] = r
            lista.append(d)
        if lista != self.sincro._presenza.get("squadra"):
            self.sincro.imposta_presenza(squadra=lista)
            if vivi and time.time() - getattr(self, "_ultima_pubblicazione", 0) > 3:   # in lotta: gli altri lo vedono subito
                self._ultima_pubblicazione = time.time()
                self.sincro._presenza_subito = True
        from .scheda import SchedaPokemon
        SchedaPokemon.aggiorna_tutte()
        if self._det_lotta:                       # l'esperienza vera è cambiata: si ricalcola quanta darne
            self._controlla_esperienza(self._det_lotta)

    def _apri_pokemon(self, chiave):
        from .correzioni import DialogoPokemon
        DialogoPokemon(self, chiave).exec()

    def _controllo(self, automatico=False):
        from .correzioni import DialogoControllo
        DialogoControllo(self, automatico).exec()

    def _controllo_automatico(self):
        """Dopo un backup ricaricato o all'avvio del gioco: se tracker e gioco non coincidono, lo dice."""
        from .correzioni import differenze
        if not self._ultimo_stato or not self._squadra_gioco or self._in_chiusura:
            return
        d = [x for x in differenze(self._ultimo_stato, self.cfg["giocatore"], self._squadra_gioco, self._box_gioco)
             if x["tipo"] in ("vivo", "ricomparso")]
        firma = tuple(sorted(x["chiave"] + x["tipo"] for x in d))
        if d and firma != self._controllo_visto:
            self._controllo_visto = firma
            self._controllo(True)

    def _apri_backup(self):
        from .finestra_backup import DialogoBackup
        DialogoBackup(self).exec()

    # ================================================================ aggiornamenti
    def _cerca_aggiornamenti(self, a_mano):
        if not a_mano and self.cfg.get("aggiorna_auto", True) is False:
            return

        def lavoro():
            try:
                self._aggiornamento.emit(aggiorna.controlla(), "", a_mano)
            except Exception as e:
                self._aggiornamento.emit(None, str(e), a_mano)
        threading.Thread(target=lavoro, daemon=True).start()

    def _esito_aggiornamento(self, info, errore, a_mano):
        if errore:
            self._log(f"Aggiornamenti: {errore}", WARN if a_mano else TENUE)
            if a_mano:
                dialoghi.avviso(self, "Non riesco a cercare aggiornamenti", errore, "avviso")
            return
        if not info:
            self._log(f"Aggiornamenti: hai già l'ultima versione ({VERSIONE})", TENUE)
            if a_mano:
                dialoghi.avviso(self, "Hai già l'ultima versione", f"Soul Link Tracker {VERSIONE} è la versione più recente.", "ok")
            return
        self._log(f"È disponibile la versione {info['versione']}", ORO)
        if not a_mano and self.cfg.get("salta_versione") == info["versione"]:
            return
        if not aggiorna.e_exe():
            dialoghi.avviso(self, f"È disponibile la versione {info['versione']}",
                            "Stai usando l'app dai sorgenti: scarica la nuova versione da GitHub.", "info")
            return
        if self._in_chiusura or self._occupato:
            QTimer.singleShot(60000, lambda: self._esito_aggiornamento(info, "", a_mano))
            return
        from .finestra_aggiorna import DialogoAggiornamento
        d = DialogoAggiornamento(self, info)
        d.exec()
        if d.scelta == "salta":
            self.cfg["salta_versione"] = info["versione"]
            self.cfg.salva()
        elif d.scelta == "aggiorna" and d.nuovo:
            try:
                self._riavvia_con = aggiorna.installa(d.nuovo)
            except aggiorna.ErroreAggiornamento as e:
                dialoghi.avviso(self, "Aggiornamento non installato", str(e), "errore")
                return
            self._log(f"Versione {info['versione']} installata: riavvio", OK)
            self.close()                              # backup, chiusura di BizHawk, poi riavvio (in closeEvent)

    # ================================================================ partite
    def _cambia_partita(self):
        if self.cfg.mancanti() and not self.cfg.get("supabase_url"):
            self._impostazioni()
            return
        attuale = self.cfg.get("codice")
        d = DialogoPartite(self.cfg, self.stato_locale, self, attuale=attuale or None, obbligatorio=False)
        ok = d.exec()
        self.cfg.salva()                                  # preferenza "chiedi all'avvio"
        if ok and d.codice and d.codice != attuale:
            self._passa_a_partita(d.codice)

    def _passa_a_partita(self, codice):
        self._partita_nuova = codice
        if self.emu.in_esecuzione:
            if not dialoghi.chiedi(self, f"Passare alla partita «{codice}»?",
                                   "BizHawk verrà chiuso: prima l'app fa un backup del punto in cui sei.",
                                   si="Cambia partita", no="Annulla"):
                return
            self._stato("Faccio un backup e chiudo BizHawk per cambiare partita…")
            self._salva_e_ferma("cambio", self._per_cambio.emit)
        else:
            self._applica_partita()

    def _applica_partita(self):
        codice = self._partita_nuova
        self.cfg["codice"] = codice
        self.cfg.salva()
        self.locale = self.stato_locale.partita(codice)
        self.locale["ultimo_accesso"] = time.time()
        self.locale.salva()
        self.sincro.cambia_partita()
        self.run_desiderata = self.locale.get("ultima_run", 1)
        self.stato_run = None
        self._popup_visto = None
        self._ultimo_stato = None
        with self._lock:
            self._avvisi_lua.clear()
            self._comandi_lua.clear()
        for p in (self.p_coppie, self.p_percorsi, self.p_obiettivi, self.p_cimitero, self.p_diario, self.p_stat):
            if hasattr(p, "forza"):
                p.forza()
        self.barra.imposta_partita(codice)
        self.setWindowTitle(f"Soul Link Tracker {VERSIONE} — {codice}")
        self.pile.setCurrentIndex(0)
        self.segnaposto.setText(f"Carico la partita «{codice}»…")
        self._occupato = False
        self._log(f"Partita «{codice}»", OK)
        self._aggiorna_locale()
        QTimer.singleShot(2500, self.assicura_gioco)

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
        self.l_stato.setText(testo[:160])
        self.l_stato.setToolTip(testo)

    def _aggiorna_locale(self):
        self.p_diag.locale = {
            "versione app": VERSIONE, "partita": self.cfg.get("codice") or "-", "porta ponte": self.ponte.porta, "BizHawk": self.cfg["bizhawk"],
            "ROM in uso": str(self.emu.rom) if self.emu.rom else "-",
            "cartella ROM": str(self.run_mgr.cartella_rom), "salvataggi BizHawk": str(self.run_mgr.cartella_saveram()),
            "salvataggio di partenza": "presente" if self.run_mgr.file_base.exists() else "non ancora creato",
            "dati scaricati da Supabase": f"{self.sincro.archivio.byte_scaricati // 1024} KB",
        }

    def eventFilter(self, ogg, ev):
        if ogg is self.destra and ev.type() == ev.Type.Resize:
            self.notifiche.riposiziona()
        return super().eventFilter(ogg, ev)

    def closeEvent(self, ev):
        if not self._chiusura_pronta and self.emu.in_esecuzione:
            ev.ignore()                               # prima si salva: la finestra si chiude da sola dopo
            if self._in_chiusura:
                return
            self._in_chiusura = True
            self._stato("Salvo la partita e chiudo…")
            self.segnaposto.setText("Salvo la partita e chiudo…")
            self.pile.setCurrentIndex(0)
            self.setEnabled(False)

            def chiudi():
                self._chiusura_pronta = True
                self.close()
            self._salva_e_ferma("chiusura", chiudi)
            return
        self.sincro.ferma()
        self.ponte.chiudi()
        ev.accept()
        if self._riavvia_con:                         # aggiornamento: parte la nuova versione
            try:
                aggiorna.riavvia(self._riavvia_con)
            except Exception as e:
                dialoghi.avviso(None, "Riavvio non riuscito", f"Avvia a mano {self._riavvia_con}.\n\n{e}", "errore")
