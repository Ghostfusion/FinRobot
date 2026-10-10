from __future__ import annotations

import sys
from typing import Any

import pytest

from finrobot.secret_store import (
    EnvSecretStore,
    SecretStoreError,
    create_secret_store,
)

# ---------------------------------------------------------------------------
# create_secret_store — Data Layer v3: credentials live in the repo-root .env,
# so every runtime (dev mode, macOS, Windows, Linux, keychain opt-in) gets the
# same read-only EnvSecretStore.
# ---------------------------------------------------------------------------


def test_create_store_returns_env_store(monkeypatch: Any) -> None:
    monkeypatch.delenv("FINROBOT_DEV_MODE", raising=False)
    store, mode = create_secret_store()
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


def test_create_store_ignores_dev_mode_arg(monkeypatch: Any) -> None:
    monkeypatch.delenv("FINROBOT_DEV_MODE", raising=False)
    store, mode = create_secret_store(dev_mode=True)
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


def test_create_store_ignores_dev_mode_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("FINROBOT_DEV_MODE", "1")
    store, mode = create_secret_store()
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


def test_create_store_macos_ignores_keychain_opt_in(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("FINROBOT_USE_KEYCHAIN", "1")
    store, mode = create_secret_store()
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


def test_create_store_windows_returns_env_store(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("FINROBOT_DEV_MODE", raising=False)
    store, mode = create_secret_store()
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


def test_create_store_linux_returns_env_store(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    store, mode = create_secret_store()
    assert isinstance(store, EnvSecretStore)
    assert mode == "env"


@pytest.mark.asyncio
async def test_create_store_rejects_writes(monkeypatch: Any) -> None:
    """The store create_secret_store returns is read-only: credentials are
    edited in .env, so every write must raise SecretStoreError."""
    monkeypatch.delenv("FINROBOT_DEV_MODE", raising=False)
    store, _mode = create_secret_store()
    with pytest.raises(SecretStoreError):
        await store.set("fmp_api_key", "sk-x")
    with pytest.raises(SecretStoreError):
        await store.delete("fmp_api_key")


# ---------------------------------------------------------------------------
# EnvSecretStore — reads resolve a settings field name to its .env var; writes
# are rejected because credentials are edited in .env, not via the API.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_env_secret_store_reads_data_key_from_env(monkeypatch: Any) -> None:
    monkeypatch.setattr("finrobot.env.env_values", lambda: {"FMP_API_KEY": "sk-env-fmp"})
    store = EnvSecretStore()
    assert await store.get("fmp_api_key") == "sk-env-fmp"
    assert await store.has("fmp_api_key") is True


@pytest.mark.asyncio
async def test_env_secret_store_unknown_key_is_none() -> None:
    store = EnvSecretStore()
    assert await store.get("not_a_secret") is None
    assert await store.has("not_a_secret") is False


@pytest.mark.asyncio
async def test_env_secret_store_writes_are_rejected() -> None:
    store = EnvSecretStore()
    with pytest.raises(SecretStoreError):
        await store.set("fmp_api_key", "sk-x")
    with pytest.raises(SecretStoreError):
        await store.delete("fmp_api_key")
