"""Account creation and login driven through the real dialogs.

`test_accounts.py` covers the rules; this covers the wiring -- validation
reaching the right dialog, the hash actually reaching the database, and the
login path verifying and then upgrading it. That upgrade is new code and the
riskiest part of the change: it rewrites a stored password.

Runs against mongomock, like `test_db.py`, so no cluster is involved. Needs a
Tk display for the same reason `test_flows.py` does, and shares the one root.
"""

from __future__ import annotations

import hashlib
import os

import mongomock
import pytest

tk = pytest.importorskip("tkinter")

import chimera_accounts  # noqa: E402
from db import ChimeraDB  # noqa: E402


@pytest.fixture
def online(app, monkeypatch):
    """The app wired to an in-memory database, with credentials configured."""
    monkeypatch.setenv("CHIMERA_USERNAME", "test-user")
    monkeypatch.setenv("CHIMERA_PASSWORD", "test-pass")
    # These flows hash and verify repeatedly, and at the production 600k rounds
    # that alone tripled the whole suite's runtime. The cost is asserted for
    # real in test_accounts.py; what is under test here is the wiring, so run it
    # cheap. Still above LEGACY_ITERATIONS is not required -- needs_rehash
    # compares against the patched value too, so the migration test stays valid.
    monkeypatch.setattr(chimera_accounts, "ITERATIONS", 1_000)
    # The menu bar the post-login rewiring drives (self.online, self.file_options)
    # is built by create_scatter, not by __init__ -- MainWindow starts with only
    # 13 attributes and none of the menus.
    app.create_scatter()
    app.database = ChimeraDB(mongomock.MongoClient().CHIMERA)
    app.dialog_calls.clear()
    # A leftover self.user from another test would put save_account into edit
    # mode instead of create mode, and would leave the menu in its logged-in
    # shape for the next one.
    if hasattr(app, "user"):
        del app.user
    yield app
    if hasattr(app, "user"):
        del app.user


def _fill_account(app, username: str, password: str, email: str) -> None:
    app.setup_account()
    for entry, value in (
        (app.username_entry, username),
        (app.password_entry, password),
        (app.email_entry, email),
    ):
        entry.delete(0, tk.END)
        entry.insert(0, value)


def _legacy_hash(password: str) -> bytes:
    salt = os.urandom(32)
    return salt + hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, chimera_accounts.LEGACY_ITERATIONS
    )


# --- creating an account ---------------------------------------------------


