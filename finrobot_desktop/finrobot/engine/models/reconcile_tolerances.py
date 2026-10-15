"""Shared reconciliation tolerance — leaf constant (ADR-0005 leaf layer,
importable by compute / pipeline / artifact alike, same as ``numeric_claim`` and
``valuation_thresholds``).

The relative tolerance below decides when two dollar amounts that *should* be the
same number (a prose $-amount vs the canonical weighted target; a basis
conclusion amount vs the headline price target) are close enough to be the same
versus a real contradiction. It lives here — not inside
``pipelines/equity_research`` — because two layers consume the SAME calibrated
value and must speak the same language:

  · the upstream narrative reconcile (``equity_research._reconcile_narrative_targets``)
    which rewrites a drifting prose $-amount back to the canonical token, and
  · the end-to-end output contract (``artifact/contract``, clause C3) which
    re-checks that the basis conclusion amount equals the headline at the persist
    boundary — and is forbidden to import ``pipelines/`` (ADR: the contract stays
    a dumb end-to-end invariant; it may import a calibrated constant from a leaf
    but never the pipeline that computed the result).

Kept tight (1%) so a rounded restatement like "$276" against $276.43 passes, but
a contradicting headline like "$280" against $276.43 is caught — the exact
table-vs-prose desync these guards exist to neutralize.
"""

from __future__ import annotations

# Relative tolerance for "these two dollar amounts are the same number".
NARRATIVE_DRIFT_TOLERANCE = 0.01

# Report-drift approximation band: an unmatched narrative amount within this
# relative distance of SOME numeric leaf is an LLM approximation ("roughly
# $400B" against a $391B leaf, 2.3%) — kept in prose, flagged for review.
# Beyond it the amount is near NOTHING the artifact computed → redacted as a
# high-confidence fabrication/material error. Calibrated 2026-07-02 on all 51
# stored artifacts (627 amounts, 99 unmatched@1%): gaps ≤10% read as roundings
# (1.4%/2.8%/4.2%…), gaps >10% were materially wrong numbers (JPM DDM
# "$1.58 trillion" 15% off, "$140.95B" 22.5% off, MU LBO "$-31892M" 102% off)
# — a visible break, not a smooth continuum.
NARRATIVE_APPROXIMATION_BAND = 0.10

# Relative tolerance for "a published quantity IS its own declared derivation"
# (contract clause C10e, which walks ``engine/models/identities``). Structural rather
# than statistical: both sides are read from the SAME published leaves of one
# artifact, so a correct value is exact to float representation and 1% only absorbs a
# provider's own rounding. The check exists for the CF 2026-10-14 shape —
# ``operating_margin`` 0.49325 published beside ``operating_income`` 3,025,000,000 /
# ``revenue`` 7,738,999,808 = 0.39088 (21% out, and above that same block's 42.49%
# gross margin, which is impossible) — where every provenance check was silent
# because one provider supplied all three figures.
#
# Named for what it now guards: the registry covers every declared identity (ratios,
# EV/EBITDA and EV/Revenue, the EV build, the trailing P/E, the margins), not just the
# ratios the clause was born for. XBRL derives this kind of tolerance from the
# published precision of the facts themselves (Calculations 1.1 §5.2.3-5.2.4, the
# rounded/truncated fact value interval); our leaves round to a fixed display precision
# per field, so a single relative band is the honest approximation until a field
# declares its own digits.
IDENTITY_RESIDUAL_TOLERANCE = 0.01
