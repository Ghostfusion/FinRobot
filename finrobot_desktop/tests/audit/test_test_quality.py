"""Meta-gate: a green suite must be *capable* of going red.

Why this file exists
--------------------
A test that cannot fail is worse than a missing test: it inflates the green
count, hides the behaviour it claims to cover, and every later refactor trusts
it. The suite grew such shapes by accident -- a leftover tautological boolean
assertion while bisecting a red test, a defensive disjunction whose literal
``True`` swallowed a real check, a source-text pin (``inspect``'s source-reading
helpers plus a substring test) that substitutes for behaviour, and a bare
string literal used as the whole condition, where the assertion message argument
migrated into the condition itself. Each one is *locally* plausible and
survives review precisely because it is a single character away from correct.

No amount of care fixes that; a machine check does. This gate walks every
test module and fails on the six unfailable shapes. Fix the offender (assert
the behaviour, not the source text) -- never delete the check.

The detection is AST-based on purpose: the banned shapes also appear inside
docstrings, comments and the snippets used to prove this detector works, and a
text scan would either flag those or -- worse -- be silently tuned until it
did not. Walking the tree also lets a comparison be classified structurally
(one comparison and its exact negation over the same operands is the same
*pair* spoken twice), which no regex can do reliably.

Why the detector is a pure function
-----------------------------------
``find_unfailable_shapes`` takes source text and returns violations; the
repo-wide walk is a thin loop over it. That split is what makes the gate
provable: the parametrised tests below feed it synthetic snippets, one per
banned shape, so a detector that silently matches nothing fails its own tests
instead of ushering every bad assertion through.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
THIS_FILE = Path(__file__).resolve()

#: ``inspect`` helpers that pin *source text* instead of behaviour. Their real
#: value is reading code; asserting on the string they return stays green after
#: the pinned symbol was renamed, deleted or never called.
_SOURCE_PINNING_ATTRS = frozenset({"getsource", "getsourcelines", "getsourcefile"})

#: Mutually-negating comparison operators. If both sides of one ``or`` compare
#: the *same* operands with a negated pair, one branch is always true.
_OP_NEGATIONS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
}


@dataclass(frozen=True)
class Violation:
    """One unfailable shape, located at ``path:lineno`` for the report."""

    path: str
    lineno: int
    reason: str


def _inspect_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    """Return (module aliases, names imported from ``inspect``).

    The canonical spelling ``inspect`` always counts as a module alias, so a
    lazy/local import (or an alias like ``import inspect as ins``) does not hide
    a call from the scan.
    """
    modules: set[str] = {"inspect"}
    members: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "inspect":
                    modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "inspect":
            for alias in node.names:
                members.add(alias.asname or alias.name)
    return modules, members


def _literal(node: ast.expr, expected: bool) -> bool:
    """True for the literal ``True``/``False`` (not 0/1, which are ints)."""
    return isinstance(node, ast.Constant) and node.value is expected


def _negation_pair(first: ast.expr, second: ast.expr) -> bool:
    """True when *first* and *second* are one comparison and its own negation.

    Same left operand, same comparator, mutually-negating operator type -- one
    comparison and its negation read as a single expression (and every sibling
    pair: ``==``/``!=``, ``in``/``not in``, ``<``/``>=``, ...) is a tautology.
    """
    if not (isinstance(first, ast.Compare) and isinstance(second, ast.Compare)):
        return False
    if len(first.ops) != 1 or len(second.ops) != 1:
        return False
    if len(first.comparators) != 1 or len(second.comparators) != 1:
        return False
    if ast.dump(first.left) != ast.dump(second.left):
        return False
    if ast.dump(first.comparators[0]) != ast.dump(second.comparators[0]):
        return False
    return _OP_NEGATIONS.get(type(first.ops[0])) is type(second.ops[0])


def _assert_reasons(node: ast.Assert) -> list[str]:
    """Unfailable shapes whose *entire* condition is a literal."""
    reasons: list[str] = []
    test = node.test
    if isinstance(test, ast.Constant) and isinstance(test.value, bool):
        reasons.append(f"literal boolean as the whole assertion condition: {test.value!r}")
    elif isinstance(test, ast.Constant) and isinstance(test.value, str) and test.value:
        reasons.append("bare non-empty string literal as the whole assertion condition")
    return reasons


def _boolop_reasons(node: ast.BoolOp) -> list[str]:
    """Unfailable shapes hiding inside a boolean expression.

    A literal ``True`` on one side of an ``or`` is always true and a literal
    ``False`` on one side of an ``and`` always false -- usually a placeholder
    that was never replaced. The subtler shape is an ``or`` of a comparison and
    its own negation: a tautology, so the assertion around it cannot fail.
    """
    reasons: list[str] = []
    if isinstance(node.op, ast.Or):
        if any(_literal(value, True) for value in node.values):
            reasons.append("literal True as an operand of a boolean or (always true)")
        pairs = (
            (first, second)
            for index, first in enumerate(node.values)
            for second in node.values[index + 1 :]
        )
        if any(_negation_pair(first, second) for first, second in pairs):
            reasons.append("a comparison and its own negation joined by or (tautology)")
    elif isinstance(node.op, ast.And):
        if any(_literal(value, False) for value in node.values):
            reasons.append("literal False as an operand of a boolean and (always false)")
    return reasons


_SOURCE_PINNING_REASON = (
    "source-text pinning: a value read from code text is compared against a string "
    "literal — parse the tree and assert structure, or assert behaviour"
)


def _source_read_reason(node: ast.Call, modules: set[str], members: set[str]) -> str | None:
    """Identify a *source read* — ``inspect.getsource`` and friends — in either
    spelling a test file realistically uses (module attribute, or the name imported
    from ``inspect``).

    Reading code text is not itself the defect; **matching** it is. Feeding the text
    to ``ast.parse`` is a structural assertion (a real test), while comparing it to a
    string literal pins prose that any refactor may legitimately change. So this
    helper answers "is this a source read?", and
    :func:`_compare_pins_source` decides whether it is being used as a pin.
    """
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _SOURCE_PINNING_ATTRS:
        if isinstance(func.value, ast.Name) and func.value.id in modules:
            return _SOURCE_PINNING_REASON
    elif isinstance(func, ast.Name) and func.id in members:
        if func.id in _SOURCE_PINNING_ATTRS:
            return _SOURCE_PINNING_REASON
    return None


def _contains_source_read(node: ast.AST, modules: set[str], members: set[str]) -> bool:
    """True when *node*'s subtree performs a source read (possibly nested inside a
    wrapper such as ``textwrap.dedent(inspect.getsource(fn))``)."""
    return any(
        isinstance(inner, ast.Call) and _source_read_reason(inner, modules, members) is not None
        for inner in ast.walk(node)
    )


def _names_bound_to_source_reads(
    tree: ast.Module, modules: set[str], members: set[str]
) -> set[str]:
    """Local names whose value came from a source read.

    Needed because the two-line pin (`body = inspect.getsource(fn)` then
    `assert "x" in body`) never puts the call and the comparison in the same node.
    The analysis is name-based and module-wide, so a same-named variable reused for
    something else would be reported too — an acceptable over-report for a test gate,
    and one a reader resolves by renaming rather than by lowering the gate.
    """
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value: ast.expr | None = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = [node.target]
        else:
            continue
        if value is None or not _contains_source_read(value, modules, members):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def _compare_pins_source(
    node: ast.Compare, modules: set[str], members: set[str], bound: set[str]
) -> bool:
    """True when a comparison matches code text against a string literal.

    Covers both spellings: the inline ``assert \"x\" in inspect.getsource(fn)`` and the
    two-step ``body = ...getsource(fn)`` / ``assert \"x\" in body``.
    """
    operands: list[ast.expr] = [node.left, *node.comparators]
    has_string = any(isinstance(o, ast.Constant) and isinstance(o.value, str) for o in operands)
    if not has_string:
        return False
    return any(
        (isinstance(o, ast.Name) and o.id in bound)
        or (isinstance(o, ast.Call) and _source_read_reason(o, modules, members) is not None)
        for o in operands
    )


def find_unfailable_shapes(source: str, *, filename: str) -> list[Violation]:
    """Return every unfailable shape in *source*, located in *filename*.

    Pure: it parses text and never touches the filesystem, so the snippets below
    can prove each banned shape is caught without writing a test module on disk.
    """
    tree = ast.parse(source, filename=filename)
    modules, members = _inspect_aliases(tree)
    bound = _names_bound_to_source_reads(tree, modules, members)
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            violations.extend(Violation(filename, node.lineno, r) for r in _assert_reasons(node))
        elif isinstance(node, ast.BoolOp):
            violations.extend(Violation(filename, node.lineno, r) for r in _boolop_reasons(node))
        elif isinstance(node, ast.Compare) and _compare_pins_source(node, modules, members, bound):
            violations.append(Violation(filename, node.lineno, _SOURCE_PINNING_REASON))
    return sorted(violations, key=lambda v: (v.path, v.lineno, v.reason))


def _test_files() -> list[Path]:
    """Every test module under tests/, minus this gate (it *names* the shapes)."""
    return sorted(path for path in TESTS.rglob("test_*.py") if path.resolve() != THIS_FILE)


# ---------------------------------------------------------------------------
# The repo-wide scan
# ---------------------------------------------------------------------------


class TestNoUnfailableShapes:
    """A passing suite must be able to fail: no assertion may be a no-op."""

    def test_scan_covers_the_test_tree(self) -> None:
        """A silently-empty walk would make the gate below vacuously green."""
        files = _test_files()
        assert len(files) >= 10, f"only {len(files)} test modules found under {TESTS}"
        assert TESTS / "audit" / "test_architecture.py" in files
        assert THIS_FILE not in files

    def test_no_unfailable_shapes_in_tests(self) -> None:
        violations: list[str] = []
        for path in _test_files():
            rel = path.relative_to(ROOT)
            for found in find_unfailable_shapes(path.read_text(), filename=str(rel)):
                violations.append(f"  {found.path}:{found.lineno} — {found.reason}")
        assert not violations, (
            f"Unfailable shapes in test modules ({len(violations)}): a green suite "
            "that cannot go red proves nothing.\n"
            "  FIX: assert the behaviour. Never delete the check, and never pin "
            "source text.\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# Proof the detector works: one synthetic snippet per banned shape
# ---------------------------------------------------------------------------

# The snippets are assembled from these tokens so that this gate's own source
# does not *read* like the shapes it bans (the file is excluded from the scan
# above, but a future text-based gate scanning test modules should not trip on
# the proof itself).
_TRUE = "True"
_FALSE = "False"
_SUBJECT = "value()"
_STRING = '"ok"'
_LONG_STRING = '"a long " "message"'
_IS_NOT_NONE = "is not None"
_IS_NONE = "is None"
_MODULE = "inspect"
_GETSOURCE = "getsource"

BANNED_SNIPPETS = [
    pytest.param(
        f"def test_x():\n    assert {_TRUE}\n",
        2,
        "boolean as the whole assertion condition",
        id="bool-true",
    ),
    pytest.param(
        f"def test_x():\n    assert {_FALSE}\n",
        2,
        "boolean as the whole assertion condition",
        id="bool-false",
    ),
    pytest.param(
        f"def test_x():\n    assert {_SUBJECT} or {_TRUE}\n",
        2,
        "literal True as an operand of a boolean or",
        id="or-true",
    ),
    pytest.param(
        f"def test_x():\n    assert {_SUBJECT} and {_FALSE}\n",
        2,
        "literal False as an operand of a boolean and",
        id="and-false",
    ),
    pytest.param(
        f"def test_x():\n    assert {_SUBJECT} {_IS_NOT_NONE} or {_SUBJECT} {_IS_NONE}\n",
        2,
        "its own negation",
        id="tautology-is-none",
    ),
    pytest.param(
        "def test_x():\n    assert totals == 0 or totals != 0\n",
        2,
        "its own negation",
        id="tautology-eq",
    ),
    pytest.param(
        f"def test_x():\n    body = {_MODULE}.{_GETSOURCE}(fn)\n    assert {_STRING} in body\n",
        3,
        "source-text pinning",
        id="getsource-attribute",
    ),
    pytest.param(
        f"def test_x():\n    lines = {_MODULE}.getsourcelines(fn)\n    assert {_STRING} in lines\n",
        3,
        "source-text pinning",
        id="getsourcelines-attribute",
    ),
    pytest.param(
        f"def test_x():\n    path = {_MODULE}.getsourcefile(fn)\n    assert {_STRING} == path\n",
        3,
        "source-text pinning",
        id="getsourcefile-attribute",
    ),
    pytest.param(
        f"def test_x():\n    assert {_STRING} in {_MODULE}.{_GETSOURCE}(fn)\n",
        2,
        "source-text pinning",
        id="getsource-inline",
    ),
    pytest.param(
        f"from {_MODULE} import {_GETSOURCE}\n"
        f"\n"
        f"def test_x():\n"
        f"    body = {_GETSOURCE}(fn)\n"
        f"    assert {_STRING} in body\n",
        5,
        "source-text pinning",
        id="getsource-imported-name",
    ),
    pytest.param(
        f"def test_x():\n    assert {_STRING}\n",
        2,
        "non-empty string literal",
        id="string-literal",
    ),
    pytest.param(
        f"def test_x():\n    assert {_LONG_STRING}\n",
        2,
        "non-empty string literal",
        id="implicit-string-concat",
    ),
]


@pytest.mark.parametrize(("source", "lineno", "fragment"), BANNED_SNIPPETS)
class TestDetectorCatchesBannedShapes:
    """Each unfailable shape, in isolation, must be reported at its own line."""

    def test_shape_is_caught(self, source: str, lineno: int, fragment: str) -> None:
        found = find_unfailable_shapes(source, filename="<snippet>")
        assert found, f"detector missed a banned shape:\n{source}"
        reasons = [v.reason for v in found]
        assert any(fragment in reason for reason in reasons), (
            f"no reason matched {fragment!r}: {reasons}"
        )
        assert [v.lineno for v in found] == sorted(v.lineno for v in found)
        assert lineno in {v.lineno for v in found}, f"wrong location: {found}"
        assert all(v.path == "<snippet>" for v in found)


LEGITIMATE_SNIPPETS = [
    pytest.param(
        "def test_ok():\n"
        "    results = compute()\n"
        "    assert results is not None\n"
        "    assert [r.value for r in results] == [1, 2]\n"
        "    assert not errors\n",
        id="ordinary-assertions",
    ),
    pytest.param(
        # Containment in a string is a real (if blunt) check -- only a *bare*
        # string literal used as the whole condition is the banned shape.
        f"def test_ok():\n    body = render()\n    assert {_STRING} in body\n    assert body\n",
        id="substring-containment",
    ),
    pytest.param(
        # Two different subjects in an `or` is a genuine disjunction.
        "def test_ok():\n    assert a is None or b is None\n",
        id="real-disjunction",
    ),
    pytest.param(
        # `is True` in a comparison is a behavioural assertion, not a literal one.
        "def test_ok():\n    flag = compute()\n    assert flag is True\n",
        id="identity-compare",
    ),
    pytest.param(
        # A `getsource` attribute on some *other* object is not an inspect pin.
        "def test_ok():\n"
        "    reader = source_reader()\n"
        "    body = reader.getsource()\n"
        f"    assert {_STRING} in body\n",
        id="foreign-getsource",
    ),
    pytest.param(
        # Reading code text to *parse* it is a structural assertion, which is a real
        # test — only matching the text against a literal is the banned shape, so this
        # must stay allowed. (A gate that banned the read outright would force call-site
        # analysis to be deleted rather than improved.)
        "import ast\n"
        "def test_ok():\n"
        f"    src = {_MODULE}.{_GETSOURCE}(compute)\n"
        "    tree = ast.parse(src)\n"
        "    assert tree.body\n",
        id="source-parsed-not-matched",
    ),
]


@pytest.mark.parametrize("source", LEGITIMATE_SNIPPETS)
class TestDetectorLeavesRealTestsAlone:
    """Snippets of legitimate tests must produce nothing (no false positives)."""

    def test_nothing_is_caught(self, source: str) -> None:
        assert find_unfailable_shapes(source, filename="<snippet>") == []
