"""Lettura e scrittura della memoria di melonDS dall'esterno.

melonDS non ha uno script interno come BizHawk: l'app apre il processo dell'emulatore e legge/scrive la RAM del
Nintendo DS direttamente (ReadProcessMemory / WriteProcessMemory su Windows, /proc/<pid>/mem su Linux).

La RAM principale del DS (4 MB, 0x02000000) è un unico blocco nella memoria di melonDS. Si trova cercando la copia
dell'intestazione della cartuccia che il DS tiene a 0x027FFE00 (= 0x3FFE00 dall'inizio della RAM): titolo e codice
del gioco, gli stessi dei primi 16 byte del file .nds.
"""
import ctypes
import re
import sys
import threading

DIM_RAM = 0x400000                 # RAM principale del DS (modalità DS)
OFF_INTESTAZIONE = 0x3FFE00        # 0x027FFE00: copia dell'intestazione della cartuccia
PAGINA = 0x1000


def firma_rom(percorso) -> bytes | None:
    """Titolo (12 byte) e codice del gioco (4 byte) dall'intestazione del file .nds."""
    try:
        with open(percorso, "rb") as f:
            x = f.read(16)
        return x if len(x) == 16 else None
    except OSError:
        return None


# ------------------------------------------------------------------ accesso al processo
class Processo:
    """Interfaccia comune: leggi/scrivi a indirizzi assoluti del processo, elenco delle zone leggibili."""

    def leggi(self, ind: int, n: int) -> bytes | None:
        raise NotImplementedError

    def scrivi(self, ind: int, dati: bytes) -> bool:
        raise NotImplementedError

    def zone(self):
        """(inizio, dimensione) delle zone di memoria leggibili e scrivibili."""
        raise NotImplementedError

    def chiudi(self):
        pass


