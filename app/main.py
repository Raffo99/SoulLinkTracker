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
    if "--aggiornato" in sys.argv and cfg.get("codice"):
        return                      # riavvio dopo un aggiornamento: si riprende la stessa partita
    supabase_ok = (cfg.get("supabase_url") or "").strip() and (cfg.get("supabase_chiave") or "").strip()
    if not cfg.get("giocatore") or (cfg.get("rete") == "supabase" and not supabase_ok):
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


def prova_moduli():
    """--prova-moduli: controlla che l'exe contenga tutto (usato dalla compilazione su GitHub)."""
    esiti = []
    for nome in ("lupa.lua54", "aiortc", "av", "paho.mqtt.client", "websockets", "cryptography.hazmat.primitives.ciphers.aead"):
        try:
            __import__(nome)
            esiti.append(f"{nome}: ok")
        except Exception as e:
            esiti.append(f"{nome}: ERRORE {e}")
    testo = "\n".join(esiti)
    if sys.stdout:
        print(testo)
    else:                                          # exe senza console: il risultato va in un file accanto
        open("prova_moduli.txt", "w", encoding="utf-8").write(testo)
    sys.exit(1 if "ERRORE" in testo else 0)


def prova_rete():
    """--prova-rete BROKER_HOST:PORTA RELAY_WS: due app finte si collegano direttamente (prova dell'exe)."""
    import time
    from sl.rete.trasporto import Rete
    i = sys.argv.index("--prova-rete")
    host, porta = sys.argv[i + 1].split(":")
    relay = sys.argv[i + 2]
    arrivi = []
    a = Rete("prova-exe", "A", lambda m, v: None, broker=[(host, int(porta))], relay=[relay], ice=[])
    b = Rete("prova-exe", "B", lambda m, v: arrivi.append((m.get("tipo"), v)), broker=[(host, int(porta))], relay=[relay], ice=[])
    a.avvia()
    b.avvia()
    t0 = time.time()
    while time.time() - t0 < 20 and not a.stato()["diretti"]:
        time.sleep(0.2)
    a.invia({"tipo": "presenza", "g": "A"})
    time.sleep(1.5)
    print("stato:", a.stato(), "| ricevuti da B:", arrivi)
    a.ferma()
    b.ferma()
    sys.exit(0 if ("presenza", "diretto") in arrivi else 1)


def main():
    if "--prova-moduli" in sys.argv:
        prova_moduli()
    if "--prova-rete" in sys.argv:
        prova_rete()
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
    w.adatta_allo_schermo()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
