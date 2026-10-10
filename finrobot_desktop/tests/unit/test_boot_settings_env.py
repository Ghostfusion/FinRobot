"""Boot settings must overlay the repo-root ``.env``.

Regression cover for a defect found by running the app: ``server.lifespan`` built
settings with a bare ``get_settings(...)``, so ``apply_env_secrets`` never ran.
``EnvSecretStore`` still hydrated data-provider API keys (the chain looked
populated), which hid the fault — but the SEC identity stayed the placeholder, so
``sec_edgar`` never registered, and ``model_name`` stayed empty, so every LLM
route answered "no usable model".
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from finrobot.env import clear_env_cache

_ENV_BODY = """\
SEC_USER_AGENT="Jane Doe jane@example.com"
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL_NAME=deepseek/deepseek-v4.1-flash
"""


@pytest.fixture()
def env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / ".env"
    path.write_text(_ENV_BODY, encoding="utf-8")
    monkeypatch.setenv("FINROBOT_ENV_FILE", str(path))
    clear_env_cache()
    yield path
    clear_env_cache()


def test_boot_settings_apply_env_identity_and_model(env_file: Path, tmp_path: Path) -> None:
    from finrobot.server import load_boot_settings

    settings, error = load_boot_settings(tmp_path / "settings.json")

    assert error is None
    assert settings.sec_user_agent == "Jane Doe jane@example.com"
    assert settings.model_name == "openrouter:deepseek/deepseek-v4.1-flash"
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"


def test_app_stored_settings_still_win_over_env(env_file: Path, tmp_path: Path) -> None:
    """The overlay only fills defaults: an explicit settings.json value is kept."""
    import json

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"model_name": "openrouter:anthropic/claude-sonnet-4-6"}))

    from finrobot.server import load_boot_settings

    settings, error = load_boot_settings(settings_path)

    assert error is None
    assert settings.model_name == "openrouter:anthropic/claude-sonnet-4-6"
    # .env still fills what settings.json left at its default.
    assert settings.sec_user_agent == "Jane Doe jane@example.com"
