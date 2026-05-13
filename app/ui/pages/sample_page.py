"""Sample page — sharp monochrome layout with VSCode-style code block.

Supports two runners controlled by ``SamplePage.runner``:

- ``kernel`` (default): emits ``run_requested`` so the chapter view executes
  the snippet in the in-app Jupyter kernel and renders the output inline.
- ``streamlit``: writes the snippet to a temp file, spawns
  ``python -m streamlit run …``, and opens the default browser. Used by
  chapter 25 to show a real Streamlit dashboard.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal
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
    ACCENT,
    INK,
    INK_3,
)
from ..code_view import CodeBlock
from ..output_pane import OutputPane


class StreamlitLauncher:
    """Process-wide singleton that tracks the running Streamlit subprocess.

    Streamlit binds to a fixed port (8501 by default). Launching twice on the
    same port produces an error, so we always terminate the previous run
    before starting a new one. The launcher is also shutdown by the main
    window's ``closeEvent`` so the subprocess never outlives the app.
    """

    PORT = 8501
    URL = f"http://localhost:{PORT}"
    _proc: subprocess.Popen | None = None
    _tmpdir: Path | None = None

    @classmethod
    def available(cls) -> bool:
        """Streamlit is importable in the current environment."""
        try:
            import streamlit  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def launch(cls, code: str) -> tuple[bool, str]:
        """Write ``code`` to a temp file, spawn streamlit, open browser.

        Returns ``(success, message)``. ``message`` is human-readable status
        for the OutputPane.
        """
        if not cls.available():
            return False, (
                "streamlit が未インストールです。"
                "次のコマンドでインストールしてください:\n"
                "  uv sync"
            )

        cls.terminate()  # always kill the previous run

        try:
            cls._tmpdir = Path(tempfile.mkdtemp(prefix="study_python_streamlit_"))
            app_py = cls._tmpdir / "app.py"
            app_py.write_text(code, encoding="utf-8")
        except OSError as e:
            return False, f"一時ファイルを作成できませんでした: {e}"

        try:
            cls._proc = subprocess.Popen(
                [
                    sys.executable, "-m", "streamlit", "run", str(app_py),
                    "--server.headless=true",
                    f"--server.port={cls.PORT}",
                    "--browser.gatherUsageStats=false",
                ],
                cwd=str(cls._tmpdir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if os.name == "nt" else 0
                ),
            )
        except FileNotFoundError as e:
            return False, f"streamlit を起動できませんでした: {e}"

        # Streamlit needs a couple of seconds to boot before the browser can
        # connect — open the URL after a short delay so the user lands on a
        # rendered page rather than a connection-refused error.
        QTimer.singleShot(2200, lambda: webbrowser.open(cls.URL))
        return True, (
            f"Streamlit を起動しました → {cls.URL}\n"
            "ブラウザが自動で開きます。コードを書き換えるには「Launch Streamlit」を"
            "もう一度押してください（前回のサーバーは停止されます）。"
        )

    @classmethod
    def terminate(cls) -> None:
        """Kill the subprocess if it's still running. Idempotent."""
        if cls._proc is not None and cls._proc.poll() is None:
            try:
                cls._proc.terminate()
                cls._proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    cls._proc.kill()
                except OSError:
                    pass
        cls._proc = None
        if cls._tmpdir is not None and cls._tmpdir.exists():
            shutil.rmtree(cls._tmpdir, ignore_errors=True)
        cls._tmpdir = None


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
            file_label = (
                "app.py" if page.runner == "streamlit"
                else f"sample_{(page.title[:20]).replace(' ', '_').lower() or 'code'}.py"
            )
            self._code_block = CodeBlock(
                page.sample_code,
                file_label=file_label,
                runnable=page.runnable,
            )
            self._code_block.set_max_height(220 if page.runner == "streamlit" else 160)
            if page.runnable:
                if page.runner == "streamlit":
                    # Re-label the Run button and route the click to our local
                    # Streamlit launcher rather than the kernel pipeline.
                    if self._code_block._run_btn is not None:
                        self._code_block._run_btn.setText("Launch Streamlit")
                        self._code_block._run_btn.setMinimumWidth(140)
                    self._code_block.run_clicked.connect(self._on_streamlit_launch)
                else:
                    self._code_block.run_clicked.connect(self.run_requested.emit)
            layout.addWidget(self._code_block)

            if page.runnable:
                self._output = OutputPane(inner)
                self._output.setMinimumHeight(60)
                self._output.setMaximumHeight(180)
                layout.addWidget(self._output, 1)

                # For Streamlit pages, pre-fill an informational banner so the
                # user knows what to expect before clicking Launch.
                if page.runner == "streamlit":
                    hint = QLabel(
                        "「Launch Streamlit」を押すと、別ターミナルで "
                        f"<code>streamlit run</code> が起動し、ブラウザが "
                        f"<a href='{StreamlitLauncher.URL}'>{StreamlitLauncher.URL}</a> "
                        "を自動で開きます。",
                        inner,
                    )
                    hint.setOpenExternalLinks(True)
                    hint.setWordWrap(True)
                    hint.setStyleSheet(
                        f"QLabel {{ color: {INK}; background: #141414;"
                        f" border-left: 3px solid {ACCENT}; padding: 8px 12px;"
                        f" font-size: 12px; }}"
                    )
                    layout.addWidget(hint)
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

    @property
    def is_streamlit(self) -> bool:
        return self.page.runner == "streamlit"

    # ------------------------------------------------------------------
    def _on_streamlit_launch(self) -> None:
        """Spawn `streamlit run` and report status in the output pane."""
        ok, msg = StreamlitLauncher.launch(self.page.sample_code)
        from ...kernel.manager import ExecutionResult
        result = ExecutionResult(
            status="ok" if ok else "error",
            stdout=msg if ok else "",
            stderr="" if ok else msg,
        )
        self._output.render(result)
