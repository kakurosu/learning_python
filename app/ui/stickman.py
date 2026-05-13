"""Mascot strip — a permanent inline bar that sits *between* the page
content and the footer. Never overlaps any interactive UI.

The widget is composed of:
- a small dog PNG figure (4 moods) on the right; falls back to the legacy
  stick-figure SVG when the PNG is missing
- a flat speech text label on the left
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QWidget,
)

from ..resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
)

Mood = Literal["normal", "happy", "sad", "explain"]
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources" / "stickman"

# Mood → mascot image mapping. The dog PNGs supersede the legacy stick-figure
# SVGs when present; the SVG path is kept as a fallback so the widget still
# renders something if a PNG is missing.
#
# Mapping rationale (set 2026-05-13):
#   normal  → dog1 (smile)   — neutral/default expression
#   happy   → dog4 (laugh)   — celebrate a correct answer
#   sad     → dog3 (cry)     — wrong answer / runtime error
#   explain → dog2 (angry)   — focused/serious while explaining
_MASCOT_PNG_SIZE = (42, 42)


class StickmanStrip(QFrame):
    """Fixed-height mascot strip + speech text.

    Place it directly above the footer in a vertical layout. It will never
    overlap with any other UI element because it occupies its own row.
    """

    HEIGHT = 60

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.setObjectName("StickmanStrip")
        self.setStyleSheet(
            f"""
            #StickmanStrip {{
                background: white;
                border: none;
                border-top: 1px solid {LINE};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 0, 40, 0)
        layout.setSpacing(16)

        self._kicker = QLabel("Assistant", self)
        self._kicker.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        self._kicker.setFixedWidth(78)
        layout.addWidget(self._kicker, 0, Qt.AlignmentFlag.AlignVCenter)

        # Vertical separator
        sep1 = QFrame(self)
        sep1.setStyleSheet(f"background: {LINE};")
        sep1.setFixedSize(1, 24)
        layout.addWidget(sep1, 0, Qt.AlignmentFlag.AlignVCenter)

        self._speech = QLabel("", self)
        self._speech.setWordWrap(False)
        self._speech.setFont(QFont("Segoe UI", 10))
        self._speech.setStyleSheet(
            f"color: {INK}; padding: 0; background: transparent; border: none;"
        )
        self._speech.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._speech, 1, Qt.AlignmentFlag.AlignVCenter)

        # Vertical separator
        sep2 = QFrame(self)
        sep2.setStyleSheet(f"background: {LINE};")
        sep2.setFixedSize(1, 24)
        layout.addWidget(sep2, 0, Qt.AlignmentFlag.AlignVCenter)

        # Mascot figure. We host both a QLabel (for PNG via QPixmap) and a
        # QSvgWidget (legacy fallback) inside a stacked container, switching
        # whichever is loaded for the current mood.
        self._mascot_holder = QWidget(self)
        self._mascot_holder.setFixedSize(*_MASCOT_PNG_SIZE)
        mascot_stack = QStackedLayout(self._mascot_holder)
        mascot_stack.setContentsMargins(0, 0, 0, 0)
        self._mascot_stack = mascot_stack

        self._pix_label = QLabel(self._mascot_holder)
        self._pix_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pix_label.setStyleSheet("background: transparent; border: none;")
        mascot_stack.addWidget(self._pix_label)

        self._svg = QSvgWidget(self._mascot_holder)
        mascot_stack.addWidget(self._svg)

        layout.addWidget(self._mascot_holder, 0, Qt.AlignmentFlag.AlignVCenter)

        self._mood_lbl = QLabel("Mentor", self)
        self._mood_lbl.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        self._mood_lbl.setFixedWidth(56)
        layout.addWidget(self._mood_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._mood: Mood = "normal"
        self.set_mood("normal")
        self.set_speech("")

    def set_mood(self, mood: Mood) -> None:
        self._mood = mood
        png = _RESOURCE_DIR / f"{mood}.png"
        if png.exists():
            pix = QPixmap(str(png))
            if not pix.isNull():
                scaled = pix.scaled(
                    _MASCOT_PNG_SIZE[0],
                    _MASCOT_PNG_SIZE[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._pix_label.setPixmap(scaled)
                self._mascot_stack.setCurrentWidget(self._pix_label)
                return
        # PNG missing or unreadable — fall back to the legacy stick-figure SVG.
        svg = _RESOURCE_DIR / f"{mood}.svg"
        if svg.exists():
            self._svg.load(str(svg))
            self._mascot_stack.setCurrentWidget(self._svg)

    def set_speech(self, text: str) -> None:
        self._speech.setText(text or "—")
