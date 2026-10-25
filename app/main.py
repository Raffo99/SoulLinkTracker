"""Soul Link Tracker - app desktop (Windows).
Avvio in sviluppo:  python main.py
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sl.config import Config, StatoLocale
from sl.finestra import Finestra, risorsa
from sl.dialoghi import installa_traduzione
from sl.partite import DialogoPartite
from sl.stile import carica_font, foglio


def scegli_partita():
    """All'avvio: quale partita giocare (se Supabase è già configurato)."""
    cfg = Config()
    if not (cfg.get("giocatore") and (cfg.get("supabase_url") or "").strip() and (cfg.get("supabase_chiave") or "").strip()):
        return                      # primo avvio: ci pensano le impostazioni
    if cfg.get("codice") and cfg.get("chiedi_partita", True) is False:
        return
    stato = StatoLocale()
    if cfg.get("codice"):
        stato.partita(cfg["codice"])          # porta nella lista anche la partita delle versioni precedenti
    d = DialogoPartite(cfg, stato, obbligatorio=not cfg.get("codice"))
    if d.exec() and d.codice:
        cfg["codice"] = d.codice
        cfg.salva()
    elif not cfg.get("codice"):
        sys.exit(0)
    else:
        cfg.salva()                 # solo la preferenza "chiedi all'avvio"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Soul Link Tracker")
    installa_traduzione(app)
    carica_font(risorsa("font"))
    app.setStyleSheet(foglio())
    icona = risorsa("icona.ico")
    if icona.exists():
        app.setWindowIcon(QIcon(str(icona)))
    scegli_partita()
    w = Finestra()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
