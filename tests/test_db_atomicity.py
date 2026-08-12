"""Multi-document writes must not half-happen.

A connection lives on both users, so creating or removing one is two writes.
These were two bare update_one calls in the UI: if the second failed the first
stood, and the two accounts disagreed about whether they were connected --
permanently, because nothing reconciles them.

The interesting tests here inject a failure into the *second* write and assert
the first was undone. Everything runs against mongomock, which has no session
support at all, which is exactly why these compensate rather than use a
transaction.
"""

from __future__ import annotations

import mongomock
import pymongo
import pytest

from db import ChimeraDB


@pytest.fixture
def database() -> ChimeraDB:
    return ChimeraDB(mongomock.MongoClient().CHIMERA)


@pytest.fixture
def pair(database: ChimeraDB) -> tuple[dict, dict]:
    """Two users with no connections between them."""
    database.insert_user({"username": "alice", "connections": [], "projects": []})
    database.insert_user({"username": "bob", "connections": [], "projects": []})
    return database.find_user("alice"), database.find_user("bob")


def connections_of(database: ChimeraDB, username: str) -> list:
    return database.find_user(username)["connections"]


class FailingSecondWrite:
    """Lets the first update through, then fails, like a dropped link mid-pair."""

    def __init__(self, collection, fail_on: int = 2) -> None:
        self._collection = collection
        self._fail_on = fail_on
        self.calls = 0

    def update_one(self, *args, **kwargs):
        self.calls += 1
        if self.calls == self._fail_on:
            raise pymongo.errors.AutoReconnect("connection lost")
        return self._collection.update_one(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._collection, name)


# --- connecting ------------------------------------------------------------


def test_connecting_records_both_sides(database: ChimeraDB, pair) -> None:
    alice, bob = pair
    database.connect_users("alice", alice["_id"], "bob", bob["_id"])

    assert connections_of(database, "alice") == [bob["_id"]]
    assert connections_of(database, "bob") == [alice["_id"]]


def test_a_failure_on_the_second_write_leaves_no_one_way_connection(
    database: ChimeraDB, pair
) -> None:
    """The regression. Previously alice ended up connected to bob, and bob not
    to alice, with nothing to ever reconcile it."""
    alice, bob = pair
    database.users = FailingSecondWrite(database.users)

    with pytest.raises(pymongo.errors.PyMongoError):
        database.connect_users("alice", alice["_id"], "bob", bob["_id"])

    assert connections_of(database, "alice") == []
    assert connections_of(database, "bob") == []


def test_a_failure_on_the_first_write_changes_nothing(database: ChimeraDB, pair) -> None:
    alice, bob = pair
    database.users = FailingSecondWrite(database.users, fail_on=1)

    with pytest.raises(pymongo.errors.PyMongoError):
        database.connect_users("alice", alice["_id"], "bob", bob["_id"])

    assert connections_of(database, "alice") == []
    assert connections_of(database, "bob") == []


def test_the_rollback_only_removes_the_connection_it_added(database: ChimeraDB, pair) -> None:
    """Alice already knows someone else; undoing must not touch that."""
    alice, bob = pair
    database.insert_user({"username": "carol", "connections": [], "projects": []})
    carol = database.find_user("carol")
    database.connect_users("alice", alice["_id"], "carol", carol["_id"])

    database.users = FailingSecondWrite(database.users)
    with pytest.raises(pymongo.errors.PyMongoError):
        database.connect_users("alice", alice["_id"], "bob", bob["_id"])

    assert connections_of(database, "alice") == [carol["_id"]]
    assert connections_of(database, "carol") == [alice["_id"]]


# --- disconnecting ---------------------------------------------------------


def test_disconnecting_clears_both_sides(database: ChimeraDB, pair) -> None:
    alice, bob = pair
    database.connect_users("alice", alice["_id"], "bob", bob["_id"])

    database.disconnect_users("alice", alice["_id"], bob["_id"])

    assert connections_of(database, "alice") == []
    assert connections_of(database, "bob") == []


