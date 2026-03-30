from sentence_transformers import SentenceTransformer
from app.core.config import settings
import string
import hashlib
from collections import Counter

_embedding_model = None


def get_embedding_model():
    """
    Load embedding model once and cache it.
    """
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

    return _embedding_model


def embed_text(text: str) -> list[float]:
    """
    Embed a single text string.
    """
    model = get_embedding_model()
    vector = model.encode(text, convert_to_numpy=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple text chunks.
    """
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]


def embed_text_sparse(text: str) -> dict:
    """
    Generate a Sparse Vector (Hashed Bag-of-Words / TF) for Keyword Search.
    Uses MD5 to ensure stable hashing across server restarts.
    """
    text = text.lower().translate(str.maketrans('', '', string.punctuation))
    words = text.split()
    counts = Counter(words)
    
    indices = []
    values = []
    
    for word, freq in counts.items():
        # Hash word to an integer space (e.g., 0 to 100,000,000)
        idx = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16) % (10**8)
        indices.append(idx)
        values.append(float(freq))
        
    return {"indices": indices, "values": values}


def embed_texts_sparse(texts: list[str]) -> list[dict]:
    """
    Generate sparse vectors for multiple text chunks.
    """
    return [embed_text_sparse(text) for text in texts]