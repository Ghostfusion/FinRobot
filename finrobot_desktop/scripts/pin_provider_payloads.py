#!/usr/bin/env python
"""Refresh the provider-payload source pins used by the cache-version audit.

The raw cache slot's tag lives in a different file from the payload it describes,
which is how the 2026-10-14 yfinance margin fix shipped without one: the CF report
served a pre-fix payload for a full TTL after the fix landed (see the ``financials
v6`` / ``CANONICAL_CONTRACT_VERSION v13`` notes, now in
``engine/data/semantics.py``).

``tests/audit/test_provider_cache_payload_pins.py`` pins three things so an edit
fails until the author STATES whether a cached row's meaning changed:

* ``sources``  — the normalized source hash of every cached-payload source module
  (a new/renamed provider must be pinned too);
* ``declared`` — the human version tags (``RAW_SLOT_VERSION`` /
  ``CANONICAL_CONTRACT_VERSION``);
* ``acknowledged`` — the ``semantics.semantics_digest`` per ``(data_type,
  provider)``, i.e. the digest of the declared FIELD MEANING + the producing
  provider module's source, which is exactly what bakes the slot tag.

This script does the mechanical half:

    python scripts/pin_provider_payloads.py

Run it AFTER deciding whether the change needs a version bump — if it does, bump
``RAW_SLOT_VERSION`` (and/or ``CANONICAL_CONTRACT_VERSION``) in the same commit and
say why in the comment block above it, then run this script to re-pin.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "finrobot"
PIN_FILE = REPO_ROOT / "tests" / "audit" / "fixtures" / "provider_payload_pins.json"


def normalized_sha(text_bytes: bytes) -> str:
    """Hash the source with line endings normalized.

    The pin must be identical on a Windows checkout (CRLF) and in CI (LF), so the
    hash is taken over ``\\n``-normalized bytes rather than raw file bytes.
    """
    return hashlib.sha256(text_bytes.replace(b"\r\n", b"\n")).hexdigest()[:16]


def source_pins() -> dict[str, str]:
    """``{repo-relative posix path: content hash}`` for every cached-payload source."""
    pins: dict[str, str] = {}
    for pattern in ("engine/data/providers/*.py", "engine/data/normalize/contracts.py"):
        for path in sorted(PACKAGE.glob(pattern)):
            if path.name == "__init__.py":
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            pins[rel] = normalized_sha(path.read_bytes())
    return pins


def declared_versions() -> dict[str, int]:
    """The human version tags a payload change must move."""
    from finrobot.engine.data.normalize.contracts import CANONICAL_CONTRACT_VERSION
    from finrobot.engine.data.semantics import RAW_SLOT_VERSION

    return {
        "canonical_contract_version": CANONICAL_CONTRACT_VERSION,
        **{f"raw_slot:{key}": value for key, value in sorted(RAW_SLOT_VERSION.items())},
    }


def acknowledged_digests() -> dict[str, str]:
    """``{"<data_type>|<provider>": semantics_digest}`` for every declared pair.

    This is the digest ``cache.raw_slot_key`` / ``cache.canonical_key`` bake into
    the slot tag (over the declared field MEANING plus the producing provider
    module's source). Re-pinning acknowledges that a change to a pair is
    read-compatible (meaning did not move); leaving a moved value un-pinned fails
    the audit test until the author decides.
    """
    from finrobot.engine.data import semantics

    return {
        f"{data_type}|{provider}": semantics.semantics_digest(data_type, provider)
        for data_type, provider in semantics.declared_pairs()
    }


def main() -> None:
    payload = {
        "sources": source_pins(),
        "declared": declared_versions(),
        "acknowledged": acknowledged_digests(),
    }
    PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIN_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {PIN_FILE.relative_to(REPO_ROOT).as_posix()} "
        f"({len(payload['sources'])} sources, {len(payload['acknowledged'])} acknowledged)"
    )


if __name__ == "__main__":
    main()
