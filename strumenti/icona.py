"""Disegna l'icona dell'app: due anelli di catena intrecciati (il "link"), con i colori dell'interfaccia.
Uso: python icona.py  ->  icona_1024.png (poi icona.ico/icona.png in app/risorse)
"""
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPainterPathStroker, QPen, QRadialGradient)

L = 1024
H, W, S, D = 410, 236, 80, 138      # altezza e larghezza di un anello, spessore, distanza dal centro


def anello(cy):
    p = QPainterPath()
    p.addRoundedRect(QRectF(-W / 2, cy - H / 2, W, H), W / 2, W / 2)
    return p


def penna(c1, c2, y1, y2, spessore=S):
    g = QLinearGradient(QPointF(-W / 2, y1), QPointF(W / 2, y2))
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    return QPen(QBrush(g), spessore, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def area(path):
    st = QPainterPathStroker()
    st.setWidth(S + 2)
    return st.createStroke(path)


def disegna():
    img = QImage(L, L, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    # fondo: quadrato arrotondato scuro con la sfumatura viola della barra in alto dell'app
    m = 40
    fondo = QPainterPath()
    fondo.addRoundedRect(QRectF(m, m, L - 2 * m, L - 2 * m), 220, 220)
    g = QLinearGradient(QPointF(m, m), QPointF(L - m, L - m))
    g.setColorAt(0, QColor("#2b2156"))
    g.setColorAt(0.55, QColor("#171826"))
    g.setColorAt(1, QColor("#0e0f15"))
    p.fillPath(fondo, g)
    alone = QRadialGradient(QPointF(L / 2, L / 2), L * 0.42)
    alone.setColorAt(0, QColor(150, 108, 255, 75))
    alone.setColorAt(1, QColor(139, 108, 255, 0))
    p.fillPath(fondo, alone)
    p.setPen(QPen(QColor(255, 255, 255, 30), 6))
    p.drawPath(fondo)

    # due anelli ruotati di 45 gradi, centrati
    p.translate(L / 2, L / 2)
    p.rotate(-45)
    a, b = anello(-D), anello(D)
    pa = penna("#7a5cff", "#a68cff", -D - H / 2, -D + H / 2)      # viola dell'app
    pb = penna("#b35cff", "#df8cff", D - H / 2, D + H / 2)        # lilla dell'app
    scuro = QPen(QColor(10, 10, 20, 190), S + 26, Qt.SolidLine, Qt.FlatCap)

    p.save()                                     # ombra morbida sotto la catena
    p.translate(0, 14)
    p.setPen(QPen(QColor(0, 0, 0, 80), S + 8))
    p.drawPath(a)
    p.drawPath(b)
    p.restore()

    p.setPen(pa)
    p.drawPath(a)
    p.setPen(pb)
    p.drawPath(b)

    sinistra = QRectF(-400, -150, 400, 300)
    destra = QRectF(0, -150, 400, 300)
    # incrocio a destra: il lilla passa sopra il viola
    p.save()
    clip = QPainterPath()
    clip.addRect(destra)
    p.setClipPath(clip.intersected(area(a)))
    p.setPen(scuro)
    p.drawPath(b)
    p.setClipRect(destra)
    p.setPen(pb)
    p.drawPath(b)
    p.restore()
    # incrocio a sinistra: il viola passa sopra il lilla
    p.save()
    clip = QPainterPath()
    clip.addRect(sinistra)
    p.setClipPath(clip.intersected(area(b)))
    p.setPen(scuro)
    p.drawPath(a)
    p.setClipRect(sinistra)
    p.setPen(pa)
    p.drawPath(a)
    p.restore()

    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    disegna().save(sys.argv[1] if len(sys.argv) > 1 else "icona_1024.png")
