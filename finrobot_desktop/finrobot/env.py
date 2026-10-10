# finrobot/env.py
"""Repo-root ``.env`` loader — the single credential source for FinRobot.

Design (see ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §3): all API keys and the LLM
provider config come from ONE ``.env`` file at the repository root. This module
owns every read of that file and of credential environment variables, extending
the project's existing red-line that only ``config.py`` (and, historically,
``secret_store.py``) touch ``os.environ``.

Precedence at the settings layer is ``init kwargs > .env > default`` — this
module only *exposes* the parsed values; the caller (``config.FinRobotSettings``)
decides how they overlay defaults, and tests that construct settings directly
stay hermetic because they never call :func:`env_values`.

No new runtime dependency: the format is the common ``KEY=VALUE`` subset
(comments, blank lines, optional ``export``, single/double quoted values, and a
trailing ``# comment`` on unquoted values).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

#: Overrides the discovery below (tests / ops point at a fixture or a deployed
#: file). When set but missing on disk, discovery falls through and returns None.
ENV_FILE_OVERRIDE = "FINROBOT_ENV_FILE"

DEFAULT_ENV_FILENAME = ".env"

#: Canonical provider id → credential env-var name. Providers absent here are
#: keyless (yfinance, polymarket, gdelt, federal_reserve, cboe). Single source of
#: truth shared by ``config`` and ``engine.data.registry``.
ENV_BY_PROVIDER: dict[str, str] = {
    "eodhd": "EODHD_API_KEY",
    "tiingo": "TIINGO_API_KEY",
    "twelvedata": "TWELVEDATA_API_KEY",
    "stockdata": "STOCKDATA_API_KEY",
    "benzinga": "BENZINGA_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
    "alpha_vantage": "ALPHAVANTAGE_API_KEY",
    "newsapi": "NEWSAPI_API_KEY",
    "fred": "FRED_API_KEY",
    "fmp": "FMP_API_KEY",
    "massive": "MASSIVE_API_KEY",
    "adanos": "ADANOS_API_KEY",
    "sec_edgar": "SEC_USER_AGENT",  # identity, not a secret
    "moomoo": "MOOMOO_ACCOUNT",  # login id only; never the password
}

#: LLM (OpenRouter) env-var names.
ENV_LLM_PROVIDER = "LANGCHAIN_PROVIDER"
ENV_LLM_KEY = "OPENROUTER_API_KEY"
ENV_LLM_BASE_URL = "OPENROUTER_BASE_URL"
ENV_LLM_MODEL = "OPENROUTER_MODEL_NAME"

#: moomoo gateway env-var names (local OpenD, no HTTP endpoint).
ENV_MOOMOO_HOST = "MOOMOO_HOST"
ENV_MOOMOO_PORT = "MOOMOO_PORT"
ENV_MOOMOO_AUTOSTART = "MOOMOO_AUTOSTART"
ENV_MOOMOO_OPEND_PATH = "MOOMOO_OPEND_PATH"


def env_file_path(start: Path | None = None) -> Path | None:
    """Locate the repo-root ``.env``.

    Order: ``$FINROBOT_ENV_FILE`` → the first ``.env`` found by walking up from
    this module's directory to the filesystem root. Walking up (not a fixed
    relative path) keeps it correct whether the package is imported from the
    source tree or an installed layout.
    """
    override = os.environ.get(ENV_FILE_OVERRIDE)
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.is_file() else None

    here = (start or Path(__file__)).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / DEFAULT_ENV_FILENAME
        if candidate.is_file():
            return candidate
    return None


def parse_env_text(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines. The last occurrence of a key wins."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            # Strip a trailing inline comment on unquoted values only, and only
            # when it is preceded by whitespace (so ``A=B#C`` keeps its hash).
            hash_idx = value.find(" #")
            if hash_idx != -1:
                value = value[:hash_idx].rstrip()
        values[key] = value
    return values


@lru_cache(maxsize=1)
def env_values() -> dict[str, str]:
    """Parsed ``.env`` values (cached). Empty dict when no file is found.

    Cached because every boot path calls it; use :func:`clear_env_cache` in tests
    that mutate the file or the override.
    """
    path = env_file_path()
    if path is None:
        return {}
    return parse_env_text(path.read_text(encoding="utf-8-sig"))


def clear_env_cache() -> None:
    """Drop the cached parse (tests that rewrite ``.env`` or the override)."""
    env_values.cache_clear()


def env_value(name: str) -> str | None:
    """A single credential value: ``.env`` first, then the process environment.

    The process environment is consulted second so an operator can override a
    single key at launch (``FOO=bar finrobot …``) without editing the file.
    """
    value = env_values().get(name)
    if value:
        return value
    return os.environ.get(name) or None
