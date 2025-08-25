import os
import tempfile
import uuid
from typing import List, Dict, Any

from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from fastapi import UploadFile

from src.models.document_model import DocumentModel, VectorPayload

from src.client.embedding_client import EmbeddingClient
from src.config.settings import get_settings
from src.repository.document_vector_repository import VectorRepository
from src.utils.chunker import chunker
from src.utils.extractor import load_document
from src.exceptions.exceptions import (
    DocumentNotFoundError,
    FileTypeError,
    EmptyDocumentError,
    ChunkingError,
    DocumentRepositoryError,
    VectorCollectionError,
    PointError,
    FileProcessingError, 
    EmbeddingError
)

settings = get_settings()


class DocumentService:
    def __init__(self):
        self.embedder = EmbeddingClient()
        self.vector_repo = VectorRepository()

    async def upload_document(self, file: UploadFile, user_id: str) -> Dict[str, Any]:
        """Upload and process a document for a specific user"""
        doc_id = str(uuid.uuid4())

        # Validate file type
        if not file.filename:
            raise FileTypeError("No filename provided")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.txt', '.pdf', '.docx']:
            raise FileTypeError("Unsupported file type. Only .txt, .pdf, and .docx files are supported.")

        try:
            # Process file content and create chunks with embeddings
            chunks_data = await self._process_document(file)

            # Create document metadata using the model
            doc_metadata = DocumentModel(
                doc_id=doc_id,
                user_id=user_id,
                filename=file.filename,
                file_type=ext,
                chunks_count=len(chunks_data),
                created_at=settings.get_utc_now().isoformat()
            ).dict()

            # Save vector points to Qdrant with doc metadata in each chunk payload
            points = []
            for i, chunk in enumerate(chunks_data):
                # Create payload using the VectorPayload model for consistent structure
                payload = VectorPayload(
                    doc_id=doc_id,
                    user_id=user_id,
                    chunk_text=chunk["text"],
                    chunk_index=i,
                    filename=file.filename,
                    file_type=ext,
                    created_at=doc_metadata["created_at"],
                    # Store complete document metadata in each chunk
                    doc_metadata=doc_metadata
                ).dict()

                # Qdrant requires an unsigned integer or a UUID as point ID.
                # Generate a stable UUIDv5 from base doc_id and chunk index.
                point_uuid = uuid.uuid5(uuid.UUID(doc_id), str(i))

                points.append(
                    PointStruct(
                        id=str(point_uuid),
                        vector=chunk["embedding"],
                        payload=payload
                    )
                )

            await self.vector_repo.save_points(points)

            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "file_type": ext,
                "chunks_count": len(chunks_data),
                "message": "Document uploaded successfully"
            }
        except (VectorCollectionError, PointError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            raise DocumentRepositoryError(f"Failed to upload document: {str(e)}")

    async def list_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """List all documents for a specific user"""
        try:
            # Get unique documents for the user from Qdrant
            documents = await self.vector_repo.get_unique_documents(user_id=user_id)
            return documents
        except PointError:
            raise
        except Exception as e:
            raise DocumentRepositoryError(f"Failed to list documents: {str(e)}")

    async def get_user_document(self, doc_id: str, user_id: str) -> Dict[str, Any]:
        """Get a specific document for a user"""
        try:
            # Get document chunks from vector store (with user_id filter for security)
            chunks = await self.vector_repo.get_points_by_doc_id(doc_id, user_id=user_id)

            if not chunks:
                raise DocumentNotFoundError(f"Document {doc_id} not found")

            # Get document metadata from the first chunk
            doc_metadata = chunks[0].get("doc_metadata", {})

            if not doc_metadata:
                # Fallback to reconstructing metadata if not available
                doc_metadata = {
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "filename": chunks[0].get("filename", "Unknown"),
                    "file_type": chunks[0].get("file_type", ""),
                    "created_at": chunks[0].get("created_at", ""),
                    "chunks_count": len(chunks)
                }

            # Add the chunks to the response
            doc_metadata["chunks"] = sorted(chunks, key=lambda x: x.get("chunk_index", 0))

            return doc_metadata
        except DocumentNotFoundError:
            raise
        except (VectorCollectionError, PointError):
            raise
        except Exception as e:
            raise DocumentRepositoryError(f"Failed to retrieve document: {str(e)}")

    async def delete_user_document(self, doc_id: str, user_id: str) -> Dict[str, str]:
        """Delete a document and its vectors for a specific user"""
        try:
            # Check if document exists and belongs to user
            chunks = await self.vector_repo.get_points_by_doc_id(doc_id, user_id=user_id)

            if not chunks:
                raise DocumentNotFoundError(f"Document {doc_id} not found")

            # Delete vectors from Qdrant with user_id filter for safety
            await self.vector_repo.delete_points_by_doc_id(doc_id, user_id=user_id)

            return {"message": f"Document {doc_id} deleted successfully"}
        except DocumentNotFoundError:
            raise
        except (VectorCollectionError, PointError):
            raise
        except Exception as e:
            raise DocumentRepositoryError(f"Failed to delete document: {str(e)}")

    async def search_user_documents(self, query: str, top_k: int, user_id: str) -> List[Dict[str, Any]]:
        """Search documents for a specific user"""
        if not query.strip():
            raise EmptyDocumentError("Query cannot be empty")

        try:
            # Generate query embedding using the actual embedding client
            query_embedding = self.embedder.embed(query, to_list=True)

            # Create filter to only search user's documents
            user_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

            # Search vectors
            results = await self.vector_repo.search(
                query_vector=query_embedding,
                top_k=top_k,
                query_filter=user_filter
            )

            return [
                {
                    "doc_id": result.payload["doc_id"],
                    "filename": result.payload.get("filename", "Unknown"),
                    "chunk_text": result.payload["chunk_text"],
                    "score": result.score,
                    "chunk_index": result.payload["chunk_index"]
                }
                for result in results
            ]
        except (VectorCollectionError, PointError):
            raise
        except Exception as e:
            raise DocumentRepositoryError(f"Failed to search documents: {str(e)}")

    async def _process_document(self, file: UploadFile) -> List[Dict[str, Any]]:
        """Process document into chunks with embeddings"""
        temp_file_path = None
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Extract text from the document using your extractor
            try:
                text = load_document(temp_file_path)
            except ValueError as e:
                raise FileTypeError(str(e))
            except Exception as e:
                raise FileProcessingError(f"Failed to extract text from document: {str(e)}")

            if not text.strip():
                raise EmptyDocumentError("Document appears to be empty or text could not be extracted")

            # Create chunks using your chunker
            try:
                chunks = chunker(text)
            except Exception as e:
                raise ChunkingError(f"Failed to chunk document: {str(e)}")

            if not chunks:
                raise ChunkingError("No chunks could be created from the document")

            # Generate embeddings for all chunks
            chunk_texts = [chunk for chunk in chunks if chunk.strip()]
            if not chunk_texts:
                raise EmptyDocumentError("No valid text chunks found in document")

            try:
                embeddings = self.embedder.embed_batch(chunk_texts, to_list=True)
            except Exception as e:
                raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")

            chunks_data = []
            for i, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunks_data.append({
                    "text": chunk_text,
                    "embedding": embedding
                })

            return chunks_data

        except (FileTypeError, EmptyDocumentError, ChunkingError, EmbeddingError, FileProcessingError):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            raise FileProcessingError(f"Unexpected error processing document: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)