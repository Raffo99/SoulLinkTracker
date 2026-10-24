COLORI_TIPI = {
    "Normale": "#9a9a7a", "Fuoco": "#ee7f30", "Acqua": "#6890f0", "Erba": "#6fbf4a", "Elettro": "#e9c02c",
    "Ghiaccio": "#7ccfcf", "Lotta": "#c03028", "Veleno": "#a040a0", "Terra": "#d6b55a", "Volante": "#a890f0",
    "Psico": "#f85888", "Coleottero": "#a8b820", "Roccia": "#b8a038", "Spettro": "#705898", "Drago": "#7038f8",
    "Buio": "#705848", "Acciaio": "#a8a8c0",
}

BG, PAN, PAN2, BORDO, TESTO, TENUE = "#12131a", "#1b1d27", "#232634", "#2f3344", "#e8e9f0", "#9498ad"
ACC, OK, WARN, KO, ORO = "#7c5cff", "#3ecf8e", "#f5b942", "#ff5c6c", "#ffd166"


def alfa(col: str, a: float) -> str:
    """Colore traslucido per i fogli di stile Qt (che leggono #AARRGGBB, non #RRGGBBAA)."""
    c = col.lstrip("#")
    return f"rgba({int(c[0:2], 16)},{int(c[2:4], 16)},{int(c[4:6], 16)},{a})"

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; color: {TESTO}; }}
QMainWindow, QDialog, QWidget#radice {{ background: {BG}; }}
QWidget#pannello, QFrame#carta, QGroupBox {{ background: {PAN}; border: 1px solid {BORDO}; border-radius: 10px; }}
QGroupBox {{ margin-top: 22px; padding: 14px 8px 8px 8px; }}
QWidget#interno {{ background: {PAN}; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; top: 4px; padding: 0 4px; color: {TENUE};
                    font-size: 8.5pt; font-weight: 600; letter-spacing: 1px; }}
QFrame#barra {{ background: {PAN}; border: 1px solid {BORDO}; border-radius: 12px; }}
QFrame#giocatore {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 10px; }}
QFrame#carta {{ background: {PAN}; border: 1px solid {BORDO}; border-radius: 12px; }}
QFrame#coppia {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 10px; }}
QFrame#coppia[allarme="true"] {{ border-color: #6b5320; background: #2a2416; }}
QLabel#sezione {{ color: {TENUE}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
QLabel#grande {{ font-size: 14pt; font-weight: 700; }}
QLabel#numero {{ font-size: 13pt; font-weight: 600; color: {TENUE}; font-family: Consolas, "Cascadia Mono", monospace; }}
QLabel#chip {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 9px; padding: 3px 10px; }}
QFrame#pk {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 8px; }}
QFrame#pk[ko="true"] {{ background: #1c1d24; }}
QLabel#titolo {{ font-size: 15pt; font-weight: 700; }}
QLabel#tenue {{ color: {TENUE}; }}
QLabel#avvisi {{ background: #2a2414; border: 1px solid #5c4b1f; border-radius: 8px; color: {WARN}; padding: 8px 10px; }}
QLabel#pill {{ border-radius: 9px; padding: 2px 10px; font-weight: 600; }}
QPushButton {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 7px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {ACC}; }}
QPushButton:disabled {{ color: #555a6e; }}
QPushButton#primario {{ background: {ACC}; border-color: {ACC}; color: white; font-weight: 600; }}
QPushButton#pericolo {{ border-color: #5c2a31; }}
QLineEdit, QComboBox, QPlainTextEdit, QSpinBox {{ background: {PAN2}; border: 1px solid {BORDO}; border-radius: 6px; padding: 5px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QTabWidget::pane {{ border: 1px solid {BORDO}; border-radius: 8px; background: {PAN}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {TENUE}; padding: 7px 14px; border: none; }}
QTabBar::tab:selected {{ color: {TESTO}; border-bottom: 2px solid {ACC}; }}
QTableWidget {{ background: {PAN}; gridline-color: #262938; border: none; selection-background-color: #2c2f45; }}
QHeaderView::section {{ background: {PAN}; color: {TENUE}; border: none; border-bottom: 1px solid {BORDO}; padding: 6px; font-weight: 600; }}
QListWidget {{ background: {PAN}; border: none; }}
QListWidget::item {{ padding: 4px; border-bottom: 1px solid #22252f; }}
QProgressBar {{ background: #0b0c10; border: none; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: {OK}; }}
QStatusBar {{ background: {PAN}; border-top: 1px solid {BORDO}; }}
QSplitter::handle {{ background: {BORDO}; width: 2px; }}
QScrollArea {{ border: none; background: transparent; }}
QToolTip {{ background: {PAN2}; color: {TESTO}; border: 1px solid {BORDO}; }}
QMenu {{ background: {PAN2}; border: 1px solid {BORDO}; }} QMenu::item:selected {{ background: #34385a; }}
"""
