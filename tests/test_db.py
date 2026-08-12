"""Tests for the ChimeraDB data-access layer, run against an in-memory Mongo
mock (mongomock) so no live cluster is required.
"""

import mongomock
import pytest

from db import ChimeraDB, _build_uri


@pytest.fixture
def database():
    return ChimeraDB(mongomock.MongoClient().CHIMERA)


def test_insert_and_find_user(database):
    database.insert_user({"username": "alice", "email": "a@example.com"})
    found = database.find_user("alice")
    assert found is not None
    assert found["email"] == "a@example.com"


def test_find_user_missing_returns_none(database):
    assert database.find_user("nobody") is None


def test_username_taken(database):
    assert database.username_taken("alice") is False
    database.insert_user({"username": "alice"})
    assert database.username_taken("alice") is True


def test_user_by_id(database):
    result = database.insert_user({"username": "bob"})
    fetched = database.user_by_id(result.inserted_id)
    assert fetched["username"] == "bob"


def test_replace_user_fields(database):
    database.insert_user({"username": "carol", "email": "old@example.com"})
    database.replace_user_fields("carol", {"email": "new@example.com"})
    assert database.find_user("carol")["email"] == "new@example.com"


def test_project_crud(database):
    assert database.all_projects() == []
    result = database.insert_project({"name": "p1", "owner": "alice"})
    projects = database.all_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "p1"

    fetched = database.project_by_id(result.inserted_id)
    assert fetched["owner"] == "alice"

    database.delete_project(result.inserted_id)
    assert database.all_projects() == []


def test_collection_accessors_present(database):
    # The complex group/connection queries still use the raw collections.
    assert database.users is not None
    assert database.projects is not None
    assert database.groups is not None


# --- connection URI ------------------------------------------------------


def test_uri_contains_plain_credentials_unchanged():
    uri = _build_uri("alice", "hunter2")
    assert "://alice:hunter2@" in uri


@pytest.mark.parametrize(
    ("password", "encoded"),
    [
        ("p@ssword", "p%40ssword"),
        ("colon:sep", "colon%3Asep"),
        ("slash/es", "slash%2Fes"),
        ("100%sure", "100%25sure"),
    ],
)
def test_uri_percent_encodes_credentials(password, encoded):
    """@ : / and % are URI delimiters -- unencoded they break the connection string."""
    uri = _build_uri("user", password)
    assert f"://user:{encoded}@chimera-data" in uri
    # The raw character must not survive into the credential section.
    assert uri.count("@") == 1


def test_uri_encodes_the_username_too():
    assert "://a%40b:pw@" in _build_uri("a@b", "pw")
