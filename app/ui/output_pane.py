"""Output pane — renders the four kinds of kernel output.

- stdout (white background)
- stderr / traceback (red text)
- display_data PNG images (matplotlib figures)
- text/html blobs (pandas DataFrames)
"""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..kernel.manager import ExecutionResult

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


class OutputPane(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        font = QFont()
        font.setFamilies(["Cascadia Mono", "Consolas", "Courier New"])
        font.setPointSize(10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(font)
        self._text.setMinimumHeight(80)
        self._text.setPlaceholderText("（実行結果がここに表示されます）")
        # Terminal-like dark surface, with a thin red top accent the first
        # time something is rendered (handled in render()) — keeps it readable
        # on the dark theme and visually distinct from the code block above.
        self._text.setStyleSheet(
            "QPlainTextEdit {"
            " background: #0F0F0F; color: #D4D4D4;"
            " border: 1px solid #262626; border-radius: 0;"
            " padding: 10px 12px;"
            " font-family: 'Cascadia Mono', Consolas, monospace;"
            "}"
        )

        # Container for images / HTML below the text.
        self._extras_container = QWidget(self)
        self._extras_layout = QVBoxLayout(self._extras_container)
        self._extras_layout.setContentsMargins(0, 0, 0, 0)
        self._extras_layout.setSpacing(6)
        self._extras_scroll = QScrollArea(self)
        self._extras_scroll.setWidgetResizable(True)
        self._extras_scroll.setWidget(self._extras_container)
        # When a chart appears, give it real estate without dominating.
        self._extras_scroll.setMinimumHeight(220)
        self._extras_scroll.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)
        layout.addWidget(self._extras_scroll, 1)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._text.clear()
        # remove all extras
        while self._extras_layout.count():
            item = self._extras_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._extras_scroll.setVisible(False)

    def render(self, result: ExecutionResult) -> None:
        self.clear()
        # If a chart / HTML extra is present, allow the pane to grow taller.
        any_extra = bool(result.images_png) or bool(result.html_blobs)
        if any_extra:
            self.setMaximumHeight(16777215)  # remove cap from page caller
        if result.stdout:
            self._append_text(result.stdout, color="#D4D4D4")
        if result.stderr:
            self._append_text(_strip_ansi(result.stderr), color="#F87171")
        if result.traceback:
            self._append_text("\n".join(_strip_ansi(t) for t in result.traceback), color="#F87171")
        if result.error_value and not result.traceback:
            self._append_text(f"{result.error_name}: {result.error_value}", color="#F87171")
        # text/plain (e.g. pandas repr) goes after stdout
        if result.text_plain and not result.html_blobs:
            for tp in result.text_plain:
                self._append_text(tp, color="#D4D4D4")

        if any_extra:
            for png in result.images_png:
                self._add_image(png)
            for html in result.html_blobs:
                self._add_html(html)
            self._extras_scroll.setVisible(True)

    # ------------------------------------------------------------------
    def _append_text(self, text: str, *, color: str) -> None:
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # Use HTML insertion for easy color, but escape lt/gt
        from html import escape

        html = f'<span style="color:{color}; white-space:pre-wrap">{escape(text)}</span><br>'
        cursor.insertHtml(html)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def _add_image(self, png_bytes: bytes) -> None:
        pix = QPixmap()
        pix.loadFromData(png_bytes, "PNG")
        if pix.isNull():
            return
        lbl = QLabel(self._extras_container)
        # Fit width without enlarging beyond original
        max_width = max(400, self._extras_container.width() - 20)
        if pix.width() > max_width:
            pix = pix.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pix)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._extras_layout.addWidget(lbl)

    def _add_html(self, html: str) -> None:
        browser = QTextBrowser(self._extras_container)
        browser.setHtml(html)
        browser.setOpenExternalLinks(True)
        browser.setMinimumHeight(120)
        self._extras_layout.addWidget(browser)
