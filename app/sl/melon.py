"""melonDS dentro l'app: download, configurazione, avvio, finestra incastrata, memoria del gioco.

L'app usa una sua copia di melonDS (nella cartella dell'app, in modalità "portable": configurazione accanto
all'eseguibile), così le impostazioni del Soul Link non toccano un melonDS che usi per altro.
"""
import io
import json
import re
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from . import memoria as M
from .config import cartella_app
from .emulatore import WIN, finestre_del_processo

if WIN:
    import ctypes
    from ctypes import wintypes
    from .emulatore import (GWL_STYLE, SWP_FRAMECHANGED, SWP_NOACTIVATE, SWP_NOZORDER, SWP_SHOWWINDOW, WM_CLOSE,
                            WS_CAPTION, WS_CHILD, WS_MAXIMIZEBOX, WS_MINIMIZEBOX, WS_POPUP, WS_SYSMENU,
                            WS_THICKFRAME, user32)
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.InternalGetWindowText.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.MapWindowPoints.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.POINTER(wintypes.POINT), wintypes.UINT]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101

URL_ULTIMA = "https://api.github.com/repos/melonDS-emu/melonDS/releases/latest"
URL_RISERVA = "https://github.com/melonDS-emu/melonDS/releases/download/1.1/melonDS-1.1-windows-x86_64.zip"

# disposizione dei due schermi: uno sopra l'altro, con uno spazio come tra i due schermi del DS
SPAZIO_SCHERMI = 16
PROPORZIONE = 256 / (384 + SPAZIO_SCHERMI)          # larghezza / altezza

# tasti di Qt (melonDS salva i codici dei tasti di Qt)
K = {"A": 0x58, "B": 0x5A, "X": 0x53, "Y": 0x41, "L": 0x51, "R": 0x57, "Start": 0x01000004, "Select": 0x01000003,
     "Right": 0x01000014, "Left": 0x01000012, "Up": 0x01000013, "Down": 0x01000015}
TASTO_TAB = 0x01000001
TASTO_F20 = 0x01000043                # usato solo dall'app per accendere/spegnere l'avanti veloce
VK_F20 = 0x83
TASTI_PREDEFINITI = "X = A · Z = B · S = X · A = Y · Q = L · W = R · Invio = Start · Backspace = Select · frecce"


def cartella_melon() -> Path:
    return cartella_app() / "melonDS"


def exe_predefinito() -> Path:
    return cartella_melon() / ("melonDS.exe" if WIN else "melonDS")


def trova_exe(cartella: Path) -> Path | None:
    nomi = ("melonDS.exe",) if WIN else ("melonDS", "melonDS.AppImage", "AppRun")
    for n in nomi:
        for p in sorted(Path(cartella).rglob(n)):
            if p.is_file():
                return p
    return None


# ------------------------------------------------------------------ download
def scarica(progresso=None) -> tuple[Path | None, str]:
    """Scarica l'ultima versione di melonDS per Windows da GitHub e la mette nella cartella dell'app.
    progresso(testo) viene chiamato ogni tanto (da un altro thread)."""
    dire = progresso or (lambda t: None)
    url, versione = URL_RISERVA, "1.1"
    try:
        req = urllib.request.Request(URL_ULTIMA, headers={"Accept": "application/vnd.github+json",
                                                          "User-Agent": "SoulLinkTracker"})
        with urllib.request.urlopen(req, timeout=20) as r:
            info = json.loads(r.read().decode("utf-8"))
        for a in info.get("assets") or []:
            nome = a.get("name") or ""
            if re.search(r"windows-x86_64\.zip$", nome):
                url, versione = a["browser_download_url"], info.get("tag_name") or versione
                break
    except Exception:
        pass                                   # senza API (limite di richieste, ecc.) si usa la 1.1
    dire(f"Scarico melonDS {versione}…")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SoulLinkTracker"})
        with urllib.request.urlopen(req, timeout=60) as r:
            tot = int(r.headers.get("Content-Length") or 0)
            dati, letti = bytearray(), 0
            while True:
                pezzo = r.read(1 << 16)
                if not pezzo:
                    break
                dati += pezzo
                letti += len(pezzo)
                if tot:
                    dire(f"Scarico melonDS {versione}… {letti * 100 // tot}%")
    except Exception as e:
        return None, f"Download di melonDS non riuscito: {e}"
    dest = cartella_melon()
    try:
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(bytes(dati))) as z:
            z.extractall(dest)
    except Exception as e:
        return None, f"Non riesco a estrarre melonDS: {e}"
    exe = trova_exe(dest)
    if not exe:
        return None, "Nel pacchetto scaricato non c'è melonDS.exe."
    (exe.parent / "portable").mkdir(exist_ok=True)
    return exe, f"melonDS {versione} pronto"


