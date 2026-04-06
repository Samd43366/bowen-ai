def split_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """
    Improved text splitter that prioritizes splitting at newlines to 
    keep list items and sections together as much as possible.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # If we are not at the end of the text, try to find a better 
        # split point (like a newline or a period) near our chunk size
        if end < text_length:
            # Look for a newline character in the last 20% of the chunk
            lookback_range = int(chunk_size * 0.2)
            search_start = max(start, end - lookback_range)
            
            # Find the last newline in this range
            newline_idx = text.rfind('\n', search_start, end)
            if newline_idx != -1:
                end = newline_idx + 1 # Include the newline itself
            else:
                # If no newline, try a period for sentence boundaries
                period_idx = text.rfind('. ', search_start, end)
                if period_idx != -1:
                    end = period_idx + 2
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        # Move the start forward, ensuring we respect the overlap
        start = max(start + 1, end - overlap)

    return chunks