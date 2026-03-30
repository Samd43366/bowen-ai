import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"

    return text.strip()