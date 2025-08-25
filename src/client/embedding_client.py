from sentence_transformers import SentenceTransformer

from src.config.settings import get_settings
from typing import List


class EmbeddingClient:
    def __init__(self, model_name: str = get_settings().EMBEDDING_MODEL):
        """
        Initialize the embedding client with a SentenceTransformers model.
        """
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str, batch_size: int = 15,to_list: bool = False) -> List[float]:
        """
        Generate an embedding vector for a single string.
        """
        embeddings = self.model.encode(text, batch_size=batch_size, show_progress_bar = True)
        return embeddings.tolist() if to_list else embeddings

    def embed_batch(self, texts: List[str], batch_size: int = 15, to_list: bool = False) -> List[List[float]]:
        """
        Generate embedding vectors for a list of strings.
        """
        return [vec.tolist() if to_list else vec for vec in self.model.encode(texts, batch_size=batch_size, show_progress_bar = True)]
