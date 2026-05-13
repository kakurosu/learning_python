"""Test history view — sharp monochrome layout."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..db.repo import Repository
from ..resources.theme import (
    ACCENT,
    INK,
    INK_3,
    INK_4,
    LINE,
    SUCCESS,
)


class HistoryView(QWidget):
    back_to_launcher = pyqtSignal()

    def __init__(self, repo: Repository, user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo = repo
        self.user_id = user_id

        # Header
        header = QFrame(self)
        header.setStyleSheet(f"QFrame {{ background: white; border-bottom: 1px solid {LINE}; }}")
        head_layout = QHBoxLayout(header)
        head_layout.setContentsMargins(24, 14, 24, 14)
        back = QPushButton("← ホーム", header)
        back.setProperty("variant", "ghost")
        back.clicked.connect(self.back_to_launcher.emit)
        head_layout.addWidget(back)
        title = QLabel("テスト結果", header)
        title.setObjectName("h2")
        head_layout.addWidget(title, 1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        body_layout = QVBoxLayout(inner)
        body_layout.setContentsMargins(80, 36, 80, 60)
        body_layout.setSpacing(28)

        results = self.repo.list_test_results(user_id)
        if not results:
            empty = QLabel(
                "まだテスト結果はありません。\nホームから「実力テスト」を受けてみよう。",
                inner,
            )
            empty.setStyleSheet(f"color: {INK_3}; font-size: 14px; padding: 60px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty)
        else:
            best = max(results, key=lambda r: r.score / max(r.total, 1))
            avg = sum(r.score / max(r.total, 1) for r in results) / len(results)

            stats_row = QHBoxLayout()
            stats_row.setSpacing(64)
            for label, val, color in [
                ("Attempts", str(len(results)), INK),
                ("Avg Score", f"{int(avg * 100)}%", ACCENT),
                ("Best", f"{best.score}/{best.total}", SUCCESS),
            ]:
                col = QVBoxLayout()
                col.setSpacing(2)
                v = QLabel(val, inner)
                v.setStyleSheet(
                    f"color: {color}; font-size: 32px; font-weight: 800; letter-spacing: -1px;"
                )
                col.addWidget(v)
                lbl = QLabel(label, inner)
                lbl.setStyleSheet(
                    f"color: {INK_3}; font-size: 10px; font-weight: 700; letter-spacing: 0;"
                )
                col.addWidget(lbl)
                stats_row.addLayout(col)
            stats_row.addStretch(1)
            body_layout.addLayout(stats_row)

            rule = QFrame(inner)
            rule.setStyleSheet(f"background: {INK};")
            rule.setFixedHeight(2)
            body_layout.addWidget(rule)

            for r in results:
                body_layout.addWidget(self._build_result_row(inner, r))
        body_layout.addStretch(1)
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header)
        root.addWidget(scroll, 1)

    def _build_result_row(self, parent: QWidget, r) -> QWidget:
        passed = (r.score / max(r.total, 1)) >= 0.6
        row = QFrame(parent)
        row.setStyleSheet(
            f"QFrame {{ background: white; border: none; border-bottom: 1px solid {LINE}; }}"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 14, 0, 14)
        layout.setSpacing(20)

        score_lbl = QLabel(f"{r.score}/{r.total}", row)
        score_lbl.setStyleSheet(
            f"color: {SUCCESS if passed else ACCENT};"
            f" font-size: 22px; font-weight: 800; letter-spacing: -0.5px;"
        )
        score_lbl.setMinimumWidth(80)
        layout.addWidget(score_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        test_lbl = QLabel(r.test_id, row)
        test_lbl.setStyleSheet(f"color: {INK}; font-size: 13px; font-weight: 600;")
        col.addWidget(test_lbl)
        sub = QLabel(
            f"{r.finished_at.strftime('%Y-%m-%d %H:%M')}   ·   所要 {r.duration_sec // 60}分{r.duration_sec % 60}秒",
            row,
        )
        sub.setStyleSheet(f"color: {INK_3}; font-size: 11px;")
        col.addWidget(sub)
        layout.addLayout(col, 1)

        verdict = QLabel("Passed" if passed else "Failed", row)
        verdict.setStyleSheet(
            f"color: {SUCCESS if passed else ACCENT};"
            f" font-size: 11px; font-weight: 800; letter-spacing: 0;"
        )
        layout.addWidget(verdict)

        return row
