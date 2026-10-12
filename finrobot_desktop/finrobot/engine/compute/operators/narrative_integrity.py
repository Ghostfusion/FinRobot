"""Narrative truncation guard — detect a section the model cut off at max_tokens.

An LLM step that hits its output limit returns a *schema-valid* payload: the JSON
closes, the pydantic model validates, and the narrative field simply stops
mid-clause. Nothing downstream can tell that section from a complete one, so the
report ships a thesis whose final argument is a dangling subordinate clause — and the
reader assumes the report is whole. Every other integrity check in the tree looks at
*numbers* (``report_drift``, the numeric-audit verifiers) or at *wiring*; this one
looks at whether the prose actually finished.

The detector is deliberately **conservative**, because a false marker is itself a
defect: a complete report labelled "truncated" trains readers to ignore the marker.
Two families of signal are used, both cheap and deterministic:

1. **Structural** — an unclosed ``` fence, an odd number of ``**`` emphasis markers, or
   an unbalanced bracket on the final line. These are unambiguous: a markdown
   construct that opens and never closes means the text was cut.
2. **Linguistic tail** — the final line is long and ends in a *continuation token*
   (a comma/semicolon/dash, or a trailing conjunction/preposition). A short line is
   never flagged, because a short line is a heading or a bullet label and those
   legitimately carry no terminator; and a tail ending in a digit is never flagged,
   because that is a complete measured value ("...$348.97", "...12.4x").

Two conventions the caller relies on: the check never *edits* the prose (it returns a
reason, and :func:`mark_truncated` is a separate, explicit, idempotent call), and the
marker is always visible — a shortened section is never silently passed off as whole.

Leaf layer (ADR-0005): stdlib only, no I/O, so both the pipeline and the artifact
layer can use it.
"""

from __future__ import annotations

import re
from typing import Literal

TruncationReason = Literal[
    "unclosed_code_fence",
    "unclosed_emphasis",
    "unbalanced_bracket",
    "continuation_tail",
]
"""Closed vocabulary. Closed on purpose: a caller (or a future aggregate) must be able
to count *why* sections are being cut, and "truncated, somehow" cannot be counted."""

TRUNCATION_MARKER = "\n\n> ⚠ Truncated: the model's output limit cut this section short."
"""Appended verbatim to a truncated section. Visible markdown, never a hidden flag —
a reader who does not open the artifact can still see it in the rendered report."""

_MIN_TAIL_CHARS = 40
"""Below this, the final line is a heading or a bullet label and its missing
terminator means nothing (Latin script)."""

_MIN_TAIL_CHARS_CJK = 12
"""The same idea for CJK script, at a much lower count: ``公司营收同比增长百分之十二，`` is a
13-character clause carrying what would take ~40 Latin characters. A single threshold
would either miss every cut in a Chinese report (the default is 40) or flag every short
English heading (if lowered to 12), so the threshold follows the script."""

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")


def _min_tail_chars(tail: str) -> int:
    """Length floor for the final line, chosen by script dominance.

    A line that is at least one third CJK is measured against the CJK floor; anything
    else against the Latin one.
    """
    if not tail:
        return _MIN_TAIL_CHARS
    cjk = len(_CJK_RE.findall(tail))
    return _MIN_TAIL_CHARS_CJK if cjk * 3 >= len(tail) else _MIN_TAIL_CHARS


_CONTINUATION_TOKENS: frozenset[str] = frozenset(
    {
        # English function words that cannot end a sentence.
        "and",
        "or",
        "but",
        "with",
        "for",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "from",
        "as",
        "while",
        "because",
        "however",
        "therefore",
        "which",
        "that",
        "is",
        "are",
        "was",
        "were",
        # Chinese connectives/particles that cannot end a sentence either.
        "而且",
        "以及",
        "因为",
        "所以",
        "但是",
        "并且",
        "的",
        "与",
        "和",
    }
)

_TERMINATORS: tuple[str, ...] = (
    ".",
    "!",
    "?",
    "…",
    "。",
    "！",
    "？",
    "|",
    "」",
    "』",
    "”",
    '"',
    ")",
    "]",
    "`",
)
"""Characters that end a complete line. ``|`` closes a markdown table row, and a
closing quote/bracket ends a citation or a parenthetical."""

