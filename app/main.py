"""Application entrypoint.

Wires together the launcher, the chapter view, the kernel session and the SQLite
repository. The MainWindow swaps between two top-level widgets — Launcher and
ChapterView — using a QStackedLayout.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStackedLayout,
    QStatusBar,
    QWidget,
)

from .content.loader import ContentError, load_chapters
from .content.test_schemas import load_test_sets
from .db.repo import Repository
from .kernel.manager import KernelSession
from .llm.claude_client import ClaudeClient
from .resources.theme import GLOBAL_STYLESHEET
from .ui.chapter_view import ChapterView
from .ui.history_view import HistoryView
from .ui.launcher import LauncherScreen
from .ui.test_view import TestView

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content" / "chapters"
TESTS_DIR = PROJECT_ROOT / "content" / "tests"
DB_PATH = PROJECT_ROOT / "progress.db"
LOG_DIR = PROJECT_ROOT / "logs"


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def _load_bundled_fonts() -> list[str]:
    """Register all .ttf / .otf files under app/resources/fonts/ with Qt.

    Returns the list of families that were successfully loaded. The QSS in
    ``theme.py`` references these families by name (Inter, JetBrains Mono,
    etc.); when the font isn't bundled the stack silently falls back to the
    OS default — no error.
    """
    fonts_dir = PROJECT_ROOT / "app" / "resources" / "fonts"
    if not fonts_dir.exists():
        return []
    loaded: list[str] = []
    for path in fonts_dir.iterdir():
        if path.suffix.lower() not in (".ttf", ".otf"):
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            logging.warning("could not load font: %s", path.name)
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        loaded.extend(families)
        logging.info("loaded font %s → %s", path.name, families)
    return loaded


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Study Python Finance")
        self.setMinimumSize(1100, 760)

        # Best-effort: load .env so ANTHROPIC_API_KEY is picked up if user set it.
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
        except ImportError:
            pass

        self.repo = Repository(DB_PATH)
        self.user = self.repo.get_or_create_default_user()
        self.kernel = KernelSession()
        self.llm = ClaudeClient()

        # Load chapters
        try:
            self.chapters = load_chapters(CONTENT_DIR)
        except ContentError as e:
            QMessageBox.critical(self, "章ファイルの読み込みに失敗しました", str(e))
            self.chapters = []

        # Load tests
        try:
            self.test_sets = load_test_sets(TESTS_DIR)
        except Exception as e:  # noqa: BLE001
            logging.exception("test set load failed")
            QMessageBox.warning(self, "テスト読み込みエラー", str(e))
            self.test_sets = {}

        if not self.chapters:
            QMessageBox.warning(
                self,
                "章がありません",
                f"{CONTENT_DIR} に章ファイル(YAML)が見つかりません。",
            )

        # Central stacked widget
        central = QWidget(self)
        self._stack = QStackedLayout(central)
        self.setCentralWidget(central)

        self.launcher = LauncherScreen(self.chapters, self.repo, self.user.id, self)
        self.launcher.chapter_selected.connect(self._open_chapter)
        self.launcher.test_requested.connect(self._open_test)
        self.launcher.history_requested.connect(self._open_history)
        self._stack.addWidget(self.launcher)

        self._chapter_view: ChapterView | None = None
        self._test_view: TestView | None = None
        self._history_view: HistoryView | None = None

        # Status bar — kernel state indicator
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        sb.showMessage("カーネルを起動中...")

        # Start kernel asynchronously-ish (blocking but quick).
        try:
            self.kernel.start()
            sb.showMessage("カーネル: ready")
        except Exception as e:  # noqa: BLE001
            logging.exception("kernel start failed")
            QMessageBox.critical(
                self,
                "カーネル起動エラー",
                f"Jupyter kernel を起動できませんでした:\n{e}",
            )
            sb.showMessage("カーネル: 起動に失敗")

    # ------------------------------------------------------------------
    def _open_chapter(self, chapter_id: int, start_page_index: int) -> None:
        ch = next((c for c in self.chapters if c.id == chapter_id), None)
        if ch is None:
            QMessageBox.warning(self, "章が見つかりません", f"chapter id={chapter_id}")
            return
        # Restart the kernel so each chapter starts with a clean namespace.
        self.kernel.restart()
        self._chapter_view = ChapterView(
            ch,
            self.repo,
            self.user.id,
            self.kernel,
            start_page_index=start_page_index,
            llm=self.llm,
        )
        self._chapter_view.back_to_launcher.connect(self._return_to_launcher)
        self._stack.addWidget(self._chapter_view)
        self._stack.setCurrentWidget(self._chapter_view)

    def _open_test(self, test_id: str) -> None:
        ts = self.test_sets.get(test_id)
        if ts is None:
            QMessageBox.information(
                self,
                "テストが見つかりません",
                f"`{test_id}` のテストはまだ用意されていません。",
            )
            return
        self.kernel.restart()
        self._test_view = TestView(ts, self.repo, self.user.id, self.kernel)
        self._test_view.back_to_launcher.connect(self._return_to_launcher)
        self._stack.addWidget(self._test_view)
        self._stack.setCurrentWidget(self._test_view)

    def _open_history(self) -> None:
        self._history_view = HistoryView(self.repo, self.user.id)
        self._history_view.back_to_launcher.connect(self._return_to_launcher)
        self._stack.addWidget(self._history_view)
        self._stack.setCurrentWidget(self._history_view)

    def _return_to_launcher(self) -> None:
        for attr in ("_chapter_view", "_test_view", "_history_view"):
            v = getattr(self, attr, None)
            if v is not None:
                self._stack.removeWidget(v)
                v.deleteLater()
                setattr(self, attr, None)
        self.launcher.refresh()
        self._stack.setCurrentWidget(self.launcher)

    def closeEvent(self, e) -> None:  # noqa: N802
        try:
            self.kernel.shutdown()
        except Exception:  # noqa: BLE001
            logging.exception("kernel shutdown failed")
        # Make sure any Streamlit subprocess launched from chapter 25 dies
        # with the main app — otherwise it keeps listening on port 8501.
        try:
            from .ui.pages.sample_page import StreamlitLauncher
            StreamlitLauncher.terminate()
        except Exception:  # noqa: BLE001
            logging.exception("streamlit shutdown failed")
        super().closeEvent(e)


def main() -> int:
    _configure_logging()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    # Load any bundled fonts (Inter / Geist / JetBrains Mono / Noto Sans JP)
    # before the stylesheet is applied so QSS font-family lookups resolve.
    families = _load_bundled_fonts()
    if families:
        logging.info("bundled fonts active: %s", ", ".join(families))
    app.setStyleSheet(GLOBAL_STYLESHEET)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
