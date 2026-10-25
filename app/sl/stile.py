"""Colori, caratteri e foglio di stile dell'app."""
from pathlib import Path

COLORI_TIPI = {
    "Normale": "#a8a77a", "Fuoco": "#ee8130", "Acqua": "#6390f0", "Erba": "#7ac74c", "Elettro": "#f7d02c",
    "Ghiaccio": "#96d9d6", "Lotta": "#c22e28", "Veleno": "#a33ea1", "Terra": "#e2bf65", "Volante": "#a98ff3",
    "Psico": "#f95587", "Coleottero": "#a6b91a", "Roccia": "#b6a136", "Spettro": "#735797", "Drago": "#6f35fc",
    "Buio": "#705746", "Acciaio": "#b7b7ce",
}

BG, PAN, PAN2, BORDO, TESTO, TENUE = "#0e0f15", "#171923", "#1f2230", "#2a2e40", "#ecedf3", "#8d92a8"
SPENTO = "#5b6075"
ACC, ACC2, OK, WARN, KO, ORO = "#8b6cff", "#c56cff", "#3ecf8e", "#f5b942", "#ff5c6c", "#ffd166"

# ogni giocatore ha il suo colore (in ordine di ingresso nella partita: uguale per tutti)
COLORI_GIOCATORI = ["#8b6cff", "#38c6d9", "#ff7eb6", "#ffa94d"]

FONT = "Inter"
RISORSE = ""          # cartella delle risorse (per le immagini del foglio di stile)


def alfa(col: str, a: float) -> str:
    """Colore traslucido per i fogli di stile Qt (che leggono #AARRGGBB, non #RRGGBBAA)."""
    c = col.lstrip("#")
    return f"rgba({int(c[0:2], 16)},{int(c[2:4], 16)},{int(c[4:6], 16)},{a})"


def colori_giocatori(st: dict) -> dict:
    """Colore di ogni giocatore, in ordine di ingresso nella partita (uguale su tutti i PC,
    qualunque sia l'ordine delle chiavi che arriva dal database)."""
    G = st.get("giocatori", {}) or {}
    ordine = sorted(G, key=lambda g: ((G[g] or {}).get("entrato") or 0, g))
    return {g: COLORI_GIOCATORI[i % len(COLORI_GIOCATORI)] for i, g in enumerate(ordine)}


def carica_font(cartella: Path) -> str:
    """Registra Inter (incluso nell'app). Se manca si usa Segoe UI."""
    global FONT, RISORSE
    from PySide6.QtGui import QFontDatabase
    RISORSE = str(Path(cartella).parent).replace("\\", "/")
    trovato = False
    for f in sorted(Path(cartella).glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(f)) >= 0:
            trovato = True
    FONT = "Inter" if trovato else "Segoe UI"
    return FONT