_CONTINUATION_CHARS: tuple[str, ...] = (",", ";", ":", "—", "–", "，", "；", "：", "-")
"""Explicit continuation punctuation. A trailing hyphen is included because a line
broken mid-word is the classic hard-wrap cut."""

_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def _last_line(text: str) -> str:
    return text.rstrip().splitlines()[-1].strip() if text.strip() else ""


def _structural_reason(text: str) -> TruncationReason | None:
    """Unclosed markdown constructs on the *whole* section — unambiguous cuts.

    A fence or emphasis marker that opens and never closes cannot be a complete
    section, whatever the prose looks like.
    """
    stripped = text.rstrip()
    if stripped.count("```") % 2 == 1:
        return "unclosed_code_fence"
    if stripped.count("**") % 2 == 1:
        return "unclosed_emphasis"
    tail = _last_line(text)
    if tail.count("(") != tail.count(")") or tail.count("[") != tail.count("]"):
        return "unbalanced_bracket"
    return None


def _continuation_tail_reason(text: str) -> TruncationReason | None:
    """The final line ends as though more were coming.

    Guards, in order: short tails are headings/labels (never flagged), a trailing
    digit is a complete measured value, and an explicit terminator ends the sentence.
    """
    tail = _last_line(text)
    # Strip markdown noise so a bullet marker or bold run does not hide the real tail.
    bare = tail.lstrip("-*#> \t").rstrip("*` ")
    if len(bare) < _min_tail_chars(bare):
        return None
    if not bare:
        return None
    if bare[-1].isdigit():
        return None
    if bare.endswith(_TERMINATORS):
        return None
    if bare.endswith(_CONTINUATION_CHARS):
        return "continuation_tail"
    words = _WORD_RE.findall(bare.lower())
    if words and words[-1] in _CONTINUATION_TOKENS:
        return "continuation_tail"
    return None


def _strip_trailing_marker(text: str) -> str:
    """Remove a trailing :data:`TRUNCATION_MARKER` before re-analysing the section.

    Without this, a marked section would read as *complete* on any later pass: the
    marker is itself a sentence ending in a full stop, so it would absorb the dangling
    tail that made the section truncated. The stored artifact would then look whole to
    exactly the check that exists to catch it — the marked text has to keep stating
    what the unmarked text said.
    """
    stripped = text.rstrip()
    marker = TRUNCATION_MARKER.strip()
    if stripped.endswith(marker):
        return stripped[: -len(marker)]
    return text


def detect_truncation(text: str) -> TruncationReason | None:
    """Return why *text* looks cut off, or ``None`` when it looks complete.

    A section that already carries :data:`TRUNCATION_MARKER` is analysed *without* it,
    so marking is not a way to make a section pass this check.

    Args:
        text: One LLM-produced section (a narrative field, a step's text output).

    Returns:
        A :data:`TruncationReason`, or ``None``. An empty/whitespace-only string
        returns ``None``: an empty section is a *different* defect (the step produced
        nothing) and conflating the two would hide it.
    """
    if not text.strip():
        return None
    body = _strip_trailing_marker(text)
    return _structural_reason(body) or _continuation_tail_reason(body)


def looks_truncated(text: str) -> bool:
    """Convenience predicate over :func:`detect_truncation`."""
    return detect_truncation(text) is not None


def mark_truncated(text: str) -> str:
    """Append :data:`TRUNCATION_MARKER` when the section is truncated.

    Idempotent: a section that already carries the marker is returned unchanged, so a
    retried step, a rebuild, or a double call cannot stack markers. Completeness is the
    caller's decision — this function only makes the state visible.
    """
    if TRUNCATION_MARKER in text:
        return text
    if detect_truncation(text) is None:
        return text
    return f"{text.rstrip()}{TRUNCATION_MARKER}"


def truncation_warning(label: str, reason: TruncationReason) -> str:
    """The plain-string warning a caller adds to ``StepOutput.warnings``.

    Same channel as the other narrative backstops (momentum hedge, numeric grounding,
    street-range disclosure): a warning annotates the report, it never gates the
    verdict, the target or the confidence.
    """
    return (
        f"{label}: section appears truncated by the model's output limit "
        f"({reason}) — it ends mid-clause; a visible marker was appended. Re-run the "
        f"step or treat this section's conclusion as incomplete."
    )
