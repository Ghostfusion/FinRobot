"""Convert FinRobot's ``strategies/`` literature reviews into native SKILL.md files.

Sibling of ``convert_skills.py`` (which converts Anthropic's financial-services
plugins). This converter reads FinRobot's own corpus reviews and maps each
document's own, uniform section template onto the native skill body:

    document section                            ->  skill section
    -----------------------------------------------  -------------------------------
    ``# Title — learnings from …``                   frontmatter ``name``
    (corpus counts preamble)                         dropped
    ``## 1. What the corpus actually offers``        ``## Core Principles``
    ``## 2. Implementable formulas & algorithms``    ``## Methods & Formulas``
    ``## 3. Data requirements → available …``        ``## Data Requirements`` (+ requires_data)
    ``## 4. Pitfalls, validation and measurement``   ``## Pitfalls & Validation``
    ``## 5. Recommended first implementation …``     ``## Recommended Workflow``
    ``## Appendix — papers read``                    ``## References``

``requires_data`` is parsed from the §3 table and cross-checked against
``strategies/endpoints.json`` (keyed on ``(provider, category)``); ``--check``
prints every row whose claimed status the live inventory contradicts, and exits
non-zero if there is any.

Reviewed per-skill metadata lives in ``strategies/skill_meta/<id>.yaml``
(``id``, ``name``, ``domain``, ``description``, ``triggers``, ``persona``,
``output_format``) — the parts a machine cannot write. Only documents with a meta
file are converted by default, so the review tranche is explicit; ``--all`` falls
back to mechanical metadata for the rest.

The documents are the source of truth: edit the document, re-run this script.

Usage:
    python scripts/convert_strategy_docs.py                      # reviewed tranche
    python scripts/convert_strategy_docs.py --check              # validate §3 only
    python scripts/convert_strategy_docs.py --only volatility-modeling
    python scripts/convert_strategy_docs.py --all --stdout       # preview
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCS_DIR = REPO_ROOT / "strategies"
DEFAULT_OUT_DIR = REPO_ROOT / "finrobot_desktop" / "skills"

H1_RE = re.compile(r"^# (.+?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
TITLE_SUFFIX_RE = re.compile(r"\s+[—–-]\s+.*$", re.DOTALL)

# document section prefix -> skill section title, in emission order
SECTION_MAP: tuple[tuple[str, str], ...] = (
    ("1.", "Core Principles"),
    ("2.", "Methods & Formulas"),
    ("3.", "Data Requirements"),
    ("4.", "Pitfalls & Validation"),
    ("5.", "Recommended Workflow"),
)

GAP_NOTE = (
    "In the table above, `gap` inputs are not served by any provider and `derived` "
    "inputs are computed locally from the others — treat both as such rather than "
    "fetching or inventing them."
)

DEFAULT_PERSONA = (
    "You are an expert quantitative analyst. Apply the methodology distilled from "
    "the FinRobot strategies corpus review below, and use only the data endpoints "
    "listed under Data Requirements."
)

REQUIRED_META_KEYS = ("id", "name", "domain", "description", "triggers", "persona")
MAX_DESCRIPTION = 300
MAX_NAME = 64

EMPTY_REFS = {"", "-", "—", "–", "n/a", "none"}


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------


def split_sections(text: str) -> dict[str, str]:
    """Map each ``## heading`` to the text up to the next ``## heading``."""
    matches = list(SECTION_RE.finditer(text))
    parts: dict[str, str] = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        parts[match.group(1).strip()] = text[start:end].strip()
    return parts


def section(parts: dict[str, str], prefix: str) -> str:
    """Return the body of the section whose heading starts with ``prefix``."""
    for heading, body in parts.items():
        if heading.startswith(prefix):
            return body
    return ""


def doc_title(text: str) -> str:
    """The document title, without its ``— learnings from …`` corpus suffix."""
    match = H1_RE.search(text)
    if not match:
        return ""
    return TITLE_SUFFIX_RE.sub("", match.group(1)).strip()


