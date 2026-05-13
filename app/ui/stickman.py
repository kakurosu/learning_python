"""Stickman strip — a permanent inline bar that sits *between* the page
content and the footer. Never overlaps any interactive UI.

The widget is composed of:
- a small SVG figure (4 moods) on the right
- a flat speech bubble on the left
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
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


class StickmanStrip(QFrame):
    """Fixed-height strip with a stickman figure + speech text.

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

        # Stickman SVG (very small inline)
        self._svg = QSvgWidget(self)
        self._svg.setFixedSize(28, 46)
        layout.addWidget(self._svg, 0, Qt.AlignmentFlag.AlignVCenter)

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
        path = _RESOURCE_DIR / f"{mood}.svg"
        if path.exists():
            self._svg.load(str(path))

    def set_speech(self, text: str) -> None:
        self._speech.setText(text or "—")
