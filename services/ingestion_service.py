from services.ingestion.pdf import extract_pdf
from services.ingestion.chunker import chunk_text


def process_pdf(file_path: str) -> list[str]:
    """
    Extract text from PDF and split it into chunks.
    """
    text = extract_pdf(file_path)
    chunks = chunk_text(text)

    return chunks