# ---------------------------------------------------------------------------
# §3 table -> requires_data
# ---------------------------------------------------------------------------


def _cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def _clean_ref(cell: str) -> str:
    """Normalise a §3 provider/category cell to a lowercase ``a / b`` alternative list."""
    ref = re.split(r"\s+\(", cell.strip().strip("`"))[0]
    options: list[str] = []
    for part in re.split(r"[,/]", ref):
        token = part.strip().strip("`").strip()
        if token and token.lower() not in EMPTY_REFS and token not in {"…", "..."}:
            options.append(token.lower())
    return " / ".join(options)


def _options(ref: str) -> list[str]:
    """Split a normalised ``a / b`` cell back into its alternatives."""
    return [part.strip() for part in ref.split("/") if part.strip()]


def normalize_status(cell: str, has_provider: bool) -> str:
    """Collapse a §3 'Probe status' cell to ok / gateway / fail / gap / derived.

    ``derived`` marks an input no provider serves because the skill computes it
    locally (a covariance matrix, an event-study residual, an internal ledger);
    ``gap`` marks one no provider serves and nothing computes.
    """
    low = cell.replace("*", "").replace("`", "").strip().lower()
    ok_prefixed = low.startswith("ok")
    if low.startswith("gateway") or (ok_prefixed and "gateway" in low):
        return "gateway"
    if ok_prefixed and "false" in low:
        return "fail"
    if ok_prefixed:
        return "ok"
    if low.startswith(("fail", "rate_limit", "rate-limit", "rate limited", "auth", "http")):
        return "fail"
    if low.startswith(("gap", "missing")):
        return "gap"
    if low.startswith("derived"):
        return "derived"
    if not has_provider:
        return "derived"
    return low[:24].strip() or "unknown"


