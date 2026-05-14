"""Dashboard view — Linear-style greeting + continue card + phase progress.

Layout:
    +----------------------------------------------------------------+
    |  こんにちは！                                                  |
    |  前回の続きから...                                              |
    |  ─                                                              |
    |  +-------------------- Continue card --------------------+      |
    |  | ● 続きから · PHASE A · CH 07                           |      |
    |  | ループ (for / while)                                    |      |
    |  | for / while で繰り返し処理を書ける                       |      |
    |  | ▷ 再開する      章のリストへ     ページ1/3                 |      |
    |  |                                              (code preview)|
    |  +--------------------------------------------------------+      |
    |  +----- フェーズ別の進捗 -----+  +--- 今週の様子 -----------+    |
    |  | A · Python 文法基礎  36% |  | 32  総章数              |    |
    |  | B · 数値ライブラリ   20% |  | 8   完了した章           |    |
    |  | ...                       |  | 4   進行中の章           |    |
    |  +--------------------------+  | 80% テスト平均点          |    |
    |                                +--------------------------+    |
    +----------------------------------------------------------------+
"""

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

from ...content.schemas import Chapter
from ...db.models import ChapterStatus
from ...db.repo import Repository
from ...resources.theme import (
    ACCENT,
    ACCENT_TINT,
    BG,
    FONT_SANS_DISPLAY,
    INK,
    INK_2,
    INK_3,
    INK_4,
    INK_5,
    LINE,
    PHASE_LABELS,
    SUCCESS,
    SURFACE,
    SURFACE_ALT,
)
from ..code_view import CodeBlock


# Phase metadata (display labels + description used in dashboard cards)
PHASE_INFO: list[tuple[str, str, str]] = [
    ("A", "Python 文法基礎",        "変数・演算・分岐・ループ・関数まで"),
    ("B", "数値・データライブラリ",   "NumPy / pandas / matplotlib"),
    ("C", "金融計算 (CMA)",          "期待値・共分散・最適化・MC"),
    ("D", "ML / DL",                "ARIMA / scikit-learn / PyTorch"),
    ("E", "外部連携",                "requests / OpenAI SDK"),
    ("F", "アプリ開発",              "Streamlit / 自動操作"),
]


