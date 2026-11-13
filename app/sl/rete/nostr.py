"""Client Nostr minimo: serve solo a far trovare le app tra loro (annunci e offerte WebRTC).

Gli eventi sono "effimeri" (kind 20000-29999: i relay li inoltrano ma non li conservano), con l'etichetta della
stanza e il contenuto cifrato. Ogni app ha una chiave Nostr usa e getta; la firma è Schnorr (BIP-340).
"""
import asyncio
import hashlib
import json
import os
import time

import websockets

KIND = 29420
RELAY = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.snort.social", "wss://nostr.mom",
         "wss://relay.primal.net"]

# ------------------------------------------------------------------ BIP-340 (implementazione di riferimento)
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
      0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and p1[1] != p2[1]:
        return None
    if p1 == p2:
        lam = (3 * p1[0] * p1[0] * pow(2 * p1[1], _P - 2, _P)) % _P
    else:
        lam = ((p2[1] - p1[1]) * pow(p2[0] - p1[0], _P - 2, _P)) % _P
    x3 = (lam * lam - p1[0] - p2[0]) % _P
    return x3, (lam * (p1[0] - x3) - p1[1]) % _P


def _mul(p, n):
    r = None
    for i in range(256):
        if (n >> i) & 1:
            r = _add(r, p)
        p = _add(p, p)
    return r


def _tagged(tag, msg):
    h = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(h + h + msg).digest()


def _x(p):
    return p[0].to_bytes(32, "big")


def chiave_pubblica(segreta: bytes) -> bytes:
    return _x(_mul(_G, int.from_bytes(segreta, "big")))


def firma(msg: bytes, segreta: bytes) -> bytes:
    d0 = int.from_bytes(segreta, "big")
    pub = _mul(_G, d0)
    d = d0 if pub[1] % 2 == 0 else _N - d0
    aux = os.urandom(32)
    t = (d ^ int.from_bytes(_tagged("BIP0340/aux", aux), "big")).to_bytes(32, "big")
    k0 = int.from_bytes(_tagged("BIP0340/nonce", t + _x(pub) + msg), "big") % _N
    r = _mul(_G, k0)
    k = k0 if r[1] % 2 == 0 else _N - k0
    e = int.from_bytes(_tagged("BIP0340/challenge", _x(r) + _x(pub) + msg), "big") % _N
    return _x(r) + ((k + e * d) % _N).to_bytes(32, "big")


def verifica(msg: bytes, pub: bytes, sig: bytes) -> bool:
    px = int.from_bytes(pub, "big")
    y2 = (pow(px, 3, _P) + 7) % _P
    y = pow(y2, (_P + 1) // 4, _P)
    if pow(y, 2, _P) != y2:
        return False
    P = (px, y if y % 2 == 0 else _P - y)
    r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    e = int.from_bytes(_tagged("BIP0340/challenge", sig[:32] + pub + msg), "big") % _N
    R = _add(_mul(_G, s), _mul(P, _N - e))
    return R is not None and R[1] % 2 == 0 and R[0] == r


def nuovo_evento(segreta: bytes, pub_hex: str, stanza: str, contenuto: str) -> dict:
    creato = int(time.time())
    tags = [["t", stanza]]
    ser = json.dumps([0, pub_hex, creato, KIND, tags, contenuto], separators=(",", ":"), ensure_ascii=False)
    eid = hashlib.sha256(ser.encode("utf-8")).digest()
    return {"id": eid.hex(), "pubkey": pub_hex, "created_at": creato, "kind": KIND, "tags": tags,
            "content": contenuto, "sig": firma(eid, segreta).hex()}


# ------------------------------------------------------------------ client
class ClientNostr:
    """Si collega a più relay (se uno non va, gli altri sì), pubblica e riceve gli eventi della stanza."""

    def __init__(self, stanza: str, ricevi, relay=None, log=None):
        self.stanza = stanza
        self._ricevi = ricevi                   # ricevi(contenuto: str) per ogni evento di altri
        self.relay = list(relay or RELAY)
        self._log = log or (lambda t: None)
        self.segreta = os.urandom(32)
        self.pub = chiave_pubblica(self.segreta).hex()
        self._ws = {}                           # url -> websocket aperto
        self._visti = set()
        self._fermo = False

    @property
    def collegati(self) -> int:
        return len(self._ws)

    async def avvia(self):
        for url in self.relay:
            asyncio.ensure_future(self._relay(url))

    async def _relay(self, url):
        attesa = 2
        while not self._fermo:
            try:
                async with websockets.connect(url, open_timeout=10, ping_interval=30, max_size=2 ** 20) as ws:
                    self._ws[url] = ws
                    attesa = 2
                    sub = "sl" + os.urandom(4).hex()
                    await ws.send(json.dumps(["REQ", sub, {"kinds": [KIND], "#t": [self.stanza],
                                                           "since": int(time.time()) - 30}]))
                    async for grezzo in ws:
                        try:
                            m = json.loads(grezzo)
                        except Exception:
                            continue
                        if m and m[0] == "EVENT" and len(m) >= 3:
                            ev = m[2]
                            if ev.get("pubkey") == self.pub or ev.get("id") in self._visti:
                                continue
                            self._visti.add(ev.get("id"))
                            if len(self._visti) > 5000:
                                self._visti.clear()
                            if ["t", self.stanza] in (ev.get("tags") or []):
                                self._ricevi(ev.get("content") or "")
            except Exception as e:
                self._log(f"Nostr {url}: {type(e).__name__}")
            finally:
                self._ws.pop(url, None)
            if self._fermo:
                return
            await asyncio.sleep(attesa)
            attesa = min(attesa * 2, 120)

    async def pubblica(self, contenuto: str):
        ev = nuovo_evento(self.segreta, self.pub, self.stanza, contenuto)
        msg = json.dumps(["EVENT", ev])
        for url, ws in list(self._ws.items()):
            try:
                await ws.send(msg)
            except Exception:
                self._ws.pop(url, None)

    async def ferma(self):
        self._fermo = True
        for ws in list(self._ws.values()):
            try:
                await ws.close()
            except Exception:
                pass
