"""Chapter view — sharp monochrome layout."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from ..content.loader import assemble_code
from ..content.schemas import Chapter, ExercisePage, SamplePage
from ..db.models import ChapterStatus
from ..db.repo import Repository
from ..grading.judge import GradingResult, grade_exercise
from ..kernel.manager import KernelSession
from ..llm.claude_client import ClaudeClient
from ..resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
    PHASE_LABELS,
)
from .pages.exercise_page import ExercisePageWidget
from .pages.result_page import ResultPageWidget
from .pages.sample_page import SamplePageWidget
from .stickman import StickmanStrip


def _phase_label(phase: str) -> str:
    """Return Title Case phase label (e.g. 'A' -> 'Phase A')."""
    return f"Phase {phase}"


class ChapterView(QWidget):
    back_to_launcher = pyqtSignal()

    def __init__(
        self,
        chapter: Chapter,
        repo: Repository,
        user_id: int,
        kernel: KernelSession,
        start_page_index: int = 0,
        llm: ClaudeClient | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chapter = chapter
        self.repo = repo
        self.user_id = user_id
        self.kernel = kernel
        self.llm = llm

        # Single combined header row — left-aligned wordmark + breadcrumb,
        # right-aligned page counter + back button. Sharper, no centered text.
        header = QFrame(self)
        header.setObjectName("chapterHeader")
        header.setFixedHeight(52)
        header.setStyleSheet(
            f"#chapterHeader {{ background: white; border-bottom: 1px solid {LINE}; }}"
        )
        head_layout = QHBoxLayout(header)
        head_layout.setContentsMargins(32, 0, 32, 0)
        head_layout.setSpacing(16)

        # Wordmark (left)
        wordmark = QLabel(header)
        wordmark.setText(
            f'<span style="color:{INK}; font-weight:800; letter-spacing:-0.3px;">STUDY</span>'
            f'<span style="color:{ACCENT}; font-weight:800;">.</span>'
            f'<span style="color:{INK}; font-weight:800; letter-spacing:-0.3px;">PY</span>'
        )
        wordmark.setStyleSheet("font-size: 14px;")
        head_layout.addWidget(wordmark)

        # Strong vertical separator between wordmark and breadcrumb
        sep_a = QFrame(header)
        sep_a.setStyleSheet(f"background: {LINE};")
        sep_a.setFixedSize(1, 28)
        head_layout.addWidget(sep_a)

        phase_lbl = QLabel(_phase_label(chapter.phase), header)
        phase_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        head_layout.addWidget(phase_lbl)

        # Visible separator between PHASE and CH
        sep_b = QFrame(header)
        sep_b.setStyleSheet(f"background: {LINE};")
        sep_b.setFixedSize(1, 18)
        head_layout.addWidget(sep_b)

        ch_num = QLabel(f"Ch {chapter.id:02d}", header)
        ch_num.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        head_layout.addWidget(ch_num)

        # Visible separator between CH and TITLE
        sep_c = QFrame(header)
        sep_c.setStyleSheet(f"background: {LINE};")
        sep_c.setFixedSize(1, 18)
        head_layout.addWidget(sep_c)

        title_lbl = QLabel(chapter.title, header)
        title_lbl.setStyleSheet(
            f"color: {INK}; font-size: 14px; font-weight: 700; letter-spacing: -0.1px;"
        )
        head_layout.addWidget(title_lbl, 1)

        # Separator before page counter
        sep_d = QFrame(header)
        sep_d.setStyleSheet(f"background: {LINE};")
        sep_d.setFixedSize(1, 18)
        head_layout.addWidget(sep_d)

        # Right side: page counter + back
        self._page_count_lbl = QLabel("", header)
        self._page_count_lbl.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
            f" font-family: 'Cascadia Mono', 'Consolas', monospace;"
        )
        head_layout.addWidget(self._page_count_lbl)

        self._back_btn = QPushButton("Close", header)
        self._back_btn.setProperty("variant", "secondary")
        self._back_btn.setStyleSheet(
            "QPushButton { padding: 5px 14px; font-size: 11px; min-width: 64px; }"
        )
        self._back_btn.clicked.connect(self.back_to_launcher.emit)
        head_layout.addWidget(self._back_btn)

        # Thin progress
        self._progress = QProgressBar(self)
        self._progress.setRange(0, len(chapter.pages))
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(2)

        # Body slot
        self._slot_container = QWidget(self)
        self._slot_container.setStyleSheet("background: white;")
        self._slot_layout = QStackedLayout(self._slot_container)
        self._slot_layout.setContentsMargins(0, 0, 0, 0)

        # Footer
        self._footer = QFrame(self)
        self._footer.setStyleSheet(f"QFrame {{ background: white; border-top: 1px solid {LINE}; }}")
        foot_layout = QHBoxLayout(self._footer)
        foot_layout.setContentsMargins(32, 10, 32, 10)
        self._prev_btn = QPushButton("Back", self._footer)
        self._prev_btn.setProperty("variant", "secondary")
        self._prev_btn.clicked.connect(self._go_prev)
        foot_layout.addWidget(self._prev_btn)
        foot_layout.addStretch(1)
        self._next_btn = QPushButton("Next", self._footer)
        self._next_btn.clicked.connect(self._on_next_clicked)
        foot_layout.addWidget(self._next_btn)

        # Inline stickman strip (above footer, never overlaps content)
        self._stickman = StickmanStrip(self)

        # Root
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(self._progress)
        root.addWidget(self._slot_container, 1)
        root.addWidget(self._stickman)
        root.addWidget(self._footer)

        # Pre-build page widgets
        self._page_widgets: list[QWidget] = []
        for p in chapter.pages:
            if isinstance(p, SamplePage):
                w = SamplePageWidget(p)
                w.run_requested.connect(self._on_sample_run)
            elif isinstance(p, ExercisePage):
                w = ExercisePageWidget(p)
                w.submit_requested.connect(self._on_submit)
                w.show_solution_requested.connect(self._on_show_solution)
            else:
                w = QLabel(f"unknown page kind: {type(p).__name__}")
            self._page_widgets.append(w)

        # Inline stickman strip (created above; reference for set_mood/set_speech)
        # NB: actually instantiated below via _create_stickman_strip and inserted
        # into the root layout above the footer.

        self._current_index = max(0, min(start_page_index, len(chapter.pages) - 1))
        self._result_overlay: ResultPageWidget | None = None
        self._show_current_page()
        self._save_progress()

    # ------------------------------------------------------------------
    def _swap_slot(self, widget: QWidget) -> None:
        while self._slot_layout.count():
            w = self._slot_layout.widget(0)
            self._slot_layout.removeWidget(w)
            w.setParent(None)
        self._slot_layout.addWidget(widget)
        self._slot_layout.setCurrentWidget(widget)

    def _current_page_model(self):
        return self.chapter.pages[self._current_index]

    def _show_current_page(self) -> None:
        if self._result_overlay is not None:
            self._result_overlay.deleteLater()
            self._result_overlay = None
        widget = self._page_widgets[self._current_index]
        self._swap_slot(widget)
        # Restore the footer (it gets hidden while a result overlay is showing).
        self._footer.setVisible(True)
        self._progress.setValue(self._current_index + 1)
        self._page_count_lbl.setText(
            f"{self._current_index + 1:02d} / {len(self.chapter.pages):02d}"
        )

        page = self._current_page_model()
        if isinstance(page, SamplePage):
            self._stickman.set_mood(page.stickman)
            self._stickman.set_speech(page.stickman_speech)
            self._next_btn.setText("Next")
            self._next_btn.setEnabled(True)
        elif isinstance(page, ExercisePage):
            self._stickman.set_mood("explain")
            self._stickman.set_speech("コードの空欄を埋めて提出ボタンを押そう。")
            # On exercise pages, the footer button SUBMITS the answer.
            self._next_btn.setText("Submit")
            self._next_btn.setEnabled(True)
        self._prev_btn.setEnabled(self._current_index > 0)

    def _save_progress(self, *, completed: bool = False) -> None:
        self.repo.upsert_progress(
            user_id=self.user_id,
            chapter_id=self.chapter.id,
            last_page_index=self._current_index,
            status=ChapterStatus.completed if completed else ChapterStatus.in_progress,
        )

    # ------------------------------------------------------------------
    def _on_sample_run(self) -> None:
        widget = self._page_widgets[self._current_index]
        if not isinstance(widget, SamplePageWidget):
            return
        result = self.kernel.execute(widget.code, timeout=15)
        widget.output_pane.render(result)
        if result.status == "ok":
            self._stickman.set_mood("happy")
            self._stickman.set_speech("実行できたね。次へ進もう。")
        else:
            self._stickman.set_mood("sad")
            self._stickman.set_speech("エラーが出たみたい。出力を確認しよう。")

    # ------------------------------------------------------------------
    def _on_submit(self) -> None:
        idx = self._current_index
        widget = self._page_widgets[idx]
        if not isinstance(widget, ExercisePageWidget):
            return
        page = widget.page
        values = widget.collect_values()

        gr = grade_exercise(page, values, self.kernel)
        self.repo.record_submission(
            user_id=self.user_id,
            chapter_id=self.chapter.id,
            page_index=idx,
            code=gr.assembled_code,
            passed=gr.overall_passed,
            stdout=gr.execution.stdout if gr.execution else "",
            stderr=gr.execution.stderr if gr.execution else "",
            hint_level_shown=0,
        )

        widget.mark_results(gr.failed_blanks)
        if not gr.overall_passed:
            attempts = widget.register_wrong_attempt()
            stickman_wrong = self._pick_wrong_speech(page, attempts)
            self._stickman.set_mood("sad")
            self._stickman.set_speech(stickman_wrong)
        else:
            self._stickman.set_mood("happy")
            self._stickman.set_speech(page.stickman_feedback.correct)
            stickman_wrong = page.stickman_feedback.wrong_hint1

        self._show_result_overlay(gr, page, stickman_wrong)

    def _show_result_overlay(
        self, gr: GradingResult, page: ExercisePage, stickman_wrong: str
    ) -> None:
        self._result_overlay = ResultPageWidget(
            gr,
            stickman_speech_correct=page.stickman_feedback.correct,
            stickman_speech_wrong=stickman_wrong,
            chapter=self.chapter,
            page=page,
            llm=self.llm,
        )
        self._result_overlay.next_requested.connect(self._advance)
        self._result_overlay.retry_requested.connect(self._retry_current)
        self._swap_slot(self._result_overlay)
        # The result page provides its own Next / Retry buttons — hide the
        # chapter-level footer so the user isn't confused by two CTAs.
        self._footer.setVisible(False)

    def _pick_wrong_speech(self, page: ExercisePage, attempts: int) -> str:
        fb = page.stickman_feedback
        if attempts >= 3:
            return fb.wrong_hint3
        if attempts == 2:
            return fb.wrong_hint2
        return fb.wrong_hint1

    def _retry_current(self) -> None:
        widget = self._page_widgets[self._current_index]
        if isinstance(widget, ExercisePageWidget):
            widget.reset_for_retry()
        self._show_current_page()
        self._stickman.set_mood("explain")
        self._stickman.set_speech("もう一度トライ。")

    def _on_show_solution(self) -> None:
        page = self._current_page_model()
        if not isinstance(page, ExercisePage):
            return
        canonical = {b.id: b.canonical_answer for b in page.blanks}
        full = assemble_code(page.code_template, canonical)
        QMessageBox.information(self, "模範解答", full)

    # ------------------------------------------------------------------
    def _on_next_clicked(self) -> None:
        page = self._current_page_model()
        if isinstance(page, ExercisePage):
            # Footer "SUBMIT" delegates to the exercise page submit handler.
            self._on_submit()
            return
        self._advance()

    def _go_prev(self) -> None:
        if self._current_index <= 0:
            return
        self._current_index -= 1
        self._show_current_page()
        self._save_progress()

    def _advance(self) -> None:
        if self._current_index + 1 >= len(self.chapter.pages):
            self._save_progress(completed=True)
            QMessageBox.information(
                self,
                "章クリア",
                f"第 {self.chapter.id:02d} 章「{self.chapter.title}」をクリアしました。",
            )
            self.back_to_launcher.emit()
            return
        self._current_index += 1
        self._show_current_page()
        self._save_progress()
