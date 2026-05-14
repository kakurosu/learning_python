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
        prompt.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
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

        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    def _build_right_pane(self) -> QWidget:
        """Two-card layout:

            ┌─ editor card ───────────────────┐
            │ header tab │ Reset Format Run   │
            ├─────────────────────────────────┤
            │ code body (template + blanks)   │
            ├─────────────────────────────────┤
            │ ● Python 3.12 · kernel: ready … │
            └─────────────────────────────────┘
                  (12px gap)
            ┌─ console card ──────────────────┐
            │ ● idle  $ python exercise.py    │
            │ > 空欄を埋めて Run を押してください  │
            └─────────────────────────────────┘

        Each card has exactly one outer border. The editor card uses thin
        1px dividers internally; the console is fully detached below.
        """
        pane = QWidget(self)
        pane.setStyleSheet(f"background: {BG};")
        pane_l = QVBoxLayout(pane)
        pane_l.setContentsMargins(20, 24, 32, 24)
        pane_l.setSpacing(12)

        pane_l.addWidget(self._build_editor_card(pane), 1)
        pane_l.addWidget(self._build_console_card(pane))
        return pane

    # ------------------------------------------------------------------
    def _build_editor_card(self, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("ExerciseEditorCard")
        # Outer container is transparent + borderless so the file tab row
        # below sits on the page background (no separate-color rectangle
        # around the file name). The code body widget keeps its own
        # filled surface so the editor itself stays visibly framed.
        card.setStyleSheet("#ExerciseEditorCard { background: transparent; border: none; }")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(0, 0, 0, 0)
        card_l.setSpacing(0)

        # 1) File tab header — same background as code body so the editor
        # card looks like a single uniform surface, just with a thin
        # divider line below it.
        header = QWidget(card)
        header.setStyleSheet("background: transparent; border: none;")
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
            "QLabel { color: #CCCCCC;"
            " font-family: 'JetBrains Mono', 'Cascadia Mono', monospace;"
            " font-size: 11px; letter-spacing: 0.4px; background: transparent;"
            " border: none; }"
        )
        h.addWidget(file_lbl)
        h.addStretch(1)
        for label, slot in [
            ("Reset",  self._on_reset_clicked),
            ("Format", None),
            ("Run",    None),
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
        card_l.addWidget(header)

        # Inner editor surface that wraps the code body + status strip.
        # This is the actual filled "editor card" — the outer #ExerciseEditorCard
        # is just a transparent container so the file-tab header above can
        # sit on the page background without a tinted rectangle of its own.
        inner = QFrame(card)
        inner.setObjectName("ExerciseInnerEditor")
        inner.setStyleSheet(
            f"#ExerciseInnerEditor {{ background: #1E1E1E;"
            f" border: 1px solid {VSCODE_GUTTER_BORDER}; }}"
        )
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 0, 0)
        inner_l.setSpacing(0)

        # 2) Code body — keeps the dark editor surface; only the file tab
        # row above is transparent so the file name doesn't get its own
        # tinted rectangle.
        code_body = QWidget(inner)
        code_body.setStyleSheet("background: transparent; border: none;")
        code_layout = QVBoxLayout(code_body)
        code_layout.setContentsMargins(20, 14, 20, 14)
        code_layout.setSpacing(2)
        self._render_template_into(code_layout, self.page.code_template)
        inner_l.addWidget(code_body, 1)
        inner_l.addWidget(self._divider(inner))

        # 3) Status strip — sits inside the same inner editor card.
        status = QWidget(inner)
        status.setStyleSheet("background: transparent; border: none;")
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
                f" background: transparent; border: none;"
            )
            sl.addWidget(lbl)
        sl.addStretch(1)
        inner_l.addWidget(status)

        card_l.addWidget(inner, 1)
        return card

    def _build_console_card(self, parent: QWidget) -> QFrame:
        console = QFrame(parent)
        console.setObjectName("ExerciseConsoleCard")
        console.setStyleSheet(
            f"#ExerciseConsoleCard {{ background: #0F0F0F;"
            f" border: 1px solid {VSCODE_GUTTER_BORDER}; }}"
        )
        console.setFixedHeight(72)
        cl = QVBoxLayout(console)
        cl.setContentsMargins(16, 12, 16, 12)
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
            f" background: transparent; border: none;"
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
            f" background: transparent; border: none;"
        )
        cl.addWidget(prompt2)
        return console

    @staticmethod
    def _divider(parent: QWidget) -> QFrame:
        """Thin horizontal 1px line used as an internal divider inside the
        editor card. Same color as the outer border so the editor card
        reads as one rectangle with subtle internal section breaks."""
        d = QFrame(parent)
        d.setFixedHeight(1)
        d.setStyleSheet(f"background: {VSCODE_GUTTER_BORDER}; border: none;")
        return d

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

        lines = template.splitlines() or [""]
        # Width of the line-number column — pad to 2 digits at minimum so
        # alignment doesn't shift when a template has 10+ lines.
        gutter_digits = max(2, len(str(len(lines))))

        # All rows share the same fixed height so blank slots (taller QLineEdit
        # widgets) and pure-text rows line up cleanly with their line numbers.
        ROW_HEIGHT = 30

        for i, line in enumerate(lines, start=1):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            # Line-number gutter (VSCode-style, right-aligned, muted color).
            num_lbl = QLabel(str(i).rjust(gutter_digits), self)
            num_lbl.setFont(mono)
            num_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            num_lbl.setStyleSheet(
                "color: #6E7681; background: transparent; border: none;"
                " padding-right: 14px; padding-left: 4px;"
            )
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

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
                    row.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
                slot_id = m.group(1)
                blank = self._blanks_by_id.get(slot_id)
                if blank is None:
                    err = QLabel(m.group(0), self)
                    err.setStyleSheet(f"color: {ACCENT};")
                    row.addWidget(err, 0, Qt.AlignmentFlag.AlignVCenter)
                else:
                    slot = BlankSlot(blank, self)
                    self._slots[slot_id] = slot
                    row.addWidget(slot, 0, Qt.AlignmentFlag.AlignVCenter)
                cursor = m.end()
            tail = line[cursor:]
            if tail:
                lbl = QLabel(tail, self)
                lbl.setFont(mono)
                lbl.setStyleSheet(
                    "color: #D4D4D4; background: transparent; border: none;"
                )
                row.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addStretch(1)
            wrapper = QWidget(self)
            wrapper.setStyleSheet("background: transparent;")
            wrapper.setLayout(row)
            wrapper.setFixedHeight(ROW_HEIGHT)
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
