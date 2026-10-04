import re


# ==================================================
# TEXT CHUNKING
# ==================================================

def chunk_text(
    text: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> list[str]:
    """
    Split text into smaller overlapping chunks.

    Args:
        text:
            Extracted document text.

        chunk_size:
            Maximum number of words in each chunk.

        overlap:
            Number of words repeated between chunks.

    Returns:
        List of text chunks.
    """

    # ----------------------------------------------
    # Clean text
    # ----------------------------------------------

    text = text.strip()

    if not text:
        return []

    # ----------------------------------------------
    # Normalize whitespace
    # ----------------------------------------------

    text = re.sub(
        r"[^\S\n]+",
        " ",
        text
    )

    # ----------------------------------------------
    # Split into words
    # ----------------------------------------------

    words = list(re.finditer(r"\S+", text))

    if not words:
        return []

    # ----------------------------------------------
    # Validate settings
    # ----------------------------------------------

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0."
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative."
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    # ----------------------------------------------
    # Create chunks
    # ----------------------------------------------

    chunks = []

    step = chunk_size - overlap

    for start in range(
        0,
        len(words),
        step
    ):

        end = start + chunk_size

        chunk_words = words[
            start:end
        ]

        if not chunk_words:
            continue

        chunk = text[chunk_words[0].start():chunk_words[-1].end()].strip()

        if chunk:
            chunks.append(
                chunk
            )

        # ------------------------------------------
        # Stop when we reach the end
        # ------------------------------------------

        if end >= len(words):
            break

    return chunks