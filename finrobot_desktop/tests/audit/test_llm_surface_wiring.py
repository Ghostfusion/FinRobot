"""LLM surface wiring audit — no reachable-surface artefact may silently rot.

The LLM-facing surface of this repo is almost entirely *names and prose living
outside the type system*: sub-agent instruction prompts
(``agents/instructions/{role}_agent.md``), the declared role tuple in
``agents/factory.py``, the ordered ``PipelineStep`` names of the equity-research
pipeline, the pipeline keys of ``pipelines/registry.py`` (the single source that
CLI / REST / orchestrator / SDK all read), the CLI's references to those keys,
and every ``SKILL.md`` the ``SkillRegistry`` loads. None of it is checked by
mypy, and none of it fails a build when it drifts — it simply stops being
reachable. This gate exists because that decay is silent:

* A prompt asset can ship and never be loaded. A sibling checkout of this repo
  had exactly that: ``bull_agent.md`` / ``bear_agent.md`` / ``judge_agent.md``
  were declared as a "Debate" chain in the README, but the router only ever
  built the five roles in ``SUB_AGENT_ROLES`` — three prompt files nothing could
  reach (or, read the other way, a debate feature that silently vanished).
* A step can be renamed in Python while a mirror elsewhere keeps the old list.
  ``desktop/src/stores/runStreamStore.ts`` mirrors the equity-research step
  order to render progress before the SSE lands; a stale 8-entry mirror once
  made the panel drop a real step and mislabel the rest (the 6-vs-8 bug called
  out in that file's own TS comment). Its comment demands an EXACT match.
* A pipeline can be registered but unbuildable, or referenced by the CLI under a
  key the registry does not contain — ``get_pipeline_factories()[key]`` would
  raise ``KeyError`` at run time, after the user already paid for deps setup.
* A skill can load with an empty trigger list or body and never surface in
  ``SkillRegistry.search`` — the only discovery path the LLM has.

Every check below is a small pure function over already-parsed data, so its
teeth are proven with a synthetic input (the ``*_bites`` tests) without touching
the tree. Failures name the ``file:line`` and say why the drift matters.

This module does NOT edit ``finrobot/`` — a genuine gap is a finding for the
parent to triage. Known finding on the tree as of this audit: the three prompt
files named above are unreferenced (see ``test_no_orphan_instruction_files``).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
FINROBOT = ROOT / "finrobot"
FACTORY = FINROBOT / "engine" / "agents" / "factory.py"
INSTRUCTIONS = FINROBOT / "engine" / "agents" / "instructions"
EQUITY_PIPELINE = FINROBOT / "engine" / "pipelines" / "equity_research.py"
FUND_PIPELINE = FINROBOT / "engine" / "pipelines" / "fund_research.py"
CLI = FINROBOT / "cli.py"
# The desktop mirrors the equity-research step order for pre-SSE progress labels;
# its own comment requires the list to match ``create_equity_research_pipeline``
# EXACTLY (order + count).
RUN_STREAM_STORE = ROOT / "desktop" / "src" / "stores" / "runStreamStore.ts"

_ROLE_VAR = "SUB_AGENT_ROLES"
_STEP_CLASS = "PipelineStep"


def _rel(path: Path) -> str:
    """Repo-relative POSIX path for a failure message (readable, portable)."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Check 1 — sub-agent role ⇄ instruction-file wiring
# ---------------------------------------------------------------------------


