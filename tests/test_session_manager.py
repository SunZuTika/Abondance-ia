"""Tests for the file-based :class:`SessionManager`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the repo root importable so ``session_manager`` can be imported when
# running ``pytest`` from any working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from session_manager import SessionManager  # noqa: E402


def test_new_session_is_empty(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    assert session.data == {}
    assert session.get("wallet_address") is None
    assert session.get("missing", "fallback") == "fallback"


def test_set_persists_value_to_disk(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.set("wallet_address", "0xabc")

    on_disk = json.loads((tmp_path / "alice.json").read_text(encoding="utf-8"))
    assert on_disk == {"wallet_address": "0xabc"}


def test_update_persists_multiple_values(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.update(wallet_address="0xabc", node_name="Node_1234")

    assert session.get("wallet_address") == "0xabc"
    assert session.get("node_name") == "Node_1234"

    on_disk = json.loads((tmp_path / "alice.json").read_text(encoding="utf-8"))
    assert on_disk == {"wallet_address": "0xabc", "node_name": "Node_1234"}


def test_data_survives_new_instance(tmp_path: Path) -> None:
    first = SessionManager(user_id="alice", session_dir=tmp_path)
    first.update(wallet_address="0xabc", node_name="Node_1234")

    # A fresh instance should rehydrate state from disk.
    second = SessionManager(user_id="alice", session_dir=tmp_path)
    assert second.get("wallet_address") == "0xabc"
    assert second.get("node_name") == "Node_1234"


def test_sessions_are_isolated_per_user(tmp_path: Path) -> None:
    alice = SessionManager(user_id="alice", session_dir=tmp_path)
    bob = SessionManager(user_id="bob", session_dir=tmp_path)

    alice.set("wallet_address", "0xalice")
    bob.set("wallet_address", "0xbob")

    assert alice.get("wallet_address") == "0xalice"
    assert bob.get("wallet_address") == "0xbob"

    # Files should be per-user.
    assert (tmp_path / "alice.json").exists()
    assert (tmp_path / "bob.json").exists()


def test_switch_user_loads_that_users_data(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.set("wallet_address", "0xalice")

    session.switch_user("bob")
    assert session.get("wallet_address") is None
    session.set("wallet_address", "0xbob")

    session.switch_user("alice")
    assert session.get("wallet_address") == "0xalice"


def test_clear_removes_file_and_data(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.set("wallet_address", "0xabc")

    session.clear()
    assert session.data == {}
    assert not (tmp_path / "alice.json").exists()


def test_delete_removes_single_key(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.update(wallet_address="0xabc", node_name="Node_1234")

    assert session.delete("wallet_address") is True
    assert session.delete("wallet_address") is False
    assert session.get("node_name") == "Node_1234"


def test_corrupt_file_is_recovered_gracefully(tmp_path: Path) -> None:
    session_file = tmp_path / "alice.json"
    session_file.write_text("not valid json {", encoding="utf-8")

    session = SessionManager(user_id="alice", session_dir=tmp_path)
    assert session.data == {}

    # The first write should overwrite the corrupt file with valid JSON.
    session.set("wallet_address", "0xabc")
    assert json.loads(session_file.read_text(encoding="utf-8")) == {
        "wallet_address": "0xabc"
    }


@pytest.mark.parametrize("bad_id", ["", "..", "a/b", "a b", "a\\b", None, 42])
def test_invalid_user_ids_are_rejected(tmp_path: Path, bad_id) -> None:
    with pytest.raises(ValueError):
        SessionManager(user_id=bad_id, session_dir=tmp_path)


def test_contains_operator(tmp_path: Path) -> None:
    session = SessionManager(user_id="alice", session_dir=tmp_path)
    session.set("wallet_address", "0xabc")
    assert "wallet_address" in session
    assert "node_name" not in session
