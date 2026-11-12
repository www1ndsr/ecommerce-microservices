from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from bson import ObjectId


class FakeRedis:
    def __init__(self):
        self.hashes: dict[str, dict[str, str]] = {}

    def hgetall(self, name: str):
        return dict(self.hashes.get(name, {}))

    def hget(self, name: str, key: str):
        return self.hashes.get(name, {}).get(key)

    def hset(self, name: str, key: str, value: str):
        self.hashes.setdefault(name, {})[key] = value
        return 1

    def hdel(self, name: str, key: str):
        values = self.hashes.get(name, {})
        return int(values.pop(key, None) is not None)

    def delete(self, name: str):
        return int(self.hashes.pop(name, None) is not None)

    def ping(self):
        return True


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field: str, direction: int):
        self.documents.sort(
            key=lambda item: item.get(field),
            reverse=direction < 0,
        )
        return self

    def skip(self, count: int):
        self.documents = self.documents[count:]
        return self

    def limit(self, count: int):
        self.documents = self.documents[:count]
        return self

    def __iter__(self):
        return iter(deepcopy(self.documents))


@dataclass
class FakeUpdateResult:
    matched_count: int
    modified_count: int
    upserted_id: Any = None


@dataclass
class FakeDeleteResult:
    deleted_count: int


class FakeMongoCollection:
    def __init__(self):
        self.documents: dict[Any, dict] = {}

    @staticmethod
    def _matches(document: dict, query: dict) -> bool:
        return all(document.get(key) == value for key, value in query.items())

    def find_one_and_update(
        self,
        query: dict,
        update: dict,
        upsert: bool = False,
        return_document=None,
    ):
        existing_key = next(
            (
                key
                for key, document in self.documents.items()
                if self._matches(document, query)
            ),
            None,
        )
        inserted = existing_key is None
        if inserted and not upsert:
            return None

        key = existing_key
        if inserted:
            key = query.get("_id", ObjectId())
            self.documents[key] = {"_id": key, **query}

        document = self.documents[key]
        if inserted:
            document.update(deepcopy(update.get("$setOnInsert", {})))
        document.update(deepcopy(update.get("$set", {})))
        return deepcopy(document)

    def update_one(self, query: dict, update: dict, upsert: bool = False):
        existing_key = next(
            (
                key
                for key, document in self.documents.items()
                if self._matches(document, query)
            ),
            None,
        )
        if existing_key is None:
            if not upsert:
                return FakeUpdateResult(0, 0)
            existing_key = query.get("_id", ObjectId())
            self.documents[existing_key] = {"_id": existing_key, **query}
            self.documents[existing_key].update(
                deepcopy(update.get("$setOnInsert", {}))
            )
            self.documents[existing_key].update(deepcopy(update.get("$set", {})))
            return FakeUpdateResult(0, 0, existing_key)

        document = self.documents[existing_key]
        document.update(deepcopy(update.get("$set", {})))
        return FakeUpdateResult(1, 1)

    def find(self, query: dict):
        return FakeCursor(
            document
            for document in self.documents.values()
            if self._matches(document, query)
        )

    def delete_one(self, query: dict):
        existing_key = next(
            (
                key
                for key, document in self.documents.items()
                if self._matches(document, query)
            ),
            None,
        )
        if existing_key is None:
            return FakeDeleteResult(0)
        del self.documents[existing_key]
        return FakeDeleteResult(1)
