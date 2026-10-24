"""Sprite dei Pokemon (scaricati una volta e tenuti in cache sul disco)."""
import threading
import urllib.request

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPixmap

from .config import cartella_app

URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/{}.png"


class Sprite(QObject):
    aggiornato = Signal()

    def __init__(self):
        super().__init__()
        self.cartella = cartella_app() / "sprite"
        self.cartella.mkdir(exist_ok=True)
        self._mem = {}
        self._in_corso = set()
        self._lock = threading.Lock()

    def pixmap(self, specie: int, lato: int = 64) -> QPixmap | None:
        if not specie:
            return None
        chiave = (specie, lato)
        if chiave in self._mem:
            return self._mem[chiave]
        f = self.cartella / f"{specie}.png"
        if f.exists():
            pm = QPixmap(str(f))
            if not pm.isNull():
                pm = pm.scaled(lato, lato, Qt.KeepAspectRatio, Qt.FastTransformation)
                self._mem[chiave] = pm
                return pm
        self._scarica(specie)
        return None

    def _scarica(self, specie):
        with self._lock:
            if specie in self._in_corso:
                return
            self._in_corso.add(specie)

        def lavoro():
            try:
                req = urllib.request.Request(URL.format(specie), headers={"User-Agent": "SoulLinkTracker-App"})
                dati = urllib.request.urlopen(req, timeout=10).read()
                (self.cartella / f"{specie}.png").write_bytes(dati)
                self.aggiornato.emit()
            except Exception:
                pass
            finally:
                with self._lock:
                    self._in_corso.discard(specie)

        threading.Thread(target=lavoro, daemon=True).start()
