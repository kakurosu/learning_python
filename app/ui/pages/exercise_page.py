"""Exercise page — sharp monochrome layout."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...content.schemas import ExercisePage
from ...resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
)
from ..blank_slot import BlankSlot
from ..code_view import VSCODE_GUTTER_BORDER

_SLOT_RE = re.compile(r"\{\{slot:([^}\s]+)\}\}")


class ExercisePageWidget(QWidget):
    submit_requested = pyqtSignal()
    show_solution_requested = pyqtSignal()

    def __init__(
        self,
        page: ExercisePage,
        parent: QWidget | None = None,
        *,
        show_solution_button: bool = True,
    ) -> None:
        super().__init__(parent)
        self.page = page
        self._slots: dict[str, BlankSlot] = {}
        self._blanks_by_id = {b.id: b for b in page.blanks}
        self._show_solution_button = show_solution_button

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(36, 14, 36, 18)
        layout.setSpacing(6)

        kicker = QLabel("Exercise", inner)
        kicker.setObjectName("kicker")
        layout.addWidget(kicker)

        title = QLabel(page.title, inner)
        title.setStyleSheet(
            f"color: {INK}; font-size: 18px; font-weight: 800; letter-spacing: -0.3px;"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        # Red accent rule
        rule = QFrame(inner)
        rule.setProperty("variant", "rule-accent")
        rule.setFixedHeight(2)
        rule.setMaximumWidth(32)
        layout.addWidget(rule)

        prompt = QTextBrowser(inner)
        prompt.setMarkdown(page.prompt)
        prompt.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; color: {INK};"
            f" font-size: 12px; }}"
        )
        prompt.document().setDocumentMargin(0)
        prompt.setMinimumHeight(40)
        # Generous max so longer commentary doesn't get clipped
        prompt.setMaximumHeight(200)
        layout.addWidget(prompt)

        # Code template panel — VSCode-style: header bar with file name above
        # the code body, hairline border, no rounded corners.
        code_wrap = QFrame(inner)
        code_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        wrap_layout = QVBoxLayout(code_wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)

        header = QFrame(code_wrap)
        header.setObjectName("ExerciseCodeHeader")
        header.setStyleSheet(
            f"""
            #ExerciseCodeHeader {{
                background: #252526;
                border: 1px solid {VSCODE_GUTTER_BORDER};
                border-bottom: none;
            }}
            """
        )
        header.setFixedHeight(32)
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 0, 12, 0)
        file_lbl = QLabel("exercise.py", header)
        file_lbl.setStyleSheet(
            "QLabel {"
            " color: #CCCCCC;"
            " font-family: 'Cascadia Mono', 'Consolas', monospace;"
            " font-size: 11px;"
            " letter-spacing: 0;"
            "}"
        )
        h.addWidget(file_lbl)
        h.addStretch(1)
        wrap_layout.addWidget(header)

        code_body = QFrame(code_wrap)
        code_body.setStyleSheet(
            f"QFrame {{ background: #1E1E1E; border: 1px solid {VSCODE_GUTTER_BORDER}; }}"
        )
        code_layout = QVBoxLayout(code_body)
        code_layout.setContentsMargins(20, 14, 20, 14)
        code_layout.setSpacing(2)
        self._render_template_into(code_layout, page.code_template)
        wrap_layout.addWidget(code_body)

        layout.addWidget(code_wrap)

        # Hint area — sharp left red border, no rounded corners
        self._hint_label = QLabel("", inner)
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(
            f"QLabel {{ color: {INK}; background: #141414;"
            f" border-left: 3px solid {ACCENT}; padding: 10px 14px;"
            f" font-size: 12px; }}"
        )
        self._hint_label.setVisible(False)
        layout.addWidget(self._hint_label)

        # Helper buttons (HINT / SOLUTION). The primary SUBMIT lives in the
        # footer of ChapterView so the exercise page is uncluttered.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._hint_btn = QPushButton("Hint", inner)
        self._hint_btn.setProperty("variant", "secondary")
        self._hint_btn.clicked.connect(self._on_hint_clicked)
        btn_row.addWidget(self._hint_btn)

        self._solution_btn = QPushButton("Solution", inner)
        self._solution_btn.setProperty("variant", "secondary")
        self._solution_btn.setEnabled(False)
        self._solution_btn.clicked.connect(self.show_solution_requested.emit)
        if self._show_solution_button:
            btn_row.addWidget(self._solution_btn)
        else:
            self._solution_btn.hide()
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._hint_index = 0
        self._wrong_attempts = 0

    # ------------------------------------------------------------------
    def _render_template_into(self, container: QVBoxLayout, template: str) -> None:
        mono = QFont("Consolas", 11)

        for line in template.splitlines():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            cursor = 0
            for m in _SLOT_RE.finditer(line):
                pre = line[cursor : m.start()]
                if pre:
                    lbl = QLabel(pre, self)
                    lbl.setFont(mono)
                    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                    lbl.setStyleSheet(f"color: {INK}; background: transparent; border: none;")
                    row.addWidget(lbl)
                slot_id = m.group(1)
                blank = self._blanks_by_id.get(slot_id)
                if blank is None:
                    err = QLabel(m.group(0), self)
                    err.setStyleSheet(f"color: {ACCENT};")
                    row.addWidget(err)
                else:
                    slot = BlankSlot(blank, self)
                    self._slots[slot_id] = slot
                    row.addWidget(slot)
                cursor = m.end()
            tail = line[cursor:]
            if tail:
                lbl = QLabel(tail, self)
                lbl.setFont(mono)
                lbl.setStyleSheet(f"color: {INK}; background: transparent; border: none;")
                row.addWidget(lbl)
            row.addStretch(1)
            wrapper = QWidget(self)
            wrapper.setStyleSheet("background: transparent;")
            wrapper.setLayout(row)
            container.addWidget(wrapper)

    # ------------------------------------------------------------------
    def collect_values(self) -> dict[str, str]:
        return {sid: slot.value() for sid, slot in self._slots.items()}

    def mark_results(self, failed_blank_ids: list[str]) -> None:
        for sid, slot in self._slots.items():
            if sid in failed_blank_ids:
                slot.mark_wrong()
            else:
                slot.mark_correct()

    def reset_for_retry(self) -> None:
        for slot in self._slots.values():
            slot.mark_neutral()

    def _on_hint_clicked(self) -> None:
        if not self.page.hints:
            self._hint_label.setText("（この問題にヒントは用意されていません）")
            self._hint_label.setVisible(True)
            return
        text = self.page.hints[min(self._hint_index, len(self.page.hints) - 1)]
        self._hint_label.setText(f"HINT {self._hint_index + 1}     {text}")
        self._hint_label.setVisible(True)
        if self._hint_index < len(self.page.hints) - 1:
            self._hint_index += 1

    def register_wrong_attempt(self) -> int:
        self._wrong_attempts += 1
        if self._wrong_attempts >= 3:
            self._solution_btn.setEnabled(True)
        return self._wrong_attempts
