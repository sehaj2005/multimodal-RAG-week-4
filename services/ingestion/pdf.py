import pymupdf4llm


def extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    """
    try:
        text = pymupdf4llm.to_markdown(file_path)
        return text

    except Exception as e:
        raise RuntimeError(f"Failed to extract PDF: {str(e)}")