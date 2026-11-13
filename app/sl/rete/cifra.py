"""Cifratura dei messaggi tra le app: chiave derivata dal codice della partita (chi non lo conosce non legge niente).

Busta: versione (1 byte) + nonce (12 byte) + AES-256-GCM(zlib(json)). I relay pubblici vedono solo byte a caso.
"""
import base64
import hashlib
import json
import os
import zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSIONE = 1
_SALE = b"soullink-tracker-p2p-v1"


class Chiave:
    def __init__(self, codice: str):
        codice = (codice or "").strip()
        self.chiave = hashlib.pbkdf2_hmac("sha256", codice.encode("utf-8"), _SALE, 120_000, 32)
        # nome della "stanza" sui relay: non rivela il codice né la chiave
        self.stanza = hashlib.sha256(b"soullink-stanza:" + self.chiave).hexdigest()[:32]
        self._aes = AESGCM(self.chiave)

    def cifra(self, dati: dict) -> bytes:
        grezzo = zlib.compress(json.dumps(dati, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 6)
        nonce = os.urandom(12)
        return bytes([VERSIONE]) + nonce + self._aes.encrypt(nonce, grezzo, self.stanza.encode())

    def decifra(self, busta: bytes) -> dict | None:
        try:
            if not busta or busta[0] != VERSIONE:
                return None
            grezzo = self._aes.decrypt(busta[1:13], busta[13:], self.stanza.encode())
            return json.loads(zlib.decompress(grezzo).decode("utf-8"))
        except Exception:
            return None                       # altra partita, messaggio rovinato o di qualcun altro

    def cifra_testo(self, dati: dict) -> str:
        return base64.b64encode(self.cifra(dati)).decode("ascii")

    def decifra_testo(self, testo: str) -> dict | None:
        try:
            return self.decifra(base64.b64decode(testo))
        except Exception:
            return None
