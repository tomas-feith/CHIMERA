"""Account rules for CHIMERA Online: validation, password hashing, connect codes.

Lifted out of ``online_ui.OnlineUIMixin`` so the security-relevant parts can be
tested without a display or a database. The mixin keeps the Tkinter dialogs and
the MongoDB calls; everything here is pure.

Password storage
----------------
Hashes were stored as a bare ``salt(32) + key(32)`` blob with the PBKDF2
iteration count written as a literal ``100000`` in two separate places -- once
in ``login`` and once in ``save_account``. That has two problems: the two copies
can drift (change one and every existing login breaks), and because the stored
value records neither the algorithm nor the cost, the cost can never be raised
without invalidating every account.

:func:`hash_password` now emits a self-describing format,

    b"pbkdf2_sha256$<iterations>$" + salt + key

so the work factor travels with the hash. :func:`verify_password` still accepts
the old bare 64-byte layout, and :func:`needs_rehash` reports when a stored hash
should be replaced -- letting the login path upgrade an account in place the
next time its owner signs in, with no flag day and nobody locked out.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

# OWASP's current floor for PBKDF2-HMAC-SHA256. The previous 100_000 dates from
# an older recommendation; because the cost is stored alongside the hash now,
# raising it again later costs nothing.
ITERATIONS = 600_000
ALGORITHM = "sha256"
SALT_BYTES = 32
_PREFIX = b"pbkdf2_sha256$"

# The pre-versioning layout: 32 bytes of salt then a 32-byte SHA-256 key, at a
# fixed 100_000 iterations. Kept only so existing accounts keep working.
LEGACY_ITERATIONS = 100_000
LEGACY_SALT_BYTES = 32
LEGACY_LENGTH = 64

MIN_PASSWORD_LENGTH = 8
CONNECT_CODE_LENGTH = 10
CONNECT_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class ValidationError(ValueError):
    """Something the user typed is not acceptable.

    Carries the dialog title and body the UI already used, so moving these
    checks out of the mixin did not change a single message. ``retry`` says
    whether the dialog should reopen for another attempt (a fixable typo) or
    simply close -- which is what the existing windows already did, case by
    case.
    """

    def __init__(self, title: str, message: str, *, retry: bool = True) -> None:
        super().__init__(message)
        self.title = title
        self.message = message
        self.retry = retry


# --- field validation ------------------------------------------------------


def validate_username(username: str) -> None:
    """Raise :class:`ValidationError` unless ``username`` is acceptable."""
    # Any whitespace, not just " " and "\t". The message always claimed
    # "spaces, tabs,..." while the check only looked for those two, so a
    # username containing a newline or a non-breaking space got through.
    if any(char.isspace() for char in username):
        raise ValidationError(
            "INVALID USERNAME", "Username cannot contain whitespace (spaces, tabs,...)."
        )
    if len(username) == 0:
        raise ValidationError("INVALID USERNAME", "Username needs to have at least one character.")


def validate_password(password: str) -> None:
    """Raise :class:`ValidationError` unless ``password`` is acceptable."""
    if any(char.isspace() for char in password):
        raise ValidationError(
            "INVALID PASSWORD", "Password cannot contain whitespace (spaces, tabs,...)."
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            "INVALID PASSWORD",
            f"Password needs to have at least {MIN_PASSWORD_LENGTH} characters.",
        )


def validate_email(email: str) -> None:
    """Raise :class:`ValidationError` unless ``email`` looks like an address."""
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValidationError("INVALID EMAIL", "Please provide a valid email address.")


def validate_account(username: str, password: str, email: str) -> None:
    """Run every field check, in the order the dialogs used to."""
    validate_username(username)
    validate_password(password)
    validate_email(email)


# --- password hashing ------------------------------------------------------


def hash_password(password: str, *, iterations: int | None = None) -> bytes:
    """Hash ``password`` into the self-describing storage format.

    ``iterations`` defaults to :data:`ITERATIONS`, looked up at call time rather
    than bound as a default argument, so a test can lower the cost by patching
    the module constant. 600k rounds is the right price for a login and the
    wrong one for a test suite that logs in thirty times.
    """
    if iterations is None:
        iterations = ITERATIONS
    salt = os.urandom(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(ALGORITHM, password.encode("utf-8"), salt, iterations)
    return b"%s%d$%s%s" % (_PREFIX, iterations, salt, key)


def _split(stored: bytes) -> tuple[int, bytes, bytes]:
    """Return ``(iterations, salt, key)`` for either storage format."""
    if stored.startswith(_PREFIX):
        rest = stored[len(_PREFIX) :]
        marker = rest.index(b"$")
        iterations = int(rest[:marker])
        body = rest[marker + 1 :]
        return iterations, body[:SALT_BYTES], body[SALT_BYTES:]
    return LEGACY_ITERATIONS, stored[:LEGACY_SALT_BYTES], stored[LEGACY_SALT_BYTES:]


def verify_password(password: str, stored: object) -> bool:
    """Constant-time check of ``password`` against a stored hash.

    Returns False rather than raising for anything unusable -- a record whose
    password field is missing, a string instead of bytes, or truncated. The
    caller is a login form, and every one of those cases means the same thing
    to it. Previously a legacy or corrupt record raised TypeError out of the
    login handler and took the window down.
    """
    if not isinstance(stored, (bytes, bytearray)):
        return False
    stored = bytes(stored)
    try:
        iterations, salt, expected = _split(stored)
    except (ValueError, IndexError):
        return False
    if not salt or not expected or iterations <= 0:
        return False
    key = hashlib.pbkdf2_hmac(ALGORITHM, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(key, expected)


def needs_rehash(stored: object) -> bool:
    """True if ``stored`` should be replaced next time the password is known.

    Covers the old bare layout and any hash whose cost is below the current
    :data:`ITERATIONS`, so raising the work factor later upgrades accounts on
    their next successful login instead of requiring a reset.
    """
    if not isinstance(stored, (bytes, bytearray)):
        return True
    stored = bytes(stored)
    if not stored.startswith(_PREFIX):
        return True
    try:
        iterations, _, _ = _split(stored)
    except (ValueError, IndexError):
        return True
    return iterations < ITERATIONS


# --- connections -----------------------------------------------------------


def check_new_connection(current_user: dict, other_user: dict | None, username: str) -> None:
    """Raise :class:`ValidationError` unless this connection may be created.

    The self-connection case was previously unchecked: entering your own
    username and your own connect code found *you*, passed the
    already-connected test (your id is not yet in your own list), and then ran
    both halves of the two-sided update against the same document -- pushing
    your own id into your own connections twice, so you appeared in your own
    connection list, duplicated.
    """
    if other_user is None:
        raise ValidationError(
            "INVALID CONNECTION",
            "The username and/or the connection code provided are incorrect.",
        )
    if other_user["_id"] == current_user["_id"]:
        raise ValidationError("INVALID CONNECTION", "You cannot create a connection with yourself.")
    if other_user["_id"] in current_user.get("connections", []):
        raise ValidationError(
            "REPEATED CONNECTION",
            f"A connection between you and {username} already exists.",
            # Nothing to correct by retyping -- the old dialog closed here too.
            retry=False,
        )


# --- account documents -----------------------------------------------------


def generate_connect_code() -> str:
    """A fresh random code others use to connect to this account."""
    return "".join(secrets.choice(CONNECT_CODE_ALPHABET) for _ in range(CONNECT_CODE_LENGTH))


def build_user_document(
    username: str,
    hashed_password: bytes,
    email: str,
    *,
    existing: dict | None = None,
) -> dict:
    """The account record to store.

    Editing an account preserves its connect code, connections and projects;
    creating one generates a code and starts both lists empty.
    """
    if existing is None:
        return {
            "username": username,
            "password": hashed_password,
            "email": email,
            "connect_code": generate_connect_code(),
            "connections": [],
            "projects": [],
        }
    return {
        "username": username,
        "password": hashed_password,
        "email": email,
        "connect_code": existing["connect_code"],
        "connections": existing.get("connections", []),
        "projects": existing.get("projects", []),
    }
