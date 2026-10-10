from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Literal

from finrobot.env import ENV_BY_PROVIDER, ENV_LLM_KEY, env_value

logger = logging.getLogger(__name__)

SecretStorageMode = Literal["keychain", "plaintext", "env"]


class SecretStoreError(RuntimeError):
    """A secret could not be written to / deleted from the underlying store.

    Raised instead of the backend's own exception type so route handlers can
    surface ONE stable error to the user (a failed key save must never look
    like success, nor like an opaque 500). The message carries only the key
    name and the backend failure — never the secret value.
    """


class SecretStore(ABC):
    """Abstract secret storage.

    Business code calls this interface and never touches the underlying
    storage mechanism directly.
    """

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Retrieve a secret by key. Returns None if not set."""

    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Store a secret."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a secret."""

    @abstractmethod
    async def has(self, key: str) -> bool:
        """Check if a secret exists without retrieving it."""


class EnvSecretStore(SecretStore):
    """Read-only secret store backed by the repo-root ``.env`` (Data Layer v3).

    Keeps the :class:`SecretStore` interface so the settings routes keep working
    unchanged: reads resolve a secret key name to its env-var value; writes are
    REJECTED because credentials are edited in ``.env``, not via the API. See
    ``docs/DATA_PROVIDERS_V3_DESIGN.md`` §3.
    """

    def _env_name(self, key: str) -> str | None:
        if key.startswith("provider_key:"):
            provider_id = key.split(":", 1)[1]
            return ENV_LLM_KEY if provider_id == "openrouter" else None
        # Data-provider keys arrive as settings field names (e.g. fmp_api_key).
        from finrobot.config import DATA_PROVIDER_KEY_FIELDS

        for provider_id, field in DATA_PROVIDER_KEY_FIELDS.items():
            if field == key:
                return ENV_BY_PROVIDER.get(provider_id)
        return None

    async def get(self, key: str) -> str | None:
        name = self._env_name(key)
        return env_value(name) if name else None

    async def has(self, key: str) -> bool:
        return (await self.get(key)) is not None

    async def set(self, key: str, value: str) -> None:
        raise SecretStoreError(
            "Credentials are managed in the repo-root .env file. Edit that file "
            "and restart instead of saving keys from the app."
        )

    async def delete(self, key: str) -> None:
        raise SecretStoreError(
            "Credentials are managed in the repo-root .env file. Remove the line "
            "there instead of clearing it from the app."
        )


def create_secret_store(
    dev_mode: bool | None = None,
) -> tuple[SecretStore, SecretStorageMode]:
    """Create the secret store for this runtime.

    Returns a ``(store, mode)`` pair so callers can surface the storage mode to
    the user without probing the store again.  ``mode`` is ``"env"``: Data Layer
    v3 moved every credential to the repo-root ``.env``, so all runtimes get the
    same read-only :class:`EnvSecretStore`. ``dev_mode`` is retained for
    signature compatibility but no longer selects a backend.
    """
    # Data Layer v3: credentials live in the repo-root .env; the OS keychain and
    # the plaintext file store are retired. ``dev_mode`` is retained for
    # signature compatibility but no longer selects a backend.
    logger.info("Using EnvSecretStore (repo-root .env)")
    return EnvSecretStore(), "env"
