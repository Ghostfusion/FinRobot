"""Golden contract fixtures — the pinned artifacts, stored as PAYLOADS (§7.2).

Each file under ``fixtures/contract/`` is a verbatim subset of one row of
``~/.finrobot/artifacts.db`` (see ``scripts/extract_contract_fixtures.py``): the
paths every clause reads, values untouched, plus the id of the row it came from
and the verdict EVERY clause returned on it at extraction time.

Two things make these fixtures worth their 600 KB rather than a dict literal:

* ``is not None`` guards cannot see a MISSING key. The first C11 probe tested
  ``a != b`` behind such a guard and missed all 63 divergent artifacts, because the
  defect IS the absent key (``test_instance_b_still_carries_the_omitted_root_slot``
  pins that shape). A hand-written fixture would have carried the same guard.
* The recorded verdict map is a regression oracle over real corpus shapes. A
  preferred-name change, a renamed field, or a container that stopped being a dict
  shows up here as a diff a reviewer can read, instead of as a clause that quietly
  stops firing in production.

Regenerate with ``uv run --no-sync python scripts/extract_contract_fixtures.py``
and REVIEW THE DIFF — a changed fixture means either a clause changed its reading
or the corpus shape moved. Both are worth knowing; neither is worth hiding.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from finrobot.artifact.contract import CONTRACT_CLAUSES
from finrobot.artifact.models import (
    Artifact,
    ArtifactAssumptions,
    ArtifactComputeVersion,
    ArtifactInputs,
    ArtifactMeta,
    ArtifactOutputs,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "contract"
_FIXTURE_PATHS = sorted(_FIXTURE_DIR.glob("*.json"))
_ALL_CLAUSES = tuple(CONTRACT_CLAUSES)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(fixture: dict[str, Any]) -> Artifact:
    """Rebuild the stored artifact from the retained paths. The scaffolding fields
    (version, caution source, timestamps) are placeholders: no clause reads them."""
    created = datetime.fromisoformat(fixture["artifact_id"][4:23]).replace(tzinfo=timezone.utc)
    return Artifact(
        id=fixture["artifact_id"],
        ticker=fixture["ticker"],
        type=fixture["type"],
        inputs=ArtifactInputs(
            data_source="yfinance",
            data_fetched_at=created,
            raw_data=fixture["inputs_raw_data"],
        ),
        assumptions=ArtifactAssumptions(parameters={}),
        compute_version=ArtifactComputeVersion(version="0.1.0", formula_id="fixture"),
        outputs=ArtifactOutputs(
            structured=fixture["outputs_structured"],
            summary_text="",
            warnings=[],
        ),
        meta=ArtifactMeta(created_at=created, source="fixture:test_contract_fixtures"),
    )


def test_the_fixture_set_is_present() -> None:
    """An empty or missing directory would make every parametrized case below
    vanish silently, and the suite would still be green."""
    assert len(_FIXTURE_PATHS) >= 12


@pytest.mark.parametrize("path", _FIXTURE_PATHS, ids=lambda p: p.stem)
def test_fixture_records_its_provenance(path: Path) -> None:
    """Every fixture names the row it came from, the store it came from, and when —
    so a regeneration can be checked against the corpus instead of trusted."""
    fixture = _load(path)
    assert fixture["artifact_id"].startswith("art_")
    # The file name is the id flattened for Windows ("_" separators, no ":").
    assert path.stem == fixture["artifact_id"].replace("_equity_research", "").replace(":", "-")
    assert fixture["source"] == "~/.finrobot/artifacts.db"
    assert fixture["notes"]
    assert fixture["extracted_at"]


@pytest.mark.parametrize("path", _FIXTURE_PATHS, ids=lambda p: p.stem)
def test_fixture_records_every_clause_verdict(path: Path) -> None:
    """A NEW clause must be measured against the corpus before it can be armed — so
    adding one turns this red until the fixtures are regenerated and the resulting
    verdicts are read."""
    fixture = _load(path)
    assert set(fixture["verdicts"]) == {clause.id for clause in _ALL_CLAUSES}


@pytest.mark.parametrize("path", _FIXTURE_PATHS, ids=lambda p: p.stem)
def test_fixture_verdicts_are_unchanged(path: Path) -> None:
    """THE ORACLE: every registered clause, re-run over the stored payload."""
    fixture = _load(path)
    artifact = _artifact(fixture)
    expected = {cid: bool(fired) for cid, fired in fixture["verdicts"].items()}
    measured = {clause.id: clause.check(artifact) is not None for clause in _ALL_CLAUSES}
    assert measured == expected
    assert set(fixture["pinned_for"]) <= {cid for cid, fired in measured.items() if fired}


@pytest.mark.parametrize("path", _FIXTURE_PATHS, ids=lambda p: p.stem)
def test_fixture_never_raises(path: Path) -> None:
    """These are real corpus shapes, including the ones with null leaves, missing
    sub-documents and ``None`` where a dict is expected. A clause that raised here
    would blank a live run at the persist boundary."""
    artifact = _artifact(_load(path))
    for clause in _ALL_CLAUSES:
        clause.check(artifact)


def test_instance_b_still_carries_the_omitted_root_slot() -> None:
    """§7.2's whole argument, pinned as a test: the C11 defect is a MISSING KEY —
    the root writer emits nothing while the synthesis writes ``false``. An
    ``is not None`` guard cannot see it, which is why the first probe measured C11
    at zero and the repaired predicate measures 63 of the 98 equity artifacts."""
    fixture = _load(next(p for p in _FIXTURE_PATHS if "99cdca" in p.name))
    structured = fixture["outputs_structured"]
    assert "valuation_withheld" not in structured
    assert structured["valuation_synthesis"]["valuation_withheld"] is False
    assert fixture["verdicts"]["C11"] is True


def test_the_calibrated_false_positive_guards_are_pinned() -> None:
    """Two predicates were re-calibrated because their first form was over-broad, and
    each correction is pinned by a real payload that must stay QUIET: ``C8`` on SKM
    (its degenerate band belongs to ``C9``, so ``C8`` reads 7 of §1.1's 8 rather than
    8) and ``C14b`` on the withheld path's own disclaimer (the coarse token scan
    flagged that class 27 times)."""
    skm = _load(next(p for p in _FIXTURE_PATHS if "2e8161" in p.name))
    assert skm["verdicts"]["C9"] is True
    assert skm["verdicts"]["C8"] is False

    disclaimer = _load(next(p for p in _FIXTURE_PATHS if "54c0a6" in p.name))
    assert disclaimer["verdicts"]["C14b"] is False
