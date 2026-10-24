"""Archivio della partita su Supabase (API REST di PostgREST).

- una riga per partita in `soullink_partite` (id = codice segreto, mandato nell'header x-partita)
- scritture "ottimistiche": si aggiorna solo se la versione e' ancora quella letta, altrimenti si rilegge e si riprova
- per sapere se l'altro ha cambiato qualcosa si legge solo il numero di versione (pochi byte)
- la presenza (online, zona, diagnostica) sta in una tabella a parte: non fa riscaricare la partita
"""
import copy
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "SoulLinkTracker-App"


class ErroreArchivio(Exception):
    pass


class Archivio:
    def __init__(self, url: str, chiave: str, partita: str):
        url = (url or "").strip().rstrip("/")
        if url and not url.endswith("/rest/v1") and "supabase" in url:
            url += "/rest/v1"
        self.base = url
        self.chiave = (chiave or "").strip()
        self.partita = (partita or "").strip()
        self.cache = None          # (stato, versione) dell'ultima lettura/scrittura
        self.byte_scaricati = 0

    # ---------- HTTP ----------
    def _req(self, metodo, tabella, query="", corpo=None, prefer=None):
        if not self.base or not self.partita:
            raise ErroreArchivio("Supabase non configurato")
        h = {"User-Agent": UA, "x-partita": self.partita, "Accept-Encoding": "gzip", "Accept": "application/json"}
        if self.chiave:
            h["apikey"] = self.chiave
            if self.chiave.startswith("eyJ"):          # vecchia chiave "anon" (JWT)
                h["Authorization"] = "Bearer " + self.chiave
        dati = None
        if corpo is not None:
            dati = json.dumps(corpo, separators=(",", ":")).encode()
            h["Content-Type"] = "application/json"
        if prefer:
            h["Prefer"] = prefer
        req = urllib.request.Request(f"{self.base}/{tabella}{query}", data=dati, headers=h, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                grezzo = r.read()
                self.byte_scaricati += len(grezzo)
                if r.headers.get("Content-Encoding") == "gzip":
                    grezzo = gzip.decompress(grezzo)
                return json.loads(grezzo) if grezzo else None
        except urllib.error.HTTPError as e:
            try:
                dettaglio = json.loads(e.read().decode()).get("message", "")
            except Exception:
                dettaglio = ""
            if e.code in (401, 403):
                raise ErroreArchivio(f"accesso negato da Supabase ({e.code}): controlla la chiave e lo script SQL. {dettaglio}")
            if e.code == 404:
                raise ErroreArchivio("tabelle non trovate: hai eseguito lo script SQL su Supabase?")
            raise ErroreArchivio(f"errore Supabase {e.code}: {dettaglio}")
        except urllib.error.URLError as e:
            raise ErroreArchivio(f"Supabase non raggiungibile: {e.reason}")

    def _q(self, **kv):
        return "?" + urllib.parse.urlencode(kv)

    # ---------- partita ----------
    def versione(self) -> int | None:
        r = self._req("GET", "soullink_partite", self._q(id=f"eq.{self.partita}", select="versione"))
        return r[0]["versione"] if r else None

    def carica(self, crea=None):
        """Legge la partita (creandola con crea() se non esiste). Restituisce (stato, versione)."""
        r = self._req("GET", "soullink_partite", self._q(id=f"eq.{self.partita}", select="stato,versione"))
        if not r:
            if crea is None:
                return None
            self._req("POST", "soullink_partite", self._q(on_conflict="id"),
                      {"id": self.partita, "stato": crea(), "versione": 0}, prefer="resolution=ignore-duplicates,return=minimal")
            r = self._req("GET", "soullink_partite", self._q(id=f"eq.{self.partita}", select="stato,versione"))
            if not r:
                raise ErroreArchivio("non riesco a creare la partita (controlla lo script SQL)")
        self.cache = (r[0]["stato"], r[0]["versione"])
        return self.cache

    def _salva(self, stato, versione) -> bool:
        r = self._req("PATCH", "soullink_partite", self._q(id=f"eq.{self.partita}", versione=f"eq.{versione}", select="versione"),
                      {"stato": stato, "versione": versione + 1, "aggiornato": datetime.now(timezone.utc).isoformat()},
                      prefer="return=representation")
        return bool(r)

    def modifica(self, fn, crea):
        """fn(stato) -> (esito, salva?) ; riprova se un altro ha scritto nel frattempo."""
        if self.cache is None:
            self.carica(crea)
        for tentativo in range(8):
            stato, versione = self.cache
            nuovo = copy.deepcopy(stato)
            esito, salva = fn(nuovo)
            if not salva:
                return nuovo, esito, False
            if self._salva(nuovo, versione):
                self.cache = (nuovo, versione + 1)
                return nuovo, esito, True
            time.sleep(0.05 + 0.05 * tentativo)
            self.carica(crea)            # qualcuno ha scritto prima di noi: rileggiamo
        raise ErroreArchivio("troppi aggiornamenti contemporanei")

    def aggiorna_se_cambiata(self, crea) -> bool:
        """Scarica la partita solo se la versione online e' diversa da quella che abbiamo."""
        v = self.versione()
        if v is None:
            self.carica(crea)
            return True
        if self.cache is None or self.cache[1] != v:
            self.carica(crea)
            return True
        return False

    # ---------- presenza ----------
    def segna_presenza(self, giocatore: str, info: dict):
        self._req("POST", "soullink_presenza", self._q(on_conflict="partita,giocatore"),
                  {"partita": self.partita, "giocatore": giocatore, "visto": datetime.now(timezone.utc).isoformat(), "info": info},
                  prefer="resolution=merge-duplicates,return=minimal")

    def presenze(self) -> dict:
        r = self._req("GET", "soullink_presenza", self._q(partita=f"eq.{self.partita}", select="giocatore,visto,info")) or []
        out = {}
        for x in r:
            try:
                t = datetime.fromisoformat(x["visto"].replace("Z", "+00:00")).timestamp()
            except Exception:
                t = 0
            out[x["giocatore"]] = {"visto": t, "info": x.get("info") or {}}
        return out
