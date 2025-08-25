from typing import List, Dict, Any, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType
)

# As requested, these are now imported from your separate files.
from src.config.settings import get_settings
from src.exceptions.exceptions import VectorCollectionError, PointError


class VectorRepository:
    """
    Asynchronous repository for handling Qdrant operations.

    This class is designed to be compatible with a JWT authentication system
    by ensuring that all operations that need to be scoped by a user, such as
    search and deletion, can accept a user ID filter. The service layer
    will be responsible for passing the authenticated user's ID to these methods.
    """

    def __init__(self,
                 url: str = get_settings().QDRANT_URL,
                 collection_name: str = get_settings().DOCUMENTS_COLLECTION,
                 vector_size: int = get_settings().VECTOR_SIZE,  # Adjust this to match your embedding model
                 distance_metric: str = "Cosine"):
        """
        Initializes the repository with a Qdrant client URL.
        """
        self.client = AsyncQdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance_metric = distance_metric
        self._collection_ready: bool = False

    async def _ensure_collection_exists(self):
        """
        Ensure the collection exists and indices are created. Cached after first success.
        """
        if self._collection_ready:
            return

        try:
            exists = await self.client.collection_exists(self.collection_name)
            if not exists:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                )

                indices = [
                    {"field_name": "user_id", "field_schema": PayloadSchemaType.KEYWORD},
                    {"field_name": "doc_id", "field_schema": PayloadSchemaType.KEYWORD},
                    {"field_name": "filename", "field_schema": PayloadSchemaType.KEYWORD},
                    {"field_name": "file_type", "field_schema": PayloadSchemaType.KEYWORD},
                    {"field_name": "created_at", "field_schema": PayloadSchemaType.TEXT},
                    {"field_name": "chunk_index", "field_schema": PayloadSchemaType.INTEGER},
                ]
                for index in indices:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=index["field_name"],
                        field_schema=index["field_schema"]
                    )

            self._collection_ready = True
        except Exception as e:
            raise VectorCollectionError(f"Failed to initialize Qdrant collection: {e}")

    async def initialize_collection(self):
        try:
            await self._ensure_collection_exists()
        except Exception:
            raise

    async def save_points(self, points: List[PointStruct]):
        """Upsert points to the collection."""
        await self._ensure_collection_exists()
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
        except Exception as e:
            raise PointError(f"Failed to save points to Qdrant: {e}")

    async def search(self,
                     query_vector: List[float],
                     top_k: int = 5,
                     query_filter: Optional[Filter] = None) -> List:
        """Search points and return a list of scored points with payloads."""
        await self._ensure_collection_exists()
        try:
            search_response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False
            )
            if isinstance(search_response, tuple):
                points = search_response[0]
            else:
                points = getattr(search_response, "points", search_response)
            return points
        except Exception as e:
            raise PointError(f"Failed to search Qdrant: {e}")

    async def get_points_by_doc_id(self, doc_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all payloads for a given document ID (optionally filtered by user)."""
        await self._ensure_collection_exists()
        try:
            conditions = [FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            if user_id:
                conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
            doc_filter = Filter(must=conditions)

            points, _ = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=doc_filter,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            return [point.payload for point in points]
        except Exception as e:
            raise PointError(f"Failed to retrieve points for document ID '{doc_id}': {e}")

    async def delete_points(self, query_filter: Filter):
        """Delete points matching the provided filter."""
        await self._ensure_collection_exists()
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=query_filter
            )
        except Exception as e:
            raise PointError(f"Failed to delete points from Qdrant: {e}")

    async def delete_points_by_doc_id(self, doc_id: str, user_id: Optional[str] = None):
        await self._ensure_collection_exists()
        try:
            conditions = [FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            if user_id:
                conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
            doc_filter = Filter(must=conditions)
            await self.delete_points(query_filter=doc_filter)
        except Exception as e:
            raise PointError(f"Failed to delete points for document ID '{doc_id}': {e}")

    async def get_unique_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return unique documents by doc_id with basic metadata."""
        await self._ensure_collection_exists()
        try:
            query_filter = None
            if user_id:
                query_filter = Filter(must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ])

            points_response = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            all_points = points_response[0]

            doc_id_map = {}
            for point in all_points:
                d_id = point.payload.get("doc_id")
                if d_id and d_id not in doc_id_map:
                    doc_id_map[d_id] = point

            points = list(doc_id_map.values())

            documents = []
            for point in points:
                if "doc_metadata" in point.payload and point.payload["doc_metadata"]:
                    doc_metadata = point.payload["doc_metadata"]
                else:
                    doc_metadata = {
                        "doc_id": point.payload["doc_id"],
                        "user_id": point.payload["user_id"],
                        "filename": point.payload["filename"],
                        "file_type": point.payload.get("file_type", ""),
                        "created_at": point.payload.get("created_at", "")
                    }
                documents.append(doc_metadata)

            return documents
        except Exception as e:
            raise PointError(f"Failed to retrieve unique documents: {e}")

    async def get_document_metadata(self, doc_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get document metadata from any chunk."""
        await self._ensure_collection_exists()
        try:
            conditions = [FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            if user_id:
                conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
            doc_filter = Filter(must=conditions)

            points, _ = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=doc_filter,
                limit=1,
                with_payload=True,
                with_vectors=False
            )

            if not points:
                return None

            point = points[0]
            if "doc_metadata" in point.payload and point.payload["doc_metadata"]:
                return point.payload["doc_metadata"]
            else:
                return {
                    "doc_id": point.payload["doc_id"],
                    "user_id": point.payload["user_id"],
                    "filename": point.payload["filename"],
                    "file_type": point.payload.get("file_type", ""),
                    "created_at": point.payload.get("created_at", "")
                }
        except Exception as e:
            raise PointError(f"Failed to retrieve document metadata for '{doc_id}': {e}")
