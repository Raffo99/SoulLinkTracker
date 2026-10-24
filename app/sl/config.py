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
        if self.get("randomizza"):
            for k, n in (("jar", "randomizer"), ("impostazioni", "impostazioni .rnqs"), ("rom_originale", "ROM originale")):
                if not Path(self.get(k) or "").exists():
                    m.append(n)
        elif not Path(self.get("rom_manuale") or "").exists():
            m.append("ROM da usare")
        return m


class StatoLocale(dict):
    def __init__(self):
        super().__init__({"ultima_run": 1})
        self.file = cartella_app() / "stato.json"
        if self.file.exists():
            try:
                self.update(json.loads(self.file.read_text("utf-8")))
            except Exception:
                pass

    def salva(self):
        self.file.write_text(json.dumps(dict(self)), "utf-8")
