"""Trasporto dei messaggi tra le app della stessa partita.

- **Diretto (WebRTC)**: le app si annunciano sui relay Nostr pubblici (e sul relay MQTT); quella con l'id più
  piccolo manda l'offerta, l'altra risponde, e da lì parlano direttamente con un canale dati, come in una
  videochiamata. I relay servono solo a presentarsi.
- **Relay (MQTT)**: se un router blocca la connessione diretta, i messaggi passano da server MQTT pubblici, che
  tengono anche l'ultimo stato della partita e la presenza di ognuno (così chi arriva dopo li recupera).

Tutto è cifrato con la chiave del codice della partita (cifra.py). Viaggiano solo i dati del tracker.
"""
import asyncio
import os
import threading
import time
from collections import OrderedDict

from .cifra import Chiave

BROKER = [("broker.emqx.io", 8883), ("broker.hivemq.com", 8883), ("test.mosquitto.org", 8886)]
ICE = ["stun:stun.l.google.com:19302", "stun:stun.cloudflare.com:3478"]
PEZZO = 48_000                       # i messaggi grandi sul canale diretto si mandano a pezzi


class Visti:
    """Ultimi id di messaggio visti (lo stesso messaggio può arrivare da più relay e dal canale diretto)."""

    def __init__(self, n=4000):
        self.n, self.d = n, OrderedDict()

    def nuovo(self, k) -> bool:
        if k in self.d:
            return False
        self.d[k] = True
        if len(self.d) > self.n:
            self.d.popitem(last=False)
        return True


