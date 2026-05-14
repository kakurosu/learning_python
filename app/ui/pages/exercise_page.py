"""Exercise page — Linear-style split-pane (instructions left, code right).

Layout follows the modern "IDE notebook" pattern from the reference design:

    +---------------------- ExercisePageWidget ---------------------+
    | scroll-left (50%)          | code editor pane (50%)            |
    | ─                          | ┌─ exercise.py [Reset Format Run]┐|
    |  EXERCISE 02/8             | │ 1  print({{slot:msg}})         │|
    |  メッセージを変えてみよう    | │ 2                              │|
    |  ─                          | │ ...                            │|
    |  print() は最も基本的な...   | └────────────────────────────────┘|
    |                            | console (kernel output)           |
    |  ⚠ ポイント: …               | ─                                |
    |                            |                                   |
    |  [Hint] [Solution]         |                                   |
    +--------------------------------------------------------------+

Footer Submit / Back lives in ``ChapterView`` (unchanged).
"""

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
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...content.schemas import ExercisePage
from ...resources.theme import (
    ACCENT,
    BG,
    FONT_MONO,
    INK,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    SURFACE,
    SURFACE_ALT,
)
from ..blank_slot import BlankSlot
from ..code_view import VSCODE_GUTTER_BORDER
from ..latex_render import render_latex_in_markdown

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

        # ============================================================
        # Outer: horizontal splitter — instructions left, code right
        # ============================================================
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {LINE}; }}"
        )

        # ---------- LEFT: instructions ----------
        left = self._build_left_pane()
        splitter.addWidget(left)

        # ---------- RIGHT: code editor + console ----------
        right = self._build_right_pane()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([520, 520])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(splitter)

        self._hint_index = 0
        self._wrong_attempts = 0

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------
    def _build_left_pane(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {BG};")

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(6)

        kicker = QLabel("Exercise", inner)
        kicker.setObjectName("kicker")
        layout.addWidget(kicker)

        title = QLabel(self.page.title, inner)
        title.setStyleSheet(
            f"color: {INK}; font-size: 22px; font-weight: 800; letter-spacing: -0.4px;"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        rule = QFrame(inner)
        rule.setProperty("variant", "rule-accent")
        rule.setFixedHeight(2)
        rule.setMaximumWidth(32)
        layout.addWidget(rule)
        layout.addSpacing(6)

        prompt = QTextBrowser(inner)
        prompt.setMarkdown(render_latex_in_markdown(self.page.prompt))
        prompt.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; color: {INK_2};"
            f" font-size: 12.5px; }}"
        )
        prompt.document().setDocumentMargin(0)
        prompt.setMinimumHeight(80)
        prompt.setMaximumHeight(360)
        layout.addWidget(prompt)

        # Hint area — sharp left red border
        self._hint_label = QLabel("", inner)
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(
            f"QLabel {{ color: {INK}; background: {SURFACE_ALT};"
            f" border: 1px solid {LINE};"
            f" border-left: 3px solid {ACCENT}; padding: 10px 14px;"
            f" font-size: 12px; }}"
        )
        self._hint_label.setVisible(False)
        layout.addWidget(self._hint_label)
        layout.addSpacing(6)

        # Hint / Solution buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._hint_btn = QPushButton("ヒント", inner)
        self._hint_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {INK_2};"
            f" border: 1px solid {LINE}; border-radius: 0;"
            f" padding: 6px 14px; font-size: 11px; font-weight: 700;"
            f" min-width: 0; min-height: 0; }}"
            f"QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}"
        )
        try:
            import qtawesome as qta
            self._hint_btn.setIcon(qta.icon("fa5s.lightbulb", color=INK_3))
        except ImportError:
            pass
        self._hint_btn.clicked.connect(self._on_hint_clicked)
        btn_row.addWidget(self._hint_btn)

        self._solution_btn = QPushButton("解答を見る", inner)
        self._solution_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {INK_2};"
            f" border: 1px solid {LINE}; border-radius: 0;"
            f" padding: 6px 14px; font-size: 11px; font-weight: 700;"
            f" min-width: 0; min-height: 0; }}"
            f"QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}"
            f"QPushButton:disabled {{ color: {INK_4}; border-color: {LINE}; }}"
        )
        self._solution_btn.setEnabled(False)
        self._solution_btn.clicked.connect(self.show_solution_requested.emit)
        if self._show_solution_button:
            btn_row.addWidget(self._solution_btn)
        else:
            self._solution_btn.hide()

        xp_hint = QLabel("ヒントを使うと XP が <span style='color:#A3A3A3'>-20%</span>", inner)
        xp_hint.setTextFormat(Qt.TextFormat.RichText)
        xp_hint.setStyleSheet(f"color: {INK_4}; font-size: 10px; padding-left: 8px;")
        btn_row.addWidget(xp_hint, 0, Qt.AlignmentFlag.AlignVCenter)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    def _build_right_pane(self) -> QWidget:
        pane = QWidget(self)
        pane.setStyleSheet(f"background: {BG};")
        pane_l = QVBoxLayout(pane)
        pane_l.setContentsMargins(20, 24, 32, 24)
        pane_l.setSpacing(0)

        # File tab header — file icon + name + buttons (Reset / Format / Run)
        header = QFrame(pane)
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
        header.setFixedHeight(38)
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 0, 8, 0)
        h.setSpacing(8)

        dot = QLabel(header)
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {ACCENT}; border: none;")
        h.addWidget(dot)
        file_lbl = QLabel("exercise.py", header)
        file_lbl.setStyleSheet(
            "QLabel { color: #CCCCCC; font-family: 'JetBrains Mono', 'Cascadia Mono', monospace;"
            " font-size: 11px; letter-spacing: 0.4px; }"
        )
        h.addWidget(file_lbl)
        h.addStretch(1)

        # Reset / Format / Run buttons — cosmetic for now, Reset wired up
        for label, slot in [
            ("Reset",  self._on_reset_clicked),
            ("Format", None),
            ("Run",    None),   # Run for exercise = Submit; left as visual cue
        ]:
            btn = QPushButton(label, header)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            primary = (label == "Run")
            btn.setStyleSheet(self._editor_btn_qss(primary=primary))
            if slot is not None:
                btn.clicked.connect(slot)
            if label == "Run":
                btn.clicked.connect(self.submit_requested.emit)
            h.addWidget(btn)
        pane_l.addWidget(header)

        # Code body — embed the existing template + blanks rendering
        code_body = QFrame(pane)
        code_body.setStyleSheet(
            f"QFrame {{ background: #1E1E1E; border: 1px solid {VSCODE_GUTTER_BORDER}; }}"
        )
        code_layout = QVBoxLayout(code_body)
        code_layout.setContentsMargins(20, 14, 20, 14)
        code_layout.setSpacing(2)
        self._render_template_into(code_layout, self.page.code_template)
        pane_l.addWidget(code_body, 1)

        # Status footer (Python 3.12 · kernel: ready · UTF-8 · access:N)
        status = QFrame(pane)
        status.setStyleSheet(
            f"QFrame {{ background: #181818; border: 1px solid {VSCODE_GUTTER_BORDER};"
            f" border-top: none; }}"
        )
        status.setFixedHeight(24)
        sl = QHBoxLayout(status)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(14)
        for label in [
            "● Python 3.12",
            "kernel: ready",
            "UTF-8",
            "LF",
            f"access:{len(self.page.blanks)}",
        ]:
            lbl = QLabel(label, status)
            color = "#10B981" if label.startswith("●") else "#858585"
            lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; font-weight: 600;"
                f" letter-spacing: 0.3px; font-family: {FONT_MONO};"
            )
            sl.addWidget(lbl)
        sl.addStretch(1)
        pane_l.addWidget(status)

        # Console — small kernel output preview area below the editor.
        # It mimics a terminal echo. Currently shows static guidance text;
        # real output is rendered on the result overlay.
        console = QFrame(pane)
        console.setStyleSheet(
            f"QFrame {{ background: #0F0F0F; border: 1px solid {VSCODE_GUTTER_BORDER};"
            f" border-top: none; }}"
        )
        cl = QVBoxLayout(console)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(4)
        prompt1 = QLabel(
            "<span style='color:#10B981'>●</span> "
            "<span style='color:#A3A3A3'>idle</span>"
            "<span style='color:#525252'>&nbsp;&nbsp;$</span> "
            "<span style='color:#D4D4D4'>python exercise.py</span>",
            console,
        )
        prompt1.setTextFormat(Qt.TextFormat.RichText)
        prompt1.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 11px; letter-spacing: 0;"
        )
        cl.addWidget(prompt1)
        prompt2 = QLabel(
            "<span style='color:#858585'>&gt;</span> "
            "<span style='color:#858585'>空欄を埋めて Run を押してください</span>",
            console,
        )
        prompt2.setTextFormat(Qt.TextFormat.RichText)
        prompt2.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 11px; letter-spacing: 0;"
        )
        cl.addWidget(prompt2)
        console.setFixedHeight(60)
        pane_l.addWidget(console)
        return pane

    @staticmethod
    def _editor_btn_qss(primary: bool) -> str:
        if primary:
            return (
                "QPushButton {"
                " background: #EF4444; color: white;"
                " border: 1px solid #EF4444; border-radius: 0;"
                " padding: 4px 14px; font-size: 11px; font-weight: 700;"
                " min-width: 56px; min-height: 22px; }"
                "QPushButton:hover { background: #F87171; border-color: #F87171; }"
            )
        return (
            "QPushButton {"
            " background: transparent; color: #CCCCCC;"
            " border: 1px solid #3C3C3C; border-radius: 0;"
            " padding: 4px 12px; font-size: 11px; font-weight: 700;"
            " min-width: 48px; min-height: 22px; }"
            "QPushButton:hover { color: white; border-color: #6E7681; }"
        )

    # ------------------------------------------------------------------
    def _render_template_into(self, container: QVBoxLayout, template: str) -> None:
        mono = QFont("JetBrains Mono", 11)
        mono.setStyleHint(QFont.StyleHint.Monospace)

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
                    lbl.setStyleSheet(
                        "color: #D4D4D4; background: transparent; border: none;"
                    )
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
                lbl.setStyleSheet(
                    "color: #D4D4D4; background: transparent; border: none;"
                )
                row.addWidget(lbl)
            row.addStretch(1)
            wrapper = QWidget(self)
            wrapper.setStyleSheet("background: transparent;")
            wrapper.setLayout(row)
            container.addWidget(wrapper)

    # ------------------------------------------------------------------
    def _on_reset_clicked(self) -> None:
        for slot in self._slots.values():
            slot.clear()
            slot.mark_neutral()

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