def parse_declared_roles(source: str) -> tuple[tuple[str, ...], int]:
    """Parse the ``SUB_AGENT_ROLES`` tuple out of the factory source with ``ast``.

    Returns ``(roles, lineno)``. The role list is read from code, never copied
    by hand, so the gate cannot drift from the factory the way the factory
    drifted from its prompts.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            targets = [node.target] if isinstance(node.target, ast.Name) else []
        elif isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
        else:
            continue
        for target in targets:
            if target.id == _ROLE_VAR:
                roles = ast.literal_eval(node.value)
                return tuple(str(role) for role in roles), node.lineno
    raise AssertionError(f"{_ROLE_VAR} is not declared in the factory source")


def parse_instruction_filenames(directory: Path) -> tuple[str, ...]:
    """Every ``*_agent.md`` prompt directly under ``directory`` (from disk)."""
    return tuple(sorted(path.name for path in directory.glob("*_agent.md")))


@dataclass(frozen=True)
class RoleWiringGaps:
    """Roles with no prompt, and prompts no role loads."""

    missing_instruction: tuple[str, ...]
    orphan_instruction: tuple[str, ...]


#: Prompt assets that ship deliberately UNWIRED. The debate chain is recorded product
#: intent (``AGENT_ONBOARDING.md`` "phantom debate agents"), so the files are kept rather
#: than deleted — but an exemption is only honest while it stays documented, which
#: ``test_documented_exemptions_are_still_recorded`` enforces. This is the "reachable, or
#: whitelisted with a reason" rule: a new orphan still fails, and a stale exemption (file
#: deleted, or runbook no longer naming it) fails too.
UNWIRED_PROMPT_ASSETS: frozenset[str] = frozenset(
    {"bull_agent.md", "bear_agent.md", "judge_agent.md"}
)

#: The runbook lives at the repository root, one level above the desktop package.
RUNBOOK = ROOT.parent / "AGENT_ONBOARDING.md"


def role_wiring_gaps(
    roles: Sequence[str],
    instruction_filenames: Sequence[str],
    *,
    exempt: Collection[str] = (),
) -> RoleWiringGaps:
    """Convention: role ``x`` loads ``x_agent.md`` (see ``create_sub_agents``).

    ``exempt`` names prompt assets that ship knowingly unwired and are recorded in the
    runbook; they are not reported as orphans.
    """
    expected = {f"{role}_agent.md" for role in roles}
    actual = set(instruction_filenames)
    return RoleWiringGaps(
        missing_instruction=tuple(sorted(expected - actual)),
        orphan_instruction=tuple(sorted(actual - expected - set(exempt))),
    )


class TestSubAgentInstructionWiring:
    """Every role has a prompt, and every prompt is loaded by a role."""

    def test_every_declared_role_has_an_instruction_file(self) -> None:
        roles, lineno = parse_declared_roles(FACTORY.read_text(encoding="utf-8"))
        filenames = parse_instruction_filenames(INSTRUCTIONS)
        gaps = role_wiring_gaps(roles, filenames)
        assert not gaps.missing_instruction, (
            f"{_rel(FACTORY)}:{lineno}: role(s) {list(gaps.missing_instruction)} are declared in "
            f"{_ROLE_VAR} but have no {_rel(INSTRUCTIONS)}/<role>_agent.md — the factory reads "
            "that path unconditionally at startup"
        )

    def test_no_orphan_instruction_files(self) -> None:
        roles, lineno = parse_declared_roles(FACTORY.read_text(encoding="utf-8"))
        filenames = parse_instruction_filenames(INSTRUCTIONS)
        gaps = role_wiring_gaps(roles, filenames, exempt=UNWIRED_PROMPT_ASSETS)
        orphans = ", ".join(f"{_rel(INSTRUCTIONS)}/{name}:1" for name in gaps.orphan_instruction)
        assert not gaps.orphan_instruction, (
            f"prompt asset(s) exist that no role loads: {orphans} — {_rel(FACTORY)}:{lineno} "
            f"only builds {list(roles)}. A shipped prompt nothing routes is dead weight (or a "
            "feature that silently vanished). Route the role, delete the file, or — if it is "
            "deliberate — add it to UNWIRED_PROMPT_ASSETS and record it in AGENT_ONBOARDING.md."
        )

    def test_documented_exemptions_are_still_recorded_and_still_present(self) -> None:
        """An exemption has to keep earning its place: the file must still ship, and the
        runbook must still name it. A whitelist that outlives its reason is how a dead
        asset becomes permanent."""
        present = set(parse_instruction_filenames(INSTRUCTIONS))
        runbook = RUNBOOK.read_text(encoding="utf-8")
        for name in sorted(UNWIRED_PROMPT_ASSETS):
            assert name in present, (
                f"{name} is exempted as a deliberate unwired asset but no longer ships — "
                "drop the exemption"
            )
            stem = name.split("_")[0]
            assert stem in runbook, (
                f"{name} is exempted but AGENT_ONBOARDING.md no longer names {stem!r} — "
                "either wire the role, delete the file, or record it in the runbook"
            )

    def test_role_wiring_checker_bites(self) -> None:
        gaps = role_wiring_gaps(("data", "analysis"), ("data_agent.md", "ghost_agent.md"))
        assert gaps.missing_instruction == ("analysis_agent.md",)
        assert gaps.orphan_instruction == ("ghost_agent.md",)
        clean = role_wiring_gaps(("data",), ("data_agent.md",))
        assert clean.missing_instruction == ()
        assert clean.orphan_instruction == ()
        # An exemption suppresses its own orphan and nothing else.
        suppressed = role_wiring_gaps(
            ("data",), ("data_agent.md", "ghost_agent.md"), exempt=("ghost_agent.md",)
        )
        assert suppressed.orphan_instruction == ()


# ---------------------------------------------------------------------------
# Check 2 — equity-research step names are unique, non-empty, and mirrored
# ---------------------------------------------------------------------------


def parse_pipeline_step_names(source: str) -> tuple[list[tuple[int, str]], list[int]]:
    """(named steps as ``(lineno, name)``, linenos of ``PipelineStep`` calls with no name).

    ``name`` is read from the keyword or the first positional ``str`` literal; a
    call whose name is neither is reported as unnamed rather than silently
    dropped (which would mask a step added without a label).
    """
    tree = ast.parse(source)
    named: list[tuple[int, str]] = []
    unnamed: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != _STEP_CLASS:
            continue
        name_value: str | None = None
        for keyword in node.keywords:
            if keyword.arg != "name":
                continue
            if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                name_value = keyword.value.value
        if name_value is None and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                name_value = first.value
        if name_value is None:
            unnamed.append(node.lineno)
        else:
            named.append((node.lineno, name_value))
    named.sort()
    return named, unnamed


def step_name_violations(steps: Sequence[tuple[int, str]], where: str) -> list[str]:
    """Duplicate or empty ``PipelineStep`` names, each with a ``where:line`` anchor.

    Step names are the run's progress/SSE vocabulary and the desktop mirror's
    key; a collision makes two steps indistinguishable in the stream, and an
    empty name renders as a blank progress row.
    """
    violations: list[str] = []
    first_seen: dict[str, int] = {}
    for lineno, name in steps:
        if not name.strip():
            violations.append(f"{where}:{lineno}: PipelineStep has an empty name")
            continue
        if name in first_seen:
            violations.append(
                f"{where}:{lineno}: duplicate PipelineStep name {name!r} "
                f"(first declared at {where}:{first_seen[name]})"
            )
        else:
            first_seen[name] = lineno
    return violations


_TS_STRING_RE = re.compile(r"'([^']+)'")


def parse_ts_step_names(source: str, pipeline_key: str) -> list[str]:
    """Extract the ``pipeline_key: [ 'a', 'b', … ]`` string list from the TS mirror."""
    match = re.search(rf"{re.escape(pipeline_key)}\s*:\s*\[(.*?)\]", source, re.DOTALL)
    if match is None:
        return []
    return _TS_STRING_RE.findall(match.group(1))


class TestEquityPipelineStepWiring:
    """The equity pipeline's step list is well-formed and the desktop mirror agrees."""

    def test_step_names_are_unique_and_non_empty(self) -> None:
        source = EQUITY_PIPELINE.read_text(encoding="utf-8")
        named, unnamed = parse_pipeline_step_names(source)
        where = _rel(EQUITY_PIPELINE)
        assert not unnamed, (
            f"{where}:{unnamed[0]}: PipelineStep call with no literal name — every step must "
            "carry a name (it is the progress/SSE label and the mirror key)"
        )
        assert named, f"{where}: no PipelineStep(name=...) found in the equity pipeline"
        violations = step_name_violations(named, where)
        assert not violations, "\n".join(violations)

    def test_desktop_step_mirror_matches_python_order(self) -> None:
        if not RUN_STREAM_STORE.exists():
            pytest.skip(f"{_rel(RUN_STREAM_STORE)} not present in this checkout")
        named, _ = parse_pipeline_step_names(EQUITY_PIPELINE.read_text(encoding="utf-8"))
        actual = [name for _, name in named]
        mirror = parse_ts_step_names(RUN_STREAM_STORE.read_text(encoding="utf-8"), "research")
        assert mirror == actual, (
            f"{_rel(RUN_STREAM_STORE)} mirrors the equity-research step order for pre-SSE "
            f"progress labels; it lists {mirror} but the pipeline registers {actual} — a "
            "shorter mirror drops a real step and mislabels the rest (the 6-vs-8 bug in its "
            "own comment)"
        )

    def test_step_name_checker_bites(self) -> None:
        violations = step_name_violations([(10, "a"), (20, "a"), (30, "")], "x.py")
        assert any("duplicate" in v for v in violations)
        assert any("empty" in v for v in violations)
        assert not step_name_violations([(1, "a"), (2, "b")], "x.py")
        assert parse_ts_step_names("research: ['a', 'b'],", "research") == ["a", "b"]


