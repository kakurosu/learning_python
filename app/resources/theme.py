"""Theme tokens — sharp / monochrome with a single vivid red accent.

Design rules:
- White / near-white surfaces; black ink for text
- A single vivid red as the accent (buttons, active state, dividers)
- Sharp corners (radius 0; never rounded)
- Hairline borders (1px) only where needed
- No emoji, no rounded badges, no soft shadows
"""

from __future__ import annotations

# Color tokens
ACCENT = "#DC2626"            # red-600 — the only saturated color in the UI
ACCENT_HOVER = "#B91C1C"
ACCENT_PRESSED = "#991B1B"
ACCENT_SOFT = "#FEF2F2"

INK = "#0A0A0A"               # near-black — primary text
INK_2 = "#262626"
INK_3 = "#525252"
INK_4 = "#A3A3A3"
LINE = "#E5E5E5"
LINE_STRONG = "#171717"
SURFACE = "#FFFFFF"
BG = "#FFFFFF"
BG_ALT = "#FAFAFA"

SUCCESS = "#0F766E"
DANGER = ACCENT

# Modern font stack — prefer Inter / SF Pro / Segoe UI Variable (Win 11)
FONT_SANS = (
    '"Inter", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", '
    '"Yu Gothic UI", "Hiragino Sans", system-ui, -apple-system, sans-serif'
)
FONT_SANS_DISPLAY = (
    '"Inter Display", "Inter", "SF Pro Display", "Segoe UI Variable Display", '
    '"Segoe UI", "Yu Gothic UI", "Hiragino Sans", system-ui, sans-serif'
)
FONT_MONO = (
    '"Cascadia Code", "Cascadia Mono", "JetBrains Mono", "Consolas", '
    '"SF Mono", "Menlo", monospace'
)

PHASE_LABELS = {
    "A": "Phase A",
    "B": "Phase B",
    "C": "Phase C",
    "D": "Phase D",
    "E": "Phase E",
    "F": "Phase F",
}


GLOBAL_STYLESHEET = f"""
/* ========================================================================
   Study Python Finance — Sharp monochrome stylesheet (white + vivid red).
   ======================================================================== */

QMainWindow, QWidget {{
    background: {BG};
    color: {INK};
    font-family: {FONT_SANS};
    font-size: 13px;
}}

/* Buttons --------------------------------------------------------------- */

QPushButton {{
    background: {ACCENT};
    color: white;
    border: 1px solid {ACCENT};
    border-radius: 0px;
    padding: 7px 18px;
    font-family: {FONT_SANS};
    font-size: 11px;
    font-weight: 700;
    min-width: 80px;
    min-height: 18px;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton:pressed {{ background: {ACCENT_PRESSED}; border-color: {ACCENT_PRESSED}; }}
QPushButton:disabled {{
    background: white;
    color: {INK_4};
    border-color: {LINE};
}}

QPushButton[variant="secondary"] {{
    background: white;
    color: {INK};
    border: 1px solid {INK};
}}
QPushButton[variant="secondary"]:hover {{
    background: {INK};
    color: white;
}}
QPushButton[variant="secondary"]:disabled {{
    background: white;
    color: {INK_4};
    border-color: {LINE};
}}

QPushButton[variant="ghost"] {{
    background: transparent;
    color: {INK_3};
    border: none;
    padding: 6px 10px;
    font-weight: 600;
    min-width: 0;
}}
QPushButton[variant="ghost"]:hover {{
    color: {ACCENT};
}}

/* Inputs ---------------------------------------------------------------- */

QLineEdit, QPlainTextEdit, QTextBrowser, QTextEdit {{
    background: white;
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 0px;
    padding: 6px 8px;
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus {{
    border-color: {INK};
}}

/* Progress bar ---------------------------------------------------------- */

QProgressBar {{
    background: {LINE};
    border: none;
    border-radius: 0px;
    height: 2px;
    text-align: center;
    color: {INK_3};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 0px;
}}

/* Group box ------------------------------------------------------------- */

QGroupBox {{
    background: white;
    border: 1px solid {LINE};
    border-radius: 0px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
    color: {INK};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: white;
    color: {INK};
}}

/* List widgets ---------------------------------------------------------- */

QListWidget {{
    background: transparent;
    border: none;
    outline: 0;
}}
QListWidget::item {{
    background: white;
    border: 1px solid {LINE};
    border-radius: 0px;
    padding: 10px 12px;
    margin-bottom: 4px;
    color: {INK};
}}
QListWidget::item:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
QListWidget::item:selected {{
    background: {INK};
    border-color: {INK};
    color: white;
}}

/* Status bar ------------------------------------------------------------ */

QStatusBar {{
    background: white;
    color: {INK_3};
    border-top: 1px solid {LINE};
}}
QStatusBar::item {{ border: none; }}

/* Tooltip --------------------------------------------------------------- */

QToolTip {{
    background: {INK};
    color: white;
    border: none;
    padding: 6px 8px;
    border-radius: 0px;
    font-size: 11px;
}}

/* Scrollbars ------------------------------------------------------------ */

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {LINE};
    min-height: 30px;
    border-radius: 0px;
}}
QScrollBar::handle:vertical:hover {{ background: {INK_4}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {LINE};
    min-width: 30px;
    border-radius: 0px;
}}
QScrollBar::handle:horizontal:hover {{ background: {INK_4}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ height: 0; width: 0; }}

/* Headings via objectName ---------------------------------------------- */

QLabel#hero {{
    font-family: {FONT_SANS_DISPLAY};
    font-size: 32px;
    font-weight: 800;
    color: {INK};
    letter-spacing: -0.6px;
}}
QLabel#h1 {{
    font-family: {FONT_SANS_DISPLAY};
    font-size: 24px;
    font-weight: 800;
    color: {INK};
    letter-spacing: -0.3px;
}}
QLabel#h2 {{
    font-size: 16px;
    font-weight: 700;
    color: {INK};
}}
QLabel#h3 {{
    font-size: 12px;
    font-weight: 700;
    color: {INK};
}}
QLabel#kicker {{
    font-size: 11px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 0;
}}
QLabel#muted {{
    color: {INK_3};
}}

/* Section divider helper class via dynamic property -------------------- */
QFrame[variant="rule"] {{
    background: {LINE};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame[variant="rule-strong"] {{
    background: {INK};
    max-height: 2px;
    min-height: 2px;
    border: none;
}}
QFrame[variant="rule-accent"] {{
    background: {ACCENT};
    max-height: 2px;
    min-height: 2px;
    border: none;
}}
"""
