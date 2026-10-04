import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def storage_path(name, default):
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else BASE_DIR / value

UPLOAD_DIR = storage_path('UPLOAD_DIR', 'uploads')
QDRANT_PATH = storage_path('QDRANT_PATH', 'qdrant_data')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///' + (BASE_DIR / 'multimodal_rag.db').as_posix())
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_MB', '10')) * 1024 * 1024
LLM_MODEL = os.getenv('LLM_MODEL', 'openai/gpt-oss-120b')
VISION_MODEL = os.getenv('VISION_MODEL', 'qwen/qwen3.8-27b')
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'whisper-large-v3')
MAX_MEDIA_SECONDS = int(os.getenv('MAX_MEDIA_SECONDS', '600'))
INDUSTRY = os.getenv('INDUSTRY', 'General document knowledge')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '384'))
ACCESS_TOKEN_MINUTES = int(os.getenv('ACCESS_TOKEN_MINUTES', '60'))
