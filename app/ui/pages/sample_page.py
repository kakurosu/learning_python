"""Sample page — sharp monochrome layout with VSCode-style code block."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...content.schemas import SamplePage
from ...resources.theme import (
    INK,
    INK_3,
)
from ..code_view import CodeBlock
from ..output_pane import OutputPane


class SamplePageWidget(QWidget):
    run_requested = pyqtSignal()

    def __init__(self, page: SamplePage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page = page

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(36, 14, 36, 18)
        layout.setSpacing(6)

        kicker = QLabel("Sample", inner)
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

        explanation = QTextBrowser(inner)
        explanation.setOpenExternalLinks(True)
        explanation.setMarkdown(page.markdown)
        explanation.setStyleSheet(
            f"QTextBrowser {{ background: transparent; border: none; color: {INK};"
            f" font-size: 13px; }}"
        )
        explanation.document().setDocumentMargin(0)
        explanation.setMinimumHeight(40)
        explanation.setMaximumHeight(140)
        layout.addWidget(explanation)

        if page.sample_code.strip():
            self._code_block = CodeBlock(
                page.sample_code,
                file_label=f"sample_{(page.title[:20]).replace(' ', '_').lower() or 'code'}.py",
                runnable=page.runnable,
            )
            self._code_block.set_max_height(160)
            if page.runnable:
                self._code_block.run_clicked.connect(self.run_requested.emit)
            layout.addWidget(self._code_block)

            if page.runnable:
                self._output = OutputPane(inner)
                self._output.setMinimumHeight(60)
                self._output.setMaximumHeight(180)
                layout.addWidget(self._output, 1)
            else:
                self._output = OutputPane(inner)
                self._output.hide()
        else:
            self._code_block = None
            self._output = OutputPane(inner)
            self._output.hide()

        layout.addStretch(1)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @property
    def output_pane(self) -> OutputPane:
        return self._output

    @property
    def runnable(self) -> bool:
        return bool(self.page.sample_code.strip()) and self.page.runnable

    @property
    def code(self) -> str:
        return self.page.sample_code
