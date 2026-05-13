"""Standalone test view (実力テスト) — sharp monochrome layout."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from ..content.test_schemas import TestSet
from ..db.repo import Repository
from ..grading.judge import grade_exercise
from ..kernel.manager import KernelSession
from ..resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
    PHASE_LABELS,
    SUCCESS,
)
from .pages.exercise_page import ExercisePageWidget
from .stickman import StickmanStrip


class TestView(QWidget):
    back_to_launcher = pyqtSignal()

    def __init__(
        self,
        test_set: TestSet,
        repo: Repository,
        user_id: int,
        kernel: KernelSession,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.test_set = test_set
        self.repo = repo
        self.user_id = user_id
        self.kernel = kernel
        self._results = []
        self._started_at: datetime | None = None
        self._seconds_remaining = test_set.time_limit_minutes * 60

        # Header
        header = QFrame(self)
        header.setStyleSheet(f"QFrame {{ background: white; border-bottom: 1px solid {LINE}; }}")
        head_layout = QHBoxLayout(header)
        head_layout.setContentsMargins(24, 14, 24, 14)
        head_layout.setSpacing(20)

        back_btn = QPushButton("← ホーム", header)
        back_btn.setProperty("variant", "ghost")
        back_btn.clicked.connect(self.back_to_launcher.emit)
        head_layout.addWidget(back_btn)

        phase_lbl = QLabel(PHASE_LABELS[test_set.phase] + " · Test", header)
        phase_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        head_layout.addWidget(phase_lbl)

        title_lbl = QLabel(test_set.title, header)
        title_lbl.setStyleSheet(f"color: {INK}; font-size: 14px; font-weight: 700;")
        head_layout.addWidget(title_lbl, 1)

        self._timer_lbl = QLabel("--:--", header)
        self._timer_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 14px; font-weight: 800;"
            f" letter-spacing: 0; font-family: 'Consolas', monospace;"
        )
        head_layout.addWidget(self._timer_lbl)

        self._q_counter = QLabel("", header)
        self._q_counter.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        head_layout.addWidget(self._q_counter)

        # Body stack
        self._stack = QStackedLayout()
        body = QWidget(self)
        body.setLayout(self._stack)
        self._splash = self._build_splash()
        self._stack.addWidget(self._splash)
        self._question_widget: QWidget | None = None
        self._summary_widget: QWidget | None = None
        self._current_q = 0

        # Footer with Skip / Submit / Next buttons. Skip and Submit are shown
        # before answering; Next replaces them after the answer is graded.
        footer = QFrame(self)
        footer.setStyleSheet(f"QFrame {{ background: white; border-top: 1px solid {LINE}; }}")
        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(32, 10, 32, 10)
        foot_layout.setSpacing(8)

        self._skip_btn = QPushButton("Skip", footer)
        self._skip_btn.setProperty("variant", "secondary")
        self._skip_btn.clicked.connect(self._on_skip)
        foot_layout.addWidget(self._skip_btn)

        foot_layout.addStretch(1)

        self._submit_btn = QPushButton("Submit", footer)
        self._submit_btn.clicked.connect(self._on_submit_question)
        foot_layout.addWidget(self._submit_btn)

        self._next_btn = QPushButton("Next Question", footer)
        self._next_btn.clicked.connect(self._on_next)
        self._next_btn.hide()
        foot_layout.addWidget(self._next_btn)

        self._footer = footer

        # Inline stickman strip
        self._stickman = StickmanStrip(self)
        self._stickman.set_mood("explain")
        self._stickman.set_speech("リラックスして取り組もう。")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(body, 1)
        root.addWidget(self._stickman)
        root.addWidget(footer)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    def _build_splash(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(80, 56, 80, 60)
        layout.setSpacing(16)

        kicker = QLabel("実力テスト", inner)
        kicker.setObjectName("kicker")
        layout.addWidget(kicker)

        title = QLabel(self.test_set.title, inner)
        title.setStyleSheet(
            f"color: {INK}; font-size: 32px; font-weight: 800; letter-spacing: -1px;"
        )
        layout.addWidget(title)

        rule = QFrame(inner)
        rule.setStyleSheet(f"background: {ACCENT};")
        rule.setFixedHeight(2)
        rule.setMaximumWidth(60)
        layout.addWidget(rule)
        layout.addSpacing(4)

        if self.test_set.description:
            desc = QLabel(self.test_set.description, inner)
            desc.setStyleSheet(f"color: {INK_3}; font-size: 13px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        layout.addSpacing(20)

        # Stats row — plain numbers, no card box
        stats_row = QHBoxLayout()
        stats_row.setSpacing(64)
        for label, val in [
            ("Questions", str(len(self.test_set.questions))),
            ("Time Limit", f"{self.test_set.time_limit_minutes} min"),
            ("Pass Score", f"{int(self.test_set.pass_score * 100)}%"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            v = QLabel(val, inner)
            v.setStyleSheet(
                f"color: {INK}; font-size: 32px; font-weight: 800; letter-spacing: -1px;"
            )
            col.addWidget(v)
            l = QLabel(label, inner)
            l.setStyleSheet(
                f"color: {INK_3}; font-size: 10px; font-weight: 700; letter-spacing: 0;"
            )
            col.addWidget(l)
            stats_row.addLayout(col)
        stats_row.addStretch(1)
        layout.addLayout(stats_row)
        layout.addSpacing(28)

        notice = QLabel(
            "・各問題は穴埋め形式。提出ボタンを押すと即座に採点されます。\n"
            "・制限時間を超えると自動で集計されます。\n"
            "・中断はホームボタンから可能（成績は記録されません）。",
            inner,
        )
        notice.setStyleSheet(f"color: {INK_3}; font-size: 12px;")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        layout.addSpacing(16)

        start_btn = QPushButton("Start Test", inner)
        start_btn.setMinimumHeight(48)
        start_btn.clicked.connect(self._start_test)
        btn_row = QHBoxLayout()
        btn_row.addWidget(start_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    # ------------------------------------------------------------------
    def _start_test(self) -> None:
        self._started_at = datetime.now(UTC).replace(tzinfo=None)
        self._current_q = 0
        self._results.clear()
        self._timer.start(1000)
        self._show_question()

    def _show_question(self) -> None:
        if self._question_widget is not None:
            self._stack.removeWidget(self._question_widget)
            self._question_widget.deleteLater()
            self._question_widget = None

        q = self.test_set.questions[self._current_q]
        # Hide the Solution button in test mode — the test is a single-shot
        # measurement, and revealing solutions defeats the point.
        widget = ExercisePageWidget(q, show_solution_button=False)
        widget.submit_requested.connect(self._on_submit_question)
        self._question_widget = widget
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)
        self._q_counter.setText(
            f"Q{self._current_q + 1:02d} / {len(self.test_set.questions):02d}"
        )
        # Pre-submit state: Skip + Submit visible, Next hidden.
        self._footer.setVisible(True)
        self._skip_btn.show()
        self._skip_btn.setEnabled(True)
        self._submit_btn.show()
        self._submit_btn.setEnabled(True)
        self._next_btn.hide()
        # Update Next button label for the last question
        if self._current_q + 1 >= len(self.test_set.questions):
            self._next_btn.setText("Finish Test")
        else:
            self._next_btn.setText("Next Question")
        self._stickman.set_mood("explain")
        self._stickman.set_speech(f"問題 {self._current_q + 1} に挑戦。")

    def _on_submit_question(self) -> None:
        if not isinstance(self._question_widget, ExercisePageWidget):
            return
        q = self.test_set.questions[self._current_q]
        values = self._question_widget.collect_values()
        gr = grade_exercise(q, values, self.kernel)
        self._results.append((gr, values))

        self._question_widget.mark_results(gr.failed_blanks)
        if gr.overall_passed:
            self._stickman.set_mood("happy")
            self._stickman.set_speech("正解。次の問題へ。")
        else:
            self._stickman.set_mood("sad")
            self._stickman.set_speech("不正解。次の問題に進めるよ。")

        self.kernel.restart()
        self._switch_to_post_submit()

    def _on_skip(self) -> None:
        """Record the current question as failed without grading."""
        if not isinstance(self._question_widget, ExercisePageWidget):
            return
        from ..grading.judge import GradingResult, TestCaseResult
        q = self.test_set.questions[self._current_q]
        values = self._question_widget.collect_values()
        # Build a minimal failed GradingResult (skipped).
        gr = GradingResult(
            overall_passed=False,
            form_results=[],
            test_results=[TestCaseResult(kind="skipped", passed=False, detail="skipped by user")],
            assembled_code="",
            execution=None,
            failed_blanks=[],
        )
        self._results.append((gr, values))
        self._stickman.set_mood("explain")
        self._stickman.set_speech("スキップ。次の問題へ。")
        self._switch_to_post_submit()

    def _switch_to_post_submit(self) -> None:
        """Hide Submit/Skip, reveal Next."""
        self._skip_btn.hide()
        self._submit_btn.hide()
        self._next_btn.show()
        self._next_btn.setEnabled(True)
        self._footer.setVisible(True)

    def _on_next(self) -> None:
        if self._current_q + 1 < len(self.test_set.questions):
            self._current_q += 1
            self._show_question()
        else:
            self._finish_test(elapsed_zero=False)

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        self._seconds_remaining -= 1
        m, s = divmod(max(self._seconds_remaining, 0), 60)
        self._timer_lbl.setText(f"{m:02d}:{s:02d}")
        if self._seconds_remaining <= 0:
            self._timer.stop()
            self._finish_test(elapsed_zero=True)

    # ------------------------------------------------------------------
    def _finish_test(self, *, elapsed_zero: bool) -> None:
        self._timer.stop()
        finished_at = datetime.now(UTC).replace(tzinfo=None)
        score = sum(1 for gr, _ in self._results if gr.overall_passed)
        total = len(self.test_set.questions)
        duration = int((finished_at - (self._started_at or finished_at)).total_seconds())

        per_q: list[dict[str, Any]] = []
        for i, (gr, vals) in enumerate(self._results):
            q = self.test_set.questions[i]
            per_q.append({
                "question_id": f"q{i + 1}",
                "title": q.title,
                "passed": gr.overall_passed,
                "submitted": vals,
                "assembled": gr.assembled_code,
                "stdout": gr.execution.stdout if gr.execution else "",
            })

        self.repo.record_test_result(
            self.user_id,
            test_id=self.test_set.id,
            score=score,
            total=total,
            duration_sec=duration,
            per_question_json=json.dumps(per_q, ensure_ascii=False),
            started_at=self._started_at or finished_at,
            finished_at=finished_at,
        )
        self._show_summary(score, total, duration, elapsed_zero=elapsed_zero, per_q=per_q)

    def _show_summary(
        self,
        score: int,
        total: int,
        duration: int,
        *,
        elapsed_zero: bool,
        per_q: list[dict[str, Any]],
    ) -> None:
        if self._question_widget is not None:
            self._stack.removeWidget(self._question_widget)
            self._question_widget.deleteLater()
            self._question_widget = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(80, 56, 80, 60)
        layout.setSpacing(16)

        kicker = QLabel("Result", inner)
        kicker.setObjectName("kicker")
        layout.addWidget(kicker)

        passed = (score / total) >= self.test_set.pass_score
        verdict = QLabel(f"{score} / {total}", inner)
        verdict.setStyleSheet(
            f"color: {SUCCESS if passed else ACCENT};"
            f" font-size: 56px; font-weight: 800; letter-spacing: -2px;"
        )
        layout.addWidget(verdict)

        rule = QFrame(inner)
        rule.setStyleSheet(f"background: {SUCCESS if passed else ACCENT};")
        rule.setFixedHeight(2)
        rule.setMaximumWidth(80)
        layout.addWidget(rule)
        layout.addSpacing(4)

        sub_text = ("Passed" if passed else "Failed") + f"   ·   所要時間 {duration // 60}分{duration % 60}秒"
        sub = QLabel(sub_text, inner)
        sub.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        layout.addWidget(sub)

        if elapsed_zero:
            warn = QLabel("制限時間を超えたため自動で集計しました。", inner)
            warn.setStyleSheet(f"color: {ACCENT}; font-size: 12px;")
            layout.addWidget(warn)
        layout.addSpacing(20)

        layout.addWidget(self._kicker_label("Breakdown"))
        breakdown = QFrame(inner)
        breakdown.setStyleSheet(f"QFrame {{ background: white; border: 1px solid {LINE}; }}")
        bl = QVBoxLayout(breakdown)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(6)
        for i, q_res in enumerate(per_q):
            mark = "Pass" if q_res["passed"] else "Fail"
            color = SUCCESS if q_res["passed"] else ACCENT
            row = QLabel(
                f'<span style="color:{color}; font-weight:800; letter-spacing: 0">{mark}</span>'
                f'  <span style="color:{INK_3}">Q{i + 1:02d}</span>'
                f'  <span style="color:{INK}">{q_res["title"]}</span>',
                breakdown,
            )
            bl.addWidget(row)
        layout.addWidget(breakdown)
        layout.addSpacing(16)

        btn_row = QHBoxLayout()
        home_btn = QPushButton("ホームに戻る", inner)
        home_btn.clicked.connect(self.back_to_launcher.emit)
        btn_row.addWidget(home_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)
        scroll.setWidget(inner)

        self._summary_widget = scroll
        self._stack.addWidget(scroll)
        self._stack.setCurrentWidget(scroll)
        self._footer.setVisible(False)

        self._stickman.set_mood("happy" if passed else "explain")
        self._stickman.set_speech(
            "合格おめでとう。次の Phase へ進もう。" if passed else "苦手な章を復習して再挑戦してね。"
        )

    def _kicker_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet(
            f"color: {INK_3}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 0; margin-top: 6px;"
        )
        return lbl