class _Section(QFrame):
    """Outlined container with a kicker + thin top rule.

    Background is intentionally transparent (no elevation tier) — the only
    visual demarcation is the hairline border, matching the Linear "flat
    surfaces, sharp borders" pattern.
    """

    def __init__(self, kicker: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DashSection")
        self.setStyleSheet(
            f"""
            #DashSection {{ background: transparent; border: 1px solid {LINE};
                border-radius: 0; }}
            """
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(12)

        # Section header — kicker only. (No cosmetic "すべて →" arrow:
        # it wasn't clickable so we removed it.)
        k = QLabel(kicker, self)
        k.setStyleSheet(
            f"color: {INK}; font-size: 13px; font-weight: 800; letter-spacing: -0.1px;"
        )
        self._layout.addWidget(k)

    def add_widget(self, w: QWidget) -> None:
        self._layout.addWidget(w)

    def add_layout(self, l) -> None:
        self._layout.addLayout(l)

    def add_stretch(self) -> None:
        self._layout.addStretch(1)


class _PhaseProgressRow(QFrame):
    """A row inside the 'フェーズ別の進捗' card."""

    def __init__(
        self,
        phase: str,
        title: str,
        completed: int,
        total: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(14)

        # Phase badge
        badge = QLabel(phase, self)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(26, 26)
        badge.setStyleSheet(
            f"background: transparent; color: {INK}; border: 1px solid {LINE};"
            f" font-size: 12px; font-weight: 800;"
        )
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        # Title + subtitle column
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(title, self)
        t.setStyleSheet(
            f"color: {INK}; font-size: 12.5px; font-weight: 700; letter-spacing: -0.1px;"
        )
        col.addWidget(t)
        sub = QLabel(f"{completed}/{total} 章", self)
        sub.setStyleSheet(
            f"color: {INK_4}; font-size: 10px;"
            f" letter-spacing: 0.3px;"
        )
        col.addWidget(sub)
        layout.addLayout(col, 1)

        # Progress track + fill
        track = QFrame(self)
        track.setFixedSize(160, 4)
        track.setStyleSheet(f"background: {LINE}; border: none;")
        layout.addWidget(track, 0, Qt.AlignmentFlag.AlignVCenter)
        pct = 0 if total == 0 else int(completed / total * 100)
        fill = QFrame(track)
        fill.setStyleSheet(f"background: {ACCENT}; border: none;")
        fill.setGeometry(0, 0, int(160 * pct / 100), 4)

        # Percent label
        v = QLabel(f"{pct}%", self)
        v.setStyleSheet(
            f"color: {INK_2}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 0;"
        )
        v.setFixedWidth(42)
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(v, 0, Qt.AlignmentFlag.AlignVCenter)


class _StatBox(QFrame):
    """A single big-number stat box inside the '今週の様子' grid."""

    def __init__(
        self,
        value: str,
        label: str,
        sub: str = "",
        accent: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{ background: transparent; border: 1px solid {LINE};
                border-radius: 0; }}
            """
        )
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(4)

        v = QLabel(value, self)
        v.setStyleSheet(
            f"color: {ACCENT if accent else INK}; font-size: 22px; font-weight: 800;"
            f" letter-spacing: -0.6px; font-family: {FONT_SANS_DISPLAY};"
        )
        l.addWidget(v)
        lab = QLabel(label, self)
        lab.setStyleSheet(
            f"color: {INK_3}; font-size: 11px; font-weight: 700; letter-spacing: -0.1px;"
        )
        l.addWidget(lab)
        if sub:
            s = QLabel(sub, self)
            s.setStyleSheet(
                f"color: {SUCCESS}; font-size: 10px; font-weight: 700;"
                f" letter-spacing: 0;"
            )
            l.addWidget(s)


class _ContinueCard(QFrame):
    """The big dark card at the top of the dashboard with chapter info + code preview."""

    clicked = pyqtSignal()

    def __init__(
        self,
        chapter: Chapter | None,
        last_page_idx: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContinueCardV2")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            #ContinueCardV2 {{ background: transparent; border: 1px solid {LINE};
                border-radius: 0; }}
            #ContinueCardV2:hover {{ border-color: {ACCENT}; }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(28)

        # Left column — kicker + title + meta + buttons
        left = QVBoxLayout()
        left.setSpacing(0)

        # ● 続きから · PHASE A · CH 07
        if chapter is not None:
            kicker_text = (
                f"<span style='color:{ACCENT}'>●</span> "
                f"<span style='color:{ACCENT}; font-weight:800;'>続きから</span>"
                f" <span style='color:{INK_4}'>·</span>"
                f" <span style='color:{INK_3}'>{PHASE_LABELS[chapter.phase]}</span>"
                f" <span style='color:{INK_4}'>·</span>"
                f" <span style='color:{INK_3}'>Ch {chapter.id:02d}</span>"
            )
        else:
            kicker_text = (
                f"<span style='color:{ACCENT}'>●</span> "
                f"<span style='color:{ACCENT}; font-weight:800;'>はじめての学習</span>"
            )
        kicker = QLabel(kicker_text, self)
        kicker.setTextFormat(Qt.TextFormat.RichText)
        kicker.setStyleSheet(
            f"font-size: 11px; letter-spacing: 0.4px;"
        )
        left.addWidget(kicker)
        left.addSpacing(10)

        title = QLabel(
            chapter.title if chapter is not None else "Begin Your Journey",
            self,
        )
        title.setStyleSheet(
            f"color: {INK}; font-size: 30px; font-weight: 800; letter-spacing: -0.8px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        title.setWordWrap(True)
        left.addWidget(title)
        left.addSpacing(6)

        sub_text = (
            chapter.learning_goals[0] if (chapter and chapter.learning_goals)
            else "第 1 章から学習を始めましょう。"
        )
        sub = QLabel(sub_text, self)
        sub.setStyleSheet(f"color: {INK_3}; font-size: 13px; letter-spacing: -0.1px;")
        sub.setWordWrap(True)
        left.addWidget(sub)
        left.addStretch(1)

        # CTA row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        resume = QPushButton("▷  再開する", self)
        resume.setCursor(Qt.CursorShape.PointingHandCursor)
        resume.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: white;"
            f" border: 1px solid {ACCENT}; border-radius: 0;"
            f" padding: 9px 22px; font-size: 12px; font-weight: 700;"
            f" min-width: 0; min-height: 0; }}"
            f"QPushButton:hover {{ background: #F87171; border-color: #F87171; }}"
        )
        resume.clicked.connect(self.clicked.emit)
        btn_row.addWidget(resume)

        list_link = QLabel("章のリストへ", self)
        list_link.setStyleSheet(
            f"color: {INK_3}; font-size: 12px; font-weight: 600;"
        )
        btn_row.addWidget(list_link)

        if chapter is not None:
            page_meta = QLabel(
                f"ページ {last_page_idx + 1}/{len(chapter.pages)}", self
            )
            page_meta.setStyleSheet(
                f"color: {INK_4}; font-size: 11px; font-weight: 700;"
                f" letter-spacing: 0;"
            )
            btn_row.addWidget(page_meta)
        btn_row.addStretch(1)
        left.addLayout(btn_row)

        layout.addLayout(left, 3)

        # Right column — code preview
        if chapter is not None:
            preview_code = (
                "# フルーツを順に表示する\n"
                'for fruit in ["apple", "banana", "cherry"]:\n'
                '    print(fruit)'
            )
            preview = CodeBlock(preview_code, file_label="preview.py", runnable=False)
            preview.set_max_height(120)
            preview.setMinimumWidth(280)
            preview.setMaximumWidth(360)
            layout.addWidget(preview, 2, Qt.AlignmentFlag.AlignTop)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class DashboardView(QWidget):
    """Top-level dashboard view shown in AppShell."""

    resume_requested = pyqtSignal()
    browse_chapters_requested = pyqtSignal()
    test_requested = pyqtSignal(str)
    history_requested = pyqtSignal()
    start_over_requested = pyqtSignal()

    def __init__(
        self,
        chapters: list[Chapter],
        repo: Repository,
        user_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chapters = chapters
        self.repo = repo
        self.user_id = user_id

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 28, 40, 40)
        layout.setSpacing(0)

        # ----- Hero greeting row -----------------------------------------
        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(16)

        hero_col = QVBoxLayout()
        hero_col.setSpacing(2)
        hero = QLabel("こんにちは！", inner)
        hero.setStyleSheet(
            f"color: {INK}; font-size: 26px; font-weight: 800; letter-spacing: -0.6px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        hero_col.addWidget(hero)
        latest = self.repo.latest_in_progress(self.user_id)
        if latest is not None:
            ch = next((c for c in self.chapters if c.id == latest.chapter_id), None)
            if ch is not None:
                sub = QLabel(
                    f"前回の続きから、{PHASE_LABELS[ch.phase]} · Ch {ch.id:02d} "
                    f"「{ch.title}」を再開できます。", inner,
                )
            else:
                sub = QLabel("章を選んで学習を始めましょう。", inner)
        else:
            sub = QLabel("第 1 章から学習を始めましょう。", inner)
        sub.setStyleSheet(f"color: {INK_3}; font-size: 13px; letter-spacing: -0.1px;")
        hero_col.addWidget(sub)
        hero_row.addLayout(hero_col, 1)
        layout.addLayout(hero_row)
        layout.addSpacing(24)

        # ----- Continue card --------------------------------------------
        latest_chapter: Chapter | None = None
        latest_page = 0
        if latest is not None:
            latest_chapter = next(
                (c for c in self.chapters if c.id == latest.chapter_id), None
            )
            latest_page = latest.last_page_index
        cont = _ContinueCard(latest_chapter, latest_page, inner)
        cont.clicked.connect(self.resume_requested.emit)
        layout.addWidget(cont)
        layout.addSpacing(20)

        # ----- Two columns: phase progress (left) + side rail (right) ----
        cols = QHBoxLayout()
        cols.setSpacing(20)

        # Phase progress card
        progress = self.repo.all_progress(self.user_id)
        completed_per_phase: dict[str, int] = {p: 0 for p in "ABCDEF"}
        total_per_phase: dict[str, int] = {p: 0 for p in "ABCDEF"}
        for ch in self.chapters:
            total_per_phase[ch.phase] = total_per_phase.get(ch.phase, 0) + 1
        completed_ids = {p.chapter_id for p in progress if p.status == ChapterStatus.completed}
        for ch in self.chapters:
            if ch.id in completed_ids:
                completed_per_phase[ch.phase] += 1

        ph_section = _Section("フェーズ別の進捗", inner)
        for phase, title, _ in PHASE_INFO:
            ph_section.add_widget(
                _PhaseProgressRow(
                    phase, title,
                    completed_per_phase.get(phase, 0),
                    total_per_phase.get(phase, 0),
                )
            )
        cols.addWidget(ph_section, 3)

        # Right rail — stats + quick actions
        rail = QVBoxLayout()
        rail.setSpacing(20)

        # 今週の様子: 2x2 grid of stat boxes
        week = _Section("今週の様子", inner)
        grid = QVBoxLayout()
        grid.setSpacing(8)
        n_total = len(self.chapters)
        n_done = sum(1 for p in progress if p.status == ChapterStatus.completed)
        n_inprog = sum(1 for p in progress if p.status == ChapterStatus.in_progress)
        results = self.repo.list_test_results(self.user_id)
        avg = 0
        if results:
            avg = int(
                sum(r.score / max(r.total, 1) for r in results) / len(results) * 100
            )

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(_StatBox(str(n_total), "総章数"))
        row1.addWidget(_StatBox(
            str(n_done), "完了した章",
            sub="✓ +2 今週" if n_done > 0 else "",
            accent=False,
        ))
        grid.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(_StatBox(str(n_inprog), "進行中の章"))
        row2.addWidget(_StatBox(
            f"{avg}%" if results else "—",
            "テスト平均点",
            sub="✓ +4 pt" if avg > 0 else "",
            accent=True,
        ))
        grid.addLayout(row2)
        week.add_layout(grid)
        rail.addWidget(week)

        # クイックアクション
        qa = _Section("クイックアクション", inner)
        for slug, icon, title, desc in [
            ("chapters",  "□", "章を選ぶ",
             "Phase A〜F の好きな章へ移動"),
            ("tests",     "✓", "実力テスト",
             "Phase ごとに 10 問で習熟度を測る"),
            ("history",   "≡", "学習履歴",
             "過去のスコアと推移を見る"),
        ]:
            qa.add_widget(_QuickActionRow(slug, icon, title, desc, on_click=self._route))
        rail.addWidget(qa)
        rail.addStretch(1)
        cols.addLayout(rail, 2)

        layout.addLayout(cols)
        layout.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _route(self, slug: str) -> None:
        if slug == "chapters":
            self.browse_chapters_requested.emit()
        elif slug == "tests":
            self.test_requested.emit("phase_a_test")  # default; UI may pick a different one
        elif slug == "history":
            self.history_requested.emit()


class _QuickActionRow(QFrame):
    """A row in the クイックアクション card (icon + title + subtitle + arrow)."""

    def __init__(
        self,
        slug: str,
        icon: str,
        title: str,
        subtitle: str,
        on_click,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("QuickActionRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # No background fill on hover (the rectangular highlight was
        # distracting). Instead the title and arrow turn accent red.
        self.setStyleSheet(
            f"""
            #QuickActionRow {{ background: transparent;
                border: none; border-bottom: 1px solid {LINE}; }}
            #QuickActionRow:hover #qaTitle {{ color: {ACCENT}; }}
            #QuickActionRow:hover #qaArrow {{ color: {ACCENT}; }}
            """
        )
        self._slug = slug
        self._on_click = on_click

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 10, 2, 10)
        layout.setSpacing(14)

        # Plain text glyph (no bordered square — the bordered square added a
        # visible rectangle that conflicted with the flat row aesthetic).
        ic = QLabel(icon, self)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setFixedWidth(20)
        ic.setStyleSheet(
            f"color: {INK_3}; background: transparent; border: none;"
            f" font-size: 14px; font-weight: 700;"
        )
        layout.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(title, self)
        t.setObjectName("qaTitle")
        t.setStyleSheet(
            f"color: {INK}; font-size: 13px; font-weight: 700; letter-spacing: -0.1px;"
        )
        col.addWidget(t)
        s = QLabel(subtitle, self)
        s.setStyleSheet(f"color: {INK_4}; font-size: 11px;")
        col.addWidget(s)
        layout.addLayout(col, 1)

        arrow = QLabel("→", self)
        arrow.setObjectName("qaArrow")
        arrow.setStyleSheet(f"color: {INK_4}; font-size: 14px; font-weight: 400;")
        layout.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._on_click(self._slug)
        super().mousePressEvent(e)
