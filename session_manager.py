"""File-based session management for Abondance AI.

This module provides a lightweight :class:`SessionManager` that persists
per-user session data (e.g. wallet address, node name, hashgraph chain) to
JSON files on disk so that state survives across multiple interactions and
application restarts.

Sessions are keyed by a ``user_id`` string. Each user's data is stored in its
own file under ``session_dir`` (``sessions/`` by default), which makes it
trivial to inspect or wipe a single user's session without affecting others.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

DEFAULT_SESSION_DIR = Path("sessions")
DEFAULT_USER_ID = "default"

# Restrict user ids to a safe subset so they can be used as filenames without
# worrying about path traversal or OS-specific illegal characters.
_USER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class SessionManager:
    """Persist a user's session data to a JSON file.

    Parameters
    ----------
    user_id:
        Identifier for the user whose session is being managed. The id is
        used as the session filename, so it must match
        ``[A-Za-z0-9_.-]+``.
    session_dir:
        Directory where session files are stored. Created if it does not
        exist. Defaults to ``sessions/`` relative to the current working
        directory.
    """

    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        session_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.session_dir = Path(session_dir) if session_dir else DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self.user_id = ""  # set via switch_user below
        self.session_file = self.session_dir / f"{DEFAULT_USER_ID}.json"
        self.switch_user(user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        if not isinstance(user_id, str) or not _USER_ID_RE.match(user_id):
            raise ValueError(
                "user_id must be a non-empty string matching [A-Za-z0-9_.-]+"
            )
        # Reject path-traversal-style ids even though they match the regex.
        if user_id in {".", ".."} or user_id.startswith(".."):
            raise ValueError("user_id must not be '.' or '..'")
        return user_id

    def _session_path(self, user_id: str) -> Path:
        return self.session_dir / f"{user_id}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load(self) -> Dict[str, Any]:
        """Load session data from disk, replacing any in-memory state."""
        if self.session_file.exists():
            try:
                with self.session_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    loaded = {}
                self._data = loaded
            except (json.JSONDecodeError, OSError):
                # Corrupt or unreadable file: start with an empty session
                # rather than crashing. The next save() will overwrite it.
                self._data = {}
        else:
            self._data = {}
        return dict(self._data)

    def save(self) -> None:
        """Persist the current in-memory session data to disk."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.session_file.with_suffix(self.session_file.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, sort_keys=True)
        tmp_path.replace(self.session_file)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value from the session, or ``default`` if missing."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single session value and persist immediately."""
        self._data[key] = value
        self.save()

    def update(self, **kwargs: Any) -> None:
        """Update several session values at once and persist immediately."""
        if not kwargs:
            return
        self._data.update(kwargs)
        self.save()

    def delete(self, key: str) -> bool:
        """Remove a key from the session. Returns True if a key was removed."""
        if key in self._data:
            del self._data[key]
            self.save()
            return True
        return False

    def clear(self) -> None:
        """Wipe the in-memory data and remove the on-disk session file."""
        self._data = {}
        if self.session_file.exists():
            self.session_file.unlink()

    def switch_user(self, user_id: str) -> None:
        """Switch to another user's session, loading their data from disk."""
        user_id = self._validate_user_id(user_id)
        self.user_id = user_id
        self.session_file = self._session_path(user_id)
        self.load()

    @property
    def data(self) -> Dict[str, Any]:
        """Return a shallow copy of the current session data."""
        return dict(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"SessionManager(user_id={self.user_id!r}, "
            f"session_file={str(self.session_file)!r})"
        )