def parse_requires_data(data_section: str) -> list[dict[str, str]]:
    """Parse the doc's §3 table into ``requires_data`` entries (one per §3 row)."""
    rows: list[dict[str, str]] = []
    for line in data_section.splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 5 or _is_separator(cells):
            continue
        if cells[0].lower() == "input":
            continue
        input_cell, _endpoint, category, provider, status_cell = cells[:5]
        provider_ref = _clean_ref(provider)
        rows.append(
            {
                "input": input_cell,
                "provider": provider_ref,
                "category": _clean_ref(category),
                "status": normalize_status(status_cell, has_provider=bool(provider_ref)),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Endpoint inventory cross-check
# ---------------------------------------------------------------------------


def load_inventory(path: Path) -> dict[tuple[str, str], bool]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {(row["provider"], row["category"]): bool(row["ok"]) for row in rows}


def validate_rows(rows: list[dict[str, str]], inventory: dict[tuple[str, str], bool]) -> list[str]:
    """Every claim in the §3 table the live inventory contradicts.

    A row's provider/category cell may list fallback alternatives; the row is
    valid when at least one ``(provider, category)`` combination is a real
    inventory row, and every combination that is real agrees with the status.
    """
    problems: list[str] = []
    for row in rows:
        if row["status"] in ("gap", "derived"):
            continue
        providers = _options(row["provider"])
        categories = _options(row["category"]) or [""]
        if not providers:
            problems.append(f"row names no provider: {row['input']}")
            continue
        present = [
            key for key in ((p, c) for p in providers for c in categories) if key in inventory
        ]
        if not present:
            problems.append(
                f"no inventory row for {row['provider']!r}/{row['category']!r} — {row['input']}"
            )
            continue
        for key in present:
            ok = inventory[key]
            if row["status"] == "ok" and not ok:
                problems.append(f"{key[0]}/{key[1]} declared ok but the inventory disagrees")
            elif row["status"] == "fail" and ok:
                problems.append(f"{key[0]}/{key[1]} declared fail but the inventory says ok")
    return problems


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def load_meta(path: Path, skill_id: str) -> dict[str, Any]:
    meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(meta, dict):
        raise SystemExit(f"{path}: meta must be a YAML mapping")
    missing = [key for key in REQUIRED_META_KEYS if not meta.get(key)]
    if missing:
        raise SystemExit(f"{path}: missing required meta keys {missing}")
    if str(meta["id"]) != skill_id:
        raise SystemExit(f"{path}: id {meta['id']!r} != filename stem {skill_id!r}")
    if len(str(meta["name"])) > MAX_NAME:
        raise SystemExit(f"{path}: name is {len(str(meta['name']))} chars (max {MAX_NAME})")
    if not isinstance(meta["triggers"], list) or not meta["triggers"]:
        raise SystemExit(f"{path}: triggers must be a non-empty list")
    description = " ".join(str(meta["description"]).split())
    if len(description) > MAX_DESCRIPTION:
        raise SystemExit(f"{path}: description is {len(description)} chars (max {MAX_DESCRIPTION})")
    meta["description"] = description
    return meta


def mechanical_meta(skill_id: str, doc_text: str) -> dict[str, Any]:
    """Unreviewed fallback metadata, for ``--all`` and documents without a meta file."""
    title = doc_title(doc_text) or skill_id.replace("-", " ").title()
    parts = split_sections(doc_text)
    bullets = [
        line.strip().lstrip("-* ").strip()
        for line in section(parts, "1.").splitlines()
        if line.strip().startswith(("-", "*"))
    ]
    description = re.sub(r"[*`$]", "", bullets[0]) if bullets else f"{title} methodology review."
    description = " ".join(description.split())
    if len(description) > MAX_DESCRIPTION - 10:
        description = description[: MAX_DESCRIPTION - 13].rsplit(" ", 1)[0] + "..."
    triggers = re.findall(r"[a-z]{4,}", title.lower())
    return {
        "id": skill_id,
        "name": title,
        "domain": "quant-research",
        "description": description,
        "triggers": triggers or [skill_id],
        "persona": DEFAULT_PERSONA,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def build_frontmatter(meta: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "id": meta["id"],
        "name": meta["name"],
        "version": "1.0.0",
        "author": "finrobot",
        "domain": meta["domain"],
        "description": meta["description"],
        "triggers": [str(trigger) for trigger in meta["triggers"]],
        "requires_data": rows,
        "requires_tools": [],
        "requires_skills": [],
        "compatible_models": [],
    }


def render_body(
    meta: dict[str, Any], parts: dict[str, str], doc_rel: str, rows: list[dict[str, str]]
) -> str:
    chunks = [
        f"# {meta['name']}",
        "",
        str(meta["persona"]).strip(),
        "",
        f"> Source: FinRobot strategies corpus review — `{doc_rel}`. "
        "Literature-derived; not validated on FinRobot's own data.",
        "",
    ]
    has_caveat = any(row["status"] in ("gap", "derived") for row in rows)
    for prefix, title in SECTION_MAP:
        body = section(parts, prefix)
        if not body:
            continue
        chunks += [f"## {title}", "", body, ""]
        if prefix == "3." and has_caveat:
            chunks += [GAP_NOTE, ""]
    if meta.get("output_format"):
        chunks += ["## Output Format", "", str(meta["output_format"]).strip(), ""]
    appendix = section(parts, "Appendix")
    if appendix:
        chunks += ["## References", "", appendix, ""]
    return "\n".join(chunks).rstrip() + "\n"


def dump_skill(frontmatter: dict[str, Any], body: str) -> str:
    yaml_str = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**9,
    )
    return f"---\n{yaml_str}---\n\n{body}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def discover_docs(docs_dir: Path) -> dict[str, Path]:
    docs: dict[str, Path] = {}
    for path in sorted(docs_dir.glob("qfin-*/*.md")):
        if path.name != "README.md":
            docs[path.stem] = path
    return docs


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run_check(docs: dict[str, Path], inventory: dict[tuple[str, str], bool]) -> int:
    total_problems = 0
    for skill_id, path in sorted(docs.items()):
        rows = parse_requires_data(section(split_sections(path.read_text(encoding="utf-8")), "3."))
        problems = validate_rows(rows, inventory)
        total_problems += len(problems)
        counts = {
            code: sum(1 for row in rows if row["status"] == code)
            for code in ("ok", "gateway", "fail", "gap", "derived")
        }
        print(
            f"{skill_id:38s} rows={len(rows):3d} ok={counts['ok']:3d} "
            f"gateway={counts['gateway']:3d} fail={counts['fail']:d} "
            f"gap={counts['gap']:2d} derived={counts['derived']:2d} "
            f"problems={len(problems)}"
        )
        for problem in problems:
            print(f"    ! {problem}")
    print(f"\n{len(docs)} documents · {total_problems} inventory mismatches")
    return 1 if total_problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--meta-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--endpoints", type=Path, default=None)
    parser.add_argument("--only", default=None, help="comma-separated skill ids")
    parser.add_argument("--all", action="store_true", help="every document, mechanically")
    parser.add_argument("--check", action="store_true", help="validate §3 tables; write nothing")
    parser.add_argument("--stdout", action="store_true", help="print instead of writing")
    parser.add_argument("--force", action="store_true", help="overwrite non-generated skills too")
    args = parser.parse_args(argv)

    meta_dir = args.meta_dir or args.docs_dir / "skill_meta"
    endpoints = args.endpoints or args.docs_dir / "endpoints.json"
    inventory = load_inventory(endpoints)
    docs = discover_docs(args.docs_dir)

    if args.check:
        return run_check(docs, inventory)

    if args.only:
        selected = [part.strip() for part in args.only.split(",") if part.strip()]
        unknown = [skill_id for skill_id in selected if skill_id not in docs]
        if unknown:
            raise SystemExit(f"no such document(s): {unknown}")
    elif args.all:
        selected = sorted(docs)
    else:
        selected = sorted(skill_id for skill_id in docs if (meta_dir / f"{skill_id}.yaml").exists())
        if not selected:
            raise SystemExit(f"no reviewed metadata under {meta_dir}; use --all for mechanical")

    reviewed = 0
    written: list[str] = []
    for skill_id in selected:
        doc_path = docs[skill_id]
        text = doc_path.read_text(encoding="utf-8")
        meta_path = meta_dir / f"{skill_id}.yaml"
        if meta_path.exists():
            meta = load_meta(meta_path, skill_id)
            reviewed += 1
        else:
            meta = mechanical_meta(skill_id, text)

        parts = split_sections(text)
        rows = parse_requires_data(section(parts, "3."))
        for problem in validate_rows(rows, inventory):
            print(f"WARNING {skill_id}: {problem}")

        content = dump_skill(
            build_frontmatter(meta, rows), render_body(meta, parts, _relative(doc_path), rows)
        )
        if args.stdout:
            print(content)
            continue

        out_path = args.out / str(meta["domain"]) / skill_id / "SKILL.md"
        if out_path.exists() and not args.force:
            head = out_path.read_text(encoding="utf-8")[:400]
            if "author: finrobot" not in head:
                raise SystemExit(f"refusing to overwrite {out_path} (not generated by this script)")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        written.append(f"{meta['domain']}/{skill_id}")

    if not args.stdout:
        gaps = sum(
            1
            for skill_id in selected
            for row in parse_requires_data(
                section(split_sections(docs[skill_id].read_text(encoding="utf-8")), "3.")
            )
            if row["status"] == "gap"
        )
        print(
            f"wrote {len(written)} skills ({reviewed} with reviewed metadata, {len(selected) - reviewed} mechanical)"
        )
        print(f"requires_data: {gaps} gap row(s) declared across the tranche")
        for name in written:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
