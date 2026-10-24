"""Ponte locale con BizHawk.

BizHawk, avviato con --socket_ip/--socket_port, si collega a questo server TCP.
Protocollo (BizHawk >= 2.6.2): ogni messaggio e' "<lunghezza in byte> <testo UTF-8>" in tutti e due i versi.
Lo script manda un messaggio, l'app risponde subito: sul PC lo scambio dura meno di un millisecondo.
"""
import json
import socket
import threading

from PySide6.QtCore import QObject, Signal


def leggi_messaggio(conn) -> str:
    lung = bytearray()
    while True:
        b = conn.recv(1)
        if not b:
            raise ConnectionError("chiuso")
        if b == b" ":
            break
        lung += b
        if len(lung) > 12:
            raise ValueError("lunghezza non valida")
    n = int(lung.decode("ascii"))
    dati = bytearray()
    while len(dati) < n:
        pezzo = conn.recv(n - len(dati))
        if not pezzo:
            raise ConnectionError("chiuso")
        dati += pezzo
    return dati.decode("utf-8", "replace")


def scrivi_messaggio(conn, testo: str):
    b = testo.encode("utf-8")
    conn.sendall(str(len(b)).encode("ascii") + b" " + b)


class Ponte(QObject):
    collegato = Signal(bool)
    payload = Signal(dict)          # copia per l'interfaccia (diagnostica, ecc.)

    def __init__(self, gestore_risposta):
        """gestore_risposta(dati: dict) -> str  viene chiamato nel thread del ponte e deve rispondere subito."""
        super().__init__()
        self._gestore = gestore_risposta
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(2)
        self.porta = self._srv.getsockname()[1]
        self.attivo = False
        self._fermo = False
        threading.Thread(target=self._accetta, daemon=True).start()

    def _accetta(self):
        while not self._fermo:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threading.Thread(target=self._servi, args=(conn,), daemon=True).start()

    def _servi(self, conn):
        self.attivo = True
        self.collegato.emit(True)
        try:
            while True:
                testo = leggi_messaggio(conn)
                try:
                    dati = json.loads(testo)
                except Exception:
                    dati = {}
                try:
                    risposta = self._gestore(dati)
                except Exception as e:  # mai lasciare lo script senza risposta
                    risposta = f"ERR {e}\n"
                scrivi_messaggio(conn, risposta or "OK\n")
                self.payload.emit(dati)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
            self.attivo = False
            self.collegato.emit(False)

    def chiudi(self):
        self._fermo = True
        try:
            self._srv.close()
        except Exception:
            pass
