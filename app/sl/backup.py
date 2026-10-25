"""Backup automatici della partita: uno stato salvato di BizHawk (il momento esatto) più una copia del
salvataggio del gioco (SaveRAM). Ogni partita e ogni run hanno la loro cartella."""
import shutil
import time
from datetime import datetime
from pathlib import Path

TIPI = {"auto": "automatico", "chiusura": "alla chiusura", "manuale": "fatto da te", "cambio": "prima di un cambio"}
TIENI = {"auto": 12, "chiusura": 6, "cambio": 6, "manuale": 30}


class GestoreBackup:
    def __init__(self, run_mgr):
        self.run_mgr = run_mgr

    def cartella(self, run) -> Path:
        p = self.run_mgr.cartella / "backup" / self.run_mgr.tag / f"run{run}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def nuovo(self, run, tipo) -> Path:
        """Percorso dello stato salvato per un backup nuovo."""
        nome = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{tipo}.State"
        return self.cartella(run) / nome

    def completa(self, stato: Path, rom) -> bool:
        """Dopo che BizHawk ha scritto lo stato: copia accanto anche il salvataggio del gioco."""
        try:
            src = self.run_mgr.file_saveram(rom)
            if src.exists():
                shutil.copyfile(src, stato.with_suffix(".SaveRAM"))
        except OSError:
            pass
        return stato.exists()

    def elenco(self, run) -> list:
        out = []
        for f in sorted(self.cartella(run).glob("*.State"), reverse=True):
            parti = f.stem.split("_")
            tipo = parti[-1] if len(parti) >= 3 else "auto"
            try:
                quando = datetime.strptime("_".join(parti[:2]), "%Y-%m-%d_%H-%M-%S").timestamp()
            except ValueError:
                quando = f.stat().st_mtime
            sr = f.with_suffix(".SaveRAM")
            out.append({"stato": f, "saveram": sr if sr.exists() else None, "tipo": tipo, "quando": quando,
                        "byte": f.stat().st_size + (sr.stat().st_size if sr.exists() else 0)})
        return out

    def pulisci(self, run):
        """Tiene solo gli ultimi backup di ogni tipo."""
        per_tipo = {}
        for b in self.elenco(run):
            per_tipo.setdefault(b["tipo"], []).append(b)
        for tipo, lista in per_tipo.items():
            for b in lista[TIENI.get(tipo, 12):]:
                for f in (b["stato"], b["saveram"]):
                    if f:
                        try:
                            f.unlink()
                        except OSError:
                            pass

    def ultimo_chiusura(self, run, rom):
        """Backup fatto alla chiusura più recente del salvataggio del gioco (per riprendere da lì)."""
        chiusure = [b for b in self.elenco(run) if b["tipo"] in ("chiusura", "cambio")]
        if not chiusure:
            return None
        b = chiusure[0]
        try:
            sr = self.run_mgr.file_saveram(rom)
            if sr.exists() and sr.stat().st_mtime > b["quando"] + 30:
                return None          # il gioco è stato salvato dopo: si riparte dal salvataggio normale
        except OSError:
            pass
        if time.time() - b["quando"] > 60 * 60 * 24 * 14:
            return None
        return b
