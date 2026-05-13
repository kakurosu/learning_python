"""Result page — sharp dark layout with motion on reveal."""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...content.schemas import Chapter, ExercisePage
from ...grading.judge import GradingResult
from ...llm.claude_client import ClaudeClient, HintRequest
from ...resources.theme import (
    ACCENT,
    INK,
    INK_3,
    LINE,
    SUCCESS,
)
from ..animated_button import AnimatedPushButton
from ..code_view import CodeBlock
from ..output_pane import OutputPane


class ResultPageWidget(QWidget):
    next_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(
        self,
        result: GradingResult,
        stickman_speech_correct: str,
        stickman_speech_wrong: str,
        chapter: Chapter | None = None,
        page: ExercisePage | None = None,
        llm: ClaudeClient | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.result = result
        self._chapter = chapter
        self._page = page
        self._llm = llm

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(36, 16, 36, 20)
        layout.setSpacing(0)

        # Verdict — game-show style large reveal.
        if result.overall_passed:
            verdict_text = "Correct"
            verdict_tag = "Clear"
            verdict_color = SUCCESS
        else:
            verdict_text = "Incorrect"
            verdict_tag = "Retry"
            verdict_color = ACCENT

        # Tag kicker
        tag_row = QHBoxLayout()
        tag_row.setContentsMargins(0, 0, 0, 0)
        tag = QLabel(verdict_tag, inner)
        tag.setStyleSheet(
            f"color: {verdict_color}; background: transparent;"
            f" font-size: 11px; font-weight: 700; letter-spacing: 0;"
        )
        tag_row.addWidget(tag)
        tag_row.addStretch(1)
        layout.addLayout(tag_row)
        layout.addSpacing(10)

        # Top accent rule (game-show style stripe)
        top_rule = QFrame(inner)
        top_rule.setStyleSheet(f"background: {verdict_color};")
        top_rule.setFixedHeight(3)
        layout.addWidget(top_rule)
        layout.addSpacing(18)

        # MASSIVE verdict word — fades + slides in for drama.
        verdict = QLabel(verdict_text, inner)
        verdict.setStyleSheet(
            f"color: {verdict_color}; background: transparent;"
            f" font-size: 72px; font-weight: 900; letter-spacing: -3px;"
        )
        layout.addWidget(verdict)
        layout.addSpacing(2)
        self._verdict_label = verdict
        # Hold animation references so they don't get GC'd before completing.
        self._anims: list[QPropertyAnimation] = []

        # Bottom heavy rule
        bottom_rule = QFrame(inner)
        bottom_rule.setStyleSheet(f"background: {INK};")
        bottom_rule.setFixedHeight(2)
        layout.addWidget(bottom_rule)
        layout.addSpacing(16)

        # Speech echo
        speech = stickman_speech_correct if result.overall_passed else stickman_speech_wrong
        feedback = QLabel(speech, inner)
        feedback.setWordWrap(True)
        feedback.setStyleSheet(
            f"color: {INK}; background: transparent;"
            f" font-size: 14px; padding: 4px 0 12px 0;"
        )
        layout.addWidget(feedback)

        layout.addWidget(self._kicker_label("Submitted Code"))
        code_block = CodeBlock(result.assembled_code, file_label="submitted.py", runnable=False)
        code_block.set_max_height(220)
        layout.addWidget(code_block)

        # Only show Output when there's something to display (stdout / stderr /
        # an error / a chart). Empty output panes look like mystery red boxes.
        has_output = (
            result.execution is not None
            and (
                result.execution.stdout
                or result.execution.stderr
                or result.execution.traceback
                or result.execution.error_value
                or result.execution.images_png
                or result.execution.html_blobs
            )
        )
        if has_output:
            layout.addWidget(self._kicker_label("Output"))
            out = OutputPane(inner)
            out.setMinimumHeight(80)
            out.render(result.execution)
            layout.addWidget(out, 1)

        # Internal grading detail is helpful only on Incorrect results — when the
        # student needs to know *why* it failed. On Correct, hide it: the user
        # already sees CORRECT + their code + their output and that's enough.
        if not result.overall_passed and result.test_results:
            layout.addWidget(self._kicker_label("What failed"))
            details_frame = QFrame(inner)
            details_frame.setStyleSheet(
                f"QFrame {{ background: #141414; border: 1px solid {LINE}; }}"
            )
            dl = QVBoxLayout(details_frame)
            dl.setContentsMargins(14, 10, 14, 10)
            dl.setSpacing(4)
            for tr in result.test_results:
                if tr.passed:
                    continue
                lbl = QLabel(
                    f'<span style="color:{ACCENT}; font-weight:700">×</span> {tr.detail}',
                    details_frame,
                )
                dl.addWidget(lbl)
            layout.addWidget(details_frame)

        # LLM "more details" button — only when API is configured
        if self._llm is not None and self._llm.available and self._chapter and self._page:
            llm_row = QHBoxLayout()
            llm_row.setSpacing(8)
            self._llm_btn = QPushButton("Ask AI", inner)
            self._llm_btn.setProperty("variant", "secondary")
            self._llm_btn.clicked.connect(self._on_llm_clicked)
            llm_row.addWidget(self._llm_btn)
            llm_row.addStretch(1)
            layout.addLayout(llm_row)

            self._llm_response = QLabel("", inner)
            self._llm_response.setWordWrap(True)
            self._llm_response.setStyleSheet(
                f"QLabel {{ color: {INK}; background: #141414;"
                f" border-left: 3px solid {ACCENT}; padding: 12px 16px; font-size: 13px; }}"
            )
            self._llm_response.setVisible(False)
            layout.addWidget(self._llm_response)

        # Action buttons — AnimatedPushButton drives smooth color fades on
        # hover / press, which the global QSS alone cannot do (QSS state
        # changes in Qt are instant). Sizing / sharp corners are kept.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if result.overall_passed:
            self._next_btn = AnimatedPushButton("Next →", inner)
            self._next_btn.set_palette(
                base="#EF4444", hover="#F87171", pressed="#DC2626",
                text="#FFFFFF", border="#EF4444",
            )
            self._next_btn.setDefault(True)
            self._next_btn.clicked.connect(self.next_requested.emit)
            btn_row.addWidget(self._next_btn)
        else:
            self._retry_btn = AnimatedPushButton("Retry", inner)
            self._retry_btn.set_palette(
                base="#141414", hover="#1F1F1F", pressed="#0A0A0A",
                text="#F5F5F5", border="#404040",
            )
            self._retry_btn.setDefault(True)
            self._retry_btn.clicked.connect(self.retry_requested.emit)
            btn_row.addWidget(self._retry_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Kick off the reveal animation after the widget is laid out.
        QTimer.singleShot(0, self._play_reveal)

    # ------------------------------------------------------------------
    def _play_reveal(self) -> None:
        """Fade-in + subtle downward settle on the verdict word."""
        eff = QGraphicsOpacityEffect(self._verdict_label)
        eff.setOpacity(0.0)
        self._verdict_label.setGraphicsEffect(eff)

        # Opacity 0 → 1 over 280ms
        fade = QPropertyAnimation(eff, b"opacity", self)
        fade.setDuration(280)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Subtle vertical settle via margin animation on the label's geometry.
        geo = self._verdict_label.geometry()
        if geo.height() > 0:
            start = geo.translated(0, -12)
            slide = QPropertyAnimation(self._verdict_label, b"geometry", self)
            slide.setDuration(360)
            slide.setStartValue(start)
            slide.setEndValue(geo)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            slide.start()
            self._anims.append(slide)

        fade.start()
        self._anims.append(fade)

    def _kicker_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 0; margin-top: 6px;"
        )
        return lbl

    def _on_llm_clicked(self) -> None:
        if self._llm is None or not self._chapter or not self._page:
            return
        self._llm_btn.setEnabled(False)
        self._llm_btn.setText("問い合わせ中…")
        self._llm_response.setText("")
        self._llm_response.setVisible(True)
        # Repaint so the user sees the "loading" state
        self.repaint()

        req = HintRequest(
            chapter_title=self._chapter.title,
            learning_goals=self._chapter.learning_goals,
            page_title=self._page.title,
            prompt=self._page.prompt,
            submitted_code=self.result.assembled_code,
            stdout=self.result.execution.stdout if self.result.execution else "",
            stderr=self.result.execution.stderr if self.result.execution else "",
            passed=self.result.overall_passed,
        )
        text = self._llm.request_more_details(req)
        self._llm_response.setText(text)
        self._llm_btn.setEnabled(True)
        self._llm_btn.setText("Ask AI")
