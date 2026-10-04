import base64
import io
from PIL import Image, ImageOps
from services.config import VISION_MODEL
from services.llm import get_client

def extract_visual_description(path):
    # Bound encoded request size even for highly compressed source images.
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((1600, 1600))
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    response = get_client().chat.completions.create(model=VISION_MODEL, temperature=0, max_completion_tokens=1024,
        messages=[{'role': 'user', 'content': [
            {'type': 'text', 'text': 'Describe the visible objects, their counts, colors, and spatial layout precisely for document search. Transcribe readable text exactly. Include a count for repeated objects when clearly visible. Preserve explicit name/title relationships if text is present. Do not invent identities, affiliations, or issuers. Mention uncertainty only for details you cannot determine.'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + encoded}}]}])
    return (response.choices[0].message.content or '').strip()
