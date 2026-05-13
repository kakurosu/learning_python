"""Code viewer + code block widget — VSCode "Light Modern" inspired.

The ``CodeView`` is a read-only ``QPlainTextEdit`` with:
- Cascadia Mono / Consolas font.
- Line numbers in a left gutter.
- Syntax highlighting using VSCode Light Modern token colors.
- 1-pixel hairline border, no rounded corners.

The ``CodeBlock`` wraps a ``CodeView`` with a sharp header bar (file name
on the left, optional RUN button on the right). The RUN button moving from
"below the code" to "inside the code header" prevents the floating stickman
overlay from ever covering the run trigger.
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, QRegularExpression, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# --- VSCode Light Modern token palette --------------------------------------

VSCODE_BG = "#FFFFFF"
VSCODE_FG = "#3B3B3B"
VSCODE_GUTTER_BG = "#FFFFFF"
VSCODE_GUTTER_FG = "#6E7781"
VSCODE_GUTTER_BORDER = "#E5E5E5"
VSCODE_SELECTION = "#ADD6FF"

VSCODE_KEYWORD = "#0000FF"
VSCODE_CONTROL = "#AF00DB"
VSCODE_STRING = "#A31515"
VSCODE_NUMBER = "#098658"
VSCODE_FUNCTION = "#795E26"
VSCODE_TYPE = "#267F99"
VSCODE_VARIABLE = "#001080"
VSCODE_COMMENT = "#008000"
VSCODE_DECORATOR = "#795E26"


class _PyHighlighter(QSyntaxHighlighter):
    """VSCode Light Modern-style Python highlighter."""

    KEYWORDS = (
        "False None True and as assert async await break class continue del "
        "elif else except finally for from global if import in is lambda "
        "nonlocal not or pass raise return try while with yield"
    ).split()

    CONTROL_FLOW = "for while return break continue raise yield".split()

    BUILTINS = (
        "abs all any bool dict enumerate filter float format int len list map max "
        "min print range repr reversed round set sorted str sum tuple type zip "
        "open input super isinstance hasattr getattr setattr"
    ).split()

    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Decorators (e.g. @staticmethod)
        deco_fmt = self._fmt(VSCODE_DECORATOR)
        self._rules.append((QRegularExpression(r"@\w+"), deco_fmt))

        # Keywords (blue)
        kw_fmt = self._fmt(VSCODE_KEYWORD)
        for kw in self.KEYWORDS:
            if kw in self.CONTROL_FLOW:
                continue
            self._rules.append((QRegularExpression(rf"\b{kw}\b"), kw_fmt))

        # Control flow (purple)
        ctrl_fmt = self._fmt(VSCODE_CONTROL)
        for kw in self.CONTROL_FLOW:
            self._rules.append((QRegularExpression(rf"\b{kw}\b"), ctrl_fmt))

        # Builtins (treated like types)
        type_fmt = self._fmt(VSCODE_TYPE)
        for b in self.BUILTINS:
            self._rules.append((QRegularExpression(rf"\b{b}\b"), type_fmt))

        # Function calls (anything followed by `(`)
        fn_fmt = self._fmt(VSCODE_FUNCTION)
        self._rules.append((QRegularExpression(r"\b([a-z_][A-Za-z0-9_]*)(?=\s*\()"), fn_fmt))
        # PascalCase classes — only when not directly followed by a paren (so calls
        # like `DataFrame(...)` get the FUNCTION color, declarations like
        # `class DataFrame:` and references `df: DataFrame` get TYPE color).
        self._rules.append((QRegularExpression(r"\b[A-Z][A-Za-z0-9_]*\b(?!\s*\()"), type_fmt))

        # Numbers
        num_fmt = self._fmt(VSCODE_NUMBER)
        self._rules.append((QRegularExpression(r"\b\d+(\.\d+)?([eE][-+]?\d+)?\b"), num_fmt))

        # Strings
        string_fmt = self._fmt(VSCODE_STRING)
        self._rules.append((QRegularExpression(r'""".*?"""'), string_fmt))
        self._rules.append((QRegularExpression(r"'''.*?'''"), string_fmt))
        self._rules.append((QRegularExpression(r'(?:f|r|rf|fr|b)?"[^"\\]*(?:\\.[^"\\]*)*"'), string_fmt))
        self._rules.append((QRegularExpression(r"(?:f|r|rf|fr|b)?'[^'\\]*(?:\\.[^'\\]*)*'"), string_fmt))

        # Comments — last so they win over earlier rules.
        comment_fmt = self._fmt(VSCODE_COMMENT, italic=True)
        self._rules.append((QRegularExpression(r"#[^\n]*"), comment_fmt))

    @staticmethod
    def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(QFont.Weight.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for regex, fmt in self._rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ---------------------------------------------------------------------------
# Line-number gutter
# ---------------------------------------------------------------------------


class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeView") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self._editor.line_number_area_paint_event(event)


class CodeView(QPlainTextEdit):
    """Read-only Python code viewer (VSCode Light Modern)."""

    def __init__(self, code: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)

        font = QFont()
        font.setFamilies(["Cascadia Mono", "Consolas", "Courier New"])
        font.setPointSize(11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background: {VSCODE_BG};
                color: {VSCODE_FG};
                border: 1px solid {VSCODE_GUTTER_BORDER};
                border-top: none;
                border-radius: 0;
                padding: 8px 4px 8px 0;
                selection-background-color: {VSCODE_SELECTION};
                selection-color: {VSCODE_FG};
            }}
            """
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTabStopDistance(QFontMetricsF(font).horizontalAdvance(" ") * 4)

        self._highlighter = _PyHighlighter(self.document())

        # Line number gutter
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width(0)

        self.setPlainText(code)

    # --- Line number gutter mechanics -------------------------------------
    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        char_w = QFontMetricsF(self.font()).horizontalAdvance("9")
        return int(char_w * digits + 18)

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(VSCODE_GUTTER_BG))
        painter.setPen(QColor(VSCODE_GUTTER_BORDER))
        x = self._line_number_area.width() - 1
        painter.drawLine(x, event.rect().top(), x, event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        painter.setFont(self.font())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                num = str(block_number + 1)
                painter.setPen(QColor(VSCODE_GUTTER_FG))
                painter.drawText(
                    0, int(top), self._line_number_area.width() - 8,
                    int(self.fontMetrics().height()),
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                    num,
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def set_code(self, code: str) -> None:
        self.setPlainText(code)


# ---------------------------------------------------------------------------
# CodeBlock — code view with a sharp header bar
# ---------------------------------------------------------------------------


class CodeBlock(QFrame):
    """Code block with a header bar (file name + optional RUN button)."""

    run_clicked = pyqtSignal()

    def __init__(
        self,
        code: str,
        *,
        file_label: str = "sample.py",
        runnable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CodeBlock")
        self.setStyleSheet(f"#CodeBlock {{ background: {VSCODE_BG}; border: none; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(self)
        header.setObjectName("CodeBlockHeader")
        header.setStyleSheet(
            f"""
            #CodeBlockHeader {{
                background: #FAFAFA;
                border: 1px solid {VSCODE_GUTTER_BORDER};
                border-bottom: none;
            }}
            """
        )
        header.setFixedHeight(34)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 6, 0)
        header_layout.setSpacing(8)

        file_lbl = QLabel(file_label, header)
        file_lbl.setStyleSheet(
            "QLabel {"
            " color: #6E7781;"
            " font-family: 'Cascadia Mono', 'Consolas', monospace;"
            " font-size: 11px;"
            " letter-spacing: 0.3px;"
            "}"
        )
        header_layout.addWidget(file_lbl)
        header_layout.addStretch(1)

        if runnable:
            self._run_btn = QPushButton("Run", header)
            self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._run_btn.setMinimumWidth(72)
            self._run_btn.setStyleSheet(
                """
                QPushButton {
                    background: #DC2626;
                    color: #FFFFFF;
                    border: 1px solid #DC2626;
                    border-radius: 0;
                    padding: 4px 14px;
                    font-size: 11px;
                    font-weight: 700;
                    min-height: 22px;
                    min-width: 64px;
                }
                QPushButton:hover { background: #B91C1C; border-color: #B91C1C; }
                QPushButton:pressed { background: #991B1B; border-color: #991B1B; }
                """
            )
            self._run_btn.clicked.connect(self.run_clicked.emit)
            header_layout.addWidget(self._run_btn)
        else:
            self._run_btn = None

        layout.addWidget(header)

        self._view = CodeView(code, self)
        self._view.setMinimumHeight(80)
        layout.addWidget(self._view, 1)

    @property
    def view(self) -> CodeView:
        return self._view

    def set_code(self, code: str) -> None:
        self._view.set_code(code)

    def set_max_height(self, h: int) -> None:
        self._view.setMaximumHeight(h)

    def set_run_enabled(self, enabled: bool) -> None:
        if self._run_btn is not None:
            self._run_btn.setEnabled(enabled)
