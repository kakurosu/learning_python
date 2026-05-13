"""BlankSlot — single fill-in-the-blank QLineEdit.

Visual states:
- neutral (initial): white background.
- partial-match (live): light blue while the user is typing and the input
  matches one of ``accept_patterns``.
- ok (after submit): green border.
- ng (after submit): red border.
"""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLineEdit, QToolTip

from ..content.schemas import Blank


class BlankSlot(QLineEdit):
    def __init__(self, blank: Blank, parent=None) -> None:
        super().__init__(parent)
        self.blank = blank
        self.setPlaceholderText(blank.placeholder or "ここに記入")
        self.setFont(QFont("Consolas", 11))
        # Approximate width by character count
        self.setMinimumWidth(max(80, blank.width * 9))
        self.setMaximumWidth(max(120, blank.width * 12))
        self.textChanged.connect(self._on_changed)
        self.setToolTip(blank.hint or "")
        self._set_state("neutral")

    # ------------------------------------------------------------------
    def _on_changed(self, _text: str) -> None:
        if self.isReadOnly():
            return
        if self._matches_pattern_now():
            self._set_state("partial")
        else:
            self._set_state("neutral")

    def _matches_pattern_now(self) -> bool:
        v = self.text().strip()
        if not v:
            return False
        if v == self.blank.canonical_answer.strip():
            return True
        return any(self._safe_fullmatch(p, v) for p in self.blank.accept_patterns)

    @staticmethod
    def _safe_fullmatch(pattern: str, text: str) -> bool:
        try:
            return re.fullmatch(pattern, text) is not None
        except re.error:
            return False

    # ------------------------------------------------------------------
    def _set_state(self, state: str) -> None:
        # Dark-mode sharp variant: surface bg, hairline border. Accent (red)
        # is the focus / partial-match cue; emerald = ok, red bg-wash = ng.
        styles = {
            "neutral": "border: 1px solid #262626; border-radius:0; padding:2px 6px; background:#1C1C1C; color:#F5F5F5;",
            "partial": "border: 1.5px solid #EF4444; border-radius:0; padding:2px 6px; background:#1C1C1C; color:#F5F5F5;",
            "ok":      "border: 1.5px solid #10B981; border-radius:0; padding:2px 6px; background:#1C1C1C; color:#F5F5F5;",
            "ng":      "border: 1.5px solid #EF4444; border-radius:0; padding:2px 6px; background:#2A0E0E; color:#F5F5F5;",
        }
        self.setStyleSheet(styles.get(state, styles["neutral"]))

    def mark_correct(self) -> None:
        self._set_state("ok")
        self.setReadOnly(True)

    def mark_wrong(self) -> None:
        self._set_state("ng")
        self.setReadOnly(False)

    def mark_neutral(self) -> None:
        self._set_state("neutral")
        self.setReadOnly(False)

    def show_hint(self) -> None:
        if self.blank.hint:
            QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.blank.hint, self)

    def value(self) -> str:
        return self.text()

    def keyPressEvent(self, e) -> None:  # noqa: N802 (Qt API)
        # F1 shows the hint
        if e.key() == Qt.Key.Key_F1:
            self.show_hint()
            return
        super().keyPressEvent(e)