if sys.platform == "win32":
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    PROCESS_VM_READ, PROCESS_VM_WRITE, PROCESS_VM_OPERATION = 0x0010, 0x0020, 0x0008
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT = 0x1000
    PAGE_GUARD, PAGE_NOACCESS = 0x100, 0x01
    SCRIVIBILI = 0x04 | 0x08 | 0x40 | 0x80          # READWRITE, WRITECOPY, EXECUTE_READWRITE, EXECUTE_WRITECOPY

    class MBI(ctypes.Structure):
        _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                    ("AllocationProtect", wintypes.DWORD), ("PartitionId", wintypes.WORD),
                    ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                    ("Type", wintypes.DWORD)]

    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                      ctypes.POINTER(ctypes.c_size_t)]
    k32.ReadProcessMemory.restype = wintypes.BOOL
    k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]
    k32.WriteProcessMemory.restype = wintypes.BOOL
    k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    class ProcessoWindows(Processo):
        def __init__(self, pid: int):
            self.h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
                                     | PROCESS_QUERY_INFORMATION, False, pid)
            if not self.h:
                raise OSError(f"non riesco ad aprire il processo di melonDS (errore {ctypes.get_last_error()})")

        def leggi(self, ind, n):
            buf = ctypes.create_string_buffer(n)
            letti = ctypes.c_size_t(0)
            if not k32.ReadProcessMemory(self.h, ctypes.c_void_p(ind), buf, n, ctypes.byref(letti)) or letti.value != n:
                return None
            return buf.raw

        def scrivi(self, ind, dati):
            scritti = ctypes.c_size_t(0)
            ok = k32.WriteProcessMemory(self.h, ctypes.c_void_p(ind), dati, len(dati), ctypes.byref(scritti))
            return bool(ok) and scritti.value == len(dati)

        def zone(self):
            ind, mbi = 0, MBI()
            while k32.VirtualQueryEx(self.h, ctypes.c_void_p(ind), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                base, dim = mbi.BaseAddress or 0, mbi.RegionSize
                if (mbi.State == MEM_COMMIT and mbi.Protect & SCRIVIBILI and not mbi.Protect & PAGE_GUARD):
                    yield base, dim
                ind = base + dim
                if dim == 0 or ind >= 0x7FFFFFFFFFFF:
                    break

        def chiudi(self):
            if self.h:
                k32.CloseHandle(self.h)
                self.h = None


class ProcessoLinux(Processo):
    """Per Linux (e per le prove): /proc/<pid>/mem."""

    def __init__(self, pid: int):
        self.pid = pid
        self.f = open(f"/proc/{pid}/mem", "r+b", buffering=0)
        self._lock = threading.Lock()

    def leggi(self, ind, n):
        try:
            with self._lock:
                self.f.seek(ind)
                x = self.f.read(n)
            return x if len(x) == n else None
        except (OSError, ValueError, OverflowError):
            return None

    def scrivi(self, ind, dati):
        try:
            with self._lock:
                self.f.seek(ind)
                return self.f.write(dati) == len(dati)
        except (OSError, ValueError, OverflowError):
            return False

    def zone(self):
        try:
            righe = open(f"/proc/{self.pid}/maps").read().splitlines()
        except OSError:
            return
        for r in righe:
            p = r.split()
            if len(p) < 2 or not p[1].startswith("rw"):
                continue
            a, b = (int(x, 16) for x in p[0].split("-"))
            yield a, b - a

    def chiudi(self):
        try:
            self.f.close()
        except Exception:
            pass


def apri_processo(pid: int) -> Processo:
    if sys.platform == "win32":
        return ProcessoWindows(pid)
    return ProcessoLinux(pid)


def trova_ram(proc: Processo, firma: bytes, suggerito: int | None = None) -> int | None:
    """Indirizzo (nel processo di melonDS) dell'inizio della RAM principale del DS, o None se non c'è ancora.
    Prima prova il valore già noto e l'inizio di ogni zona grande (il caso normale), poi cerca nelle zone."""
    if not firma:
        return None

    def giusto(base):
        x = proc.leggi(base + OFF_INTESTAZIONE, 0x28)
        if not x or x[:16] != firma:
            return False
        ingresso = int.from_bytes(x[0x24:0x28], "little")             # ingresso dell'ARM9: sempre nella RAM
        return 0x02000000 <= ingresso < 0x02400000

    if suggerito and giusto(suggerito):
        return suggerito
    grandi = [(a, d) for a, d in proc.zone() if d >= DIM_RAM]
    for a, d in grandi:
        if giusto(a):
            return a
    patt = re.compile(re.escape(firma))
    BLOCCO = 0x1000000
    for a, d in grandi:
        for da in range(a + OFF_INTESTAZIONE, a + d, BLOCCO):
            n = min(BLOCCO + 16, a + d - da)
            x = proc.leggi(da, n)
            if not x:
                continue
            for m in patt.finditer(x):
                base = da + m.start() - OFF_INTESTAZIONE
                if base >= a and base + DIM_RAM <= a + d and giusto(base):
                    return base
    return None


# ------------------------------------------------------------------ la RAM del DS vista dallo script
class RamDS:
    """I 4 MB della RAM principale, con indirizzi da 0 (come il dominio "Main RAM" di BizHawk).
    Le letture passano da una piccola memoria a pagine che si svuota a ogni giro dello script: tante letture
    vicine costano una sola chiamata al sistema."""

    def __init__(self, proc: Processo, base: int):
        self.proc, self.base = proc, base
        self._pagine = {}

    def nuovo_giro(self):
        self._pagine.clear()

    def _controlla(self, a, n):
        if a < 0 or n < 0 or a + n > DIM_RAM:
            raise IndexError(f"indirizzo fuori dalla RAM: 0x{a:X} (+{n})")

    def _pagina(self, p):
        x = self._pagine.get(p)
        if x is None:
            x = self.proc.leggi(self.base + p * PAGINA, PAGINA)
            if x is None:
                raise OSError("melonDS non risponde (memoria non leggibile)")
            self._pagine[p] = x
        return x

    def leggi(self, a: int, n: int) -> bytes:
        self._controlla(a, n)
        if n >= 0x10000:                                    # blocchi grandi: una lettura sola, senza memoria a pagine
            x = self.proc.leggi(self.base + a, n)
            if x is None:
                raise OSError("melonDS non risponde (memoria non leggibile)")
            return x
        p0, p1 = a // PAGINA, (a + n - 1) // PAGINA if n else a // PAGINA
        if p0 == p1:
            o = a - p0 * PAGINA
            return self._pagina(p0)[o:o + n]
        dati = b"".join(self._pagina(p) for p in range(p0, p1 + 1))
        o = a - p0 * PAGINA
        return dati[o:o + n]

    def scrivi(self, a: int, dati: bytes):
        self._controlla(a, len(dati))
        if not self.proc.scrivi(self.base + a, dati):
            raise OSError("scrittura nella memoria di melonDS non riuscita")
        for p in range(a // PAGINA, (a + len(dati) - 1) // PAGINA + 1):
            self._pagine.pop(p, None)

    def intestazione_ok(self, firma: bytes) -> bool:
        x = self.proc.leggi(self.base + OFF_INTESTAZIONE, 16)
        return x == firma


class RamFinta(RamDS):
    """RAM in un bytearray (per le prove senza melonDS)."""

    def __init__(self, ram: bytearray):
        self.ram = ram
        self._pagine = {}
        self.base = 0

    def leggi(self, a, n):
        self._controlla(a, n)
        return bytes(self.ram[a:a + n])

    def scrivi(self, a, dati):
        self._controlla(a, len(dati))
        self.ram[a:a + len(dati)] = dati

    def intestazione_ok(self, firma):
        return bytes(self.ram[OFF_INTESTAZIONE:OFF_INTESTAZIONE + 16]) == firma