def test_creating_an_account_stores_a_versioned_hash(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()

    stored = online.database.find_user("tomas")
    assert stored is not None
    assert stored["email"] == "t@example.com"
    # Never the plaintext, and in the self-describing format.
    assert stored["password"] != b"goodpassword"
    assert stored["password"].startswith(b"pbkdf2_sha256$")
    assert chimera_accounts.verify_password("goodpassword", stored["password"])
    assert not chimera_accounts.needs_rehash(stored["password"])


def test_a_new_account_gets_a_connect_code_and_empty_lists(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()

    stored = online.database.find_user("tomas")
    assert len(stored["connect_code"]) == chimera_accounts.CONNECT_CODE_LENGTH
    assert stored["connections"] == []
    assert stored["projects"] == []


@pytest.mark.parametrize(
    ("username", "password", "email", "expected"),
    [
        ("has space", "goodpassword", "t@example.com", "INVALID USERNAME"),
        ("", "goodpassword", "t@example.com", "INVALID USERNAME"),
        ("tomas", "short", "t@example.com", "INVALID PASSWORD"),
        ("tomas", "has space pw", "t@example.com", "INVALID PASSWORD"),
        ("tomas", "goodpassword", "not-an-email", "INVALID EMAIL"),
    ],
)
def test_invalid_input_warns_and_stores_nothing(
    online, username: str, password: str, email: str, expected: str
) -> None:
    _fill_account(online, username, password, email)
    online.dialog_calls.clear()
    online.save_account()

    assert expected in online.dialog_calls
    assert online.database.find_user(username) is None


def test_a_duplicate_username_is_refused(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()

    _fill_account(online, "tomas", "otherpassword", "other@example.com")
    online.dialog_calls.clear()
    online.save_account()

    assert "INVALID USERNAME" in online.dialog_calls
    # The original account is untouched.
    assert chimera_accounts.verify_password(
        "goodpassword", online.database.find_user("tomas")["password"]
    )


# --- logging in ------------------------------------------------------------


def _login_as(app, username: str, password: str) -> None:
    app.create_login()
    app.username_entry.delete(0, tk.END)
    app.username_entry.insert(0, username)
    app.password_entry.delete(0, tk.END)
    app.password_entry.insert(0, password)
    app.dialog_calls.clear()
    app.login()


def test_logging_in_with_the_right_password_succeeds(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()

    _login_as(online, "tomas", "goodpassword")
    assert "LOGIN SUCCESSFUL" in online.dialog_calls
    assert online.user["username"] == "tomas"


def test_logging_in_with_the_wrong_password_fails(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()

    _login_as(online, "tomas", "wrongpassword")
    assert "INVALID LOGIN" in online.dialog_calls


def test_logging_in_as_an_unknown_user_fails(online) -> None:
    _login_as(online, "nobody", "whateverpass")
    assert "INVALID LOGIN" in online.dialog_calls


def test_a_corrupt_stored_password_is_a_failed_login_not_a_crash(online) -> None:
    """A record whose password is a string, not bytes -- previously TypeError
    straight out of the handler."""
    online.database.insert_user(
        {
            "username": "legacy",
            "password": "plaintext-from-some-old-version",
            "email": "l@example.com",
            "connect_code": "CODE123456",
            "connections": [],
            "projects": [],
        }
    )
    _login_as(online, "legacy", "anything123")
    assert "INVALID LOGIN" in online.dialog_calls


# --- the migration ---------------------------------------------------------


def test_a_legacy_hash_is_upgraded_on_a_successful_login(online) -> None:
    """The point of the versioned format: cost rises without a password reset."""
    online.database.insert_user(
        {
            "username": "olduser",
            "password": _legacy_hash("oldpassword"),
            "email": "o@example.com",
            "connect_code": "CODE123456",
            "connections": [],
            "projects": [],
        }
    )
    before = online.database.find_user("olduser")["password"]
    assert chimera_accounts.needs_rehash(before)

    _login_as(online, "olduser", "oldpassword")

    assert "LOGIN SUCCESSFUL" in online.dialog_calls
    after = online.database.find_user("olduser")["password"]
    assert after != before
    assert after.startswith(b"pbkdf2_sha256$")
    assert not chimera_accounts.needs_rehash(after)
    # And crucially the same password still works afterwards.
    assert chimera_accounts.verify_password("oldpassword", after)


def test_a_failed_login_against_a_legacy_hash_does_not_rewrite_it(online) -> None:
    """Only a correct password reveals the plaintext, so only success upgrades."""
    online.database.insert_user(
        {
            "username": "olduser",
            "password": _legacy_hash("oldpassword"),
            "email": "o@example.com",
            "connect_code": "CODE123456",
            "connections": [],
            "projects": [],
        }
    )
    before = online.database.find_user("olduser")["password"]

    _login_as(online, "olduser", "wrongpassword")

    assert "INVALID LOGIN" in online.dialog_calls
    assert online.database.find_user("olduser")["password"] == before


def test_a_current_hash_is_not_rewritten_on_login(online) -> None:
    _fill_account(online, "tomas", "goodpassword", "t@example.com")
    online.save_account()
    before = online.database.find_user("tomas")["password"]

    _login_as(online, "tomas", "goodpassword")

    assert online.database.find_user("tomas")["password"] == before
