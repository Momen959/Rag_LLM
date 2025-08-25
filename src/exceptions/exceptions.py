class UserRepositoryError(Exception):
    """Raised when there's an error in the user repository operations."""
    pass


class UserNotFoundError(Exception):
    """Raised when a user cannot be found by the provided identifier."""
    pass


class UserExistsError(Exception):
    """Raised when attempting to create a user that already exists."""
    pass


class UserUpdateError(Exception):
    """Raised when there's an error updating a user record."""
    pass


class UserDeleteError(Exception):
    """Raised when there's an error deleting a user record."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when user credentials are invalid."""
    pass


class TokenError(Exception):
    """Raised when there's an error with JWT tokens."""
    pass


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""
    pass


# Vector Repository Exceptions
class VectorCollectionError(Exception):
    """Raised when there's an error with Qdrant vector collections."""
    pass


class PointError(Exception):
    """Raised when there's an error with Qdrant vector points."""
    pass


# Document Exceptions
class DocumentRepositoryError(Exception):
    """Raised when there's an error in document repository operations."""
    pass


class DocumentNotFoundError(Exception):
    """Raised when a document cannot be found."""
    pass


class DocumentValidationError(Exception):
    """Raised when document validation fails."""
    pass


class FileTypeError(Exception):
    """Raised when an unsupported file type is encountered."""
    pass


class EmptyDocumentError(Exception):
    """Raised when a document is empty or has no valid content."""
    pass


class ChunkingError(Exception):
    """Raised when there's an error chunking document text."""
    pass


class EmbeddingError(Exception):
    """Raised when there's an error generating embeddings."""
    pass


class FileProcessingError(Exception):
    """Raised when there's an error processing a file."""
    pass