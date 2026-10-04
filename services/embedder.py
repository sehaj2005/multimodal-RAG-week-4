from functools import lru_cache
from services.config import EMBEDDING_MODEL

@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)

def create_embedding(text: str) -> list[float]:
    return get_model().encode(text).tolist()
