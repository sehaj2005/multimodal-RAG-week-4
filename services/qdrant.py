import logging
import os
from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from services.config import QDRANT_PATH, EMBEDDING_DIMENSION
from services.embedder import create_embedding

logger = logging.getLogger(__name__)
COLLECTION_NAME = 'documents'
if os.getenv('QDRANT_IN_MEMORY') == '1':
    client = QdrantClient(':memory:')
else:
    QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(QDRANT_PATH))
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(collection_name=COLLECTION_NAME,
                             vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE))

def normalize_text(
    text: str,
) -> str:
    """
    Normalize text for lexical matching.
    """

    return " ".join(
        text.lower().split()
    )

def get_query_words(
    query: str,
) -> set[str]:
    """
    Extract useful words from the query.

    Common question words are ignored.
    """

    stop_words = {
        "who",
        "what",
        "when",
        "where",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "this",
        "that",
        "these",
        "those",
        "to",
        "of",
        "for",
        "in",
        "on",
        "and",
        "or",
        "did",
        "do",
        "does",
        "has",
        "have",
        "had",
        "with",
        "about",
        "exact",
        "designation",
        "person",
        "role",
    }

    words = normalize_text(
        query
    ).split()

    cleaned_words = set()

    for word in words:

        word = word.strip(
            ".,?!:;()[]{}\"'"
        )

        if not word:
            continue

        if word in stop_words:
            continue

        cleaned_words.add(
            word
        )

    return cleaned_words

def calculate_lexical_score(
    query: str,
    text: str,
) -> float:
    """
    Calculate word overlap between
    query and document text.
    """

    query_words = get_query_words(
        query
    )

    if not query_words:
        return 0.0

    normalized_text = normalize_text(
        text
    )

    text_words = set(
        normalized_text.split()
    )

    matched_words = (
        query_words.intersection(
            text_words
        )
    )

    return (
        len(matched_words)
        / len(query_words)
    )

def has_exact_phrase(
    query: str,
    text: str,
) -> bool:
    """
    Check whether the meaningful part
    of the query appears in the document.
    """

    normalized_query = normalize_text(
        query
    )

    normalized_text = normalize_text(
        text
    )

    query_words = get_query_words(
        query
    )

    if not query_words:
        return False

    # ----------------------------------------------
    # COMPLETE QUERY
    # ----------------------------------------------

    if (
        normalized_query
        and normalized_query in normalized_text
    ):
        return True

    # ----------------------------------------------
    # MEANINGFUL WORDS
    # ----------------------------------------------

    meaningful_words = [
        word
        for word in normalized_query.split()
        if word in query_words
    ]

    if len(meaningful_words) >= 2:

        phrase = " ".join(
            meaningful_words
        )

        if phrase in normalized_text:
            return True

    return False

def embed_and_store(chunks: list[str], room_id: int, file_id: int, filename: str, file_type: str):
    points = []
    for index, chunk in enumerate(chunks):
        if not chunk or not chunk.strip():
            continue
        # Random point IDs avoid collisions with reused SQLite IDs after deletion.
        points.append(PointStruct(id=str(uuid4()), vector=create_embedding(chunk),
                                 payload={'room_id': room_id, 'file_id': file_id, 'filename': filename,
                                          'chunk_index': index, 'file_type': file_type, 'text': chunk}))
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    logger.info('Stored %s chunks for room %s file %s', len(points), room_id, file_id)
    return len(points)

def search_similar(query: str, room_id: int, limit: int = 5, score_threshold: float | None = None):
    results = client.query_points(
        collection_name=COLLECTION_NAME, query=create_embedding(query),
        query_filter=Filter(must=[FieldCondition(key='room_id', match=MatchValue(value=room_id))]),
        limit=max(limit * 5, 25), score_threshold=score_threshold)
    ranked = []
    for result in results.points:
        payload = result.payload or {}
        text = payload.get('text', '')
        vector_score = float(result.score or 0)
        lexical = calculate_lexical_score(query, text)
        exact = has_exact_phrase(query, text)
        combined = vector_score * 0.60 + lexical * 0.40 + (0.35 if exact else 0)
        payload.update(_vector_score=vector_score, _lexical_score=lexical,
                       _exact_match=exact, _combined_score=combined)
        result.payload = payload
        result.score = combined
        ranked.append(result)
    ranked.sort(key=lambda result: result.score, reverse=True)
    logger.info('Retrieved %s candidates for room %s', len(ranked), room_id)
    return ranked[:limit]

def delete_vectors(room_id: int, file_id: int | None = None):
    conditions = [FieldCondition(key='room_id', match=MatchValue(value=room_id))]
    if file_id is not None:
        conditions.append(FieldCondition(key='file_id', match=MatchValue(value=file_id)))
    client.delete(collection_name=COLLECTION_NAME, points_selector=Filter(must=conditions), wait=True)
