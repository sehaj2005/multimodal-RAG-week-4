from pathlib import Path
from services.llm import get_client
from services.config import WHISPER_MODEL

def extract_audio(path):
    path = Path(path)
    if path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Audio exceeds the 25 MB transcription limit; split it into smaller clips')
    with path.open('rb') as audio:
        response = get_client().audio.transcriptions.create(
            file=(path.name, audio.read()), model=WHISPER_MODEL,
            response_format='text', temperature=0)
    return response.strip() if isinstance(response, str) else (response.text or '').strip()