def copia_locale(exe: Path) -> Path:
    """melonDS indicato a mano: se ne usa una copia nella cartella dell'app, così la sua configurazione
    (la cartella "portable" con le impostazioni del tracker) non tocca il melonDS che usi per altro."""
    exe = Path(exe)
    dest = cartella_melon()
    try:
        if exe.parent.resolve() == dest.resolve():
            return exe
    except OSError:
        pass
    dest.mkdir(parents=True, exist_ok=True)
    import shutil
    for f in exe.parent.iterdir():
        if f.is_file() and (f == exe or f.suffix.lower() in (".dll", ".so", ".dylib")):
            g = dest / f.name
            if not g.exists() or g.stat().st_mtime < f.stat().st_mtime or g.stat().st_size != f.stat().st_size:
                shutil.copy2(f, g)
    return dest / exe.name


# ------------------------------------------------------------------ configurazione (melonDS.toml)
def _toml_valore(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_valore(x) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def _toml_scrivi(d: dict) -> str:
    righe = []

    def tabella(t, nome):
        semplici = {k: v for k, v in t.items() if not isinstance(v, dict)}
        if nome is not None and (semplici or not any(isinstance(v, dict) for v in t.values())):
            righe.append(f"\n[{nome}]")
        for k, v in semplici.items():
            righe.append(f"{_chiave(k)} = {_toml_valore(v)}")
        for k, v in t.items():
            if isinstance(v, dict):
                tabella(v, f"{nome}.{_chiave(k)}" if nome else _chiave(k))

    tabella(d, None)
    return "\n".join(righe).lstrip("\n") + "\n"


def _chiave(k):
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k)


def _toml_leggi(testo: str) -> dict:
    try:
        import tomllib
        return tomllib.loads(testo)
    except Exception:
        return {}


def _poni(d, percorso, valore, solo_se_manca=False):
    *capi, ultimo = percorso.split(".")
    for c in capi:
        d = d.setdefault(c, {})
        if not isinstance(d, dict):
            return
    if solo_se_manca and d.get(ultimo, -1) not in (-1, None, ""):
        return
    d[ultimo] = valore


def prepara_config(exe: Path, salvataggi: Path, stati: Path, avanti_veloce: float) -> Path:
    """Scrive melonDS.toml nella cartella "portable" accanto a melonDS: tiene quello che hai cambiato in melonDS
    (tasti, audio, video…) e impone solo quello che serve al tracker."""
    port = Path(exe).parent / "portable"
    port.mkdir(parents=True, exist_ok=True)
    f = port / "melonDS.toml"
    d = _toml_leggi(f.read_text("utf-8")) if f.exists() else {}
    salvataggi.mkdir(parents=True, exist_ok=True)
    stati.mkdir(parents=True, exist_ok=True)
    imposti = {
        "JIT.Enable": False,                 # con il JIT le modifiche al codice del gioco (regole sull'esperienza) non valgono
        "PauseLostFocus": False,             # il gioco continua anche mentre usi l'app
        "LimitFPS": True,
        "TargetFPS": 60.0,
        "FastForwardFPS": float(avanti_veloce),
        "Emu.DirectBoot": True,
        "Emu.ConsoleType": 0,                # DS (non DSi): la RAM è quella che il tracker conosce
        "Screen.UseGL": True,                # schermo in una finestra sua: serve per tagliare via il menu
        "Instance0.SaveFilePath": str(salvataggi),
        "Instance0.SavestatePath": str(stati),
        "Instance0.Window0.ScreenLayout": 0,
        "Instance0.Window0.ScreenRotation": 0,
        "Instance0.Window0.ScreenSizing": 0,
        "Instance0.Window0.ScreenSwap": False,
        "Instance0.Window0.ScreenGap": SPAZIO_SCHERMI,
        "Instance0.Window0.IntegerScaling": False,
        "Instance0.Window0.ScreenAspectTop": 0,
        "Instance0.Window0.ScreenAspectBot": 0,
        "Instance0.Window0.Geometry": "",     # la posizione salvata da incastrata non ha senso da sola
        "Instance0.Keyboard.HK_FastForwardToggle": TASTO_F20,
    }
    for k, v in imposti.items():
        _poni(d, k, v)
    for k, v in K.items():                                       # tasti del DS solo se non li hai ancora scelti
        _poni(d, f"Instance0.Keyboard.{k}", v, solo_se_manca=True)
    _poni(d, "Instance0.Keyboard.HK_FastForward", TASTO_TAB, solo_se_manca=True)
    f.write_text(_toml_scrivi(d), "utf-8")
    return f


