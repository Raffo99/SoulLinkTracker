"""Mappa schematica di Unima (disegnata dall'app, non è la mappa del gioco): città e percorsi collegati,
gli obiettivi della run (fatti, il prossimo, quelli dopo) e dove si trova ogni giocatore."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from .stile import ACC, KO, OK, ORO, TENUE, WARN, colori_giocatori

# chiave: (nome, x, y, tipo, indici del nome del luogo nel gioco). Coordinate su una griglia 100 x 80.
NODI = {
    # sud-ovest (nuovo in Nero 2 / Bianco 2)
    "alisopoli": ("Alisopoli", 6, 66, "citta", [117, 146]),
    "p19": ("Percorso 19", 11, 61, "percorso", [124]),
    "venturia": ("Venturia", 16, 56, "citta", [122]),
    "fattoria": ("Fattoria di Venturia", 11, 50, "luogo", [130]),
    "giuramento": ("Bosco del Giuramento", 5, 54, "luogo", [153]),
    "p20": ("Percorso 20", 22, 61, "percorso", [125]),
    "zondopoli": ("Zondopoli", 28, 68, "citta", [118, 145]),
    "cantiere": ("Cantiere Zondopoli", 33, 73, "luogo", [131]),
    "pokewood": ("Pokéwood", 36, 66, "luogo", [120]),
    # centro
    "austropoli": ("Austropoli", 46, 63, "citta", [8, 109]),
    "fogne": ("Fogne di Austropoli", 42, 69, "luogo", [129]),
    "sentiero": ("Antico Sentiero", 33, 55, "luogo", [136]),
    "p4": ("Percorso 4", 46, 55, "percorso", [17]),
    "galleria": ("Galleria Solidarietà", 51, 59, "luogo", [121]),
    "deserto": ("Deserto della Quiete", 39, 52, "luogo", [34]),
    "castello": ("Castello Sepolto", 36, 47, "luogo", [35]),
    "sciroccopoli": ("Sciroccopoli", 46, 45, "citta", [9, 76, 110]),
    "roteolia": ("Roteolia", 53, 36, "citta", [43]),
    "p16": ("Percorso 16", 53, 45, "percorso", [29, 103]),
    "smarrimento": ("Bosco Smarrimento", 56, 41, "luogo", [72]),
    "p5": ("Percorso 5", 39, 45, "percorso", [18, 93]),
    "ponte_lib": ("Ponte Libecciopoli", 32, 45, "luogo", [65, 89]),
    "libecciopoli": ("Libecciopoli", 25, 45, "citta", [10, 77]),
    "pwt": ("PWT", 20, 52, "luogo", [36]),
    "tunnel_rafan": ("Passo di Rafan", 18, 40, "luogo", [137, 149]),
    # nord-ovest
    "p6": ("Percorso 6", 23, 37, "percorso", [19, 94]),
    "cava_pon": ("Cava Ponentopoli", 15, 33, "luogo", [54]),
    "pietrelettrica": ("Cava Pietrelettrica", 27, 29, "luogo", [37, 85]),
    "ponentopoli": ("Ponentopoli", 18, 23, "citta", [11, 78]),
    "p7": ("Percorso 7", 24, 17, "percorso", [20, 95]),
    "torre_cielo": ("Torre Cielo", 29, 21, "luogo", [56]),
    "monte_vite": ("Monte Vite", 27, 10, "luogo", [38, 86]),
    "mistralopoli": ("Mistralopoli", 33, 7, "citta", [12, 79]),
    "dragospira": ("Torre Dragospira", 38, 3, "luogo", [39, 87]),
    "p8": ("Percorso 8", 37, 13, "percorso", [21, 96]),
    "palude": ("Palude Mistralopoli", 33, 16, "luogo", [57]),
    "ponte_prop": ("Ponte Propulsione", 42, 16, "luogo", [66, 90]),
    # nord
    "p9": ("Percorso 9", 45, 20, "percorso", [22, 97]),
    "boreduopoli": ("Boreduopoli", 50, 23, "citta", [13, 80, 111]),
    "p11": ("Percorso 11", 56, 25, "percorso", [24, 98]),
    "ponte_vil": ("Ponte Villaggio", 62, 26, "luogo", [67, 91]),
    "p12": ("Percorso 12", 68, 27, "percorso", [25, 99]),
    "fortebrezza": ("Fortebrezza", 75, 27, "citta", [41, 104]),
    "fossa": ("Fossa Gigante", 76, 17, "luogo", [61, 88]),
    "p23": ("Percorso 23", 64, 12, "percorso", [128]),
    "via_vittoria": ("Via Vittoria", 55, 8, "luogo", [134, 40]),
    "lega": ("Lega Pokémon", 46, 3, "citta", [44, 73, 74, 150, 151, 152]),
    # est
    "p13": ("Percorso 13", 82, 32, "percorso", [26, 100]),
    "spiraria": ("Spiraria", 86, 39, "citta", [42, 105, 107]),
    "baia": ("Baia Spiraria", 93, 40, "luogo", [71]),
    "tunnel_marino": ("Tunnel Marino", 90, 31, "luogo", [144]),
    "grecalopoli": ("Grecalopoli", 92, 23, "citta", [119]),
    "p22": ("Percorso 22", 84, 19, "percorso", [127]),
    "p21": ("Percorso 21", 96, 16, "percorso", [126]),
    "grotta": ("Grotta Costiera", 92, 10, "luogo", [141]),
    "fregata": ("Fregata Plasma", 84, 10, "luogo", [135]),
    "antipodi": ("Monte Antipodi", 90, 47, "luogo", [132]),
    "poggiovento": ("Poggiovento", 93, 54, "citta", [123]),
    "casa_bizzarra": ("Casa Bizzarra", 97, 60, "luogo", [133]),
    "p14": ("Percorso 14", 83, 45, "percorso", [27, 101]),
    "tempio": ("Tempio Abbondanza", 79, 41, "luogo", [70]),
    "citta_nera": ("Città Nera", 77, 50, "citta", [50, 51, 82, 83, 139, 140]),
    "p15": ("Percorso 15", 70, 49, "percorso", [28, 102]),
    "ponte_mer": ("Ponte Meraviglie", 62, 47, "luogo", [68, 92]),
    # sud-est (Nero / Bianco)
    "ponte_fre": ("Ponte Freccialuce", 53, 63, "luogo", [64]),
    "girandola": ("Bosco Girandola", 58, 61, "luogo", [33]),
    "zefiropoli": ("Zefiropoli", 61, 57, "citta", [7, 108]),
    "p3": ("Percorso 3", 66, 56, "percorso", [16]),
    "levantopoli": ("Levantopoli", 71, 58, "citta", [6]),
    "p2": ("Percorso 2", 72, 63, "percorso", [15]),
    "quattroventi": ("Quattroventi", 73, 67, "citta", [5, 106]),
    "p1": ("Percorso 1", 73, 71, "percorso", [14]),
    "soffiolieve": ("Soffiolieve", 73, 76, "citta", [4, 81]),
    "p17": ("Percorsi 17 e 18", 82, 73, "percorso", [30, 31]),
    "p2lab": ("Laboratorio P2", 88, 71, "luogo", [63]),
    "riserva": ("Riserva Naturale", 66, 76, "luogo", [147]),
}

ARCHI = [
    ("alisopoli", "p19"), ("alisopoli", "giuramento"), ("p19", "venturia"), ("venturia", "fattoria"), ("venturia", "p20"),
    ("p20", "zondopoli"), ("zondopoli", "cantiere"), ("zondopoli", "pokewood"), ("pokewood", "austropoli"),
    ("austropoli", "fogne"), ("fogne", "sentiero"), ("sentiero", "pwt"), ("austropoli", "galleria"), ("galleria", "p4"),
    ("p4", "deserto"), ("deserto", "castello"), ("p4", "sciroccopoli"), ("sciroccopoli", "p5"), ("p5", "ponte_lib"),
    ("ponte_lib", "libecciopoli"), ("libecciopoli", "pwt"), ("libecciopoli", "tunnel_rafan"), ("libecciopoli", "p6"),
    ("sciroccopoli", "roteolia"), ("sciroccopoli", "p16"), ("p16", "smarrimento"), ("p16", "ponte_mer"),
    ("p6", "cava_pon"), ("p6", "pietrelettrica"), ("pietrelettrica", "ponentopoli"), ("ponentopoli", "p7"),
    ("p7", "torre_cielo"), ("p7", "monte_vite"), ("monte_vite", "mistralopoli"), ("mistralopoli", "dragospira"),
    ("mistralopoli", "p8"), ("p8", "palude"), ("p8", "ponte_prop"), ("ponte_prop", "p9"), ("p9", "boreduopoli"),
    ("boreduopoli", "p11"), ("p11", "ponte_vil"), ("ponte_vil", "p12"), ("p12", "fortebrezza"), ("fortebrezza", "fossa"),
    ("fortebrezza", "p13"), ("p13", "spiraria"), ("spiraria", "baia"), ("spiraria", "tunnel_marino"),
    ("tunnel_marino", "grecalopoli"), ("grecalopoli", "p22"), ("p22", "fossa"), ("p22", "p23"), ("p23", "via_vittoria"),
    ("via_vittoria", "lega"), ("grecalopoli", "p21"), ("p21", "grotta"), ("grotta", "fregata"), ("fregata", "fossa"),
    ("spiraria", "antipodi"), ("antipodi", "poggiovento"), ("poggiovento", "casa_bizzarra"), ("spiraria", "p14"),
    ("p14", "tempio"), ("p14", "citta_nera"), ("citta_nera", "p15"), ("p15", "ponte_mer"),
    ("austropoli", "ponte_fre"), ("ponte_fre", "girandola"), ("girandola", "zefiropoli"), ("zefiropoli", "p3"),
    ("p3", "levantopoli"), ("levantopoli", "p2"), ("p2", "quattroventi"), ("quattroventi", "p1"), ("p1", "soffiolieve"),
    ("soffiolieve", "p17"), ("p17", "p2lab"), ("levantopoli", "riserva"),
]

NODO_DA_LUOGO = {i: k for k, v in NODI.items() for i in v[4]}
SIMBOLO_TIPO = {"rivale": "R", "plasma": "P", "lega": "4", "campione": "C"}
COLORE_TIPO = {"palestra": ORO, "rivale": "#8fc7ff", "plasma": KO, "lega": "#c56cff", "campione": "#c56cff"}


def nodo_di(luogo):
    try:
        return NODO_DA_LUOGO.get(int(luogo))
    except (TypeError, ValueError):
        return None


class MappaUnima(QWidget):
    def __init__(self, compatta=False):
        super().__init__()
        self.compatta = compatta
        self.st, self.io = None, None
        self.setMouseTracking(True)
        self.setMinimumHeight(80 if compatta else 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._fase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._anima)
        self._timer.start(60)
        self._firma = None

    def _anima(self):
        if self.isVisible() and self.st:
            self._fase = (self._fase + 0.06) % (2 * math.pi)
            self.update()

    def imposta(self, st, io):
        self.st, self.io = st, io
        self.update()

    # ---------- geometria ----------
    def _vista(self):
        """Parte della mappa da mostrare (in unità della griglia). La mappa piccola si avvicina a dove sei
        e al tuo prossimo obiettivo; quella grande mostra tutto."""
        if not self.compatta or not self.st:
            return QRectF(0, 0, 100, 80)
        g = (self.st.get("giocatori") or {}).get(self.io) or {}
        punti = [nodo_di(g.get("luogo_attuale")), nodo_di((g.get("prossimo") or {}).get("luogo"))]
        punti = [NODI[k] for k in punti if k]
        if not punti:
            return QRectF(0, 0, 100, 80)
        xs, ys = [p[1] for p in punti], [p[2] for p in punti]
        x0, x1, y0, y1 = min(xs) - 9, max(xs) + 9, min(ys) - 7, max(ys) + 8
        w, h = max(x1 - x0, 34), max(y1 - y0, 20)
        r = QRectF(self.rect())
        rapporto = r.width() / max(1, r.height())
        if w / h < rapporto:
            w = h * rapporto
        else:
            h = w / rapporto
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return QRectF(cx - w / 2, cy - h / 2, w, h)

    def _area(self):
        m = 8 if self.compatta else 22
        r = QRectF(self.rect()).adjusted(m, m, -m, -m)
        v = self._vista()
        scala = min(r.width() / v.width(), r.height() / v.height())
        w, h = v.width() * scala, v.height() * scala
        return QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h), scala

    def _pos(self, k):
        area, scala = self._area()
        v = self._vista()
        _, x, y, _, _ = NODI[k]
        return QPointF(area.left() + (x - v.left()) * scala, area.top() + (y - v.top()) * scala)

    # ---------- dati ----------
    def _obiettivi_per_nodo(self):
        st = self.st or {}
        fatti = st.get("fatti") or {}
        G = list(st.get("giocatori") or {})
        out = {}
        for o in st.get("obiettivi") or []:
            k = nodo_di(o.get("luogo"))
            if not k:
                continue
            chi = [g for g in G if (fatti.get(g) or {}).get(o["id"])]
            out.setdefault(k, []).append({**o, "fatto_da": chi, "tutti": bool(G) and len(chi) == len(G)})
        return out

    def _prossimi(self):
        st = self.st or {}
        return {g: (x.get("prossimo") or {}) for g, x in (st.get("giocatori") or {}).items()}

    def _giocatori_per_nodo(self):
        st = self.st or {}
        out = {}
        for g, x in (st.get("giocatori") or {}).items():
            if not x.get("online"):
                continue
            k = nodo_di(x.get("luogo_attuale"))
            if k:
                out.setdefault(k, []).append(g)
        return out

    def _visitati(self):
        st = self.st or {}
        return {nodo_di(r["luogo"]) for r in st.get("percorsi") or []} - {None}

    # ---------- disegno ----------
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area, scala = self._area()
        fondo = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(255, 255, 255, 14), 1))
        p.setBrush(QColor("#11131b"))
        p.drawRoundedRect(fondo, 12, 12)
        clip = QPainterPath()
        clip.addRoundedRect(fondo, 12, 12)
        p.setClipPath(clip)
        if not self.st:
            return
        ob = self._obiettivi_per_nodo()
        pross = self._prossimi()
        mio_pross = pross.get(self.io) or {}
        k_pross = nodo_di(mio_pross.get("luogo"))
        presenti = self._giocatori_per_nodo()
        visitati = self._visitati()
        colori = colori_giocatori(self.st)
        k_io = nodo_di(((self.st.get("giocatori") or {}).get(self.io) or {}).get("luogo_attuale"))

        # strade
        spess = max(1.5, scala * (0.55 if self.compatta else 0.7))
        p.setPen(QPen(QColor("#2b2f40"), spess, Qt.SolidLine, Qt.RoundCap))
        for a, b in ARCHI:
            p.drawLine(self._pos(a), self._pos(b))

        # luoghi
        f = QFont(self.font())
        f.setPointSizeF(7 if self.compatta else 7.5)
        p.setFont(f)
        for k, (nome, x, y, tipo, _) in NODI.items():
            c = self._pos(k)
            vis = k in visitati or k == k_io
            if tipo == "citta":
                r = scala * (1.25 if self.compatta else 1.35)
                p.setPen(QPen(QColor("#5a5f78") if not vis else QColor("#9aa0bb"), 1.2))
                p.setBrush(QColor("#262a3a") if not vis else QColor("#353a52"))
                p.drawRoundedRect(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), r * 0.45, r * 0.45)
            elif tipo == "luogo":
                r = scala * 0.8
                p.setPen(QPen(QColor("#4a4f66"), 1))
                p.setBrush(QColor("#1f2230") if not vis else QColor("#2f3448"))
                p.drawEllipse(c, r, r)
            else:
                r = scala * 0.45
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#3a3f55") if not vis else QColor("#6a7090"))
                p.drawEllipse(c, r, r)
            if tipo == "citta" and (not self.compatta or scala >= 4):
                p.setPen(QColor("#8d92a8"))
                p.drawText(QRectF(c.x() - 60, c.y() + scala * 1.5, 120, 14), Qt.AlignHCenter | Qt.AlignTop, nome)

        # obiettivi
        for k, lista in ob.items():
            c = self._pos(k)
            r = scala * (1.25 if self.compatta else 1.5)
            for j, o in enumerate(lista[:3]):
                cc = QPointF(c.x() + (j - (min(len(lista), 3) - 1) / 2) * r * 1.6, c.y() - r * 1.9)
                col = QColor(COLORE_TIPO.get(o["tipo"], ACC))
                if o["tutti"]:
                    p.setPen(Qt.NoPen)
                    p.setBrush(QColor(OK).darker(160))
                    p.drawEllipse(cc, r * 0.62, r * 0.62)
                    p.setPen(QPen(QColor(OK), max(1.2, r * 0.18), Qt.SolidLine, Qt.RoundCap))
                    p.drawLine(QPointF(cc.x() - r * 0.3, cc.y()), QPointF(cc.x() - r * 0.05, cc.y() + r * 0.25))
                    p.drawLine(QPointF(cc.x() - r * 0.05, cc.y() + r * 0.25), QPointF(cc.x() + r * 0.35, cc.y() - r * 0.25))
                    continue
                p.setPen(QPen(col, 1.2))
                p.setBrush(QColor(col.red(), col.green(), col.blue(), 70 if o["fatto_da"] else 40))
                p.drawEllipse(cc, r * 0.62, r * 0.62)
                if not self.compatta or scala >= 4:
                    ff = QFont(f)
                    ff.setBold(True)
                    ff.setPointSizeF(6.5)
                    p.setFont(ff)
                    p.setPen(col)
                    testo = str(o.get("medaglia")) if o["tipo"] == "palestra" else SIMBOLO_TIPO.get(o["tipo"], "•")
                    p.drawText(QRectF(cc.x() - r, cc.y() - r, 2 * r, 2 * r), Qt.AlignCenter, testo)
                    p.setFont(f)

        # il mio prossimo obiettivo: anello che pulsa
        if k_pross:
            c = self._pos(k_pross)
            onda = (math.sin(self._fase) + 1) / 2
            r = scala * (2.2 + 1.3 * onda)
            col = QColor(ACC)
            col.setAlpha(int(200 - 120 * onda))
            p.setPen(QPen(col, max(1.5, scala * 0.35)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(c, r, r)
            if not self.compatta:                 # nella carta il nome è già scritto sopra
                ff = QFont(f)
                ff.setBold(True)
                p.setFont(ff)
                testo = f"{mio_pross.get('nome', '')}"
                fm = p.fontMetrics()
                w = fm.horizontalAdvance(testo) + 12
                box = QRectF(c.x() - w / 2, c.y() + scala * 2.6, w, fm.height() + 4)
                if box.bottom() > self.height() - 4:
                    box.moveBottom(c.y() - scala * 3.6)
                box.moveLeft(max(4, min(self.width() - w - 4, box.left())))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(139, 108, 255, 225))
                p.drawRoundedRect(box, 6, 6)
                p.setPen(QColor("white"))
                p.drawText(box, Qt.AlignCenter, testo)
                p.setFont(f)

        # giocatori
        for k, chi in presenti.items():
            c = self._pos(k)
            r = scala * (0.95 if self.compatta else 1.15)
            for j, g in enumerate(chi):
                ang = -math.pi / 2 + (j - (len(chi) - 1) / 2) * 0.9 + math.pi
                cc = QPointF(c.x() + math.cos(ang) * r * 2.1, c.y() - math.sin(ang) * r * 2.1) if len(chi) > 1 else \
                    QPointF(c.x() + r * 1.8, c.y() + r * 1.4)
                col = QColor(colori.get(g, ACC))
                p.setPen(QPen(QColor("#11131b"), 2))
                p.setBrush(col)
                p.drawEllipse(cc, r, r)
                if g == self.io:
                    p.setPen(QPen(QColor("white"), 1.6))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(cc, r + 2, r + 2)
                ff = QFont(f)
                ff.setBold(True)
                ff.setPointSizeF(6.5 if self.compatta else 7)
                p.setFont(ff)
                p.setPen(QColor("#14151d"))
                p.drawText(QRectF(cc.x() - r, cc.y() - r, 2 * r, 2 * r), Qt.AlignCenter, g[:1].upper())
                p.setFont(f)

    # ---------- suggerimenti al passaggio del mouse ----------
    def mouseMoveEvent(self, e):
        if not self.st:
            return
        _, scala = self._area()
        pos = e.position()
        vicino, dist = None, 1e9
        for k in NODI:
            d = math.hypot(self._pos(k).x() - pos.x(), self._pos(k).y() - pos.y())
            if d < dist:
                vicino, dist = k, d
        if not vicino or dist > max(10, scala * 2.6):
            QToolTip.hideText()
            return
        nome = NODI[vicino][0]
        righe = [f"<b>{nome}</b>"]
        ob = self._obiettivi_per_nodo().get(vicino) or []
        G = list((self.st.get("giocatori") or {}))
        for o in ob:
            stato = "fatto da tutti" if o["tutti"] else ("fatto da " + ", ".join(o["fatto_da"]) if o["fatto_da"] else "da fare")
            righe.append(f"{o['nome']} <span style='color:{TENUE}'>· {stato}</span>")
        chi = self._giocatori_per_nodo().get(vicino) or []
        if chi:
            righe.append(f"<span style='color:{TENUE}'>Qui adesso:</span> " + ", ".join(chi))
        pross = [g for g, o in self._prossimi().items() if nodo_di(o.get("luogo")) == vicino]
        if pross:
            righe.append(f"<span style='color:{TENUE}'>Prossimo obiettivo di:</span> " + ", ".join(pross))
        QToolTip.showText(e.globalPosition().toPoint(), "<br>".join(righe), self)


LEGENDA = (f"<span style='color:{TENUE};font-size:8.5pt'><span style='color:{ORO}'>●</span> capopalestra (col numero della medaglia) · "
           f"<span style='color:#8fc7ff'>R</span> rivale · <span style='color:{KO}'>P</span> Team Plasma · "
           f"<span style='color:#c56cff'>4</span> Lega · <span style='color:{OK}'>✓</span> fatto da tutti · "
           f"l'anello viola è il tuo prossimo obiettivo, i cerchi colorati siete voi (col bordo bianco tu). "
           f"Passa col mouse su un luogo per i dettagli. La mappa è uno schema: le distanze sono indicative.</span>")


class DialogoMappa(QDialog):
    """La mappa grande, in una finestra a parte che si può ingrandire; si aggiorna da sola."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Mappa di Unima")
        self.setObjectName("dialogo")
        self.resize(980, 760)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 10)
        v.setSpacing(8)
        self.mappa = MappaUnima()
        v.addWidget(self.mappa, 1)
        l = QLabel(LEGENDA)
        l.setWordWrap(True)
        v.addWidget(l)

    def imposta(self, st, io):
        self.mappa.imposta(st, io)
