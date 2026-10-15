"""A provider payload change must move the cache version tag it depends on.

The version tag that makes a cached row unreachable (``cache._RAW_SLOT_VERSION``,
``normalize.contracts.CANONICAL_CONTRACT_VERSION``) lives in a different file from
the payload it describes — and the payload is read back through a 24h TTL, so
forgetting the bump is invisible at review time and only shows up as a report
publishing pre-fix numbers. That is exactly what happened on 2026-10-14: the
yfinance margin derivation was fixed (``4e1a75f``, 15:41) while CF's canonical
snapshot (cached 06:19 the same day) kept serving Yahoo's ``info.operatingMargins``
— the report then published an operating margin (49.33%) above its own gross margin
(42.49%) beside an income block that computes 39.09%.

This guard makes the coupling mechanical: every module that can write a cached
payload has its normalized-source hash pinned here, together with the declared
versions. Editing one of those files fails until the author STATES whether a cached
row's meaning changed — bump the version and explain it in the comment block above
it, or re-pin to record that the change is read-compatible.

    python scripts/pin_provider_payloads.py     # after deciding

Pinned (see the script for the exact globs): every module under
``finrobot/engine/data/providers/`` plus ``normalize/contracts.py`` (the file that
declares the canonical contract version and the payload schemas it versions).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PIN_FILE = Path(__file__).resolve().parent / "fixtures" / "provider_payload_pins.json"

_spec = importlib.util.spec_from_file_location(
    "_pin_provider_payloads", _REPO_ROOT / "scripts" / "pin_provider_payloads.py"
)
assert _spec is not None and _spec.loader is not None
pins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pins)


def _pinned_sources() -> dict[str, str]:
    """``{repo-relative path: content hash}`` as pinned."""
    return json.loads(_PIN_FILE.read_text(encoding="utf-8"))["sources"]


def _pinned_declared() -> dict[str, int]:
    """``{version name: value}`` as pinned."""
    return json.loads(_PIN_FILE.read_text(encoding="utf-8"))["declared"]


def test_declared_cache_versions_match_the_pin() -> None:
    """A bump without re-pinning (or a re-pin without the bump) is a half-done change."""
    pinned = _pinned_declared()
    live = pins.declared_versions()

    assert pinned == live, (
        "the declared cache versions moved without refreshing "
        f"{_PIN_FILE.relative_to(_REPO_ROOT).as_posix()} — if the change alters what a "
        "cached row MEANS, that is correct (keep it) and you must re-pin with "
        "`python scripts/pin_provider_payloads.py`; if it does not, revert the bump."
    )


def test_every_cached_payload_source_is_pinned() -> None:
    """A newly added provider module must be pinned too, not silently unpinned."""
    current = pins.source_pins()
    pinned = _pinned_sources()

    assert set(current) == set(pinned), (
        "the set of cached-payload sources changed (added/removed/renamed): "
        f"current-only={sorted(set(current) - set(pinned))} "
        f"pinned-only={sorted(set(pinned) - set(current))} — re-pin with "
        "`python scripts/pin_provider_payloads.py`."
    )


def test_provider_payload_sources_are_unchanged_since_the_pin() -> None:
    """Any edit to a cached-payload source forces the version decision.

    A mismatch does NOT mean the change is wrong — it means the author must state
    whether a cached row's meaning moved (bump + explain) or not (re-pin).
    """
    pinned = _pinned_sources()
    current = pins.source_pins()
    changed = sorted(name for name, digest in current.items() if pinned.get(name) != digest)

    assert not changed, (
        "these cached-payload sources changed since the pin was taken:\n  "
        + "\n  ".join(changed)
        + "\n\nDecide: does a cached row's MEANING change? If yes, bump "
        "_RAW_SLOT_VERSION for the affected DataType (and/or "
        "CANONICAL_CONTRACT_VERSION) and record why in the comment block above it. "
        "Then re-pin:\n  python scripts/pin_provider_payloads.py"
    )
