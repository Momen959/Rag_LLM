from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field
from datetime import datetime, timezone


class Settings(BaseSettings):
    # Existing settings...
    QDRANT_URL: str = Field(description="URL of Qdrant server")
    DOCUMENTS_COLLECTION: str = Field(description="Name of the documents collection")
    VECTOR_SIZE: int =  Field(description="Size of the vector")
    MONGO_URL: str = Field(description="URL of MongoDB server")
    DATABASE_NAME: str = Field(description="Name of the database")
    USERS_COLLECTION: str = Field(description="Name of the users collection")
    EMBEDDING_MODEL: str = Field(description="Embedding model to use")
    CHUNK_SIZE: int = Field(description="Size of the chunks")
    OVERLAP: int = Field(description="Overlap of the chunks")
    # JWT Settings
    JWT_SECRET: str = Field(description="JWT secret.")
    JWT_ALGORITHM: str = Field(description="JWT algorithm")
    JWT_EXPIRES_MINUTES: int = Field(description="JWT expiration time in minutes")

    @staticmethod
    def get_utc_now():
        return datetime.now(timezone.utc)

    class Config:
        env_file = ".env"


def get_settings():
    return Settings()