class Rete:
    def __init__(self, codice: str, nome: str, ricevi, log=None, broker=None, relay=None, ice=None, webrtc=True):
        """ricevi(msg: dict, via: str) viene chiamato da un thread della rete per ogni messaggio degli altri."""
        self.chiave = Chiave(codice)
        self.nome = nome or "?"
        self.peer = os.urandom(8).hex()
        self.prefisso = f"soullink/{self.chiave.stanza}/"
        self._ricevi = ricevi
        self._log = log or (lambda t: None)
        self.broker = list(BROKER if broker is None else broker)
        self.relay = relay
        self.ice = list(ICE if ice is None else ice)
        self.usa_webrtc = webrtc
        self._visti = Visti()
        self._mqtt = []                       # client paho
        self._mqtt_ok = set()
        self._loop = None
        self._nostr = None
        self._pc = {}                         # peer -> RTCPeerConnection
        self._canali = {}                     # peer -> canale dati aperto
        self._pezzi = {}
        self._conosciuti = {}                 # peer -> (nome, ultimo annuncio)
        self._fermo = False

    # ---------------------------------------------------------------- avvio e stato
    def avvia(self):
        self._avvia_mqtt()
        threading.Thread(target=self._ciclo_asyncio, daemon=True).start()

    def ferma(self):
        self._fermo = True
        for c in self._mqtt:
            try:
                c.disconnect()
                c.loop_stop()
            except Exception:
                pass
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._chiudi_tutto(), self._loop)

    def stato(self) -> dict:
        ora = time.time()
        return {"diretti": len(self._canali), "mqtt": len(self._mqtt_ok),
                "nostr": self._nostr.collegati if self._nostr else 0,
                "altri": sum(1 for _, t in self._conosciuti.values() if ora - t < 60)}

    # ---------------------------------------------------------------- invio
    def invia(self, msg: dict, solo_relay=False):
        """A tutti gli altri: diretto a chi è collegato, e dal relay se qualcuno non lo è (o non si sa ancora)."""
        msg = dict(msg, da=self.peer, mid=os.urandom(6).hex())
        busta = self.chiave.cifra(msg)
        ora = time.time()
        attivi = {p for p, (_, t) in self._conosciuti.items() if ora - t < 60}
        diretti = set(self._canali) if not solo_relay else set()
        for p in list(diretti):
            self._manda_diretto(p, busta)
        if solo_relay or not attivi or not attivi <= diretti:
            self._pubblica_mqtt("msg", busta)

    def trattieni(self, nome: str, msg: dict):
        """Messaggio "trattenuto" dai relay MQTT (ultimo stato, presenza): chi si collega dopo lo riceve subito."""
        msg = dict(msg, da=self.peer, mid=os.urandom(6).hex())
        self._pubblica_mqtt(nome, self.chiave.cifra(msg), trattenuto=True)

    def _arrivato(self, busta: bytes, via: str):
        msg = self.chiave.decifra(busta)
        if not msg or msg.get("da") == self.peer or not self._visti.nuovo(msg.get("mid")):
            return
        if msg.get("da"):
            vecchio = self._conosciuti.get(msg["da"])
            self._conosciuti[msg["da"]] = (msg.get("g") or (vecchio[0] if vecchio else "?"), time.time())
        tipo = msg.get("tipo")
        if tipo in ("ciao", "sdp"):
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._segnale(msg), self._loop)
            return
        try:
            self._ricevi(msg, via)
        except Exception as e:
            self._log(f"rete: messaggio non gestito ({e})")

    # ---------------------------------------------------------------- MQTT
    def _avvia_mqtt(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self._log("rete: MQTT non disponibile")
            return
        for host, porta in self.broker:
            try:
                c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sl-" + os.urandom(6).hex())
                if porta in (8883, 8886):
                    c.tls_set()
                c.reconnect_delay_set(2, 60)

                def connesso(cl, ud, flags, rc, props=None, host=host):
                    if not rc.is_failure:
                        self._mqtt_ok.add(host)
                        cl.subscribe(self.prefisso + "#", qos=1)

                def staccato(cl, ud, flags, rc, props=None, host=host):
                    self._mqtt_ok.discard(host)

                def messaggio(cl, ud, m):
                    resto = m.topic[len(self.prefisso):]
                    if resto.startswith("segnali/") and resto != "segnali/" + self.peer:
                        return
                    self._arrivato(m.payload, "relay")

                c.on_connect, c.on_disconnect, c.on_message = connesso, staccato, messaggio
                c.connect_async(host, porta, keepalive=45)
                c.loop_start()
                self._mqtt.append(c)
            except Exception as e:
                self._log(f"rete: MQTT {host}: {e}")

    def _pubblica_mqtt(self, nome, busta, trattenuto=False):
        for c in self._mqtt:
            try:
                c.publish(self.prefisso + nome, busta, qos=1, retain=trattenuto)
            except Exception:
                pass

    # ---------------------------------------------------------------- asyncio: Nostr e WebRTC
    def _ciclo_asyncio(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._principale())
        except Exception as e:
            self._log(f"rete: {e}")

    async def _principale(self):
        try:
            from .nostr import ClientNostr
            self._nostr = ClientNostr(self.chiave.stanza, lambda t: self._arrivato_testo(t), relay=self.relay, log=self._log)
            await self._nostr.avvia()
        except Exception as e:
            self._log(f"rete: Nostr non disponibile ({e})")
            self._nostr = None
        while not self._fermo:
            await self._annuncia()
            for _ in range(15):
                if self._fermo:
                    break
                await asyncio.sleep(1)
                self._pulisci_connessioni()

    def _arrivato_testo(self, testo):
        import base64
        try:
            self._arrivato(base64.b64decode(testo), "nostr")
        except Exception:
            pass

    async def _annuncia(self):
        msg = {"tipo": "ciao", "da": self.peer, "g": self.nome, "mid": os.urandom(6).hex(), "t": time.time()}
        busta = self.chiave.cifra(msg)
        self._pubblica_mqtt("ciao", busta)
        if self._nostr:
            import base64
            try:
                await self._nostr.pubblica(base64.b64encode(busta).decode("ascii"))
            except Exception:
                pass

    async def _manda_segnale(self, msg):
        msg = dict(msg, da=self.peer, mid=os.urandom(6).hex())
        busta = self.chiave.cifra(msg)
        self._pubblica_mqtt("segnali/" + msg["per"], busta)
        if self._nostr:
            import base64
            try:
                await self._nostr.pubblica(base64.b64encode(busta).decode("ascii"))
            except Exception:
                pass

    def _pulisci_connessioni(self):
        ora = time.time()
        for p, pc in list(self._pc.items()):
            avviata = getattr(pc, "_sl_inizio", ora)
            if p not in self._canali and ora - avviata > 40:        # non si è collegato: si riproverà
                asyncio.ensure_future(self._chiudi(p))

    async def _segnale(self, msg):
        if not self.usa_webrtc:
            return
        try:
            from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
        except Exception:
            self.usa_webrtc = False
            self._log("rete: WebRTC non disponibile, solo relay")
            return
        p = msg.get("da")
        if not p or p == self.peer:
            return
        if msg["tipo"] == "ciao":
            if p in self._pc or p in self._canali or not (self.peer < p):
                return                                # offre solo chi ha l'id più piccolo
            pc = self._nuova_pc(p, RTCPeerConnection, RTCConfiguration, RTCIceServer)
            canale = pc.createDataChannel("soullink", ordered=True)
            self._prepara_canale(p, canale)
            await pc.setLocalDescription(await pc.createOffer())
            await self._manda_segnale({"tipo": "sdp", "per": p, "kind": "offer", "sdp": pc.localDescription.sdp})
        elif msg["tipo"] == "sdp" and msg.get("per") == self.peer:
            desc = RTCSessionDescription(sdp=msg["sdp"], type=msg["kind"])
            if msg["kind"] == "offer":
                if p in self._pc:
                    await self._chiudi(p)
                pc = self._nuova_pc(p, RTCPeerConnection, RTCConfiguration, RTCIceServer)

                @pc.on("datachannel")
                def nuovo_canale(canale, p=p):
                    self._prepara_canale(p, canale)
                await pc.setRemoteDescription(desc)
                await pc.setLocalDescription(await pc.createAnswer())
                await self._manda_segnale({"tipo": "sdp", "per": p, "kind": "answer", "sdp": pc.localDescription.sdp})
            elif msg["kind"] == "answer" and p in self._pc:
                try:
                    await self._pc[p].setRemoteDescription(desc)
                except Exception as e:
                    self._log(f"rete: risposta WebRTC non valida ({e})")

    def _nuova_pc(self, p, RTCPeerConnection, RTCConfiguration, RTCIceServer):
        conf = RTCConfiguration(iceServers=[RTCIceServer(urls=u) for u in self.ice])
        pc = RTCPeerConnection(conf)
        pc._sl_inizio = time.time()
        self._pc[p] = pc

        @pc.on("connectionstatechange")
        async def cambio():
            if pc.connectionState in ("failed", "closed"):
                await self._chiudi(p)
        return pc

    def _prepara_canale(self, p, canale):
        @canale.on("open")
        def aperto():
            self._canali[p] = canale
            self._log(f"rete: collegamento diretto con {self._conosciuti.get(p, ('?',))[0]}")
            try:
                self._ricevi({"tipo": "_collegato", "da": p}, "diretto")
            except Exception:
                pass

        @canale.on("message")
        def messaggio(dati):
            if isinstance(dati, str):
                return
            self._pezzo(p, dati)

        @canale.on("close")
        def chiuso():
            self._canali.pop(p, None)

        if canale.readyState == "open":
            aperto()

    def _manda_diretto(self, p, busta: bytes):
        canale = self._canali.get(p)
        if not canale or not self._loop:
            return
        if len(busta) <= PEZZO:
            pezzi = [b"M" + busta]
        else:
            ident = os.urandom(4)
            parti = [busta[i:i + PEZZO] for i in range(0, len(busta), PEZZO)]
            pezzi = [b"C" + ident + i.to_bytes(2, "big") + len(parti).to_bytes(2, "big") + x for i, x in enumerate(parti)]

        def manda():
            try:
                for x in pezzi:
                    canale.send(x)
            except Exception:
                self._canali.pop(p, None)
        self._loop.call_soon_threadsafe(manda)

    def _pezzo(self, p, dati: bytes):
        if dati[:1] == b"M":
            self._arrivato(dati[1:], "diretto")
            return
        if dati[:1] != b"C" or len(dati) < 9:
            return
        ident, i, tot = dati[1:5], int.from_bytes(dati[5:7], "big"), int.from_bytes(dati[7:9], "big")
        parti = self._pezzi.setdefault((p, ident), {})
        parti[i] = dati[9:]
        if len(parti) == tot:
            del self._pezzi[(p, ident)]
            self._arrivato(b"".join(parti[k] for k in range(tot)), "diretto")

    async def _chiudi(self, p):
        self._canali.pop(p, None)
        pc = self._pc.pop(p, None)
        if pc:
            try:
                await pc.close()
            except Exception:
                pass

    async def _chiudi_tutto(self):
        for p in list(self._pc):
            await self._chiudi(p)
        if self._nostr:
            await self._nostr.ferma()
