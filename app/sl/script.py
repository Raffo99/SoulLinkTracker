"""Lo script Lua del tracker (soullink.lua) fatto girare dentro l'app.

Con BizHawk lo script girava dentro l'emulatore. melonDS non ha script, quindi l'app lo esegue lei (con Lua 5.4
tramite lupa) e gli offre le stesse funzioni di BizHawk che usa: memory.* legge e scrive la RAM del DS dentro
melonDS, emu.framecount() conta i fotogrammi del gioco, comm.* parla con l'app senza passare da internet.
Lo script resta lo stesso file e si prova allo stesso modo di prima.
"""
import threading
import time
import traceback
from pathlib import Path

FOTOGRAMMI_PER_GIRO_MAX = 24          # oltre questa velocità lo script resta un po' indietro (non perde dati)


def _lua():
    try:
        from lupa import lua54
        return lua54.LuaRuntime(unpack_returned_tuples=True)
    except ImportError:
        import lupa
        return lupa.LuaRuntime(unpack_returned_tuples=True)


class MotoreScript(threading.Thread):
    """Esegue soullink.lua un fotogramma alla volta.

    ram()        -> RamDS oppure None se la RAM del gioco non è ancora disponibile
    scambia(s)   -> risposta dell'app al messaggio JSON s dello script (come il ponte di BizHawk)
    fps()        -> fotogrammi al secondo del gioco adesso (dal titolo di melonDS), None se non si sa
    nome_rom()   -> nome della ROM senza estensione (gameinfo.getromname di BizHawk)
    """

    def __init__(self, percorso: Path, ram, scambia, fps=None, nome_rom=None, log=None, collegato=None):
        super().__init__(daemon=True)
        self.percorso = Path(percorso)
        self._ram, self._scambia = ram, scambia
        self._fps = fps or (lambda: 60.0)
        self._nome_rom = nome_rom or (lambda: "")
        self._log = log or (lambda t: None)
        self._collegato = collegato or (lambda si: None)
        self._fermo = threading.Event()
        self.fc = 0
        self.vivo = False                    # lo script sta girando (RAM trovata, nessun errore)
        self.errore = None
        self.L = None
        self._attuale = None                 # RamDS del giro in corso
        self._da_inviare = ""

    # ---------------------------------------------------------------- funzioni "di BizHawk"
    def _r(self):
        r = self._attuale
        if r is None:
            raise OSError("RAM del gioco non disponibile")
        return r

    def _api(self):
        L = self.L
        g = L.globals()
        r = self._r

        def u8(a, dom=None):
            return r().leggi(int(a), 1)[0]

        def u16(a, dom=None):
            return int.from_bytes(r().leggi(int(a), 2), "little")

        def u32(a, dom=None):
            return int.from_bytes(r().leggi(int(a), 4), "little")

        def stringa(a, n, dom=None):
            return r().leggi(int(a), int(n))

        def array(a, n, dom=None):
            return L.table_from(list(r().leggi(int(a), int(n))))

        def w(n):
            return lambda a, v, dom=None: r().scrivi(int(a), (int(v) & ((1 << (8 * n)) - 1)).to_bytes(n, "little"))

        g.memory = L.table_from(dict(read_u8=u8, read_u16_le=u16, read_u32_le=u32, read_bytes_as_binary_string=stringa,
                                     read_bytes_as_array=array, write_u8=w(1), write_u16_le=w(2), write_u32_le=w(4)))
        g.emu = L.table_from(dict(framecount=lambda: self.fc, frameadvance=L.eval("coroutine.yield")))

        def invia(s):
            self._da_inviare = s if isinstance(s, str) else bytes(s).decode("utf-8", "replace")
            return len(self._da_inviare)

        def risposta():
            return self._scambia(self._da_inviare)

        g.comm = L.table_from(dict(socketServerIsConnected=lambda: True, socketServerSetTimeout=lambda t: None,
                                   socketServerSend=invia, socketServerResponse=risposta, httpPost=lambda *a: None))

        def niente(*a):
            return None

        def non_disponibile(*a):
            raise RuntimeError("non disponibile con melonDS")

        g.client = L.table_from(dict(saveram=niente, speedmode=niente, openrom=non_disponibile))
        g.savestate = L.table_from(dict(save=non_disponibile, load=non_disponibile))
        g.gui = L.table_from(dict(text=niente, clearGraphics=niente))
        g.joypad = L.table_from(dict(get=lambda: L.table_from({}), set=niente))
        g.gameinfo = L.table_from(dict(getromname=lambda: self._nome_rom()))
        g.print = lambda *a: self._log(" ".join(str(x) for x in a))

    def _carica(self):
        self.L = _lua()
        self._api()
        src = self.percorso.read_text("utf-8")
        # nome del pezzo "@percorso": lo script trova la sua cartella con debug.getinfo, come in BizHawk
        self.L.execute("local src, nome = ...; CO = coroutine.create(assert(load(src, nome)))", src, "@" + str(self.percorso))
        self._riprendi = self.L.eval("function() local ok, e = coroutine.resume(CO); return ok, e, coroutine.status(CO) end")
        self.fc = 0

    # ---------------------------------------------------------------- ciclo
    def ferma(self):
        self._fermo.set()

    def run(self):
        accumulati, ultimo = 0.0, time.monotonic()
        pausa_errore = 0
        while not self._fermo.is_set():
            ora = time.monotonic()
            dt, ultimo = ora - ultimo, ora
            ram = None
            try:
                ram = self._ram()
            except Exception:
                ram = None
            if ram is None:
                if self.vivo:
                    self.vivo = False
                    self._collegato(False)
                self.L = None                       # alla RAM ritrovata (gioco riavviato) lo script riparte da capo
                time.sleep(0.25)
                ultimo = time.monotonic()
                continue
            if self.L is None:
                if time.monotonic() < pausa_errore:
                    time.sleep(0.25)
                    continue
                try:
                    self._carica()
                    self.errore = None
                except Exception as e:
                    self.errore = f"script non caricato: {e}"
                    self._log(self.errore)
                    pausa_errore = time.monotonic() + 10
                    continue
                self.vivo = True
                self._collegato(True)
            fps = self._fps()
            if fps is None:
                fps = 60.0
            accumulati += max(0.0, fps) * dt
            n = min(int(accumulati), FOTOGRAMMI_PER_GIRO_MAX)
            accumulati = min(accumulati - n, FOTOGRAMMI_PER_GIRO_MAX)
            self._attuale = ram
            try:
                for _ in range(n):
                    ram.nuovo_giro()
                    ok, err, st = self._riprendi()
                    if not ok or st == "dead":
                        raise RuntimeError(err or "lo script è finito")
                    self.fc += 1
            except Exception as e:
                self.errore = str(e)
                self._log(f"Errore nello script: {e}")
                if not isinstance(e, RuntimeError):
                    self._log(traceback.format_exc(limit=3))
                self.L = None
                self.vivo = False
                self._collegato(False)
                pausa_errore = time.monotonic() + 5          # si riprova tra poco, da capo
            finally:
                self._attuale = None
            time.sleep(1 / 120)
        if self.vivo:
            self.vivo = False
            self._collegato(False)