def test_a_failed_disconnect_leaves_both_sides_connected(database: ChimeraDB, pair) -> None:
    """The mirror image: a half-removed connection is just as inconsistent."""
    alice, bob = pair
    database.connect_users("alice", alice["_id"], "bob", bob["_id"])
    database.users = FailingSecondWrite(database.users)

    with pytest.raises(pymongo.errors.PyMongoError):
        database.disconnect_users("alice", alice["_id"], bob["_id"])

    assert connections_of(database, "alice") == [bob["_id"]]
    assert connections_of(database, "bob") == [alice["_id"]]


def test_disconnect_is_idempotent(database: ChimeraDB, pair) -> None:
    alice, bob = pair
    database.disconnect_users("alice", alice["_id"], bob["_id"])
    assert connections_of(database, "alice") == []


# --- projects and groups ---------------------------------------------------


def test_purging_a_project_removes_it_from_every_group(database: ChimeraDB) -> None:
    """delete_project queried {"$in": {"projects": id}}, which Mongo rejects
    outright, so the project vanished and every group kept a dead reference."""
    result = database.insert_project({"name": "p"})
    pid = result.inserted_id
    database.groups.insert_one({"name": "g1", "projects": [pid, "other"]})
    database.groups.insert_one({"name": "g2", "projects": [pid]})
    database.groups.insert_one({"name": "g3", "projects": ["unrelated"]})

    database.purge_project(pid)

    assert database.project_by_id(pid) is None
    assert database.groups.find_one({"name": "g1"})["projects"] == ["other"]
    assert database.groups.find_one({"name": "g2"})["projects"] == []
    assert database.groups.find_one({"name": "g3"})["projects"] == ["unrelated"]


def test_the_old_group_query_really_was_rejected(database: ChimeraDB) -> None:
    """Guard the guard: confirm the shape that used to be used is invalid, so
    the test above is testing a real fix and not a style change."""
    with pytest.raises(pymongo.errors.OperationFailure, match="unknown top level operator"):
        list(database.groups.find({"$in": {"projects": "anything"}}))


def test_purge_clears_references_before_deleting(database: ChimeraDB) -> None:
    """If the delete fails, the project must still exist rather than the groups
    holding a dangling id."""
    result = database.insert_project({"name": "p"})
    pid = result.inserted_id
    database.groups.insert_one({"name": "g", "projects": [pid]})

    class FailingDelete:
        def __init__(self, collection):
            self._collection = collection

        def delete_one(self, *args, **kwargs):
            raise pymongo.errors.AutoReconnect("connection lost")

        def __getattr__(self, name):
            return getattr(self._collection, name)

    database.projects = FailingDelete(database.projects)
    with pytest.raises(pymongo.errors.PyMongoError):
        database.purge_project(pid)

    # No dangling reference, and the project is still there to retry against.
    assert database.groups.find_one({"name": "g"})["projects"] == []


def test_removing_a_project_from_a_group_actually_removes_it(database: ChimeraDB) -> None:
    """The field name was " projects", with a leading space, so this pulled from
    a field no document has and the button silently did nothing."""
    group = database.groups.insert_one({"name": "g", "projects": ["p1", "p2"]})

    database.remove_project_from_group(group.inserted_id, "p1")

    assert database.groups.find_one({"_id": group.inserted_id})["projects"] == ["p2"]


def test_dropping_a_member_only_touches_groups_you_own(database: ChimeraDB) -> None:
    database.groups.insert_one({"name": "mine", "owner": "alice", "members": ["bob", "carol"]})
    database.groups.insert_one({"name": "theirs", "owner": "dave", "members": ["bob"]})

    database.drop_member_from_owned_groups("alice", "bob")

    assert database.groups.find_one({"name": "mine"})["members"] == ["carol"]
    assert database.groups.find_one({"name": "theirs"})["members"] == ["bob"]
