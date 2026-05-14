"""Chapter picker view — Linear-style with search, filter chips and phase blocks.

Layout:
    +---------------------------------------------------------------+
    | 進行中 4   完了 8   残り 20                                     |
    +---------------------------------------------------------------+
    | 章を選ぶ                                                        |
    | 全 6 Phase · 32 章。 …                                          |
    | ─                                                              |
    | [search]                       All In-progress Todo Done  List Grid|
    | PHASE A                                                  11 章 |
    | A   Python 文法基礎                                              |
    |     変数・演算・分岐・ループ・関数まで                  完了 0 · 進行中 4 |
    | ─                                                              |
    |  01  はじめての Python                       ━━━━━━━━━━  In progress → |
    |  02  変数と型                                ──────────  Not started → |
    +---------------------------------------------------------------+
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
    FONT_MONO,
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
from .dashboard import PHASE_INFO


class _FilterChip(QPushButton):
    """A small monochrome chip — sharp border, accent when active."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._qss(False))
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, on: bool) -> None:
        self.setStyleSheet(self._qss(on))

    @staticmethod
    def _qss(on: bool) -> str:
        if on:
            return (
                f"QPushButton {{ background: {ACCENT_TINT}; color: {INK};"
                f" border: 1px solid {ACCENT}; border-radius: 0;"
                f" padding: 5px 12px; font-size: 11px; font-weight: 800;"
                f" min-width: 0; min-height: 0; letter-spacing: -0.1px; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {INK_3};"
            f" border: 1px solid {LINE}; border-radius: 0;"
            f" padding: 5px 12px; font-size: 11px; font-weight: 700;"
            f" min-width: 0; min-height: 0; letter-spacing: -0.1px; }}"
            f"QPushButton:hover {{ color: {INK}; border-color: {INK_5}; }}"
        )


