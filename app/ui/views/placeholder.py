"""Placeholder view — used for sidebar entries that don't yet have content
(Practice / References / Settings).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...resources.theme import (
    ACCENT,
    FONT_MONO,
    FONT_SANS_DISPLAY,
    INK,
    INK_3,
    INK_4,
    LINE,
    SURFACE,
)


class PlaceholderView(QWidget):
    """A "coming soon" panel."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 28, 40, 40)
        outer.setSpacing(0)

        kicker = QLabel("Soon", self)
        kicker.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 800; letter-spacing: 0.6px;"
            f" font-family: {FONT_MONO};"
        )
        outer.addWidget(kicker)
        outer.addSpacing(8)

        t = QLabel(title, self)
        t.setStyleSheet(
            f"color: {INK}; font-size: 32px; font-weight: 800; letter-spacing: -1px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        outer.addWidget(t)

        if subtitle:
            s = QLabel(subtitle, self)
            s.setStyleSheet(f"color: {INK_3}; font-size: 13px; padding-top: 4px;")
            s.setWordWrap(True)
            outer.addWidget(s)
        outer.addSpacing(28)

        card = QFrame(self)
        card.setStyleSheet(
            f"QFrame {{ background: transparent; border: 1px solid {LINE};"
            f" border-radius: 0; }}"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(28, 24, 28, 24)
        coming = QLabel("この画面は近日公開予定です。", card)
        coming.setStyleSheet(
            f"color: {INK_3}; font-size: 13px; letter-spacing: -0.1px;"
        )
        card_l.addWidget(coming)
        hint = QLabel(
            "他の章を学習したり、実力テストにチャレンジして待っていてください。",
            card,
        )
        hint.setStyleSheet(f"color: {INK_4}; font-size: 12px; padding-top: 6px;")
        hint.setWordWrap(True)
        card_l.addWidget(hint)

        outer.addWidget(card)
        outer.addStretch(1)
