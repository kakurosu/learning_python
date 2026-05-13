"""Pydantic schemas for chapter YAML files.

A chapter YAML is structured as an ordered list of pages.
Each page is one of:
- ``sample``: explanation + example code (read-only, runnable).
- ``exercise``: fill-in-the-blank exercise with optional test cases.

Result pages are not stored in YAML; the UI inserts them dynamically after grading.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Common reusable types
# ---------------------------------------------------------------------------

StickmanMood = Literal["normal", "happy", "sad", "explain"]


class StickmanFeedback(BaseModel):
    """Stickman speech variants shown after grading."""

    model_config = ConfigDict(extra="forbid")

    correct: str = "正解！"
    wrong_hint1: str = "もう少し！ヒントを見てみよう。"
    wrong_hint2: str = "あと一歩！書き方を見直してみよう。"
    wrong_hint3: str = "答えに近い形を出すよ。"


# ---------------------------------------------------------------------------
# Test cases (used by both exercise pages and the standalone test sets)
# ---------------------------------------------------------------------------


class NamespaceCheck(BaseModel):
    """Evaluate boolean asserts against the kernel namespace after the student code runs."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["namespace_check"]
    asserts: list[str] = Field(min_length=1)


class StdoutRegex(BaseModel):
    """Match the captured stdout against a (multiline) regex pattern."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["stdout_regex"]
    pattern: str
    flags: list[Literal["IGNORECASE", "MULTILINE", "DOTALL"]] = Field(default_factory=list)

    @field_validator("pattern")
    @classmethod
    def _compilable(cls, v: str) -> str:
        re.compile(v)  # raise if invalid; caught by pydantic
        return v


class PytestLike(BaseModel):
    """Run a pytest-like test file against the assembled student code."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["pytest_like"]
    test_code: str  # full pytest module body


TestCase = Annotated[NamespaceCheck | StdoutRegex | PytestLike, Field(discriminator="kind")]


# ---------------------------------------------------------------------------
# Blank slot
# ---------------------------------------------------------------------------


class Blank(BaseModel):
    """A single fill-in-the-blank slot."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[A-Za-z_]\w*$")
    placeholder: str = ""
    width: int = 16  # approx characters; UI uses for sizing
    accept_patterns: list[str] = Field(default_factory=list)
    canonical_answer: str
    hint: str = ""

    @field_validator("accept_patterns")
    @classmethod
    def _valid_regex(cls, v: list[str]) -> list[str]:
        for p in v:
            re.compile(p)
        return v


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


class SamplePage(BaseModel):
    """Read-only sample page: explanation + runnable example code."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["sample"]
    title: str
    markdown: str
    sample_code: str = ""
    runnable: bool = True
    expected_output: str = ""
    stickman: StickmanMood = "explain"
    stickman_speech: str = "サンプルを見てみよう。実行ボタンを押すと結果が見られるよ。"


class ExercisePage(BaseModel):
    """Fill-in-the-blank exercise page."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["exercise"]
    title: str
    prompt: str
    code_template: str
    blanks: list[Blank] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    stickman_feedback: StickmanFeedback = Field(default_factory=StickmanFeedback)
    timeout_seconds: int = 10

    @field_validator("code_template")
    @classmethod
    def _has_known_slots(cls, v: str) -> str:
        # Allow templates without slots (rare). Only validate slot syntax shape.
        for m in re.finditer(r"\{\{slot:([^}\s]+)\}\}", v):
            slot_id = m.group(1)
            if not re.fullmatch(r"[A-Za-z_]\w*", slot_id):
                raise ValueError(f"invalid slot id: {slot_id!r}")
        return v


Page = Annotated[SamplePage | ExercisePage, Field(discriminator="kind")]


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------


Phase = Literal["A", "B", "C", "D", "E", "F"]


class Chapter(BaseModel):
    """A single chapter loaded from ``content/chapters/NN_*.yaml``."""

    model_config = ConfigDict(extra="forbid")
    id: int = Field(ge=1)
    title: str
    phase: Phase
    prerequisites: list[int] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    pages: list[Page] = Field(min_length=1)

    def page_ids(self) -> list[str]:
        """Stable identifier for each page (used in DB to track progress)."""
        return [f"{self.id:02d}-{i}-{p.kind}" for i, p in enumerate(self.pages)]

    def referenced_blanks(self, page_index: int) -> dict[str, Blank]:
        page = self.pages[page_index]
        if not isinstance(page, ExercisePage):
            return {}
        return {b.id: b for b in page.blanks}
