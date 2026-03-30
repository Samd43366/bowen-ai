import docx
import io


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from a .docx file.
    """
    doc = docx.Document(io.BytesIO(file_bytes))
    full_text = []
    
    for para in doc.paragraphs:
        full_text.append(para.text)
        
    return "\n".join(full_text).strip()