def foglio() -> str:
    linea = "rgba(255,255,255,0.06)"
    carta = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b1d29, stop:1 #161822)"
    return f"""
* {{ font-family: "{FONT}", "Segoe UI", sans-serif; font-size: 9.5pt; color: {TESTO}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#radice {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12131c, stop:0.6 #0e0f15, stop:1 #0c0d12); }}
QWidget#pannello {{ background: #0a0b10; border: 1px solid {linea}; border-radius: 16px; }}
QFrame#barra {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #251d45, stop:0.28 #1a1b28, stop:1 #171923);
               border: 1px solid {linea}; border-radius: 16px; }}
QFrame#barraBasso {{ background: {carta}; border: 1px solid {linea}; border-radius: 16px; }}
QFrame#carta {{ background: {carta}; border: 1px solid {linea}; border-radius: 16px; }}
QFrame#giocatore {{ background: rgba(255,255,255,0.035); border: 1px solid {linea}; border-radius: 14px; }}
QFrame#giocatore[lotta="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245,185,66,0.16), stop:1 rgba(245,185,66,0.05));
                                 border: 1px solid rgba(245,185,66,0.45); }}
QFrame#giocatore[boss="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255,92,108,0.20), stop:1 rgba(255,92,108,0.06));
                                border: 1px solid rgba(255,92,108,0.55); }}
QFrame#coppia {{ background: {carta}; border: 1px solid {linea}; border-radius: 14px; }}
QFrame#coppia[allarme="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2c2618, stop:1 #1f1d1c); border: 1px solid #5a4720; }}
QGroupBox {{ background: {carta}; border: 1px solid {linea}; border-radius: 14px; margin-top: 24px; padding: 16px 12px 12px 12px; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 12px; top: 4px; padding: 0 4px;
                    color: {TENUE}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
QWidget#interno {{ background: transparent; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#titolo {{ font-size: 15pt; font-weight: 700; letter-spacing: -0.3px; }}
QLabel#tenue {{ color: {TENUE}; }}
QLabel#piccolo {{ color: {TENUE}; font-size: 8pt; }}
QLabel#sezione {{ color: #7c8199; font-size: 7.5pt; font-weight: 700; letter-spacing: 1.4px; padding: 4px 2px 2px 2px; }}
QLabel#grande {{ font-size: 14pt; font-weight: 700; letter-spacing: -0.2px; padding-top: 2px; }}
QLabel#numero {{ font-size: 12.5pt; font-weight: 600; color: #b9bdd0; font-family: "Cascadia Mono", Consolas, monospace; }}
QLabel#pill {{ border-radius: 9px; padding: 4px 11px; font-weight: 600; font-size: 8.5pt; }}
QLabel#avvisi {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245,185,66,0.13), stop:1 rgba(245,185,66,0.05));
                 border: 1px solid rgba(245,185,66,0.28); border-radius: 14px; color: {WARN}; padding: 12px 16px; }}
QLabel#segnaposto {{ color: {TENUE}; font-size: 10.5pt; }}
QPushButton {{ background: rgba(255,255,255,0.05); border: 1px solid {linea}; border-radius: 10px; padding: 8px 14px; font-weight: 500; }}
QPushButton:hover {{ background: rgba(255,255,255,0.09); border-color: rgba(255,255,255,0.12); }}
QPushButton:pressed {{ background: rgba(255,255,255,0.13); }}
QPushButton:disabled {{ color: #555a6e; }}
QPushButton#primario {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACC}, stop:1 {ACC2}); color: white;
                        font-weight: 600; border: 1px solid rgba(255,255,255,0.18); }}
QPushButton#primario:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9a7fff, stop:1 #d083ff); }}
QPushButton#primario:pressed {{ background: {ACC}; }}
QPushButton#primario:disabled {{ background: rgba(139,108,255,0.25); color: rgba(255,255,255,0.45); border-color: transparent; }}
QPushButton#partita {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 9px;
                       padding: 3px 10px; font-size: 8.5pt; font-weight: 600; color: #cfc6ff; }}
QPushButton#partita:hover {{ background: rgba(139,108,255,0.22); border-color: rgba(139,108,255,0.5); }}
QListWidget#partite::item {{ padding: 0; margin: 2px 0; border-radius: 12px; }}
QListWidget#partite::item:selected {{ background: rgba(139,108,255,0.16); border: 1px solid rgba(139,108,255,0.45); }}
QPushButton#sceltaLotta {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0; }}
QPushButton#sceltaLotta:checked {{ background: rgba(139,108,255,0.22); border-color: rgba(139,108,255,0.6); }}
QPushButton#sceltaLotta:disabled {{ background: rgba(255,92,108,0.06); }}
QPushButton#pericolo {{ background: rgba(255,92,108,0.16); color: #ffb3bc; font-weight: 600; border: 1px solid rgba(255,92,108,0.4); }}
QPushButton::menu-indicator {{ subcontrol-position: right center; right: 7px; width: 8px; }}
QLineEdit, QComboBox, QPlainTextEdit, QSpinBox {{ background: rgba(0,0,0,0.25); border: 1px solid {BORDO}; border-radius: 9px; padding: 6px 9px;
                                               selection-background-color: {ACC}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACC}; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{RISORSE}/freccia.png"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: #1f2231; border: 1px solid #343850; border-radius: 8px; padding: 4px;
                               selection-background-color: rgba(139,108,255,0.3); outline: 0; }}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #454a63; border-radius: 5px; background: rgba(0,0,0,0.3); }}
QCheckBox::indicator:hover {{ border-color: {ACC}; }}
QCheckBox::indicator:checked {{ background: {ACC}; border-color: {ACC}; image: url("{RISORSE}/spunta.png"); }}
QCheckBox::indicator:disabled {{ border-color: #2e3244; }}
QTabWidget::pane {{ border: none; background: transparent; top: 8px; }}
QTabBar::tab {{ background: transparent; color: {TENUE}; padding: 7px 14px; margin-right: 4px; border-radius: 10px; font-weight: 500; }}
QTabBar::tab:hover {{ color: {TESTO}; background: rgba(255,255,255,0.05); }}
QTabBar::tab:selected {{ color: #e6e0ff; background: rgba(139,108,255,0.20); font-weight: 600; }}
QTableWidget {{ background: {carta}; alternate-background-color: rgba(255,255,255,0.022); border: 1px solid {linea}; border-radius: 14px;
                selection-background-color: rgba(139,108,255,0.22); outline: 0; }}
QTableWidget::item {{ padding: 6px 12px; border: none; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: transparent; border: none; border-bottom: 1px solid {linea}; padding: 10px 12px;
                        font-size: 8pt; font-weight: 700; }}
QTableCornerButton::section {{ background: transparent; border: none; }}
QListWidget {{ background: {carta}; border: 1px solid {linea}; border-radius: 14px; padding: 6px; outline: 0; }}
QListWidget::item {{ padding: 7px 10px; border: none; border-radius: 8px; margin: 1px 0; }}
QListWidget::item:hover {{ background: rgba(255,255,255,0.04); }}
QListWidget::item:selected {{ background: rgba(139,108,255,0.20); color: {TESTO}; }}
QTreeWidget {{ background: {carta}; border: 1px solid {linea}; border-radius: 14px; padding: 6px; outline: 0; }}
QTreeWidget::item {{ padding: 7px 4px; border: none; }}
QTreeWidget::item:hover {{ background: rgba(255,255,255,0.04); }}
QTreeWidget::item:selected {{ background: rgba(139,108,255,0.20); color: {TESTO}; }}
QFrame#notifica {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #272a3b, stop:1 #212433);
                   border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; }}
QPlainTextEdit {{ background: {carta}; border: 1px solid {linea}; border-radius: 14px; padding: 10px; }}
QProgressBar {{ background: rgba(0,0,0,0.35); border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: {OK}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 6px 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.12); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.2); }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 6px; }}
QScrollBar::handle:horizontal {{ background: rgba(255,255,255,0.12); border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ background: #232637; color: {TESTO}; border: 1px solid #3a3f56; border-radius: 6px; padding: 7px 9px; }}
QMenu {{ background: #1f2231; border: 1px solid #343850; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px 7px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: rgba(139,108,255,0.25); }}
QMenu::section {{ color: #7c8199; font-size: 7.5pt; font-weight: 700; padding: 8px 14px 3px 14px; background: transparent; }}
QMenu::separator {{ height: 1px; background: {BORDO}; margin: 6px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; left: 4px; }}
QLabel#dialogoTitolo {{ font-size: 12pt; font-weight: 700; color: {TESTO}; }}
QLabel#dialogoTesto {{ color: #c3c6d4; font-size: 9.5pt; }}
QPushButton#collegamento {{ background: transparent; border: none; color: #b6a4ff; padding: 2px 0; font-weight: 600; }}
QPushButton#collegamento:hover {{ color: #d4c8ff; text-decoration: underline; }}
QPlainTextEdit#dettagli {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 8.5pt; color: #b9bdd0; }}
QPushButton#pericolo:hover {{ background: rgba(255,92,108,0.28); }}
"""


QSS = foglio()
