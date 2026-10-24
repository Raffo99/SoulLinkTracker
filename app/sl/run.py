"""ROM delle run, randomizer e salvataggio di partenza."""
import re
import shutil
import subprocess
import sys
from pathlib import Path


def nome_sicuro(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", s or "") or "Giocatore"


def run_della_rom(percorso) -> int | None:
    if not percorso:
        return None
    n = re.sub(r"[\s_\-.]", "", Path(percorso).stem).lower()
    if "soullink" not in n:
        return None
    m = re.search(r"run(\d+)$", n) or re.search(r"run(\d+)", n)
    return int(m.group(1)) if m else None


class GestoreRun:
    def __init__(self, cfg):
        self.cfg = cfg

    # ---------- percorsi ----------
    @property
    def cartella(self) -> Path:
        p = Path(self.cfg["cartella_dati"])
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cartella_rom(self) -> Path:
        p = self.cartella / "rom"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def file_base(self) -> Path:
        return self.cartella / "salvataggio_base.SaveRAM"

    def rom_per_run(self, run: int) -> Path:
        if not self.cfg["randomizza"]:
            return Path(self.cfg["rom_manuale"])
        return self.cartella_rom / f"SoulLink_{nome_sicuro(self.cfg['giocatore'])}_run{run}.nds"

    def cartella_saveram(self) -> Path:
        if self.cfg.get("cartella_saveram"):
            return Path(self.cfg["cartella_saveram"])
        return Path(self.cfg["bizhawk"]).parent / "NDS" / "SaveRAM"

    def file_saveram(self, rom) -> Path:
        # BizHawk usa il nome del file senza estensione, con "_" sostituiti da spazi
        return self.cartella_saveram() / (Path(rom).stem.replace("_", " ") + ".SaveRAM")

    # ---------- randomizer ----------
    def randomizza(self, run: int) -> tuple[Path | None, str]:
        out = self.rom_per_run(run)
        if out.exists():
            return out, "ROM gia' presente"
        c = self.cfg
        for k, nome in (("jar", "il randomizer (PokeRandoZX.jar)"), ("impostazioni", "il file .rnqs"), ("rom_originale", "la ROM originale")):
            if not Path(c.get(k) or "").exists():
                return None, f"Manca {nome}: controlla le impostazioni."
        jar = Path(c["jar"])
        cmd = [c.get("java") or "java", "-Xmx2048M", "-jar", str(jar), "cli", "-s", str(c["impostazioni"]),
               "-i", str(c["rom_originale"]), "-o", str(out), "-l"]
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            r = subprocess.run(cmd, cwd=str(jar.parent), capture_output=True, text=True, timeout=600, creationflags=flags)
        except FileNotFoundError:
            return None, "Java non trovato: installalo (adoptium.net) o indica java.exe nelle impostazioni."
        except subprocess.TimeoutExpired:
            return None, "Il randomizer non ha finito in tempo."
        if r.returncode != 0 or not out.exists():
            return None, "Errore del randomizer:\n" + (r.stderr or r.stdout or "")[-1500:]
        return out, "ROM generata"

    # ---------- salvataggio di partenza ----------
    @staticmethod
    def vuoto(dati: bytes) -> bool:
        if len(dati) < 0x1000:
            return True
        primo = dati[:0x400]
        return primo.count(0xFF) == len(primo) or primo.count(0) == len(primo)

    def prepara_salvataggio(self, rom) -> str | None:
        """Prima di aprire per la prima volta la ROM di una run: ci copia il salvataggio di partenza."""
        if not self.cfg["salta_inizio"] or not self.file_base.exists():
            return None
        dest = self.file_saveram(rom)
        if dest.exists():
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.file_base, dest)
        return "Salvataggio di partenza copiato: premi Continua!"

    def cattura_base(self, nome_rom: str) -> str | None:
        """Lo script ha visto arrivare lo starter: il salvataggio in camera e' ancora sulla cartuccia."""
        if not self.cfg["salta_inizio"] or self.file_base.exists() or not nome_rom:
            return None
        src = self.cartella_saveram() / (nome_rom.replace("_", " ") + ".SaveRAM")
        if not src.exists():
            return f"Non trovo il salvataggio di BizHawk ({src})."
        dati = src.read_bytes()
        if self.vuoto(dati):
            return "Non avevi salvato in camera prima dello starter: niente salvataggio di partenza per ora."
        self.file_base.write_bytes(dati)
        return "Salvataggio di partenza creato! Dalla prossima run si parte dalla camera."
