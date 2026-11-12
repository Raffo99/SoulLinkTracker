"""Backup automatici della partita: una copia del salvataggio del gioco (il file .sav di melonDS).
Ogni partita e ogni run hanno la loro cartella. I backup fatti con BizHawk (.State + .SaveRAM) restano elencati:
il loro salvataggio del gioco si può ancora rimettere."""
import shutil
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
        """Percorso del file per un backup nuovo."""
        nome = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{tipo}.sav"
        return self.cartella(run) / nome

    def fai(self, run, tipo, rom) -> Path | None:
        """Copia il salvataggio attuale del gioco. None se il gioco non è mai stato salvato."""
        src = self.run_mgr.file_saveram(rom)
        if not src.exists():
            return None
        dest = self.nuovo(run, tipo)
        try:
            shutil.copyfile(src, dest)
        except OSError:
            return None
        self.pulisci(run)
        return dest

    def elenco(self, run) -> list:
        out = []
        cart = self.cartella(run)
        file = list(cart.glob("*.sav")) + list(cart.glob("*.State"))
        for f in sorted(file, key=lambda f: f.stem, reverse=True):
            parti = f.stem.split("_")
            tipo = parti[-1] if len(parti) >= 3 else "auto"
            try:
                quando = datetime.strptime("_".join(parti[:2]), "%Y-%m-%d_%H-%M-%S").timestamp()
            except ValueError:
                quando = f.stat().st_mtime
            if f.suffix == ".sav":
                sr, stato = f, None
            else:                                               # backup di BizHawk
                sr, stato = f.with_suffix(".SaveRAM"), f
                if not sr.exists():
                    sr = None
            out.append({"stato": stato, "file": f, "saveram": sr, "tipo": tipo, "quando": quando,
                        "byte": sum(x.stat().st_size for x in {f, sr} if x)})
        return out

    def pulisci(self, run):
        """Tiene solo gli ultimi backup di ogni tipo."""
        per_tipo = {}
        for b in self.elenco(run):
            per_tipo.setdefault(b["tipo"], []).append(b)
        for tipo, lista in per_tipo.items():
            for b in lista[TIENI.get(tipo, 12):]:
                for f in {b["file"], b["saveram"]}:
                    if f:
                        try:
                            f.unlink()
                        except OSError:
                            pass

    def ultimo_chiusura(self, run, rom):
        """Con melonDS il salvataggio del gioco è già quello giusto alla chiusura: niente da riprendere."""
        return None
