"""LaTeX math rendering for markdown content.

QTextBrowser's built-in markdown engine has zero support for LaTeX math.
We pre-process markdown strings: any ``$$ ... $$`` (display) and ``$ ... $``
(inline) expression is rendered to a PNG via matplotlib's mathtext engine
(which ships with the project's matplotlib dependency — no MiKTeX needed)
and substituted into the markdown as a base64 data-URI image.

QTextBrowser preserves images encoded as ``![alt](data:image/png;base64,…)``
through its markdown → HTML pipeline, so the rendered math appears inline.

We cache rendered images by (latex, fontsize, color) so a page with many
expressions only pays the rendering cost once per unique expression.
"""

from __future__ import annotations

import base64
import io
import re
from functools import lru_cache

import matplotlib
matplotlib.use("Agg")  # no GUI backend required
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


# `$$ ... $$` (display) and `$ ... $` (inline). The display variant is
# greedy across newlines; the inline variant must stay on one line and may
# not start with another `$`.
_DISPLAY_RE = re.compile(r"\$\$([^$]+?)\$\$", re.DOTALL)
_INLINE_RE = re.compile(r"(?<![\$\\])\$([^\$\n]+?)\$(?!\$)")


@lru_cache(maxsize=256)
def _render_to_png_b64(
    latex: str,
    *,
    fontsize: int,
    color: str,
    dpi: int,
) -> str:
    """Render a LaTeX snippet to a base64-encoded PNG (no data: prefix)."""
    # Wrap with $...$ since matplotlib mathtext expects math-mode delimiters.
    expr = f"${latex.strip()}$"
    # Use a tiny figure; bbox_inches="tight" auto-crops to the math glyphs.
    fig = Figure(figsize=(0.01, 0.01), dpi=dpi)
    fig.patch.set_alpha(0.0)  # transparent background
    fig.text(0.0, 0.0, expr, fontsize=fontsize, color=color)
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        pad_inches=0.05,
        transparent=True,
    )
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_latex_in_markdown(
    md: str,
    *,
    color: str = "#F5F5F5",
    fontsize_display: int = 11,
    fontsize_inline: int = 9,
    dpi: int = 160,
) -> str:
    """Return ``md`` with $$ … $$ and $ … $ replaced by base64-image syntax.

    The output is still valid Markdown — only the math fragments are turned
    into ``![](data:image/png;base64,…)`` references that QTextBrowser
    renders inline.

    On any rendering failure (malformed LaTeX, unsupported macro, etc.) the
    original ``$...$`` text is preserved so the user at least sees the
    source rather than a blank space.
    """

    def _sub(match: re.Match[str], *, fontsize: int) -> str:
        latex = match.group(1)
        try:
            b64 = _render_to_png_b64(
                latex, fontsize=fontsize, color=color, dpi=dpi
            )
        except Exception:  # noqa: BLE001 — matplotlib raises various subclasses
            return match.group(0)
        return f"![{latex}](data:image/png;base64,{b64})"

    # Display first (so we don't accidentally split a $$..$$ into two $..$)
    md = _DISPLAY_RE.sub(lambda m: _sub(m, fontsize=fontsize_display), md)
    md = _INLINE_RE.sub(lambda m: _sub(m, fontsize=fontsize_inline), md)
    return md


def clear_cache() -> None:
    """Drop the LRU cache. Useful after a theme color change."""
    _render_to_png_b64.cache_clear()
