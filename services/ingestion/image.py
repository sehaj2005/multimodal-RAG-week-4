"""OCR text with spatial regions preserved to keep columns and signatories separate."""
import os
import shutil
from collections import defaultdict
from statistics import median
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
from services.ingestion.chunker import chunk_text

TESSERACT_PATH = os.getenv('TESSERACT_PATH') or shutil.which('tesseract')
if not TESSERACT_PATH:
    default = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.isfile(default):
        TESSERACT_PATH = default
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def preprocess_image(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    # Avoid upscaling already large scans into hundreds of megapixels.
    scale = min(2.0, 3600 / max(image.size))
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(1.5)
    return ImageEnhance.Sharpness(image).enhance(2.0).filter(ImageFilter.SHARPEN)


def regions_from_data(data, image_width):
    """Split wide gaps within OCR lines, then link nearby left-aligned lines.

    Tesseract can put two signature columns on a single line. Word coordinates
    keep them separate even when block/paragraph IDs are shared.
    """
    lines = defaultdict(list)
    for i, value in enumerate(data['text']):
        text = value.strip()
        confidence = float(data['conf'][i])
        if not text or confidence < 25:
            continue
        key = tuple(data[field][i] for field in ('block_num', 'par_num', 'line_num'))
        lines[key].append({'text': text, 'left': int(data['left'][i]), 'top': int(data['top'][i]),
                           'width': int(data['width'][i]), 'height': int(data['height'][i])})
    segments = []
    for words in lines.values():
        words.sort(key=lambda word: word['left'])
        typical_height = median(word['height'] for word in words)
        gap_limit = max(typical_height * 3, image_width * 0.035)
        groups = [[]]
        for word in words:
            if groups[-1]:
                previous = groups[-1][-1]
                gap = word['left'] - previous['left'] - previous['width']
                if gap > gap_limit:
                    groups.append([])
            groups[-1].append(word)
        for group in groups:
            segments.append({'text': ' '.join(word['text'] for word in group),
                             'left': min(word['left'] for word in group),
                             'right': max(word['left'] + word['width'] for word in group),
                             'top': min(word['top'] for word in group),
                             'bottom': max(word['top'] + word['height'] for word in group),
                             'height': max(word['height'] for word in group)})
    regions = []
    for segment in sorted(segments, key=lambda line: (line['top'], line['left'])):
        candidates = []
        for region in regions:
            previous = region[-1]
            height = max(previous['height'], segment['height'])
            vertical_gap = segment['top'] - previous['bottom']
            # Require a distinct subsequent row and similar left alignment.
            if (-height * 0.3 <= vertical_gap <= height * 3
                    and abs(previous['left'] - segment['left']) <= height * 2):
                candidates.append((abs(vertical_gap), region))
        if candidates:
            min(candidates, key=lambda candidate: candidate[0])[1].append(segment)
        else:
            regions.append([segment])
    return regions


def extract_image_text(file_path):
    try:
        with Image.open(file_path) as source:
            image = preprocess_image(source)
        data = pytesseract.image_to_data(image, config='--psm 3', output_type=pytesseract.Output.DICT)
        regions = regions_from_data(data, image.width)
        # Select one reading; concatenating different OCR layouts mixes relationships.
        if sum(len(region) for region in regions) < 3:
            alternatives = [regions]
            for mode in (6, 11):
                alternate = pytesseract.image_to_data(image, config=f'--psm {mode}', output_type=pytesseract.Output.DICT)
                alternatives.append(regions_from_data(alternate, image.width))
            regions = max(alternatives, key=lambda candidate: sum(len(line['text']) for region in candidate for line in region))
        return '\n\n'.join(f'OCR region {index}:\n' + '\n'.join(line['text'] for line in region)
                            for index, region in enumerate(regions, 1))
    except Exception as exc:
        raise RuntimeError(f'Failed to extract image text: {exc}') from exc


def chunk_image_text(text, chunk_size=150, overlap=30):
    # Do not overlap chunks across spatial regions: that would rejoin columns.
    return [chunk for region in text.split('\n\n')
            for chunk in chunk_text(region, chunk_size=chunk_size, overlap=overlap)]