class _ChapterCard(QFrame):
    """A clickable chapter row (Linear-style with hairline divider and hover accent)."""

    clicked = pyqtSignal(int)

    def __init__(self, chapter: Chapter, status: ChapterStatus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.chapter = chapter
        self.setObjectName("ChapterCardV2")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            #ChapterCardV2 {{ background: transparent;
                border: none; border-bottom: 1px solid {LINE};
                border-left: 2px solid transparent; }}
            #ChapterCardV2:hover {{ background: {SURFACE_ALT};
                border-left: 2px solid {ACCENT}; }}
            #ChapterCardV2:hover #ccv2Title {{ color: {ACCENT}; }}
            """
        )
        self.setMinimumHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(20)

        num = QLabel(f"{chapter.id:02d}", self)
        num.setStyleSheet(
            f"color: {INK_4}; font-size: 12px; font-weight: 700;"
            f" font-family: {FONT_MONO}; letter-spacing: 0.4px;"
        )
        num.setMinimumWidth(28)
        layout.addWidget(num, 0, Qt.AlignmentFlag.AlignVCenter)

        # Title / subtitle
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(chapter.title, self)
        t.setObjectName("ccv2Title")
        t.setStyleSheet(
            f"color: {INK}; font-size: 13px; font-weight: 700; letter-spacing: -0.1px;"
        )
        col.addWidget(t)
        if chapter.learning_goals:
            sub = QLabel(chapter.learning_goals[0], self)
            sub.setStyleSheet(f"color: {INK_4}; font-size: 11px;")
            sub.setWordWrap(False)
            col.addWidget(sub)
        layout.addLayout(col, 1)

        # Mini progress track
        track = QFrame(self)
        track.setFixedSize(120, 4)
        track.setStyleSheet(f"background: {LINE}; border: none;")
        # Fill = full when completed, half when in_progress, 0 otherwise
        pct = {
            ChapterStatus.completed: 100,
            ChapterStatus.in_progress: 50,
            ChapterStatus.not_started: 0,
        }.get(status, 0)
        fill = QFrame(track)
        fill.setStyleSheet(f"background: {ACCENT}; border: none;")
        fill.setGeometry(0, 0, int(120 * pct / 100), 4)
        layout.addWidget(track, 0, Qt.AlignmentFlag.AlignVCenter)

        # Status label
        st_text, st_color = {
            ChapterStatus.completed:   ("● Done",        SUCCESS),
            ChapterStatus.in_progress: ("● In progress", ACCENT),
            ChapterStatus.not_started: ("○ Not started", INK_4),
        }.get(status, ("—", INK_4))
        st = QLabel(st_text, self)
        st.setStyleSheet(
            f"color: {st_color}; font-size: 10px; font-weight: 800;"
            f" letter-spacing: 0.3px; font-family: {FONT_MONO};"
        )
        st.setMinimumWidth(110)
        layout.addWidget(st, 0, Qt.AlignmentFlag.AlignVCenter)

        arrow = QLabel("→", self)
        arrow.setStyleSheet(f"color: {INK_4}; font-size: 14px;")
        layout.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.chapter.id)
        super().mousePressEvent(e)


class _PhaseHeader(QFrame):
    """Big Phase letter block with title + counts."""

    def __init__(
        self,
        phase: str,
        title: str,
        desc: str,
        total: int,
        completed: int,
        in_progress: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        letter = QLabel(phase, self)
        letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        letter.setFixedSize(54, 54)
        letter.setStyleSheet(
            f"color: {INK}; background: transparent; border: 1px solid {LINE};"
            f" font-size: 28px; font-weight: 800; letter-spacing: -1px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        layout.addWidget(letter, 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        kicker = QLabel(PHASE_LABELS[phase], self)
        kicker.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 800;"
            f" letter-spacing: 0.6px; font-family: {FONT_MONO};"
        )
        col.addWidget(kicker)
        t = QLabel(title, self)
        t.setStyleSheet(
            f"color: {INK}; font-size: 22px; font-weight: 800; letter-spacing: -0.6px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        col.addWidget(t)
        d = QLabel(desc, self)
        d.setStyleSheet(f"color: {INK_3}; font-size: 12px;")
        col.addWidget(d)
        layout.addLayout(col, 1)

        # Right side meta
        meta = QVBoxLayout()
        meta.setSpacing(2)
        n_text = QLabel(f"{total} 章", self)
        n_text.setStyleSheet(
            f"color: {INK_2}; font-size: 14px; font-weight: 800;"
            f" font-family: {FONT_MONO}; letter-spacing: 0;"
        )
        n_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        meta.addWidget(n_text)
        s_text = QLabel(f"完了 {completed} · 進行中 {in_progress}", self)
        s_text.setStyleSheet(
            f"color: {INK_4}; font-size: 10px; font-weight: 700;"
            f" font-family: {FONT_MONO}; letter-spacing: 0.3px;"
        )
        s_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        meta.addWidget(s_text)
        layout.addLayout(meta, 0)


class ChapterPickerView(QWidget):
    """Top-level chapter picker shown in AppShell."""

    chapter_selected = pyqtSignal(int, int)

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
        self._filter = "all"
        self._search = ""

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 28, 40, 40)
        layout.setSpacing(0)

        # ----- Top counters strip (進行中 / 完了 / 残り) -----
        progress = repo.all_progress(user_id)
        n_done = sum(1 for p in progress if p.status == ChapterStatus.completed)
        n_inprog = sum(1 for p in progress if p.status == ChapterStatus.in_progress)
        n_remain = len(chapters) - n_done

        strip = QHBoxLayout()
        strip.setSpacing(28)
        for label, value, color in [
            ("進行中", n_inprog, ACCENT),
            ("完了",   n_done,   SUCCESS),
            ("残り",   n_remain, INK_3),
        ]:
            chunk = QLabel(
                f"<span style='color:{INK_4}; font-size:11px; font-weight:700;"
                f" letter-spacing:0.3px;'>{label}</span>"
                f" &nbsp;&nbsp;"
                f"<span style='color:{color}; font-size:14px; font-weight:800;"
                f" font-family:{FONT_MONO}; letter-spacing:0;'>{value}</span>",
                inner,
            )
            chunk.setTextFormat(Qt.TextFormat.RichText)
            strip.addWidget(chunk)
        strip.addStretch(1)
        layout.addLayout(strip)
        layout.addSpacing(20)

        # ----- Hero -----
        title = QLabel("章を選ぶ", inner)
        title.setStyleSheet(
            f"color: {INK}; font-size: 32px; font-weight: 800; letter-spacing: -1px;"
            f" font-family: {FONT_SANS_DISPLAY};"
        )
        layout.addWidget(title)
        sub = QLabel(
            "全 6 Phase · 32 章。気になる章から始めましょう。"
            "各章にはレッスン・練習・閃絡チェックが含まれます。", inner,
        )
        sub.setStyleSheet(f"color: {INK_3}; font-size: 13px; letter-spacing: -0.1px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)
        layout.addSpacing(20)

        # ----- Search + filter chips + view toggle -----
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._search_box = QLineEdit(inner)
        self._search_box.setPlaceholderText("章名・トピックを検索")
        self._search_box.setFixedWidth(280)
        self._search_box.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {INK_2};"
            f" border: 1px solid {LINE}; border-radius: 0; padding: 7px 12px;"
            f" font-size: 12px; }}"
            f"QLineEdit:focus {{ border-color: {ACCENT}; }}"
        )
        self._search_box.textChanged.connect(self._on_search)
        controls.addWidget(self._search_box, 0, Qt.AlignmentFlag.AlignVCenter)

        controls.addStretch(1)

        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        for slug, label in [
            ("all", "All"),
            ("in_progress", "In progress"),
            ("todo", "Todo"),
            ("done", "Done"),
        ]:
            chip = _FilterChip(label, inner)
            chip.setProperty("filter", slug)
            self._chip_group.addButton(chip)
            controls.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
            if slug == "all":
                chip.setChecked(True)
        self._chip_group.buttonToggled.connect(self._on_chip)

        # Spacer
        sep = QFrame(inner)
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background: {LINE};")
        controls.addWidget(sep, 0, Qt.AlignmentFlag.AlignVCenter)

        for label, active in [("List", True), ("Grid", False)]:
            t = QPushButton(label, inner)
            t.setCheckable(True)
            t.setChecked(active)
            t.setCursor(Qt.CursorShape.PointingHandCursor)
            t.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {INK_3};"
                f" border: 1px solid {LINE}; border-radius: 0;"
                f" padding: 5px 12px; font-size: 11px; font-weight: 700;"
                f" min-width: 0; min-height: 0; }}"
                f"QPushButton:checked {{ background: {ACCENT_TINT};"
                f" color: {INK}; border-color: {ACCENT}; }}"
            )
            controls.addWidget(t, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(controls)
        layout.addSpacing(28)

        # ----- Phase blocks + chapter cards -----
        self._body_layout = QVBoxLayout()
        self._body_layout.setSpacing(28)
        layout.addLayout(self._body_layout)
        layout.addStretch(1)

        self._rebuild_body()

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    def _on_search(self, text: str) -> None:
        self._search = text.strip().lower()
        self._rebuild_body()

    def _on_chip(self, btn, on: bool) -> None:
        if not on:
            return
        slug = btn.property("filter")
        if slug:
            self._filter = slug
            self._rebuild_body()

    def _matches_filter(self, status: ChapterStatus) -> bool:
        f = self._filter
        if f == "all":
            return True
        if f == "in_progress":
            return status == ChapterStatus.in_progress
        if f == "done":
            return status == ChapterStatus.completed
        if f == "todo":
            return status == ChapterStatus.not_started
        return True

    def _matches_search(self, chapter: Chapter) -> bool:
        if not self._search:
            return True
        hay = (chapter.title + " " + " ".join(chapter.learning_goals)).lower()
        return self._search in hay

    def _rebuild_body(self) -> None:
        # Clear
        while self._body_layout.count():
            it = self._body_layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                la = it.layout()
                if la is not None:
                    self._clear_layout(la)

        progress_by_chapter = {
            p.chapter_id: p for p in self.repo.all_progress(self.user_id)
        }

        for phase, ptitle, desc in PHASE_INFO:
            chs = [c for c in self.chapters if c.phase == phase]
            if not chs:
                continue
            phase_total = len(chs)
            phase_done = sum(
                1 for c in chs
                if (p := progress_by_chapter.get(c.id))
                and p.status == ChapterStatus.completed
            )
            phase_inprog = sum(
                1 for c in chs
                if (p := progress_by_chapter.get(c.id))
                and p.status == ChapterStatus.in_progress
            )

            # Filter rows in this phase
            visible: list[tuple[Chapter, ChapterStatus]] = []
            for c in chs:
                status = (progress_by_chapter.get(c.id).status
                          if progress_by_chapter.get(c.id) else ChapterStatus.not_started)
                if not self._matches_filter(status):
                    continue
                if not self._matches_search(c):
                    continue
                visible.append((c, status))

            if not visible:
                continue

            section = QVBoxLayout()
            section.setSpacing(0)

            section.addWidget(_PhaseHeader(
                phase, ptitle, desc,
                total=phase_total, completed=phase_done, in_progress=phase_inprog,
            ))
            # divider
            rule = QFrame()
            rule.setFixedHeight(1)
            rule.setStyleSheet(f"background: {LINE};")
            section.addSpacing(10)
            section.addWidget(rule)

            for c, status in visible:
                card = _ChapterCard(c, status)
                card.clicked.connect(self._on_pick)
                section.addWidget(card)
            self._body_layout.addLayout(section)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                child = it.layout()
                if child is not None:
                    self._clear_layout(child)

    def _on_pick(self, chapter_id: int) -> None:
        # Resume at the last_page_index if we have progress, else page 0
        prog = self.repo.get_progress(self.user_id, chapter_id)
        page = prog.last_page_index if prog else 0
        self.chapter_selected.emit(chapter_id, page)

    def refresh(self) -> None:
        self._rebuild_body()
