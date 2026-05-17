class LazySentenceTransformer:
    """Load the embedding model only when upload/search actually needs it."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, *args, **kwargs):
        return self._load().encode(*args, **kwargs)

    def get_sentence_embedding_dimension(self):
        return self._load().get_sentence_embedding_dimension()


embed_model = LazySentenceTransformer('all-mpnet-base-v2')