class TestFundPipelineStepWiring:
    """The fund pipeline's four steps are well-formed and the desktop mirror agrees.

    Same contract as the equity pin above, with one extra hazard: the fund run's
    step vocabulary (fund_data / fund_assessment / fund_narrative / fund_report)
    shares no name with the equity spine and lives under its OWN registry key
    (``fund_research``, which is also the artifact type), so a mirror keyed
    ``research`` would label a fund run with the equity steps — and the panel
    would silently render names for steps that never ran.
    """

    def test_step_names_are_unique_and_non_empty(self) -> None:
        source = FUND_PIPELINE.read_text(encoding="utf-8")
        named, unnamed = parse_pipeline_step_names(source)
        where = _rel(FUND_PIPELINE)
        assert not unnamed, (
            f"{where}:{unnamed[0]}: PipelineStep call with no literal name — every step must "
            "carry a name (it is the progress/SSE label and the mirror key)"
        )
        assert named, f"{where}: no PipelineStep(name=...) found in the fund pipeline"
        violations = step_name_violations(named, where)
        assert not violations, "\n".join(violations)

    def test_desktop_step_mirror_matches_python_order(self) -> None:
        if not RUN_STREAM_STORE.exists():
            pytest.skip(f"{_rel(RUN_STREAM_STORE)} not present in this checkout")
        named, _ = parse_pipeline_step_names(FUND_PIPELINE.read_text(encoding="utf-8"))
        actual = [name for _, name in named]
        mirror = parse_ts_step_names(RUN_STREAM_STORE.read_text(encoding="utf-8"), "fund_research")
        assert mirror == actual, (
            f"{_rel(RUN_STREAM_STORE)} mirrors the fund step order for pre-SSE progress "
            f"labels; it lists {mirror} but the pipeline registers {actual} — a shorter "
            "mirror drops a real step and mislabels the rest"
        )


