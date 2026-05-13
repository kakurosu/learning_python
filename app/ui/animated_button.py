"""Animated push button — smooth fade on hover / press states.

PyQt6 does NOT interpolate stylesheet `:hover` states automatically: the
transition is an instant swap. For primary CTAs (Run, Submit, Next, Retry,
Launch Streamlit) we want a quick fade so the UI feels modern. This helper
animates the background color of a QPushButton via a QPropertyAnimation on
its palette, driven by enter/leave/press events.

Usage:
    btn = AnimatedPushButton("Submit")
    btn.set_palette(
        base="#EF4444", hover="#F87171", pressed="#DC2626",
        text="#FFFFFF", border="#EF4444",
    )

The widget still respects its parent's QSS for sizing / typography; only the
background + border colors are owned by this class. Keep stylesheet rules
limited to padding / font / border-radius (sharp corners stay at 0).
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    pyqtProperty,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton


class AnimatedPushButton(QPushButton):
    """QPushButton with animated background-color transitions."""

    _DURATION_MS = 140

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._base   = QColor("#EF4444")
        self._hover  = QColor("#F87171")
        self._pressed = QColor("#DC2626")
        self._text   = QColor("#FFFFFF")
        self._border = QColor("#EF4444")
        self._current = QColor(self._base)
        self._anim = QPropertyAnimation(self, b"bg_color", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(self._DURATION_MS)
        self._apply_style()

    # ------------------------------------------------------------------
    # Public configuration
    # ------------------------------------------------------------------
    def set_palette(
        self,
        *,
        base: str,
        hover: str | None = None,
        pressed: str | None = None,
        text: str = "#FFFFFF",
        border: str | None = None,
    ) -> None:
        self._base    = QColor(base)
        self._hover   = QColor(hover) if hover else self._base.lighter(115)
        self._pressed = QColor(pressed) if pressed else self._base.darker(115)
        self._text    = QColor(text)
        self._border  = QColor(border) if border else self._base
        self._current = QColor(self._base)
        self._apply_style()

    # ------------------------------------------------------------------
    # Animated background-color property (driven by QPropertyAnimation)
    # ------------------------------------------------------------------
    def _get_bg(self) -> QColor:
        return self._current

    def _set_bg(self, c: QColor) -> None:
        self._current = c
        self._apply_style()

    bg_color = pyqtProperty(QColor, _get_bg, _set_bg)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{"
            f" background: {self._current.name()};"
            f" color: {self._text.name()};"
            f" border: 1px solid {self._border.name()};"
            f" border-radius: 0;"
            f" padding: 9px 26px;"
            f" font-size: 12px;"
            f" font-weight: 700;"
            f" min-width: 112px;"
            f" min-height: 26px;"
            f" }}"
            f"QPushButton:disabled {{"
            f" background: #1C1C1C; color: #525252; border-color: #262626;"
            f" }}"
        )

    # ------------------------------------------------------------------
    # Event hooks
    # ------------------------------------------------------------------
    def enterEvent(self, event: QEvent) -> None:  # noqa: N802
        self._animate_to(self._hover)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self._animate_to(self._base)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._animate_to(self._pressed, duration=80)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._animate_to(self._hover)
        super().mouseReleaseEvent(event)

    def _animate_to(self, color: QColor, *, duration: int | None = None) -> None:
        self._anim.stop()
        self._anim.setDuration(duration or self._DURATION_MS)
        self._anim.setStartValue(self._current)
        self._anim.setEndValue(color)
        self._anim.start()
