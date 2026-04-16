"""Integration tests verifying that :class:`Abondance` persists user data."""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture()
def abondance_module():
    """Import the ``Abondance ia code`` module (which has spaces in its name)."""
    source_path = REPO_ROOT / "Abondance ia code"
    loader = SourceFileLoader("abondance_ia_code", str(source_path))
    spec = importlib.util.spec_from_loader("abondance_ia_code", loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wallet_address_persists_across_instances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abondance_module
) -> None:
    monkeypatch.chdir(tmp_path)

    first = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    first.process_input("connect wallet 0xABCDEF")
    original_node_name = first.node_name
    assert first.wallet_address == "0xabcdef"

    # A fresh instance should rehydrate the wallet and keep the same node
    # name rather than generating a new one.
    second = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    assert second.wallet_address == "0xabcdef"
    assert second.node_name == original_node_name


def test_hashgraph_chain_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abondance_module
) -> None:
    monkeypatch.chdir(tmp_path)

    first = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    first.process_input("replicate Wi-Fi")
    first.process_input("replicate Bluetooth")
    assert len(first.hashgraph_chain) == 2

    second = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    assert second.hashgraph_chain == first.hashgraph_chain


def test_login_switches_between_users(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abondance_module
) -> None:
    monkeypatch.chdir(tmp_path)

    ai = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    ai.process_input("connect wallet 0xalice")
    alice_node = ai.node_name

    ai.process_input("login bob")
    assert ai.session.user_id == "bob"
    assert ai.wallet_address is None  # Bob has no wallet yet.
    ai.process_input("connect wallet 0xbob")

    ai.process_input("login alice")
    assert ai.wallet_address == "0xalice"
    assert ai.node_name == alice_node


def test_logout_clears_session_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abondance_module
) -> None:
    monkeypatch.chdir(tmp_path)
    session_dir = tmp_path / "s"

    ai = abondance_module.Abondance(user_id="alice", session_dir=session_dir)
    ai.process_input("connect wallet 0xalice")
    assert (session_dir / "alice.json").exists()

    ai.process_input("logout")
    # After logout the session file should have been recreated with a
    # freshly generated node name and no wallet.
    assert ai.wallet_address is None
    assert ai.node_name is not None
    assert ai.session.get("wallet_address") is None


def test_whoami_reports_current_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abondance_module
) -> None:
    monkeypatch.chdir(tmp_path)

    ai = abondance_module.Abondance(user_id="alice", session_dir=tmp_path / "s")
    response = ai.process_input("whoami")
    assert "alice" in response
    assert ai.node_name in response
    assert "<not connected>" in response

    ai.process_input("connect wallet 0xabc")
    response = ai.process_input("whoami")
    assert "0xabc" in response