# ---------------------------------------------------------------------------
# Check 3 — pipeline registry keys resolve and line up with the CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PipelineKeyDrift:
    """Keys the CLI cannot reach, and CLI keys the registry does not know."""

    registered_but_not_in_cli: tuple[str, ...]
    in_cli_but_not_registered: tuple[str, ...]


def pipeline_key_drift(registered: Sequence[str], cli_keys: Sequence[str]) -> PipelineKeyDrift:
    """Set-difference both ways between the registry and the CLI's references."""
    reg, cli = set(registered), set(cli_keys)
    return PipelineKeyDrift(
        registered_but_not_in_cli=tuple(sorted(reg - cli)),
        in_cli_but_not_registered=tuple(sorted(cli - reg)),
    )


_CLI_BUILD_RE = re.compile(r"_build_pipeline\(\s*\"([^\"]+)\"")
_CLI_FACTORY_RE = re.compile(r"factories\[\s*\"([^\"]+)\"\s*\]")


def parse_cli_pipeline_keys(source: str) -> set[str]:
    """Keys the CLI passes to ``_build_pipeline`` / ``factories[...]`` (both call forms)."""
    return set(_CLI_BUILD_RE.findall(source)) | set(_CLI_FACTORY_RE.findall(source))


class TestPipelineRegistryWiring:
    """Registered pipelines are buildable and reachable from the CLI."""

    def test_every_registered_pipeline_factory_resolves(self) -> None:
        from finrobot.engine.pipelines.registry import iter_pipeline_specs

        specs = iter_pipeline_specs()
        keys = [spec.key for spec in specs]
        assert len(keys) == len(set(keys)), f"duplicate pipeline keys in the registry: {keys}"
        for spec in specs:
            assert spec.key.strip(), "pipeline spec with an empty key"
            factory = spec.factory  # lazy import — the registry's whole reason to exist
            expected = spec.import_path.partition(":")[2]
            assert callable(factory), f"{spec.key}: {spec.import_path!r} is not callable"
            assert factory.__name__ == expected, (
                f"{spec.key}: {spec.import_path!r} resolves to {factory.__name__!r}, "
                f"not {expected!r}"
            )

    def test_registry_and_cli_keys_agree(self) -> None:
        from finrobot.engine.pipelines.registry import iter_pipeline_specs

        registered = [spec.key for spec in iter_pipeline_specs()]
        cli_keys = parse_cli_pipeline_keys(CLI.read_text(encoding="utf-8"))
        drift = pipeline_key_drift(registered, sorted(cli_keys))
        assert not drift.in_cli_but_not_registered, (
            f"{_rel(CLI)} references pipeline key(s) {list(drift.in_cli_but_not_registered)} "
            "through _build_pipeline()/factories[] that pipelines/registry.py does not "
            "register — get_pipeline_factories()[key] raises KeyError at run time"
        )
        assert not drift.registered_but_not_in_cli, (
            f"pipeline key(s) {list(drift.registered_but_not_in_cli)} are registered but no "
            f"CLI subcommand reaches them ({_rel(CLI)}) — a pipeline no user path can build"
        )

    def test_pipeline_key_drift_checker_bites(self) -> None:
        drift = pipeline_key_drift(["research"], ["research", "ghost"])
        assert drift.in_cli_but_not_registered == ("ghost",)
        assert drift.registered_but_not_in_cli == ()
        drift2 = pipeline_key_drift(["research", "dcf"], ["research"])
        assert drift2.registered_but_not_in_cli == ("dcf",)
        clean = pipeline_key_drift(["research"], ["research"])
        assert clean.in_cli_but_not_registered == ()
        assert clean.registered_but_not_in_cli == ()
        snippet = 'x = _build_pipeline("ddm", d); y = factories["lbo"]'
        assert parse_cli_pipeline_keys(snippet) == {"ddm", "lbo"}


