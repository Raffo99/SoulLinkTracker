"""Scelta della partita: ogni partita ha il suo codice (chi usa lo stesso codice gioca nello stesso Soul Link).
ROM, salvataggi e stato locale di ogni partita restano separati."""
import secrets
import threading
import time

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from . import dialoghi
from .archivio import Archivio, ErroreArchivio
from .riepilogo import Avatar, logo
from .stile import ACC, COLORI_GIOCATORI, KO, OK, ORO, SPENTO, TENUE, TESTO, WARN, alfa, colori_giocatori

PAROLE = ["fuoco", "acqua", "erba", "tuono", "luna", "sole", "vento", "roccia", "ombra", "drago", "stella", "neve",
          "fulmine", "onda", "foglia", "brace", "nebbia", "cometa", "aurora", "ghiaccio"]


def codice_nuovo() -> str:
    """Codice leggibile ma difficile da indovinare (fa anche da password della partita)."""
    return f"{secrets.choice(PAROLE)}-{secrets.choice(PAROLE)}-{secrets.randbelow(9000) + 1000}"


def tempo_fa(t) -> str:
    if not t:
        return "mai"
    d = max(0, time.time() - t)
    if d < 90:
        return "adesso"
    if d < 3600:
        return f"{int(d // 60)} min fa"
    if d < 86400:
        h = int(d // 3600)
        return "1 ora fa" if h == 1 else f"{h} ore fa"
    g = int(d // 86400)
    return "ieri" if g == 1 else f"{g} giorni fa"


class _Ponte(QObject):
    pronto = Signal(str, object)


class RigaPartita(QFrame):
    def __init__(self, codice, locale, attuale):
        super().__init__()
        self.setObjectName("rigaPartita")
        self.codice = codice
        self.locale = locale or {}
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 12, 16, 12)
        h.setSpacing(14)
        self.avatar = Avatar(40)
        self.avatar.imposta(codice, COLORI_GIOCATORI[sum(map(ord, codice)) % len(COLORI_GIOCATORI)])
        h.addWidget(self.avatar, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(3)
        uso = f"&nbsp;&nbsp;<span style='color:{OK};font-size:8pt;font-weight:600'>● IN USO</span>" if attuale else ""
        self.l_titolo = QLabel(f"<b style='font-size:11pt'>{codice}</b>{uso}")
        self.l_run = QLabel("")
        self.l_gioc = QLabel("")
        for l in (self.l_titolo, self.l_run, self.l_gioc):
            l.setTextFormat(Qt.RichText)
            col.addWidget(l)
        h.addLayout(col, 1)
        self.l_quando = QLabel("")
        self.l_quando.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.l_quando.setObjectName("piccolo")
        h.addWidget(self.l_quando)
        self.imposta(None, caricamento=True)

    def imposta(self, r, caricamento=False, errore=""):
        loc = self.locale.get("riassunto") or {}
        mia = self.locale.get("ultimo_accesso")
        if r is None and not loc:
            if caricamento:
                self.l_run.setText(f"<span style='color:{TENUE}'>carico le informazioni…</span>")
            elif errore:
                self.l_run.setText(f"<span style='color:{WARN}'>{errore}</span>")
            else:
                self.l_run.setText(f"<span style='color:{TENUE}'>partita nuova: nessuno ha ancora giocato</span>")
            self.l_gioc.setText("")
            self.l_quando.setText(f"giocata {tempo_fa(mia)}" if mia else "")
            return
        dati = r or {"run": loc.get("run"), "stato_run": loc.get("stato"), "online": [],
                     "giocatori": {g: {"medaglie": m, "entrato": i} for i, (g, m) in enumerate((loc.get("giocatori") or {}).items())}}
        stato = dati.get("stato_run") or "in_corso"
        col, testo = {"game_over": (KO, "game over"), "vinta": (ORO, "vinta!")}.get(stato, (OK, "in corso"))
        finite = dati.get("run_finite")
        extra = f" · {finite} run concluse" if finite else ""
        nota = "" if r else f" <span style='color:{SPENTO}'>· dati salvati sul PC</span>"
        self.l_run.setText(f"Run <b>#{dati.get('run') or 1}</b> · <span style='color:{col}'>{testo}</span>"
                           f"<span style='color:{TENUE}'>{extra}</span>{nota}")
        pezzi = []
        online = set(dati.get("online") or [])
        G = dati.get("giocatori") or {}
        colori = colori_giocatori({"giocatori": G})
        for g in sorted(G, key=lambda g: ((G[g] or {}).get("entrato") or 0, g)):
            x, c = G[g], colori[g]
            punto = f"<span style='color:{OK}'>●</span>&nbsp;" if g in online else ""
            pezzi.append(f"{punto}<span style='color:{c};font-weight:600'>{g}</span>"
                         f"&nbsp;<span style='color:{ORO}'>{(x or {}).get('medaglie') or 0}</span>")
        self.l_gioc.setText("&nbsp;&nbsp;&nbsp;".join(pezzi) if pezzi else f"<span style='color:{TENUE}'>nessun giocatore</span>")
        quando = []
        if mia:
            quando.append(f"giocata {tempo_fa(mia)}")
        if r and r.get("aggiornato_t"):
            quando.append(f"aggiornata {tempo_fa(r['aggiornato_t'])}")
        self.l_quando.setText("<br>".join(quando))


class DialogoCodice(QDialog):
    """Codice di una partita nuova (proposto) o di quella di un amico (da scrivere)."""

    def __init__(self, parent, nuova):
        super().__init__(parent)
        self.setWindowTitle("Nuova partita" if nuova else "Entra con un codice")
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        t = QLabel("Nuova partita" if nuova else "Entra nella partita di un amico")
        t.setObjectName("grande")
        v.addWidget(t)
        spiega = (f"Ecco il codice della nuova partita. <b>Mandalo agli amici</b>: chi lo inserisce gioca con te. "
                  f"Puoi anche cambiarlo." if nuova else "Scrivi il codice che ti ha mandato l'amico che ha creato la partita.")
        l = QLabel(spiega)
        l.setWordWrap(True)
        l.setObjectName("tenue")
        v.addWidget(l)
        self.campo = QLineEdit(codice_nuovo() if nuova else "")
        self.campo.setPlaceholderText("es. drago-luna-4821")
        self.campo.setMinimumHeight(36)
        self.campo.setStyleSheet("font-size: 12pt; font-weight: 600;")
        v.addWidget(self.campo)
        if nuova:
            b = QPushButton("Proponi un altro codice")
            b.clicked.connect(lambda: self.campo.setText(codice_nuovo()))
            v.addWidget(b, 0, Qt.AlignLeft)
        v.addSpacing(6)
        h = QHBoxLayout()
        h.addStretch()
        annulla = QPushButton("Annulla")
        annulla.clicked.connect(self.reject)
        ok = QPushButton("Crea e gioca" if nuova else "Entra")
        ok.setObjectName("primario")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        h.addWidget(annulla)
        h.addWidget(ok)
        v.addLayout(h)

    def _ok(self):
        c = self.campo.text().strip()
        if len(c) < 4:
            dialoghi.avviso(self, "Codice troppo corto", "Il codice deve avere almeno 4 caratteri.")
            return
        self.codice = c
        self.accept()


class DialogoPartite(QDialog):
    """Quale partita giocare. Al termine: self.codice è la partita scelta."""

    def __init__(self, cfg, stato_locale, parent=None, attuale=None, obbligatorio=False):
        super().__init__(parent)
        self.cfg, self.stato_locale, self.attuale = cfg, stato_locale, attuale
        self.obbligatorio = obbligatorio
        self.codice = None
        self.righe = {}
        self._ponte = _Ponte()
        self._ponte.pronto.connect(self._arrivato)
        self.setWindowTitle("Scegli la partita")
        self.resize(640, 560)
        self.setMinimumSize(520, 420)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        testa = QHBoxLayout()
        testa.setSpacing(14)
        testa.addWidget(logo(46), 0, Qt.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(3)
        t = QLabel("Quale partita vuoi giocare?")
        t.setObjectName("grande")
        tv.addWidget(t)
        s = QLabel("Ogni partita ha il suo codice: chi usa lo stesso codice gioca nello stesso Soul Link. "
                   "ROM e salvataggi di ogni partita restano separati.")
        s.setWordWrap(True)
        s.setObjectName("tenue")
        tv.addWidget(s)
        tv.addStretch()
        testa.addLayout(tv, 1)
        v.addLayout(testa, 0)

        self.lista = QListWidget()
        self.lista.setObjectName("partite")
        self.lista.setSpacing(3)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.itemDoubleClicked.connect(lambda _: self._gioca())
        self.lista.currentItemChanged.connect(lambda *_: self._aggiorna_pulsanti())
        v.addWidget(self.lista, 1)
        self.vuota = QLabel("Non hai ancora nessuna partita.\nCreane una nuova o entra in quella di un amico con il suo codice.")
        self.vuota.setAlignment(Qt.AlignCenter)
        self.vuota.setObjectName("tenue")
        self.vuota.setStyleSheet("background: rgba(255,255,255,0.025); border: 1px dashed rgba(255,255,255,0.10); border-radius: 14px;")
        v.addWidget(self.vuota, 1)

        r = QHBoxLayout()
        r.setSpacing(8)
        b_nuova = QPushButton("＋  Nuova partita")
        b_nuova.clicked.connect(lambda: self._aggiungi(True))
        b_entra = QPushButton("Entra con un codice")
        b_entra.clicked.connect(lambda: self._aggiungi(False))
        self.b_togli = QPushButton("Togli")
        self.b_togli.setToolTip("Toglie la partita da questa lista (e se vuoi cancella ROM e salvataggi dal PC)")
        self.b_togli.clicked.connect(self._togli)
        r.addWidget(b_nuova)
        r.addWidget(b_entra)
        r.addWidget(self.b_togli)
        r.addStretch()
        v.addLayout(r)

        sotto = QHBoxLayout()
        self.c_chiedi = QCheckBox("Chiedi ogni volta all'avvio")
        self.c_chiedi.setChecked(cfg.get("chiedi_partita", True) is not False)
        sotto.addWidget(self.c_chiedi)
        sotto.addStretch()
        if True:
            annulla = QPushButton("Esci" if obbligatorio else "Annulla")
            annulla.clicked.connect(self.reject)
            sotto.addWidget(annulla)
        self.b_gioca = QPushButton("Gioca")
        self.b_gioca.setObjectName("primario")
        self.b_gioca.setMinimumWidth(120)
        self.b_gioca.setDefault(True)
        self.b_gioca.clicked.connect(self._gioca)
        sotto.addWidget(self.b_gioca)
        v.addLayout(sotto)
        self._riempi()

    # ---------- lista ----------
    def _riempi(self, seleziona=None):
        self.lista.clear()
        self.righe = {}
        codici = self.stato_locale.codici()
        cfg_cod = (self.cfg.get("codice") or "").strip()
        if cfg_cod and cfg_cod not in codici:
            codici.insert(0, cfg_cod)
        for c in codici:
            riga = RigaPartita(c, self.stato_locale.dati["partite"].get(c), c == self.attuale)
            it = QListWidgetItem()
            it.setData(Qt.UserRole, c)
            it.setSizeHint(QSize(100, riga.sizeHint().height() + 6))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, riga)
            self.righe[c] = riga
            self._carica(c)
        self.vuota.setVisible(not codici)
        self.lista.setVisible(bool(codici))
        scelta = seleziona or self.attuale or (codici[0] if codici else None)
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.UserRole) == scelta:
                self.lista.setCurrentRow(i)
        self._aggiorna_pulsanti()

    def _carica(self, codice):
        url, chiave = self.cfg.get("supabase_url"), self.cfg.get("supabase_chiave")

        def lavoro():
            try:
                r = Archivio(url, chiave, codice).riassunto()
                self._ponte.pronto.emit(codice, ("ok", r))
            except ErroreArchivio as e:
                self._ponte.pronto.emit(codice, ("errore", str(e)))
            except Exception as e:
                self._ponte.pronto.emit(codice, ("errore", str(e)))
        threading.Thread(target=lavoro, daemon=True).start()

    def _arrivato(self, codice, esito):
        riga = self.righe.get(codice)
        if not riga:
            return
        tipo, r = esito
        try:
            if tipo == "ok":
                riga.imposta(r)
            else:
                riga.imposta(None, errore="non riesco a leggere la partita: " + r[:80])
        except RuntimeError:          # la finestra è già stata chiusa
            pass

    def _selezionato(self):
        it = self.lista.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _aggiorna_pulsanti(self):
        c = self._selezionato()
        self.b_gioca.setEnabled(bool(c))
        self.b_togli.setEnabled(bool(c) and c != self.attuale)

    # ---------- azioni ----------
    def _aggiungi(self, nuova):
        d = DialogoCodice(self, nuova)
        if not d.exec():
            return
        c = d.codice
        if not nuova:
            try:
                r = Archivio(self.cfg.get("supabase_url"), self.cfg.get("supabase_chiave"), c).riassunto()
            except ErroreArchivio as e:
                dialoghi.avviso(self, "Non riesco a controllare il codice", str(e), "errore")
                return
            if r is None and not dialoghi.chiedi(self, "Partita non trovata", f"Non esiste ancora una partita con il codice «{c}».\n\n"
                                                 "Controlla di averlo scritto giusto, oppure creala tu.", si="Creala", no="Annulla"):
                return
        self.stato_locale.partita(c)          # la aggiunge alla lista
        self._riempi(seleziona=c)
        if nuova:
            self._gioca()

    def _togli(self):
        c = self._selezionato()
        if not c or c == self.attuale:
            return
        scelta = dialoghi.scegli(self, f"Togliere «{c}» dalla lista?",
                                 "La partita online resta: gli amici possono continuare a giocarla e potrai rientrarci con il codice.",
                                 [("annulla", "Annulla", None), ("file", "Togli e cancella ROM e salvataggi", "pericolo"),
                                  ("solo", "Togli dalla lista", "primario")])
        if scelta not in ("file", "solo"):
            return
        if scelta == "file":
            from .run import GestoreRun
            cfg2 = dict(self.cfg)
            cfg2["codice"] = c
            ed = (self.stato_locale.dati["partite"].get(c) or {}).get("edizioni", [])
            try:
                GestoreRun(cfg2).cancella_tutto(anche_partenza=False, edizioni=ed)
            except Exception as e:
                dialoghi.avviso(self, "Non ho cancellato tutti i file", str(e), "errore")
        self.stato_locale.togli(c)
        if (self.cfg.get("codice") or "").strip() == c:
            self.cfg["codice"] = ""
        self._riempi()

    def _gioca(self):
        c = self._selezionato()
        if not c:
            return
        self.codice = c
        self.stato_locale.partita(c)
        self.stato_locale.dati["partite"][c]["ultimo_accesso"] = time.time()
        self.stato_locale.salva()
        self.cfg["chiedi_partita"] = self.c_chiedi.isChecked()
        self.accept()

    def reject(self):
        self.cfg["chiedi_partita"] = self.c_chiedi.isChecked()
        super().reject()          # all'avvio senza nessuna partita scelta l'app si chiude