# ------------------------------------------------------------------ finestra
def figli(hwnd) -> list:
    out = []
    if not WIN:
        return out

    def cb(h, _):
        out.append(h)
        return True
    user32.EnumChildWindows(hwnd, WNDENUMPROC(cb), 0)
    return out


def altezza_menu(hwnd) -> int:
    """Altezza della barra dei menu di melonDS: lo schermo (OpenGL) è una finestra figlia, il menu è sopra."""
    if not WIN or not hwnd:
        return 0
    migliore = None
    for h in figli(hwnd):
        if not user32.IsWindowVisible(h):
            continue
        r = wintypes.RECT()
        user32.GetClientRect(h, ctypes.byref(r))
        if r.right - r.left < 64 or r.bottom - r.top < 64:
            continue
        p = wintypes.POINT(0, 0)
        user32.MapWindowPoints(h, hwnd, ctypes.byref(p), 1)
        if migliore is None or (r.right - r.left) * (r.bottom - r.top) > migliore[1]:
            migliore = (p.y, (r.right - r.left) * (r.bottom - r.top))
    if migliore is not None and 0 < migliore[0] < 120:
        return migliore[0]
    try:                                                          # schermo senza OpenGL: stima dalla scala
        dpi = user32.GetDpiForWindow(hwnd) or 96
    except Exception:
        dpi = 96
    return round(26 * dpi / 96)


def incastra(hwnd, ospite_hwnd, w, h, menu):
    if not WIN:
        return
    st = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    st &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_POPUP)
    st |= WS_CHILD
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, st)
    user32.SetParent(hwnd, ospite_hwnd)
    user32.SetWindowPos(hwnd, 0, 0, -menu, w, h + menu, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)


def adatta(hwnd, w, h, menu):
    if WIN and hwnd:
        user32.SetWindowPos(hwnd, 0, 0, -menu, w, h + menu, SWP_NOZORDER | SWP_NOACTIVATE)


def titolo(hwnd) -> str:
    if not WIN or not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    user32.InternalGetWindowText(hwnd, buf, 256)          # non manda messaggi: non si blocca se melonDS è occupato
    return buf.value


