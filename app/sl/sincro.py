"""Sincronizzazione della partita tra i due giocatori, tutta in sottofondo.

Le regole del Soul Link le applica l'app stessa (sl.logica) sullo stato condiviso in Supabase.
- gli aggiornamenti dello script vengono uniti e applicati (scrivendo solo se cambia davvero qualcosa)
- ogni 2 secondi si controlla il numero di versione: si riscarica la partita solo se l'altro l'ha modificata
- la presenza (online, zona, diagnostica) va in una tabella a parte ogni 10 secondi
"""
import copy
import json
import queue
import threading
import time

from PySide6.QtCore import QObject, Signal

from . import logica as L
from .archivio import Archivio, ErroreArchivio


def unisci(a: dict, b: dict) -> dict:
    """Unisce due aggiornamenti consecutivi dello script senza perdere eventi."""
    if a.get("run_rom") != b.get("run_rom"):
        return dict(b)        # dati di una ROM diversa (cambio run): quelli vecchi non servono piu'
    out = dict(a)
    for k, v in b.items():
        if k == "eventi":
            out["eventi"] = (out.get("eventi") or []) + (v or [])
        else:
            out[k] = v
    return out


def _firma(s: dict) -> str:
    """Contenuto della partita senza i campi che cambiano a ogni contatto (per non scrivere a vuoto)."""
    c = copy.copy(s)
    c["giocatori"] = {g: {k: v for k, v in x.items() if k not in ("visto", "emulatore")} for g, x in s["giocatori"].items()}
    return json.dumps(c, sort_keys=True, separators=(",", ":"))


