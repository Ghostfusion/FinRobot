# Skill Attribution

## Vendored playbooks (`author: anthropic`)

The 56 vendored skills are derived from Anthropic's
[financial-services-plugins](https://github.com/anthropics/financial-services-plugins).

- **Original author**: Anthropic
- **License**: MIT (see upstream repository)
- **Conversion**: Automated via `scripts/convert_skills.py` on 2026-03-31
- **Modifications**: Format conversion from Anthropic plugin format to FinRobot native SKILL.md
  format, plus dependency declaration (`requires_data`, `requires_tools`) added 2026-10-11.
  Prose content unchanged.

See `UPSTREAM_VERSION.txt` for conversion metadata.

## Corpus-derived skills (`author: finrobot`)

The method skills under `derivatives/`, `fixed-income/`, `quant-research/`, `risk-management/`,
`systematic-trading/`, `portfolio-management/`, `news-sentiment/`, `macro-research/`, `execution/`
and `equity-research/` are FinRobot's own, generated from the literature
reviews in [`../strategies/`](../strategies/) by `scripts/convert_strategy_docs.py`.

- **Original author**: FinRobot
- **Source**: FinRobot's `strategies/` corpus reviews, which cite their arXiv sources by id
- **Generated**: 2026-10-11 — regenerate with `python scripts/convert_strategy_docs.py`
- **Modifications**: none — the body is a mechanical section mapping of the source document;
  the reviewed metadata lives in `strategies/skill_meta/<id>.yaml`

These are literature-derived and **not validated on FinRobot's own data**; §4/§5 of each source
document is the testing plan. The verdicts for all 63 corpus documents are in
[`../strategies/SKILLS_PLAN.md`](../strategies/SKILLS_PLAN.md).