# ------------------------------------------------------------------ emulatore
class MelonDS(QObject):
    finestra_pronta = Signal(int)      # hwnd della finestra principale di melonDS
    terminato = Signal(int)            # codice di uscita
    errore = Signal(str)

    def __init__(self):
        super().__init__()
        self.proc = None
        self.hwnd = None
        self.rom = None
        self.menu = 0                  # altezza della barra dei menu (tagliata via)
        self.mostra_menu = False
        self.avanti_veloce_avvio = 0.0  # FastForwardFPS con cui è partito melonDS
        self._veloce = False            # avanti veloce acceso dall'app
        self._mem = None                # processo aperto
        self._ram = None                # RamDS
        self._firma = None
        self._ultima_ricerca = 0.0
        self._ultimo_controllo = 0.0
        self._fps = None
        self._fps_letto = 0.0
        self._cerca_dal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._controlla)
        self._timer.start(300)
        self.console_visibile = False

    @property
    def in_esecuzione(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def avvia(self, exe, rom: Path, salvataggi: Path, stati: Path, velocita: int) -> bool:
        exe = Path(exe)
        if not exe.exists():
            self.errore.emit(f"Non trovo melonDS: {exe}")
            return False
        self.avanti_veloce_avvio = 60.0 * max(2, velocita / 100) if velocita > 100 else 60.0 * 3
        try:
            prepara_config(exe, salvataggi, stati, self.avanti_veloce_avvio)
        except Exception as e:
            self.errore.emit(f"Configurazione di melonDS non scritta: {e}")
            return False
        flags = 0
        if WIN:
            flags = subprocess.CREATE_NO_WINDOW
        self.proc = subprocess.Popen([str(exe), str(rom)], cwd=str(exe.parent), creationflags=flags)
        self.rom = Path(rom)
        self._firma = M.firma_rom(rom)
        self.hwnd = None
        self._veloce = False
        self._chiudi_memoria()
        self._cerca_dal = time.time()
        return True

    # ---------------------------------------------------------------- memoria (chiamato dal thread dello script)
    def _chiudi_memoria(self):
        if self._mem:
            self._mem.chiudi()
        self._mem, self._ram = None, None

    def ram(self):
        """RamDS del gioco in corso, o None se melonDS non è avviato o il gioco non è ancora caricato."""
        proc = self.proc
        if proc is None or proc.poll() is not None or not self._firma:
            return None
        ora = time.monotonic()
        if self._ram is not None:
            if ora - self._ultimo_controllo < 1.0:
                return self._ram
            self._ultimo_controllo = ora
            if self._ram.intestazione_ok(self._firma):
                return self._ram
            self._ram = None                                    # gioco riavviato o cambiato: si ricerca
        if ora - self._ultima_ricerca < 1.5:
            return None
        self._ultima_ricerca = ora
        try:
            if self._mem is None:
                self._mem = M.apri_processo(proc.pid)
            base = M.trova_ram(self._mem, self._firma)
        except Exception:
            self._chiudi_memoria()
            return None
        if base is None:
            return None
        self._ram = M.RamDS(self._mem, base)
        self._ultimo_controllo = ora
        return self._ram

    def fps(self):
        """Fotogrammi al secondo del gioco, dal titolo di melonDS ("[60/60] melonDS 1.1")."""
        ora = time.monotonic()
        if ora - self._fps_letto > 0.5:
            self._fps_letto = ora
            m = re.match(r"\[(\d+)/", titolo(self.hwnd)) if self.hwnd else None
            self._fps = float(m.group(1)) if m else None
        return self._fps

    # ---------------------------------------------------------------- finestra
    def _controlla(self):
        if self.proc is None:
            return
        codice = self.proc.poll()
        if codice is not None:
            self.proc, self.hwnd = None, None
            self._chiudi_memoria()
            self.terminato.emit(codice)
            return
        if not WIN or self.hwnd is not None:
            return
        finestre = finestre_del_processo(self.proc.pid)
        cand = [(a, h) for h, t, a in finestre if "melonDS" in t]
        if not cand and time.time() - self._cerca_dal > 8:
            cand = [(a, h) for h, t, a in finestre if a > 40000]
        if cand:
            self.hwnd = max(cand)[1]
            self.finestra_pronta.emit(self.hwnd)

    def calcola_menu(self):
        self.menu = 0 if self.mostra_menu else altezza_menu(self.hwnd)
        return self.menu

    def avanti_veloce(self, acceso: bool):
        """Accende o spegne l'avanti veloce di melonDS (tasto F20, che usa solo l'app)."""
        if acceso == self._veloce or not (WIN and self.hwnd):
            return
        self._veloce = acceso
        hwnd = self.hwnd
        scan = user32.MapVirtualKeyW(VK_F20, 0)

        def premi():
            user32.PostMessageW(hwnd, WM_KEYDOWN, VK_F20, 1 | (scan << 16))
            time.sleep(0.12)
            user32.PostMessageW(hwnd, WM_KEYUP, VK_F20, 1 | (scan << 16) | (0xC0 << 24))
        threading.Thread(target=premi, daemon=True).start()

    @property
    def veloce(self):
        return self._veloce

    def mostra_console(self, visibile: bool):
        self.console_visibile = visibile

    def ferma(self, attesa=15.0, alla_fine=None):
        """Chiusura pulita (melonDS scrive il salvataggio del gioco all'uscita), poi forzata se serve."""
        proc, hwnd = self.proc, self.hwnd

        def lavoro():
            if proc and proc.poll() is None:
                if WIN and hwnd:
                    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                else:
                    proc.terminate()
                try:
                    proc.wait(attesa)
                except subprocess.TimeoutExpired:
                    proc.kill()
            if alla_fine:
                alla_fine()

        threading.Thread(target=lavoro, daemon=True).start()
