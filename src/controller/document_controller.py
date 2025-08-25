from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List, Dict, Any

from src.service.document_service import DocumentService
from src.service.authentication_service import get_current_user_bearer
from src.exceptions.exceptions import (
    VectorCollectionError, 
    PointError,
    DocumentRepositoryError,
    DocumentNotFoundError,
    FileTypeError,
    EmptyDocumentError,
    ChunkingError,
    EmbeddingError,
    FileProcessingError
)
from src.models.document_model import (
    DocumentResponse,
    DocumentUploadResponse,
    SearchResult,
    DeleteResponse
)

document_router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


@document_router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Upload and process a document for the authenticated user"""
    try:
        return await document_service.upload_document(
            file=file, 
            user_id=current_user["user_id"]
        )
    except FileTypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except EmptyDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ChunkingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except EmbeddingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except FileProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except VectorCollectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector storage error: {str(e)}"
        )
    except PointError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector point error: {str(e)}"
        )
    except DocumentRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@document_router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """List all documents for the authenticated user"""
    try:
        # Get all documents for the user from Qdrant
        documents = await document_service.list_user_documents(
            user_id=current_user["user_id"]
        )

        # Convert to response model format
        return [
            DocumentResponse(
                id=doc.get("doc_id", ""),  # Using doc_id as the primary ID now
                doc_id=doc.get("doc_id", ""),
                filename=doc.get("filename", ""),
                file_type=doc.get("file_type", ""),
                chunks_count=doc.get("chunks_count", 0),
                created_at=doc.get("created_at", ""),
                user_id=doc.get("user_id", "")
            ) for doc in documents
        ]
    except PointError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector storage error: {str(e)}"
        )
    except DocumentRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@document_router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Get a specific document for the authenticated user"""
    try:
        document = await document_service.get_user_document(
            doc_id=doc_id, 
            user_id=current_user["user_id"]
        )

        # Extract the document metadata without the chunks for the response
        chunks = document.pop("chunks", [])
        chunks_count = len(chunks)

        return DocumentResponse(
            id=document.get("doc_id", ""),
            doc_id=document.get("doc_id", ""),
            filename=document.get("filename", ""),
            file_type=document.get("file_type", ""),
            chunks_count=chunks_count,
            created_at=document.get("created_at", ""),
            user_id=document.get("user_id", "")
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except VectorCollectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector storage error: {str(e)}"
        )
    except PointError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector point error: {str(e)}"
        )
    except DocumentRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@document_router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Delete a document for the authenticated user"""
    try:
        return await document_service.delete_user_document(
            doc_id=doc_id, 
            user_id=current_user["user_id"]
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except VectorCollectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector storage error: {str(e)}"
        )
    except PointError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector point error: {str(e)}"
        )
    except DocumentRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@document_router.post("/search", response_model=List[SearchResult])
async def search_documents(
    query: str,
    top_k: int = 5,
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Search documents for the authenticated user"""
    try:
        search_results = await document_service.search_user_documents(
            query=query, 
            top_k=top_k, 
            user_id=current_user["user_id"]
        )

        # Convert to SearchResult model
        return [
            SearchResult(
                doc_id=result.get("doc_id", ""),
                filename=result.get("filename", ""),
                chunk_text=result.get("chunk_text", ""),
                score=result.get("score", 0.0),
                chunk_index=result.get("chunk_index", 0)
            ) for result in search_results
        ]
    except EmptyDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VectorCollectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector storage error: {str(e)}"
        )
    except PointError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector point error: {str(e)}"
        )
    except DocumentRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search documents: {str(e)}"
        )