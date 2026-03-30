import re
from app.core.config import settings


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None
) -> list[dict]:
    """
    Returns:
        [
            {
                "chunk_index": 0,
                "text": "...",
                "char_count": 723
            }
        ]
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    text = normalize_text(text)
    if not text:
        return []

    paragraphs = split_paragraphs(text)
    chunks = []

    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": current_chunk,
                    "char_count": len(current_chunk)
                })
                chunk_index += 1

            # if paragraph itself is too long, split it safely
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    piece = para[start:end]
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": piece,
                        "char_count": len(piece)
                    })
                    chunk_index += 1
                    start += max(1, chunk_size - overlap)
                current_chunk = ""
            else:
                # start new chunk with overlap from previous chunk
                if chunks:
                    prev_text = chunks[-1]["text"]
                    overlap_text = prev_text[-overlap:] if overlap < len(prev_text) else prev_text
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para

    if current_chunk:
        chunks.append({
            "chunk_index": chunk_index,
            "text": current_chunk,
            "char_count": len(current_chunk)
        })

    return chunks