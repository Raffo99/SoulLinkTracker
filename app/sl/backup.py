"""Backup automatici della partita: lo stato salvato di melonDS (il momento esatto) più una copia del salvataggio
del gioco (.sav). Ogni partita e ogni run hanno la loro cartella. I backup fatti con BizHawk restano elencati:
il loro salvataggio del gioco si può ancora rimettere."""
import shutil
import time
from datetime import datetime
from pathlib import Path

TIPI = {"auto": "automatico", "chiusura": "alla chiusura", "manuale": "fatto da te", "cambio": "prima di un cambio"}
TIENI = {"auto": 12, "chiusura": 6, "cambio": 6, "manuale": 30}
ESTENSIONI = (".stato", ".sav", ".State", ".SaveRAM")


class GestoreBackup:
    def __init__(self, run_mgr):
        self.run_mgr = run_mgr

    def cartella(self, run) -> Path:
        p = self.run_mgr.cartella / "backup" / self.run_mgr.tag / f"run{run}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def nuovo(self, run, tipo) -> Path:
        """Nome (senza estensione) per un backup nuovo: accanto ci vanno .stato e .sav."""
        return self.cartella(run) / (datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{tipo}")

    def copia_sav(self, base: Path, rom) -> bool:
        src = self.run_mgr.file_saveram(rom)
        if not src.exists():
            return False
        try:
            shutil.copyfile(src, base.with_suffix(".sav"))
            return True
        except OSError:
            return False

    def copia_stato(self, base: Path, stato: Path) -> bool:
        try:
            shutil.copyfile(stato, base.with_suffix(".stato"))
            return True
        except OSError:
            return False

    def elenco(self, run) -> list:
        gruppi = {}
        for f in self.cartella(run).iterdir():
            if f.is_file() and f.suffix in ESTENSIONI:
                gruppi.setdefault(f.stem, {})[f.suffix] = f
        out = []
        for stem in sorted(gruppi, reverse=True):
            g = gruppi[stem]
            parti = stem.split("_")
            tipo = parti[-1] if len(parti) >= 3 else "auto"
            primo = next(iter(g.values()))
            try:
                quando = datetime.strptime("_".join(parti[:2]), "%Y-%m-%d_%H-%M-%S").timestamp()
            except ValueError:
                quando = primo.stat().st_mtime
            out.append({"stato": g.get(".stato"), "saveram": g.get(".sav") or g.get(".SaveRAM"),
                        "bizhawk": ".State" in g, "file": primo, "files": list(g.values()), "tipo": tipo,
                        "quando": quando, "byte": sum(x.stat().st_size for x in g.values())})
        return out

    def pulisci(self, run):
        """Tiene solo gli ultimi backup di ogni tipo."""
        per_tipo = {}
        for b in self.elenco(run):
            per_tipo.setdefault(b["tipo"], []).append(b)
        for tipo, lista in per_tipo.items():
            for b in lista[TIENI.get(tipo, 12):]:
                for f in b["files"]:
                    try:
                        f.unlink()
                    except OSError:
                        pass

    def ultimo_chiusura(self, run, rom):
        """Backup fatto alla chiusura (con lo stato di melonDS) più recente del salvataggio del gioco: si può
        riprendere da lì. None se dopo hai salvato nel gioco o se è troppo vecchio."""
        chiusure = [b for b in self.elenco(run) if b["tipo"] in ("chiusura", "cambio") and b["stato"]]
        if not chiusure:
            return None
        b = chiusure[0]
        try:
            sr = self.run_mgr.file_saveram(rom)
            if sr.exists() and sr.stat().st_mtime > b["quando"] + 60:
                return None          # il gioco è stato salvato dopo: si riparte dal salvataggio normale
        except OSError:
            pass
        if time.time() - b["quando"] > 60 * 60 * 24 * 14:
            return None
        return b
