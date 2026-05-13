"""Reading page — read a code snippet and pick what it represents.

Sharp monochrome layout matching SamplePage / ExercisePage. No fill-in
blanks and no kernel execution: the only interaction is selecting one of
the multiple-choice options and pressing Submit (in the chapter footer).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QRadioButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...content.schemas import ReadingPage
from ...resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
)
from ..code_view import CodeBlock


class ReadingPageWidget(QWidget):
    submit_requested = pyqtSignal()

    def __init__(self, page: ReadingPage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page = page

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(36, 14, 36, 18)
        layout.setSpacing(6)

        kicker = QLabel("Reading", inner)
        kicker.setObjectName("kicker")
        layout.addWidget(kicker)

        title = QLabel(page.title, inner)
        title.setStyleSheet(
            f"color: {INK}; font-size: 18px; font-weight: 800; letter-spacing: -0.3px;"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

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
        prompt.setMaximumHeight(120)
        layout.addWidget(prompt)

        # Read-only code snippet — looks identical to the sample page's code
        # block, but with no RUN button.
        self._code_block = CodeBlock(
            page.code,
            file_label=page.code_file_label,
            runnable=False,
        )
        self._code_block.set_max_height(200)
        layout.addWidget(self._code_block)

        # "Question" kicker above the choices
        q_kicker = QLabel("Question", inner)
        q_kicker.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 0; margin-top: 8px;"
        )
        layout.addWidget(q_kicker)

        # Choice group: a QButtonGroup wraps a list of QRadioButtons so we
        # can read back the picked index via checkedId().
        choices_box = QFrame(inner)
        choices_box.setStyleSheet(f"QFrame {{ background: #141414; border: 1px solid {LINE}; }}")
        choices_layout = QVBoxLayout(choices_box)
        choices_layout.setContentsMargins(14, 10, 14, 10)
        choices_layout.setSpacing(6)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        # Circular radio indicator with strong contrast. The default Qt look
        # blends into the background; we draw a clear black-bordered white
        # circle when unchecked, and a solid red circle (with red ring) when
        # checked. A radius of 8 on a 16x16 box produces a perfect circle.
        radio_qss = (
            f"QRadioButton {{ color: {INK}; font-size: 13px; padding: 6px 4px;"
            f" spacing: 10px; background: transparent; }}"
            f"QRadioButton:hover {{ color: {ACCENT}; }}"
            f"QRadioButton::indicator {{ width: 16px; height: 16px;"
            f" border: 2px solid {INK_3}; background: #141414;"
            f" border-radius: 9px; }}"
            f"QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}"
            f"QRadioButton::indicator:checked {{ border: 2px solid {ACCENT};"
            f" background: {ACCENT}; border-radius: 9px; }}"
        )
        for i, text in enumerate(page.choices):
            rb = QRadioButton(text, choices_box)
            rb.setStyleSheet(radio_qss)
            self._group.addButton(rb, i)
            choices_layout.addWidget(rb)
        layout.addWidget(choices_box)

        # Hint banner shown when the user presses Submit without selecting.
        self._notice = QLabel("", inner)
        self._notice.setWordWrap(True)
        self._notice.setStyleSheet(
            f"QLabel {{ color: {INK}; background: #141414;"
            f" border-left: 3px solid {ACCENT}; padding: 8px 14px; font-size: 12px; }}"
        )
        self._notice.setVisible(False)
        layout.addWidget(self._notice)

        layout.addStretch(1)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    def selected_index(self) -> int | None:
        idx = self._group.checkedId()
        return idx if idx >= 0 else None

    def show_unanswered_notice(self) -> None:
        self._notice.setText("選択肢を 1 つ選んでから提出してください。")
        self._notice.setVisible(True)

    def reset_for_retry(self) -> None:
        checked = self._group.checkedButton()
        if checked is not None:
            self._group.setExclusive(False)
            checked.setChecked(False)
            self._group.setExclusive(True)
        self._notice.setVisible(False)
