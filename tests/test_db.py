"""Tests for the ChimeraDB data-access layer, run against an in-memory Mongo
mock (mongomock) so no live cluster is required.
"""

import mongomock
import pytest

from db import ChimeraDB


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
