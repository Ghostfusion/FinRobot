"""Truncation-guard tests.

Two failure modes have to be held apart, and most of these cases exist to separate
them:

* a **miss** — a section the model cut at max_tokens passing as complete, which ships
  a report whose final argument is a dangling clause;
* a **false marker** — a complete section labelled truncated, which teaches readers to
  ignore the marker and so degrades the honesty of every real one.

The detector is therefore tested for both directions: every unambiguous cut is caught,
and the shapes that *look* cut but are legitimate (a short bullet label, a trailing
measured value, a table row, a complete Chinese sentence) are explicitly not flagged.
"""

from __future__ import annotations

import pytest

from finrobot.engine.compute.operators.narrative_integrity import (
    TRUNCATION_MARKER,
    detect_truncation,
    looks_truncated,
    mark_truncated,
    truncation_warning,
)

# Long enough to clear the Latin tail floor; ends mid-clause on each continuation shape.
_LONG = "The company's operating margin expanded to twenty four point three percent"


@pytest.mark.parametrize(
    ("label", "text", "expected"),
    [
        ("complete sentence", "Revenue grew 12% year over year, driven by cloud demand.", None),
        ("exclamation", "The setup is compelling!", None),
        ("chinese full stop", "公司营收同比增长百分之十二，主要受益于云业务需求。", None),
        ("table row", "| Blended | 12.4x | 11.8x |", None),
        ("trailing measured value", f"{_LONG} at 24.3", None),
        ("short bold verdict", "**BUY**", None),
        ("short bullet label", "- Strong balance sheet", None),
        ("heading", "## Investment Thesis", None),
        ("empty", "", None),
        ("whitespace only", "   \n\t ", None),
        ("comma tail", f"{_LONG},", "continuation_tail"),
        ("colon tail", f"{_LONG}:", "continuation_tail"),
        ("dash tail", f"{_LONG} —", "continuation_tail"),
        ("conjunction tail", f"{_LONG} and", "continuation_tail"),
        ("preposition tail", f"{_LONG} of", "continuation_tail"),
        (
            "chinese comma tail",
            "公司营收同比增长百分之十二，主要受益于云业务需求，",
            "continuation_tail",
        ),
        (
            "chinese connective tail",
            "公司营收同比增长百分之十二，主要受益于云业务需求，以及",
            "continuation_tail",
        ),
        ("unclosed fence", "## Notes\n\n```python\nprint(1)\n", "unclosed_code_fence"),
        ("closed fence", "## Notes\n\n```python\nprint(1)\n```\n", None),
        ("unclosed emphasis", "The **moat is durable across cycles", "unclosed_emphasis"),
        ("closed emphasis", "The **moat** is durable across cycles.", None),
        ("unbalanced paren", f"{_LONG} (a step up from last year", "unbalanced_bracket"),
        ("balanced paren", f"{_LONG} (a step up from last year).", None),
    ],
)
def test_detect_truncation(label: str, text: str, expected: str | None) -> None:
    assert detect_truncation(text) == expected, label


def test_cjk_and_latin_floors_are_script_aware() -> None:
    """A single floor would miss every Chinese cut or flag every short English
    heading. The same short clause is judged by its own script's density."""
    short_cjk = "公司营收同比增长百分之十二，"
    assert len(short_cjk) < 40
    assert detect_truncation(short_cjk) == "continuation_tail"
    # A short Latin bullet label of comparable character count stays unflagged.
    assert detect_truncation("- Revenue up") is None


@pytest.mark.parametrize(
    "text",
    [
        "Revenue grew 12% year over year, driven by cloud demand.",
        f"{_LONG},",
        "## Notes\n\n```python\nprint(1)\n",
    ],
)
def test_looks_truncated_agrees_with_detect(text: str) -> None:
    assert looks_truncated(text) is (detect_truncation(text) is not None)


def test_mark_appends_a_visible_marker_only_when_truncated() -> None:
    cut = f"{_LONG},"
    marked = mark_truncated(cut)
    assert TRUNCATION_MARKER in marked
    assert marked.startswith(cut.rstrip())

    complete = "Revenue grew 12% year over year, driven by cloud demand."
    assert mark_truncated(complete) == complete


def test_mark_is_idempotent() -> None:
    """A retried step or a rebuilt report must not stack markers."""
    once = mark_truncated(f"{_LONG},")
    assert mark_truncated(once) == once
    assert once.count(TRUNCATION_MARKER) == 1


def test_marker_survives_a_second_detection_pass() -> None:
    """The marked text must still *read* as truncated, so a later rebuild that
    re-checks the stored section reaches the same conclusion."""
    marked = mark_truncated(f"{_LONG},")
    assert looks_truncated(marked) is True


def test_warning_names_the_label_and_the_reason() -> None:
    """The warning rides ``StepOutput.warnings`` into the artifact, so it has to be
    quotable on its own — a reader sees the text without the code."""
    message = truncation_warning("thesis", "continuation_tail")
    assert "thesis" in message
    assert "continuation_tail" in message