# ---------------------------------------------------------------------------
# Check 4 — every loaded skill is well-formed and discoverable
# ---------------------------------------------------------------------------


def skill_reachability_violations(skills: Sequence[Any]) -> list[str]:
    """Skills whose id/name/description/triggers/body is empty or whose id collides.

    Relies only on the duck-typed ``Skill`` fields, so it can be exercised with
    synthetic objects in the ``*_bites`` test.
    """
    violations: list[str] = []
    seen: dict[str, str] = {}
    for skill in skills:
        where = str(getattr(skill, "source_path", "?"))
        skill_id = str(getattr(skill, "id", "") or "")
        if not skill_id.strip():
            violations.append(f"{where}:1: skill has an empty id")
        elif skill_id in seen:
            violations.append(
                f"{where}:1: duplicate skill id {skill_id!r} (already loaded from {seen[skill_id]})"
            )
        else:
            seen[skill_id] = f"{where}:1"
        if not str(getattr(skill, "name", "") or "").strip():
            violations.append(f"{where}:1: skill {skill_id!r} has an empty name")
        if not str(getattr(skill, "description", "") or "").strip():
            violations.append(f"{where}:1: skill {skill_id!r} has an empty description")
        triggers = [str(t) for t in (getattr(skill, "triggers", None) or []) if str(t).strip()]
        if not triggers:
            violations.append(
                f"{where}:1: skill {skill_id!r} declares no non-empty trigger — "
                "SkillRegistry.search can never surface it by keyword"
            )
        if not str(getattr(skill, "full_content", "") or "").strip():
            violations.append(f"{where}:1: skill {skill_id!r} has an empty body (full_content)")
    return violations


