"""Single logging-configuration entry point for CLI and server."""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from finrobot.obs.filters import RedactSecretsFilter, TraceFilter
from finrobot.obs.formatters import HumanFormatter, JsonFormatter

if TYPE_CHECKING:
    from finrobot.config import FinRobotSettings

#: Loggers pinned to WARNING. ``edgar`` (edgartools) logs the configured SEC
#: identity — a person's name + email, i.e. personal data — at INFO when its REST
#: client is initialised, and the JSON file handler would persist it to
#: finrobot.log. Pinning it keeps the library's warnings/errors without the leak.
_NOISY = ("httpx", "httpcore", "urllib3", "yfinance", "filelock", "edgar")
_CONFIGURED = False


def setup_logging(
    settings: "FinRobotSettings",
    *,
    logs_dir: Path | None = None,
    force: bool = False,
) -> None:
    """Configure root logging. Idempotent unless ``force=True``.

    Console handler (human, colorized when stderr is a tty) is always added.
    A daily-rotating JSON file handler is added when ``settings.log_to_file``
    and the directory is writable; failure to open the file degrades to
    console-only rather than crashing startup.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    if logs_dir is None:
        from finrobot.paths import LOGS_DIR

        logs_dir = LOGS_DIR

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(settings.log_level.upper())

    trace = TraceFilter()
    # Handler-level (not logger-level) so it also scrubs records propagated up
    # from uvicorn.access — whose full request line carries the ?token= secret.
    redact = RedactSecretsFilter()

    from finrobot.config import console_color_enabled

    console = logging.StreamHandler(stream=sys.stderr)
    console.setFormatter(HumanFormatter(color=console_color_enabled(sys.stderr)))
    console.addFilter(trace)
    console.addFilter(redact)
    root.addHandler(console)

    if settings.log_to_file:
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_handler = TimedRotatingFileHandler(
                logs_dir / "finrobot.log",
                when="midnight",
                backupCount=settings.log_retention_days,
                encoding="utf-8",
                utc=False,
            )
            file_handler.setFormatter(JsonFormatter())
            file_handler.addFilter(trace)
            file_handler.addFilter(redact)
            root.addHandler(file_handler)
        except OSError:
            logging.getLogger(__name__).warning(
                "File logging disabled — could not open %s; console only", logs_dir
            )

    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    _CONFIGURED = True
