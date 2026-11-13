"""Partita condivisa senza server: le app si passano lo stato direttamente (WebRTC) o tramite relay pubblici.

Stessa interfaccia dell'Archivio di Supabase (carica, modifica, aggiorna_se_cambiata, presenze…), così il resto
dell'app non cambia. Come funziona l'accordo tra le app:

- lo stato della partita ha una versione (numero, autore). Ogni modifica la alza e lo stato nuovo parte verso gli
  altri (diretto e, ogni pochi secondi, "trattenuto" sul relay MQTT per chi arriva dopo);
- chi riceve uno stato più nuovo lo adotta; se nel frattempo aveva fatto modifiche sue che quello stato non
  contiene, le riapplica sopra (come fa l'Archivio di Supabase quando un altro ha scritto prima) e lo rimanda;
- ogni app tiene anche una copia sul disco: se i relay perdessero lo stato, la partita resta.
"""
import copy
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from .archivio import ErroreArchivio
from .config import cartella_app


def cartella_p2p() -> Path:
    p = cartella_app() / "partite_p2p"
    p.mkdir(parents=True, exist_ok=True)
    return p


class ArchivioP2P:
    ATTESA_PRIMO_STATO = 6.0              # secondi per ricevere la partita dai relay prima di usare la copia locale

    def __init__(self, codice: str, giocatore: str, importa=None, rete=None, **opzioni_rete):
        from .rete.trasporto import Rete
        self.partita = (codice or "").strip()
        self.io = giocatore or "?"
        self._importa = importa                # Supabase → P2P: la prima volta si parte dalla partita che c'era
        self._lock = threading.RLock()
        self.cache = None                      # (stato, (versione, autore))
        self._incl = {}                        # modifiche già contenute nello stato: id sessione -> ultimo numero
        self._seq = 0
        self._pendenti = []                    # (numero, fn) modifiche mie non ancora viste dagli altri
        self._cambiata = False
        self._presenze = {}
        self._pronto = threading.Event()
        self._da_inviare = threading.Event()
        self._ultimo_trattenuto = 0.0
        self._trattenere = False
        self._ultimo_disco = 0.0
        self._disco_sporco = False
        self._ultima_risposta = 0.0
        self._presenza_trattenuta = (0.0, None)
        self.byte_scaricati = 0
        self._fermo = False
        self.rete = rete or Rete(self.partita, self.io, self._ricevi, **opzioni_rete)
        self.peer = self.rete.peer
        self.file = cartella_p2p() / f"{self.rete.chiave.stanza}.json"
        self._carica_disco()
        if rete is None:
            self.rete.avvia()
        self._inizio = time.time()
        threading.Thread(target=self._ciclo, daemon=True).start()

    # ---------------------------------------------------------------- copia sul disco
    def _carica_disco(self):
        try:
            d = json.loads(self.file.read_text("utf-8"))
            self._locale = (d["stato"], (int(d["v"]), d["a"]), d.get("incl") or {})
        except Exception:
            self._locale = None

    def _salva_disco(self):
        with self._lock:
            if not self.cache:
                return
            stato, (v, a) = self.cache
            dati = json.dumps({"stato": stato, "v": v, "a": a, "incl": self._incl, "salvato": time.time()},
                              separators=(",", ":"), ensure_ascii=False)
        tmp = self.file.with_suffix(".tmp")
        try:
            tmp.write_text(dati, "utf-8")
            os.replace(tmp, self.file)
        except OSError:
            pass

    # ---------------------------------------------------------------- interfaccia dell'Archivio
    def versione(self):
        with self._lock:
            return self.cache[1][0] if self.cache else None

    def carica(self, crea=None):
        """Aspetta un attimo la partita dagli altri (relay o diretto); se non arriva, copia locale, Supabase o nuova."""
        self._pronto.wait(max(0.0, self.ATTESA_PRIMO_STATO - (time.time() - self._inizio)))
        with self._lock:
            if self.cache is not None:
                return self.cache
            if self._locale:
                stato, ver, incl = self._locale
                self.cache, self._incl = (stato, ver), dict(incl)
            else:
                stato = None
                if self._importa:
                    try:
                        r = self._importa()
                        stato = r[0] if r else None
                    except Exception:
                        stato = None
                if stato is None:
                    if crea is None:
                        return None
                    stato = crea()
                self.cache, self._incl = (stato, (1, self.peer)), {}
                self._segna_cambio(invia=True)
            self._pronto.set()
            return self.cache

    def modifica(self, fn, crea):
        """fn(stato) -> (esito, salva?). La modifica vale subito qui e parte verso gli altri."""
        with self._lock:
            if self.cache is None:
                self.carica(crea)
            stato, (v, _) = self.cache
            nuovo = copy.deepcopy(stato)
            esito, salva = fn(nuovo)
            if not salva:
                return nuovo, esito, False
            self._seq += 1
            self._pendenti.append((self._seq, fn, time.time()))
            self._incl[self.peer] = self._seq
            self.cache = (nuovo, (v + 1, self.peer))
            self._segna_cambio(invia=True)
            return nuovo, esito, True

    def aggiorna_se_cambiata(self, crea) -> bool:
        if self.cache is None:
            self.carica(crea)
            return True
        st = self.rete.stato()
        if not (st["mqtt"] or st["nostr"] or st["diretti"]) and time.time() - self._inizio > 25:
            raise ErroreArchivio("nessun relay raggiungibile: la partita resta sul PC e si sincronizza appena torna internet")
        with self._lock:
            c, self._cambiata = self._cambiata, False
            return c

    def segna_presenza(self, giocatore: str, info: dict):
        msg = {"tipo": "presenza", "g": giocatore, "info": info, "t": time.time()}
        self.rete.invia(msg)
        ora = time.time()
        quando, firma = self._presenza_trattenuta
        nuova_firma = (bool(info.get("emulatore")), info.get("zona"))
        if ora - quando > 30 or nuova_firma != firma:            # sul relay ogni tanto: per chi arriva dopo
            self._presenza_trattenuta = (ora, nuova_firma)
            self.rete.trattieni("presenza/" + hashlib.sha256(giocatore.encode()).hexdigest()[:12], msg)

    def presenze(self) -> dict:
        with self._lock:
            return {g: dict(p) for g, p in self._presenze.items()}

    def riassunto(self) -> dict | None:
        return riassunto_da_stato(self.cache[0] if self.cache else (self._locale[0] if self._locale else None),
                                  self.presenze())

    def stato_rete(self) -> dict:
        return self.rete.stato()

    def chiudi(self):
        self._fermo = True
        self._salva_disco()
        self.rete.ferma()

    # ---------------------------------------------------------------- ricezione
    def _ricevi(self, msg: dict, via: str):
        tipo = msg.get("tipo")
        if tipo == "stato":
            self.byte_scaricati += len(json.dumps(msg.get("s") or {})) // 4
            self._adotta(msg)
        elif tipo == "presenza" and msg.get("g") and msg.get("g") != self.io:
            with self._lock:
                vecchia = self._presenze.get(msg["g"])
                t = min(float(msg.get("t") or 0), time.time())
                if not vecchia or t >= vecchia["visto"]:
                    self._presenze[msg["g"]] = {"visto": t, "info": msg.get("info") or {}}
        elif tipo == "_collegato":                 # nuovo collegamento diretto: gli mando subito la partita
            self._da_inviare.set()

    def _adotta(self, msg):
        try:
            rv = (int(msg["v"]), str(msg["a"]))
            stato = msg["s"]
        except Exception:
            return
        with self._lock:
            mia = self.cache[1] if self.cache else (-1, "")
            if rv <= mia:
                if rv < mia and time.time() - self._ultima_risposta > 2:     # è indietro: gli rimando la mia
                    self._ultima_risposta = time.time()
                    self._da_inviare.set()
                return
            incl = dict(msg.get("incl") or {})
            vista = incl.get(self.peer, 0)
            self._pendenti = [x for x in self._pendenti if x[0] > vista]
            v, a = rv
            rifatte = False
            for num, fn, _ in self._pendenti:        # le mie modifiche che quello stato non ha ancora
                nuovo = copy.deepcopy(stato)
                try:
                    _, salva = fn(nuovo)
                except Exception:
                    continue
                if salva:
                    stato, v, a = nuovo, v + 1, self.peer
                    incl[self.peer] = num
                    rifatte = True
            self.cache, self._incl = (stato, (v, a)), incl
            self._cambiata = True
            self._pronto.set()
            self._segna_cambio(invia=rifatte)

    # ---------------------------------------------------------------- invio
    def _segna_cambio(self, invia):
        self._disco_sporco = True
        self._trattenere = True
        if invia:
            self._da_inviare.set()

    def _messaggio_stato(self):
        with self._lock:
            stato, (v, a) = self.cache
            return {"tipo": "stato", "v": v, "a": a, "incl": dict(self._incl), "s": stato}

    def _ciclo(self):
        while not self._fermo:
            self._da_inviare.wait(0.5)
            if self._fermo:
                break
            ora = time.time()
            if self._da_inviare.is_set() and self.cache:
                self._da_inviare.clear()
                time.sleep(0.25)                       # le modifiche ravvicinate partono insieme
                self.rete.invia(self._messaggio_stato())
            if self._trattenere and self.cache and ora - self._ultimo_trattenuto > 4:
                self._trattenere = False
                self._ultimo_trattenuto = ora
                self.rete.trattieni("stato", self._messaggio_stato())
            if self._disco_sporco and ora - self._ultimo_disco > 2:
                self._disco_sporco = False
                self._ultimo_disco = ora
                self._salva_disco()
            with self._lock:                           # modifiche mai confermate da nessuno: non all'infinito
                if len(self._pendenti) > 2000 or (self._pendenti and ora - self._pendenti[0][2] > 6 * 3600):
                    self._pendenti = [x for x in self._pendenti[-500:] if ora - x[2] < 6 * 3600]


