"""Tests for CHIMERA Online account rules: validation, hashing, connect codes.

online_ui was the least-covered module in the repo at 12%, and the part of it
that most deserved coverage was the password handling -- which lived inline in
two Tkinter dialogs with the PBKDF2 iteration count written as a bare literal in
each, so the two could silently disagree and lock everyone out.

The backward-compatibility tests here are the important ones: real accounts are
stored in the old bare salt+key layout, and they have to keep working.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from chimera_accounts import (
    CONNECT_CODE_ALPHABET,
    CONNECT_CODE_LENGTH,
    ITERATIONS,
    LEGACY_ITERATIONS,
    MIN_PASSWORD_LENGTH,
    ValidationError,
    build_user_document,
    check_new_connection,
    generate_connect_code,
    hash_password,
    needs_rehash,
    validate_account,
    validate_email,
    validate_password,
    validate_username,
    verify_password,
)


def legacy_hash(password: str) -> bytes:
    """A hash in the pre-versioning format: 32-byte salt then the key."""
    salt = os.urandom(32)
    return salt + hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, LEGACY_ITERATIONS)


# --- validation ------------------------------------------------------------


@pytest.mark.parametrize("username", ["tomas", "a", "user_123", "ÜberUser", "x" * 200])
def test_acceptable_usernames_pass(username: str) -> None:
    validate_username(username)


@pytest.mark.parametrize(
    ("username", "reason"),
    [
        ("", "at least one character"),
        ("has space", "whitespace"),
        ("has\ttab", "whitespace"),
        ("has\nnewline", "whitespace"),
        ("has\rreturn", "whitespace"),
        ("nbsp" + chr(0xA0) + "here", "whitespace"),  # a non-breaking space
    ],
)
def test_rejected_usernames(username: str, reason: str) -> None:
    """The message always said "spaces, tabs,..." but the check only looked for
    those two, so a newline or a non-breaking space used to be accepted."""
    with pytest.raises(ValidationError, match=reason):
        validate_username(username)


def test_username_error_carries_the_dialog_title() -> None:
    with pytest.raises(ValidationError) as exc:
        validate_username("")
    assert exc.value.title == "INVALID USERNAME"


@pytest.mark.parametrize("password", ["abcdefgh", "S3cur3!Passw0rd", "x" * 500])
def test_acceptable_passwords_pass(password: str) -> None:
    validate_password(password)


@pytest.mark.parametrize("password", ["", "short", "seven77", "has space1", "has\ttab1"])
def test_rejected_passwords(password: str) -> None:
    with pytest.raises(ValidationError) as exc:
        validate_password(password)
    assert exc.value.title == "INVALID PASSWORD"


def test_password_length_boundary() -> None:
    validate_password("a" * MIN_PASSWORD_LENGTH)
    with pytest.raises(ValidationError):
        validate_password("a" * (MIN_PASSWORD_LENGTH - 1))


@pytest.mark.parametrize(
    "email",
    ["a@b.co", "tomas.feith@example.com", "x+tag@sub.domain.org", "a_b%c@d-e.io"],
)
def test_acceptable_emails_pass(email: str) -> None:
    validate_email(email)


@pytest.mark.parametrize(
    "email",
    ["", "nope", "no@tld", "no@dot,com", "spaces @example.com", "a@b.c", "trailing@example.com "],
)
def test_rejected_emails(email: str) -> None:
    """fullmatch, so a valid address with anything around it is still rejected."""
    with pytest.raises(ValidationError) as exc:
        validate_email(email)
    assert exc.value.title == "INVALID EMAIL"


def test_validate_account_reports_the_first_problem_in_dialog_order() -> None:
    """Username before password before email, as the dialogs always did."""
    with pytest.raises(ValidationError) as exc:
        validate_account("bad name", "short", "nope")
    assert exc.value.title == "INVALID USERNAME"

    with pytest.raises(ValidationError) as exc:
        validate_account("fine", "short", "nope")
    assert exc.value.title == "INVALID PASSWORD"

    with pytest.raises(ValidationError) as exc:
        validate_account("fine", "longenough", "nope")
    assert exc.value.title == "INVALID EMAIL"


# --- hashing ---------------------------------------------------------------


def test_a_password_verifies_against_its_own_hash() -> None:
    stored = hash_password("correct horse battery")
    assert verify_password("correct horse battery", stored)


def test_a_wrong_password_does_not_verify() -> None:
    stored = hash_password("correct horse battery")
    assert not verify_password("Correct horse battery", stored)
    assert not verify_password("", stored)
    assert not verify_password("correct horse batter", stored)


def test_the_same_password_hashes_differently_every_time() -> None:
    """A fresh random salt per hash, so identical passwords are not identical rows."""
    a = hash_password("same password")
    b = hash_password("same password")
    assert a != b
    assert verify_password("same password", a)
    assert verify_password("same password", b)


def test_the_hash_records_its_own_work_factor() -> None:
    """The whole point of the format change: the cost travels with the hash."""
    stored = hash_password("whatever123")
    assert stored.startswith(b"pbkdf2_sha256$")
    assert str(ITERATIONS).encode() in stored


def test_the_current_cost_is_at_least_the_owasp_floor() -> None:
    assert ITERATIONS >= 600_000


# --- backward compatibility (the part real accounts depend on) -------------


def test_an_existing_legacy_hash_still_verifies() -> None:
    """Accounts predating the format change must keep working."""
    stored = legacy_hash("my old password")
    assert verify_password("my old password", stored)
    assert not verify_password("wrong", stored)


def test_a_legacy_hash_is_flagged_for_upgrade() -> None:
    assert needs_rehash(legacy_hash("my old password"))


def test_a_current_hash_is_not_flagged_for_upgrade() -> None:
    assert not needs_rehash(hash_password("my new password"))


def test_a_hash_below_the_current_cost_is_flagged() -> None:
    """Raising ITERATIONS again later must re-flag everything below it."""
    weak = hash_password("pw12345678", iterations=1000)
    assert verify_password("pw12345678", weak)  # still correct, just cheap
    assert needs_rehash(weak)


def test_upgrading_a_legacy_hash_keeps_the_password_working() -> None:
    """The migration the login path performs, end to end."""
    old = legacy_hash("unchanged password")
    assert verify_password("unchanged password", old)

    new = hash_password("unchanged password")
    assert verify_password("unchanged password", new)
    assert not needs_rehash(new)
    assert old != new


# --- malformed stored values -----------------------------------------------


@pytest.mark.parametrize(
    "stored",
    [
        None,
        "a string, not bytes",
        b"",
        b"too short",
        b"pbkdf2_sha256$notanumber$" + b"x" * 64,
        b"pbkdf2_sha256$600000$",  # header but no salt or key
        12345,
    ],
)
def test_a_malformed_stored_password_is_a_failed_login_not_a_crash(stored: object) -> None:
    """A corrupt or legacy-plaintext record used to raise TypeError straight out
    of the login handler and take the window down. It is just a wrong password."""
    assert verify_password("anything", stored) is False


@pytest.mark.parametrize("stored", [None, "a string", b"", 12345])
def test_an_unusable_stored_password_is_flagged_for_rehash(stored: object) -> None:
    assert needs_rehash(stored)


# --- connect codes ---------------------------------------------------------


def test_a_connect_code_has_the_expected_shape() -> None:
    code = generate_connect_code()
    assert len(code) == CONNECT_CODE_LENGTH
    assert all(char in CONNECT_CODE_ALPHABET for char in code)


def test_connect_codes_do_not_repeat() -> None:
    """Not proof of uniqueness, but a stuck generator would show up here."""
    codes = {generate_connect_code() for _ in range(500)}
    assert len(codes) == 500


# --- account documents -----------------------------------------------------


def test_a_new_account_starts_empty_with_a_fresh_code() -> None:
    doc = build_user_document("tomas", b"hashed", "t@example.com")
    assert doc["username"] == "tomas"
    assert doc["password"] == b"hashed"
    assert doc["email"] == "t@example.com"
    assert doc["connections"] == []
    assert doc["projects"] == []
    assert len(doc["connect_code"]) == CONNECT_CODE_LENGTH


def test_editing_an_account_preserves_code_connections_and_projects() -> None:
    """An edit must not silently drop the user's connections or saved projects."""
    existing = {
        "connect_code": "KEEPTHIS12",
        "connections": ["alice", "bob"],
        "projects": ["p1", "p2"],
    }
    doc = build_user_document("newname", b"newhash", "new@example.com", existing=existing)

    assert doc["connect_code"] == "KEEPTHIS12"
    assert doc["connections"] == ["alice", "bob"]
    assert doc["projects"] == ["p1", "p2"]
    assert doc["username"] == "newname"
    assert doc["password"] == b"newhash"


