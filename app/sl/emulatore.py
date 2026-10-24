"""Avvio di BizHawk, ricerca della sua finestra e chiusura pulita (Windows)."""
import ctypes
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from .config import cartella_app

WIN = sys.platform == "win32"
if WIN:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    GWL_STYLE = -16
    WS_CAPTION, WS_THICKFRAME, WS_SYSMENU = 0x00C00000, 0x00040000, 0x00080000
    WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_POPUP, WS_CHILD = 0x00020000, 0x00010000, 0x80000000, 0x40000000
    WM_CLOSE = 0x0010
    SW_HIDE, SW_SHOW = 0, 5


def finestre_del_processo(pid: int) -> list:
    """[(hwnd, titolo, area)] delle finestre visibili del processo."""
    out = []
    if not WIN:
        return out

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append((hwnd, buf.value, (r.right - r.left) * (r.bottom - r.top)))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def togli_bordi(hwnd):
    if not WIN:
        return
    st = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    st &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_POPUP)
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, st)


def adatta(hwnd, x, y, w, h):
    if WIN:
        user32.MoveWindow(hwnd, x, y, w, h, True)


def prepara_config_bizhawk(exe: Path) -> Path:
    """Copia la configurazione di BizHawk in un file solo per il Soul Link e attiva le opzioni necessarie
    quando la finestra e' incastrata nell'app: input anche senza 'focus' e niente pausa in background."""
    dest = cartella_app() / "bizhawk_soullink.ini"
    dati = {}
    sorgenti = [dest, exe.parent / "config.ini"]
    for s in sorgenti:
        if s.exists():
            try:
                dati = json.loads(s.read_text("utf-8-sig"))
                break
            except Exception:
                continue
    dati.update({
        "AcceptBackgroundInput": True,
        "AcceptBackgroundInputControllerOnly": False,
        "RunInBackground": True,
        "SingleInstanceMode": False,
    })
    dest.write_text(json.dumps(dati, indent=2), "utf-8")
    return dest


class Emulatore(QObject):
    finestra_pronta = Signal(int)      # hwnd della finestra principale di BizHawk
    terminato = Signal(int)            # codice di uscita
    errore = Signal(str)

    def __init__(self):
        super().__init__()
        self.proc = None
        self.hwnd = None
        self.hwnd_lua = None
        self.rom = None
        self._cerca_dal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._controlla)
        self._timer.start(300)
        self.console_visibile = False

    @property
    def in_esecuzione(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def avvia(self, exe: str, rom: Path, porta: int, lua: Path):
        exe = Path(exe)
        if not exe.exists():
            self.errore.emit(f"Non trovo BizHawk: {exe}")
            return False
        if not WIN:
            self.errore.emit("L'avvio di BizHawk dentro l'app funziona solo su Windows.")
            return False
        cfg = prepara_config_bizhawk(exe)
        args = [str(exe), f"--config={cfg}", "--socket_ip=127.0.0.1", f"--socket_port={porta}",
                f"--lua={lua}", str(rom)]
        self.proc = subprocess.Popen(args, cwd=str(exe.parent))
        self.rom = Path(rom)
        self.hwnd = None
        self.hwnd_lua = None
        self._cerca_dal = time.time()
        return True

    def _controlla(self):
        if self.proc is None:
            return
        codice = self.proc.poll()
        if codice is not None:
            self.proc, self.hwnd = None, None
            self.terminato.emit(codice)
            return
        if not WIN:
            return
        finestre = finestre_del_processo(self.proc.pid)
        for hwnd, titolo, _ in finestre:
            if titolo.startswith("Lua Console") and hwnd != self.hwnd_lua:
                self.hwnd_lua = hwnd
                if not self.console_visibile:
                    user32.ShowWindow(hwnd, SW_HIDE)
        if self.hwnd is None:
            cand = [(a, h) for h, t, a in finestre if "BizHawk" in t and not t.startswith("Lua Console")]
            if not cand and time.time() - self._cerca_dal > 8:
                cand = [(a, h) for h, t, a in finestre if not t.startswith("Lua Console") and a > 40000]
            if cand:
                self.hwnd = max(cand)[1]
                self.finestra_pronta.emit(self.hwnd)

    def mostra_console(self, visibile: bool):
        self.console_visibile = visibile
        if WIN and self.hwnd_lua:
            user32.ShowWindow(self.hwnd_lua, SW_SHOW if visibile else SW_HIDE)

    def ferma(self, attesa=15.0, alla_fine=None):
        """Chiusura pulita (BizHawk salva la SaveRAM all'uscita), poi forzata se serve."""
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
