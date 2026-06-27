"""Base repository with common CRUD operations."""

from typing import Any, Generic, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pydantic import BaseModel

from app.utils.exceptions import NotFoundError
from app.utils.helpers import utc_now

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Generic async MongoDB repository."""

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_class: type[T]) -> None:
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_class = model_class

    def _to_model(self, document: dict[str, Any] | None) -> T | None:
        if document is None:
            return None
        document["_id"] = str(document["_id"])
        return self.model_class.model_validate(document)

    def _to_document(self, model: T) -> dict[str, Any]:
        data = model.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"]:
            data["_id"] = ObjectId(data["_id"])
        elif "_id" in data:
            del data["_id"]
        return data

    async def create(self, model: T) -> T:
        document = self._to_document(model)
        document.pop("_id", None)
        result = await self.collection.insert_one(document)
        document["_id"] = str(result.inserted_id)
        return self.model_class.model_validate(document)

    async def find_by_id(self, entity_id: str) -> T | None:
        document = await self.collection.find_one({"_id": ObjectId(entity_id)})
        return self._to_model(document)

    async def find_by_id_or_raise(self, entity_id: str) -> T:
        entity = await self.find_by_id(entity_id)
        if entity is None:
            raise NotFoundError(f"{self.model_class.__name__} not found: {entity_id}")
        return entity

    async def update(self, entity_id: str, updates: dict[str, Any]) -> T | None:
        if "updated_at" in self.model_class.model_fields:
            updates["updated_at"] = utc_now()
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(entity_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_model(result)

    async def delete(self, entity_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(entity_id)})
        return result.deleted_count > 0

    async def find_many(
        self,
        filter_query: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        cursor = self.collection.find(filter_query or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_model(doc) for doc in documents if doc]

    async def count(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.collection.count_documents(filter_query or {})