class TestSkillRegistryReachability:
    """Every ``SKILL.md`` loads, has metadata, and is findable by name."""

    @staticmethod
    def _registry() -> tuple[Path, Any]:
        from finrobot.engine.skills.registry import SkillRegistry
        from finrobot.paths import default_skills_dir

        skills_dir = Path(default_skills_dir())
        if not skills_dir.exists():
            pytest.skip(f"skills dir {skills_dir} not present in this checkout")
        return skills_dir, SkillRegistry(skills_dir)

    def test_every_skill_file_loads_and_ids_are_unique(self) -> None:
        skills_dir, registry = self._registry()
        files = sorted(skills_dir.glob("**/SKILL.md"))
        assert files, f"no SKILL.md found under {skills_dir}"
        assert registry.count == len(files), (
            f"{len(files)} SKILL.md files but only {registry.count} loaded — a duplicate id "
            "silently overwrites in the id→Skill dict and a SkillLoadError is only logged"
        )
        violations = skill_reachability_violations(registry.list_all())
        assert not violations, "\n".join(violations)

    def test_every_skill_is_findable_by_its_own_name(self) -> None:
        _, registry = self._registry()
        misses = [
            skill.id for skill in registry.list_all() if skill not in registry.search(skill.name)
        ]
        assert not misses, (
            f"SkillRegistry.search(name) does not return {misses} — the skill loads but the only "
            "discovery path the LLM has cannot surface it"
        )

    def test_skill_reachability_checker_bites(self) -> None:
        from types import SimpleNamespace

        good = SimpleNamespace(
            id="dcf-model",
            name="Discounted Cash Flow",
            description="d",
            triggers=["dcf"],
            full_content="body",
            source_path="a/SKILL.md",
        )
        assert not skill_reachability_violations([good])
        bad = SimpleNamespace(
            id="", name="", description="", triggers=[], full_content="", source_path="y/SKILL.md"
        )
        violations = skill_reachability_violations([bad])
        assert any("empty id" in v for v in violations)
        assert any("empty name" in v for v in violations)
        assert any("trigger" in v for v in violations)
        assert any("empty body" in v for v in violations)
        duplicate = SimpleNamespace(
            id="dcf-model",
            name="Other",
            description="d",
            triggers=["x"],
            full_content="body",
            source_path="b/SKILL.md",
        )
        assert any(
            "duplicate skill id" in v for v in skill_reachability_violations([good, duplicate])
        )
