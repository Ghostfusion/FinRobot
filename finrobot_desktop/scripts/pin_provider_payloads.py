#!/usr/bin/env python
"""Refresh the provider-payload source pins used by the cache-version audit.

The raw cache slot's version tag (``cache._RAW_SLOT_VERSION``) lives in a different
file from the payload it describes, which is how the 2026-10-14 yfinance margin fix
shipped without one: the CF report served a pre-fix payload for a full TTL after the
fix landed (see the ``financials v6`` / ``CANONICAL_CONTRACT_VERSION v13`` notes).

``tests/audit/test_provider_cache_payload_pins.py`` pins each provider module's
normalized source hash plus the declared slot versions, so an edit to any of them
fails until the author STATES whether a cached row's meaning changed. This script
does the mechanical half:

    python scripts/pin_provider_payloads.py

Run it AFTER deciding whether the change needs a version bump — if it does, bump
``_RAW_SLOT_VERSION`` (and/or ``CANONICAL_CONTRACT_VERSION``) in the same commit and
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
    """The version tags a payload change must move."""
    from finrobot.engine.data.cache import _RAW_SLOT_VERSION
    from finrobot.engine.data.normalize.contracts import CANONICAL_CONTRACT_VERSION

    return {
        "canonical_contract_version": CANONICAL_CONTRACT_VERSION,
        **{f"raw_slot:{key}": value for key, value in sorted(_RAW_SLOT_VERSION.items())},
    }


def main() -> None:
    payload = {"sources": source_pins(), "declared": declared_versions()}
    PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIN_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {PIN_FILE.relative_to(REPO_ROOT).as_posix()} ({len(payload['sources'])} sources)")


if __name__ == "__main__":
    main()
