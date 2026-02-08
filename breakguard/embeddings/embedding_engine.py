"""
BreakGuard - Embeddings Module
Handles conversion of API descriptions to semantic vector embeddings.
"""

from sentence_transformers import SentenceTransformer

# Default model: all-MiniLM-L6-v2 produces 384-dimensional vectors
DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingEngine:
    """Generates semantic embeddings from API descriptions."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize the embedding engine.

        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        print(f"  Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"  Model loaded. Dimension: {self.dimension}")

    def api_to_text(self, api: dict) -> str:
        """
        Convert an API entry into a semantic text description.

        Combines function name, description, signature, category, and params
        into a rich text representation for embedding.

        Args:
            api: Dictionary with function, description, signature, etc.

        Returns:
            A text string suitable for embedding.
        """
        parts = []

        # Function name is primary
        func_name = api.get("function", "")
        parts.append(func_name)

        # Description provides semantic meaning
        description = api.get("description", "")
        if description:
            parts.append(description)

        # Signature shows usage pattern
        signature = api.get("signature", "")
        if signature:
            parts.append(f"Usage: {signature}")

        # Category adds context
        category = api.get("category", "")
        if category:
            parts.append(f"Category: {category}")

        # Params provide detail
        params = api.get("params", [])
        if params:
            parts.append(f"Parameters: {', '.join(params)}")

        # Return type
        returns = api.get("returns", "")
        if returns:
            parts.append(f"Returns: {returns}")

        return ". ".join(parts)

    def encode(self, text: str) -> list:
        """
        Encode a text string into a vector embedding.

        Args:
            text: The text to encode.

        Returns:
            List of floats representing the embedding vector.
        """
        vector = self.model.encode(text)
        return vector.tolist()

    def encode_api(self, api: dict) -> list:
        """
        Encode an API entry directly into a vector.

        Args:
            api: Dictionary with API information.

        Returns:
            List of floats representing the embedding vector.
        """
        text = self.api_to_text(api)
        return self.encode(text)

    def encode_batch(self, texts: list) -> list:
        """
        Encode multiple texts at once for efficiency.

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors.
        """
        vectors = self.model.encode(texts)
        return [v.tolist() for v in vectors]
