"""Sincronizzazione con il sito Cloudflare, tutta in sottofondo.

- inoltra al sito gli aggiornamenti dello script (unendo quelli arrivati nel frattempo)
- tiene i messaggi per lo script e l'ultimo stato della run
- legge lo stato completo per l'interfaccia ogni pochi secondi
"""
import json
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QObject, Signal

UA = "SoulLinkTracker-App"


def _http(url, dati=None, form=False, timeout=10):
    headers = {"User-Agent": UA}
    corpo = None
    if dati is not None:
        if form:
            corpo = urllib.parse.urlencode({"payload": json.dumps(dati)}).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            corpo = json.dumps(dati).encode()
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corpo, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


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


class Sincro(QObject):
    stato_server = Signal(dict)       # stato completo (/api/stato)
    connessione = Signal(bool, str)   # online?, eventuale errore
    messaggio = Signal(str)           # messaggi per il giocatore (anche in gioco)
    run_cambiata = Signal(int, str)   # run, stato
    ignorato = Signal(str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.coda = queue.Queue()
        self.per_lua = queue.Queue()
        self.run = None
        self.stato = None
        self.ultimo_msg = -1
        self.online = False
        self.ultimo_stato = None
        self._fermo = False
        self._run_rom = None
        self._emulatore = False
        self._sveglia_stato = True
        threading.Thread(target=self._ciclo_invio, daemon=True).start()
        threading.Thread(target=self._ciclo_stato, daemon=True).start()

    # ---------- chiamate dall'app ----------
    def imposta_run_rom(self, run_rom):
        self._run_rom = run_rom

    def imposta_emulatore(self, attivo: bool):
        self._emulatore = attivo

    def accoda(self, dati: dict):
        self.coda.put(dati)

    def messaggi_per_lua(self) -> list:
        out = []
        while True:
            try:
                out.append(self.per_lua.get_nowait())
            except queue.Empty:
                return out

    def azione(self, dati: dict, alla_fine=None):
        def lavoro():
            try:
                r = json.loads(_http(self.cfg.server + "/api/azione", dict(dati, codice=self.cfg["codice"])))
            except urllib.error.HTTPError as e:
                try:
                    r = json.loads(e.read().decode())
                except Exception:
                    r = {"errore": f"errore {e.code}"}
            except Exception as e:
                r = {"errore": str(e)}
            if alla_fine:
                alla_fine(r)
            self.aggiorna_ora()
        threading.Thread(target=lavoro, daemon=True).start()

    def aggiorna_ora(self):
        self._sveglia_stato = True

    def ferma(self):
        self._fermo = True

    # ---------- invio aggiornamenti ----------
    def _ciclo_invio(self):
        in_sospeso = None
        attesa = 0
        ultimo = 0
        while not self._fermo:
            try:
                d = self.coda.get(timeout=1)
                in_sospeso = unisci(in_sospeso, d) if in_sospeso else d
                while True:   # unisci tutto quello che e' gia' arrivato
                    try:
                        in_sospeso = unisci(in_sospeso, self.coda.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                pass
            ora = time.time()
            if in_sospeso is None and ora - ultimo < 5:
                continue          # niente da mandare: un contatto ogni 5 secondi per i messaggi
            if ora < attesa:
                continue
            if not self.cfg.server:
                continue
            dati = dict(in_sospeso or {"attivo": self._emulatore})
            dati.pop("salva_base", None)
            dati.setdefault("run_rom", self._run_rom)
            dati.update(codice=self.cfg["codice"], giocatore=self.cfg["giocatore"], ultimo_msg=self.ultimo_msg)
            try:
                risp = _http(self.cfg.server + "/api/gioco", dati, form=True)
                self._leggi_risposta(risp)
                in_sospeso = None
                attesa = 0
                ultimo = ora
                if not self.online:
                    self.online = True
                    self.connessione.emit(True, "")
            except Exception as e:
                self.online = False
                self.connessione.emit(False, str(e))
                attesa = ora + 5

    def _leggi_risposta(self, risp: str):
        for riga in risp.splitlines():
            cmd, _, resto = riga.partition(" ")
            if cmd == "RUN":
                parti = resto.split()
                run, stato = int(parti[0]), parti[1] if len(parti) > 1 else ""
                if (run, stato) != (self.run, self.stato):
                    self.run, self.stato = run, stato
                    self.run_cambiata.emit(run, stato)
            elif cmd == "ULTIMO":
                self.ultimo_msg = int(resto or 0)
            elif cmd == "MSG":
                id_, _, testo = resto.partition(" ")
                if int(id_) > self.ultimo_msg:
                    self.ultimo_msg = int(id_)
                    self.per_lua.put(f"MSG {id_} {testo}")
                    self.messaggio.emit(testo)
            elif cmd == "IGNORATO":
                if resto != getattr(self, "_ultimo_ignorato", None) or time.time() - getattr(self, "_t_ignorato", 0) > 60:
                    self._ultimo_ignorato, self._t_ignorato = resto, time.time()
                    self.ignorato.emit(resto)
            elif cmd == "ERR":
                self.connessione.emit(False, resto)

    # ---------- stato completo per l'interfaccia ----------
    def _ciclo_stato(self):
        prossimo = 0
        while not self._fermo:
            if (time.time() >= prossimo or self._sveglia_stato) and self.cfg.server:
                self._sveglia_stato = False
                try:
                    st = json.loads(_http(self.cfg.server + "/api/stato", timeout=10))
                    if "errore" not in st:
                        self.ultimo_stato = st
                        if (st["run"], st["stato"]) != (self.run, self.stato):
                            self.run, self.stato = st["run"], st["stato"]
                            self.run_cambiata.emit(st["run"], st["stato"])
                        self.stato_server.emit(st)
                        if not self.online:
                            self.online = True
                            self.connessione.emit(True, "")
                except Exception as e:
                    if self.online:
                        self.online = False
                    self.connessione.emit(False, str(e))
                prossimo = time.time() + 3
            time.sleep(0.2)
