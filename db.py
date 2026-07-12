"""Data-access layer for CHIMERA Online.

Wraps the MongoDB collections behind a small object so the Tkinter code in
``main.py`` does not embed connection strings or query details. Query logic lives
here where it can be unit-tested against an in-memory mock, separate from the UI.

The connection itself (:meth:`ChimeraDB.connect`) still requires a live cluster
and shared credentials -- that architectural limitation is tracked separately
(code-review item #1). Everything else is plain data access.
"""

from typing import Any

import pymongo

_URI_TEMPLATE = (
    "mongodb+srv://{user}:{password}"
    "@chimera-data.gbqbn.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
_MAX_TIME_MS = 5000


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
            _URI_TEMPLATE.format(user=username, password=password),
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

    # --- projects --------------------------------------------------------

    def all_projects(self) -> list:
        return list(self.projects.find({}))

    def project_by_id(self, project_id: Any) -> Any:
        return self.projects.find_one({"_id": project_id})

    def insert_project(self, doc: dict) -> Any:
        return self.projects.insert_one(doc)

    def delete_project(self, project_id: Any) -> Any:
        return self.projects.delete_one({"_id": project_id})
