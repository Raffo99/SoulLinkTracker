"""Configurazione dell'app e piccolo stato locale (ultima run, ultima ROM)."""
import json
import os
import sys
from pathlib import Path


def cartella_app() -> Path:
    """Dove l'app tiene configurazione e file interni (non visibili all'utente)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / "SoulLinkTracker"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cartella_documenti() -> Path:
    p = Path.home() / "Documents"
    if not p.exists():
        p = Path.home()
    return p / "SoulLink Tracker"


PREDEFINITA = {
    "giocatore": "",
    "supabase_url": "",
    "supabase_chiave": "",
    "codice": "",
    "bizhawk": "C:/BizHawk/EmuHawk.exe",
    "java": "java",
    "jar": "",
    "impostazioni": "",
    "rom_originale": "",
    "cartella_dati": str(cartella_documenti()),
    "randomizza": True,
    "rom_manuale": "",
    "salta_inizio": True,
    "cartella_saveram": "",
    "diagnostica": False,
    "chiedi_partita": True,          # all'avvio chiede quale partita giocare
}


class Config(dict):
    def __init__(self):
        super().__init__(PREDEFINITA)
        self.file = cartella_app() / "config.json"
        if self.file.exists():
            try:
                self.update(json.loads(self.file.read_text("utf-8")))
            except Exception:
                pass
        self["randomizza"] = True          # la ROM si genera sempre dal randomizer

    def salva(self):
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(self), indent=2, ensure_ascii=False), "utf-8")
        os.replace(tmp, self.file)

    def mancanti(self) -> list:
        """Campi indispensabili ancora vuoti (per aprire le impostazioni al primo avvio)."""
        m = []
        if not self.get("giocatore"):
            m.append("nome giocatore")
        if not (self.get("supabase_url") or "").strip():
            m.append("indirizzo Supabase")
        if not (self.get("supabase_chiave") or "").strip():
            m.append("chiave Supabase")
        if not self.get("codice"):
            m.append("codice della partita")
        if not Path(self.get("bizhawk") or "").exists():
            m.append("BizHawk (EmuHawk.exe)")
        for k, n in (("jar", "randomizer"), ("impostazioni", "impostazioni .rnqs"), ("rom_originale", "la tua ROM")):
            if not Path(self.get(k) or "").exists():
                m.append(n)
        return m


class StatoLocale:
    """Stato locale di ogni partita (per codice): ultima run, edizione, edizioni viste, riassunto per la scelta."""

    def __init__(self):
        self.file = cartella_app() / "stato.json"
        self.dati = {"partite": {}}
        if self.file.exists():
            try:
                self.dati.update(json.loads(self.file.read_text("utf-8")))
            except Exception:
                pass
        self.dati.setdefault("partite", {})

    def salva(self):
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.dati, ensure_ascii=False), "utf-8")
        os.replace(tmp, self.file)

    def partita(self, codice: str) -> "LocalePartita":
        codice = (codice or "").strip()
        P = self.dati["partite"]
        if codice and codice not in P:
            P[codice] = {"ultima_run": 1, "edizioni": []}
            vecchio = {k: self.dati.pop(k) for k in ("ultima_run", "ultima_edizione") if k in self.dati}
            if vecchio:                        # file della versione 4.4 o precedente: era tutto di questa partita
                P[codice].update(vecchio)
                if vecchio.get("ultima_edizione"):
                    P[codice]["edizioni"].append(vecchio["ultima_edizione"])
            self.salva()
        return LocalePartita(self, codice)

    def codici(self) -> list:
        """Partite conosciute, dalla più recente."""
        P = self.dati["partite"]
        return sorted(P, key=lambda c: -(P[c].get("ultimo_accesso") or 0))

    def togli(self, codice):
        self.dati["partite"].pop(codice, None)
        self.salva()


class LocalePartita(dict):
    """Vista sulla partita attiva: si usa come un dizionario, salva() scrive tutto il file."""

    def __init__(self, padre: StatoLocale, codice: str):
        self.padre, self.codice = padre, codice
        super().__init__(padre.dati["partite"].get(codice, {"ultima_run": 1, "edizioni": []}) if codice else {"ultima_run": 1})

    def salva(self):
        if self.codice:
            self.padre.dati["partite"].setdefault(self.codice, {}).update(self)
            self.padre.salva()