def riassunto_da_stato(stato, presenze=None) -> dict | None:
    """Le stesse informazioni del riassunto di Supabase (per la finestra di scelta della partita)."""
    if not stato:
        return None
    ora = time.time()
    return {"run": stato.get("run"), "stato_run": stato.get("stato"), "giocatori": stato.get("giocatori") or {},
            "run_finite": len(stato.get("storico") or []), "iniziata": stato.get("iniziata"),
            "aggiornato_t": max([p.get("visto", 0) for p in (presenze or {}).values()] + [0]) or None,
            "online": sorted(g for g, p in (presenze or {}).items() if ora - p.get("visto", 0) < 40)}


def riassunto_p2p(codice: str, attesa: float = 4.0, **opzioni_rete) -> dict | None:
    """Riassunto di una partita P2P senza entrarci: copia locale subito, poi quello che dicono i relay."""
    from .rete.trasporto import Rete
    trovati = {"stato": None, "v": (-1, ""), "presenze": {}}

    def ricevi(msg, via):
        if msg.get("tipo") == "stato":
            try:
                rv = (int(msg["v"]), str(msg["a"]))
            except Exception:
                return
            if rv > trovati["v"]:
                trovati["v"], trovati["stato"] = rv, msg.get("s")
        elif msg.get("tipo") == "presenza" and msg.get("g"):
            trovati["presenze"][msg["g"]] = {"visto": min(float(msg.get("t") or 0), time.time())}

    r = Rete(codice, "?", ricevi, webrtc=False, **opzioni_rete)
    locale = None
    try:
        d = json.loads((cartella_p2p() / f"{r.chiave.stanza}.json").read_text("utf-8"))
        locale, trovati["v"], trovati["stato"] = d["stato"], (int(d["v"]), d["a"]), d["stato"]
    except Exception:
        pass
    r.avvia()
    fine = time.time() + attesa
    while time.time() < fine:
        time.sleep(0.2)
    r.ferma()
    return riassunto_da_stato(trovati["stato"] or locale, trovati["presenze"])
