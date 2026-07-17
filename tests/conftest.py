"""Shared fixtures and import-time stubs for the test suite.

The app talks to real hardware: the microphone via ``sounddevice`` (PortAudio)
and global ``keyboard`` / ``mouse`` hooks. Those modules either fail to import
or need elevated privileges on a headless CI box, so we swap them for mocks
*before* any ``services.*`` module is imported. The tests never touch real I/O,
the OS credential store, or the developer's own config.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# --- stub hardware modules so `services.audio_writer` imports anywhere -------
# Inserted before the first `import services.*`, so audio_writer picks these up
# instead of the real (platform-specific, privileged) packages.
for _name in ("sounddevice", "keyboard", "mouse"):
    sys.modules.setdefault(_name, MagicMock(name=_name))

import keyring  # noqa: E402
import pytest  # noqa: E402
from keyring.backend import KeyringBackend  # noqa: E402
from keyring.errors import PasswordDeleteError  # noqa: E402


class InMemoryKeyring(KeyringBackend):
    """Volatile keyring backend — tests never read/write the real OS store."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        try:
            del self._store[(service, username)]
        except KeyError:
            raise PasswordDeleteError("not set")


@pytest.fixture(autouse=True)
def _isolate_keyring():
    """Every test gets a fresh, empty in-memory keyring."""
    keyring.set_keyring(InMemoryKeyring())
    yield


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Point %APPDATA% at a temp dir so each test gets an isolated config dir."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path
