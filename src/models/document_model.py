from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Any
from datetime import datetime, timezone


class DocumentModel(BaseModel):
    """
    Pydantic model for a document's metadata, stored in Qdrant with each chunk.

    This model represents the full document's information.
    The `doc_id` is a UUID that links all chunks of the document in the vector store.
    """
    doc_id: str = Field(..., description="Unique document identifier (UUID string)")
    user_id: str = Field(..., description="Owner user identifier")
    filename: str = Field(..., description="Original filename with extension")
    file_type: Optional[str] = Field(default=None, description="Lowercased file extension, e.g. .pdf")
    chunks_count: int = Field(..., ge=0, description="Number of chunks extracted from the document")
    created_at: Union[datetime, str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Document creation timestamp (UTC ISO format)",
    )

    class Config:
        populate_by_name = True


class ChunkModel(BaseModel):
    """
    Model for a document chunk stored in Qdrant.
    Each chunk includes both chunk-specific data and the parent document's metadata.
    """
    # Chunk-specific data
    chunk_text: str = Field(..., description="The text content of the chunk")
    chunk_index: int = Field(..., ge=0, description="Zero-based index of this chunk within the document")

    # Document identification
    doc_id: str = Field(..., description="Parent document identifier")
    user_id: str = Field(..., description="Owner user identifier")

    # Document metadata fields
    filename: str = Field(..., description="Original filename with extension")
    file_type: Optional[str] = Field(default=None, description="Lowercased file extension, e.g. .pdf")
    created_at: Optional[Union[datetime, str]] = Field(default=None, description="Creation timestamp (UTC ISO format)")

    # Complete document metadata as a nested object
    doc_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Full document metadata payload")


class VectorPayload(ChunkModel):
    """
    Payload schema for vectors stored in Qdrant. Matches the fields written in DocumentService.
    Inherits from ChunkModel as it has identical structure.
    """
    pass


class DocumentResponse(BaseModel):
    """Response model for listing/getting documents"""
    id: str = Field(..., description="Primary id mirror of doc_id for compatibility")
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: Optional[str] = Field(default=None, description="File extension")
    chunks_count: int = Field(..., ge=0, description="Number of chunks")
    created_at: Union[datetime, str] = Field(..., description="Creation timestamp")
    user_id: str = Field(..., description="Owner user identifier")


class DocumentUploadResponse(BaseModel):
    """Response model for successful document upload"""
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: Optional[str] = Field(default=None, description="File extension")
    chunks_count: int = Field(..., ge=0, description="Number of chunks created")
    message: str = Field(..., description="Status message")


class SearchResult(BaseModel):
    """Model for search results returned from vector search"""
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_text: str = Field(..., description="Matched chunk text")
    score: float = Field(..., description="Similarity score from vector search")
    chunk_index: int = Field(..., ge=0, description="Index of the chunk in the document")


class DeleteResponse(BaseModel):
    """Response model for delete operation"""
    message: str = Field(..., description="Deletion status message")