def test_editing_an_account_missing_the_optional_lists_does_not_raise() -> None:
    """Older records may predate connections/projects; only connect_code is required."""
    doc = build_user_document("x", b"h", "x@y.zz", existing={"connect_code": "CODE123456"})
    assert doc["connections"] == []
    assert doc["projects"] == []


def test_a_new_account_gets_a_different_code_each_time() -> None:
    a = build_user_document("a", b"h", "a@b.cc")
    b = build_user_document("b", b"h", "b@c.dd")
    assert a["connect_code"] != b["connect_code"]


# --- connections -----------------------------------------------------------


def _user(uid: str, connections: list | None = None) -> dict:
    return {"_id": uid, "username": f"user-{uid}", "connections": connections or []}


def test_a_valid_new_connection_is_allowed() -> None:
    check_new_connection(_user("me"), _user("them"), "user-them")


def test_a_wrong_username_or_code_is_rejected() -> None:
    """find_one returned nothing: the pair did not match."""
    with pytest.raises(ValidationError) as exc:
        check_new_connection(_user("me"), None, "ghost")
    assert exc.value.title == "INVALID CONNECTION"
    assert exc.value.retry is True


def test_connecting_to_yourself_is_rejected() -> None:
    """The regression.

    Entering your own username and your own connect code found *you*: the
    already-connected test passed (your id is not yet in your own list), and
    both halves of the two-sided update then ran against the same document,
    pushing your own id into your own connections twice.
    """
    me = _user("me")
    with pytest.raises(ValidationError, match="cannot create a connection with yourself"):
        check_new_connection(me, me, "user-me")


def test_connecting_to_yourself_is_rejected_even_via_a_separate_lookup() -> None:
    """Identity is by _id, not by object -- the DB hands back a fresh dict."""
    me = _user("me")
    same_user_from_db = {"_id": "me", "username": "user-me", "connections": []}
    with pytest.raises(ValidationError, match="yourself"):
        check_new_connection(me, same_user_from_db, "user-me")


def test_an_existing_connection_is_rejected_and_does_not_reopen() -> None:
    me = _user("me", connections=["them"])
    with pytest.raises(ValidationError) as exc:
        check_new_connection(me, _user("them"), "user-them")
    assert exc.value.title == "REPEATED CONNECTION"
    assert "user-them" in exc.value.message
    # Retyping cannot fix this, so the dialog closes rather than reopening.
    assert exc.value.retry is False


def test_a_user_with_no_connections_key_is_handled() -> None:
    """Older records may predate the field."""
    check_new_connection({"_id": "me"}, _user("them"), "user-them")