class Sincro(QObject):
    stato_server = Signal(dict)       # vista completa per l'interfaccia
    connessione = Signal(bool, str)   # online?, eventuale errore
    messaggio = Signal(str)           # messaggi per il giocatore (anche in gioco)
    run_cambiata = Signal(int, str)   # run, stato
    ignorato = Signal(str)
    esito_azione = Signal(dict)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.coda = queue.Queue()
        self.per_lua = queue.Queue()
        self.run = None
        self.stato = None
        self.ultimo_msg = None          # None = non ancora letto: all'avvio non ripetiamo i vecchi messaggi
        self.online = False
        self.ultimo_stato = None
        self.presenze = {}
        self._presenza = {}
        self._run_rom = None
        self._lock = threading.Lock()
        self._lock_msg = threading.Lock()
        self._fermo = False
        self._sveglia = threading.Event()
        self._presenza_subito = False
        self.archivio = self._nuovo_archivio()
        threading.Thread(target=self._ciclo_lavoro, daemon=True).start()
        threading.Thread(target=self._ciclo_osserva, daemon=True).start()

    def _nuovo_archivio(self):
        return Archivio(self.cfg.get("supabase_url"), self.cfg.get("supabase_chiave"), self.cfg.get("codice"))

    def riconfigura(self):
        with self._lock:
            self.archivio = self._nuovo_archivio()
            self.ultimo_msg = None
        self._sveglia.set()

    # ---------- chiamate dall'app ----------
    def imposta_run_rom(self, run_rom):
        self._run_rom = run_rom

    def imposta_presenza(self, **kv):
        self._presenza.update(kv)

    def accoda(self, dati: dict):
        self.coda.put(("gioco", dati, None))

    def azione(self, dati: dict, alla_fine=None):
        self.coda.put(("azione", dati, alla_fine))

    def aggiorna_ora(self):
        self._sveglia.set()

    def messaggi_per_lua(self) -> list:
        out = []
        while True:
            try:
                out.append(self.per_lua.get_nowait())
            except queue.Empty:
                return out

    def ferma(self):
        self._fermo = True
        self._sveglia.set()

    # ---------- interni ----------
    def _crea(self):
        return L.nuovo_stato(time.time())

    def _dopo_lettura(self, s: dict):
        """Messaggi nuovi per me, cambi di run, vista per l'interfaccia."""
        io = self.cfg.get("giocatore")
        with self._lock_msg:
            if self.ultimo_msg is None:
                self.ultimo_msg = s.get("id_msg", 0)
            else:
                for m in s.get("messaggi", {}).get(io, []):
                    if m["id"] > self.ultimo_msg:
                        self.ultimo_msg = m["id"]
                        self.per_lua.put(f"MSG {m['id']} {m['testo']}")
                        self.messaggio.emit(m["testo"])
        if (s["run"], s["stato"]) != (self.run, self.stato):
            self.run, self.stato = s["run"], s["stato"]
            self.run_cambiata.emit(s["run"], s["stato"])
        self._emetti_vista(s)

    def _emetti_vista(self, s: dict):
        ora = time.time()
        v = L.vista(s, ora)
        for g, x in v["giocatori"].items():   # online, zona e diagnostica arrivano dalla presenza
            p = self.presenze.get(g)
            if p:
                x["online"] = ora - p["visto"] < 40
                inf = p["info"]
                x["emulatore"] = bool(inf.get("emulatore"))
                if inf.get("zona") is not None:
                    x["zona"] = inf["zona"]
                    x["luogo_attuale"] = L.luogo_incontro(s, {"zona": inf["zona"]})
                    x["zona_nome"] = L.nome_luogo(x["luogo_attuale"])
                if inf.get("diagnostica"):
                    x["diagnostica"] = inf["diagnostica"]
            else:
                x["online"] = False
            x["prossimo"] = L.prossimo_obiettivo(s, g)
        self.ultimo_stato = v
        self.stato_server.emit(v)

    def _ok(self):
        if not self.online:
            self.online = True
            self.connessione.emit(True, "")

    def _errore(self, e):
        self.online = False
        self.connessione.emit(False, str(e))

    # ---------- applicazione degli aggiornamenti ----------
    def _ciclo_lavoro(self):
        while not self._fermo:
            try:
                tipo, dati, alla_fine = self.coda.get(timeout=0.5)
            except queue.Empty:
                continue
            if tipo == "gioco":                 # unisci tutti gli aggiornamenti gia' arrivati
                altri = []
                while True:
                    try:
                        t2, d2, f2 = self.coda.get_nowait()
                    except queue.Empty:
                        break
                    if t2 == "gioco":
                        dati = unisci(dati, d2)
                    else:
                        altri.append((t2, d2, f2))
                for x in altri:
                    self.coda.put(x)
            for tentativo in range(3):
                try:
                    if tipo == "gioco":
                        self._applica_gioco(dati)
                    else:
                        self._applica_azione(dati, alla_fine)
                    self._ok()
                    break
                except ErroreArchivio as e:
                    self._errore(e)
                    if tipo == "azione" and alla_fine:
                        alla_fine({"errore": str(e)})
                        break
                    time.sleep(3)
                except Exception as e:  # mai fermare il thread
                    self._errore(e)
                    break

    def _applica_gioco(self, dati: dict):
        d = dict(dati)
        # questi campi vanno nella presenza, non nella partita
        zona_prima = self._presenza.get("zona")
        for k in ("zona", "diagnostica", "attivo"):
            if k in d:
                self._presenza["zona" if k == "zona" else "diagnostica" if k == "diagnostica" else "emulatore"] = d.pop(k)
        if self._presenza.get("zona") != zona_prima:
            self._presenza_subito = True       # "Dove sei" deve cambiare appena cambi zona
            self._sveglia.set()
        d.setdefault("run_rom", self._run_rom)
        d["giocatore"] = self.cfg.get("giocatore")
        d["attivo"] = True
        risultato = {}

        def fn(s):
            prima = _firma(s)
            r = L.aggiorna_da_gioco(s, time.time(), d)
            risultato.update(r)
            return r, (not r.get("errore")) and _firma(s) != prima

        with self._lock:
            arch = self.archivio
        s, r, scritto = arch.modifica(fn, self._crea)
        if r.get("ignorato"):
            self.ignorato.emit(r["ignorato"])
        if r.get("errore"):
            self.connessione.emit(False, r["errore"])
        self._dopo_lettura(s)

    def _applica_azione(self, dati: dict, alla_fine):
        def fn(s):
            r = L.azione(s, time.time(), dati)
            return r, not r.get("errore")
        with self._lock:
            arch = self.archivio
        s, r, _ = arch.modifica(fn, self._crea)
        self._dopo_lettura(s)
        if alla_fine:
            alla_fine(r)

    # ---------- osservazione della partita e presenza ----------
    def _ciclo_osserva(self):
        prossima_presenza = 0
        while not self._fermo:
            with self._lock:
                arch = self.archivio
            ora = time.time()
            try:
                if (ora >= prossima_presenza or self._presenza_subito) and self.cfg.get("giocatore"):
                    self._presenza_subito = False
                    info = dict(self._presenza)
                    info["run_rom"] = self._run_rom
                    arch.segna_presenza(self.cfg["giocatore"], info)
                    self.presenze = arch.presenze()
                    prossima_presenza = ora + 10
                    if arch.cache:
                        self._emetti_vista(arch.cache[0])
                if arch.aggiorna_se_cambiata(self._crea):
                    self._dopo_lettura(arch.cache[0])
                self._ok()
            except ErroreArchivio as e:
                self._errore(e)
                prossima_presenza = 0
            except Exception as e:
                self._errore(e)
            self._sveglia.wait(2)
            self._sveglia.clear()
