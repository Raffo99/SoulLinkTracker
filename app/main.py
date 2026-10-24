"""Soul Link Tracker - app desktop (Windows).
Avvio in sviluppo:  python main.py
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sl.finestra import Finestra, risorsa
from sl.stile import QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Soul Link Tracker")
    app.setStyleSheet(QSS)
    icona = risorsa("icona.ico")
    if icona.exists():
        app.setWindowIcon(QIcon(str(icona)))
    w = Finestra()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
