"""Data-access layer for CHIMERA Online.

Wraps the MongoDB collections behind a small object so the Tkinter code in
``main.py`` does not embed connection strings or query details. Query logic lives
here where it can be unit-tested against an in-memory mock, separate from the UI.

The connection itself (:meth:`ChimeraDB.connect`) still requires a live cluster
and shared credentials -- that architectural limitation is tracked separately
(code-review item #1). Everything else is plain data access.
"""

from typing import Any
from urllib.parse import quote_plus

import pymongo

_URI_TEMPLATE = (
    "mongodb+srv://{user}:{password}"
    "@chimera-data.gbqbn.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
_MAX_TIME_MS = 5000


def _build_uri(username: str, password: str) -> str:
    """The connection URI, with credentials percent-encoded.

    MongoDB requires this: ``@``, ``:``, ``/`` and ``%`` are all URI delimiters,
    so a password containing any of them silently produced a malformed URI and
    an opaque connection failure. Percent-encoding is what MongoDB's own docs
    prescribe for credentials embedded in a connection string.
    """
    return _URI_TEMPLATE.format(user=quote_plus(username), password=quote_plus(password))


class ChimeraDB:
    """Thin wrapper over the CHIMERA MongoDB database.

    Construct directly from a database handle (used by tests with a mock), or
    via :meth:`connect` which builds a real ``MongoClient``.
    """

    def __init__(self, database: Any, client: Any = None) -> None:
        self._client = client
        self.users = database.users
        self.projects = database.projects
        self.groups = database.groups

    @classmethod
    def connect(cls, username: str, password: str, connect_timeout_ms: int = 5000) -> "ChimeraDB":
        client: Any = pymongo.MongoClient(
            _build_uri(username, password),
            connectTimeoutMS=connect_timeout_ms,
        )
        return cls(client.CHIMERA, client=client)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    # --- users -----------------------------------------------------------

    def find_user(self, username: str) -> Any:
        return self.users.find_one({"username": username}, max_time_ms=_MAX_TIME_MS)

    def user_by_id(self, user_id: Any) -> Any:
        return self.users.find_one({"_id": user_id})

    def username_taken(self, username: str) -> bool:
        return self.find_user(username) is not None

    def insert_user(self, doc: dict) -> Any:
        return self.users.insert_one(doc)

    def replace_user_fields(self, username: str, changes: dict) -> Any:
        return self.users.update_one({"username": username}, {"$set": changes})

    # --- connections -----------------------------------------------------
    #
    # A connection is stored on both users, so creating or removing one is two
    # writes that must not half-happen. These were previously two bare
    # update_one calls in the UI: if the second failed, the first stood, and the
    # two accounts disagreed about whether they were connected -- permanently,
    # since nothing ever reconciles them.
    #
    # They compensate rather than use a transaction. Atlas would support one,
    # but mongomock has no session support at all ("Mongomock does not support
    # sessions yet"), so a transactional path could not be tested here, and an
    # untested branch in a write path is its own hazard. Undoing the first write
    # narrows the failure window to "the undo also failed", which is strictly
    # better and exercised by the tests.

    def connect_users(self, a_username: str, a_id: Any, b_username: str, b_id: Any) -> None:
        """Record a connection on both accounts, or on neither."""
        self.users.update_one({"username": a_username}, {"$push": {"connections": b_id}})
        try:
            self.users.update_one({"username": b_username}, {"$push": {"connections": a_id}})
        except pymongo.errors.PyMongoError:
            self.users.update_one({"username": a_username}, {"$pull": {"connections": b_id}})
            raise

    def disconnect_users(self, a_username: str, a_id: Any, b_id: Any) -> None:
        """Remove a connection from both accounts, or from neither."""
        self.users.update_one({"username": a_username}, {"$pull": {"connections": b_id}})
        try:
            self.users.update_one({"_id": b_id}, {"$pull": {"connections": a_id}})
        except pymongo.errors.PyMongoError:
            self.users.update_one({"username": a_username}, {"$push": {"connections": b_id}})
            raise

    def drop_member_from_owned_groups(self, owner_username: str, member_id: Any) -> Any:
        """Remove a user from every group the given owner runs."""
        return self.groups.update_many(
            {"owner": owner_username, "members": {"$in": [member_id]}},
            {"$pull": {"members": member_id}},
        )

    # --- projects --------------------------------------------------------

    def all_projects(self) -> list:
        return list(self.projects.find({}))

    def project_by_id(self, project_id: Any) -> Any:
        return self.projects.find_one({"_id": project_id})

    def insert_project(self, doc: dict) -> Any:
        return self.projects.insert_one(doc)

    def delete_project(self, project_id: Any) -> Any:
        return self.projects.delete_one({"_id": project_id})

    def purge_project(self, project_id: Any) -> None:
        """Delete a project and drop it from every group that referenced it.

        Group references are cleared *first*, deliberately. The reverse order
        (what the UI did) leaves dangling references in every group if the
        cleanup fails after the delete has landed, and a group listing a project
        that no longer exists is the harder state to recover from. This way a
        failure leaves the project intact and merely un-grouped.
        """
        self.groups.update_many(
            {"projects": {"$in": [project_id]}}, {"$pull": {"projects": project_id}}
        )
        self.projects.delete_one({"_id": project_id})

    def remove_project_from_group(self, group_id: Any, project_id: Any) -> Any:
        """Drop one project from one group."""
        return self.groups.update_one({"_id": group_id}, {"$pull": {"projects": project_id}})
