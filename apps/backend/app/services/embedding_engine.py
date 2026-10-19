"""Local zero-cost embedding engine using FastEmbed and MiniLM."""

from fastembed import TextEmbedding

from app.core.config import settings


class EmbeddingEngine:
    """Generates dense vector embeddings using local ONNX runtime."""

    _model: TextEmbedding | None = None

    @classmethod
    def get_model(cls) -> TextEmbedding:
        """Lazily initializes and returns the cached TextEmbedding model.

        Returns:
            The loaded TextEmbedding model instance.
        """
        if cls._model is None:
            cls._model = TextEmbedding(model_name=settings.embedding_model)
        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> list[float]:
        """Embeds a single string into a 384-dimensional vector.

        Args:
            text: The text string to embed.

        Returns:
            A list of 384 floats representing the normalized embedding vector.
        """
        model = cls.get_model()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()

    @classmethod
    def embed_texts(cls, texts: list[str]) -> list[list[float]]:
        """Embeds multiple strings into 384-dimensional vectors in batch.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of 384-float embedding vectors.
        """
        model = cls.get_model()
        embeddings = list(model.embed(texts))
        return [emb.tolist() for emb in embeddings]
