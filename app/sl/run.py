"""ROM delle run, randomizer e salvataggio di partenza."""
import fnmatch
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
    def tag(self) -> str:
        """Il codice della partita, ripulito: separa ROM e salvataggi di partite diverse."""
        return nome_sicuro(self.cfg.get("codice"))[:20] or "partita"

    @property
    def cartella_rom(self) -> Path:
        p = self.cartella / "rom" / self.tag
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def file_base(self) -> Path:
        return self.cartella / "salvataggio_base.SaveRAM"

    def rom_per_run(self, run: int, edizione: str = "") -> Path:
        """ROM della run. L'edizione cambia quando la partita viene azzerata: così non si riprende una vecchia ROM."""
        if not self.cfg["randomizza"]:
            return Path(self.cfg["rom_manuale"])
        g = nome_sicuro(self.cfg["giocatore"])
        ed = f"_{nome_sicuro(edizione)}" if edizione else ""
        vecchia = self.cartella / "rom" / f"SoulLink_{g}{ed}_run{run}.nds"     # versione 4.4 e precedenti
        if edizione and vecchia.exists():
            return vecchia
        return self.cartella_rom / f"SoulLink_{g}_{self.tag}{ed}_run{run}.nds"

    def cartella_stati(self) -> Path:
        return self.cartella_saveram().parent / "State"

    def schemi_partita(self, edizioni=()) -> list:
        """Nomi dei file (ROM, salvataggi, stati di BizHawk) di questa partita, con _ e spazi equivalenti."""
        g = nome_sicuro(self.cfg["giocatore"]).lower()
        schemi = [f"soullink {g} {self.tag.lower()} *"]
        schemi += [f"soullink {g} {nome_sicuro(e).lower()} run*" for e in edizioni if e]     # nomi della 4.4
        return schemi

    def della_partita(self, nome: str, edizioni=()) -> bool:
        n = nome.replace("_", " ").lower()
        return any(fnmatch.fnmatchcase(n, s) for s in self.schemi_partita(edizioni))

    def cancella_tutto(self, anche_partenza: bool, edizioni=()) -> list:
        """Reset locale di QUESTA partita: ROM generate, salvataggi e stati salvati di BizHawk.
        Le altre partite (altri codici) non vengono toccate."""
        cancellati = []
        for cartella in (self.cartella_rom, self.cartella / "rom", self.cartella_saveram(), self.cartella_stati()):
            if cartella.exists():
                for f in cartella.iterdir():
                    if f.is_file() and self.della_partita(f.name, edizioni):
                        try:
                            f.unlink()
                            cancellati.append(f)
                        except OSError:
                            pass
        backup = self.cartella / "backup" / self.tag
        if backup.exists():
            for f in backup.rglob("*"):
                if f.is_file():
                    cancellati.append(f)
            shutil.rmtree(backup, ignore_errors=True)
        if anche_partenza and self.file_base.exists():
            self.file_base.unlink()
            cancellati.append(self.file_base)
        return cancellati

    def cartella_saveram(self) -> Path:
        if self.cfg.get("cartella_saveram"):
            return Path(self.cfg["cartella_saveram"])
        return Path(self.cfg["bizhawk"]).parent / "NDS" / "SaveRAM"

    def file_saveram(self, rom) -> Path:
        # BizHawk usa il nome del file senza estensione, con "_" sostituiti da spazi
        return self.cartella_saveram() / (Path(rom).stem.replace("_", " ") + ".SaveRAM")

    # ---------- randomizer ----------
    def randomizza(self, run: int, edizione: str = "") -> tuple[Path | None, str]:
        out = self.rom_per_run(run, edizione)
        if out.exists():
            return out, "ROM già presente"
        c = self.cfg
        for k, nome in (("jar", "il randomizer (PokeRandoZX.jar)"), ("impostazioni", "il file .rnqs"), ("rom_originale", "la ROM originale")):
            if not Path(c.get(k) or "").exists():
                return None, f"Manca {nome}: controlla le impostazioni."
        jar = Path(c["jar"])
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        ultimo = ""
        # Java a 32 bit (o con poca RAM libera) non riesce a riservare 2 GB: si scende finche' parte
        for memoria in ("-Xmx1024M", "-Xmx768M", "-Xmx512M", None):
            cmd = [c.get("java") or "java"] + ([memoria] if memoria else []) + [
                "-jar", str(jar), "cli", "-s", str(c["impostazioni"]), "-i", str(c["rom_originale"]), "-o", str(out), "-l"]
            try:
                r = subprocess.run(cmd, cwd=str(jar.parent), capture_output=True, text=True, timeout=600, creationflags=flags)
            except FileNotFoundError:
                return None, "Java non trovato: installalo (adoptium.net, versione a 64 bit) o indica java.exe nelle impostazioni."
            except subprocess.TimeoutExpired:
                return None, "Il randomizer non ha finito in tempo."
            ultimo = (r.stderr or "") + (r.stdout or "")
            if r.returncode == 0 and out.exists():
                break
            if not any(x in ultimo for x in ("reserve enough space", "Invalid maximum heap size", "Could not create the Java Virtual Machine",
                                              "OutOfMemoryError", "Too small maximum heap")):
                break          # errore diverso dalla memoria: inutile riprovare
        if not out.exists():
            if "reserve enough space" in ultimo or "Invalid maximum heap size" in ultimo:
                return None, ("Java non riesce a riservare memoria: probabilmente è Java a 32 bit. Installa Java a 64 bit "
                              "(adoptium.net, 'Windows x64') e, se serve, indica il nuovo java.exe nelle impostazioni.\n\n" + ultimo[-600:])
            return None, "Errore del randomizer:\n" + ultimo[-1500:]
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

    def cattura_base(self, nome_rom: str, forza: bool = False) -> str | None:
        """Copia da parte l'ultimo salvataggio fatto nel gioco (quello sulla cartuccia).
        Automatico: quando arriva lo starter (se non c'è ancora una partenza). Forzato: dal pulsante dell'app."""
        if not nome_rom or (not forza and (not self.cfg["salta_inizio"] or self.file_base.exists())):
            return None
        src = self.cartella_saveram() / (nome_rom.replace("_", " ") + ".SaveRAM")
        if not src.exists():
            return f"Non trovo il salvataggio di BizHawk ({src})."
        dati = src.read_bytes()
        if self.vuoto(dati):
            return "Non c'è nessun salvataggio fatto nel gioco: salva prima della scena dello starter."
        self.file_base.write_bytes(dati)
        return "Salvataggio di partenza creato! Dalla prossima run si riparte da li'."
