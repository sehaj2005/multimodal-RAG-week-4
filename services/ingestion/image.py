"""OCR text with spatial regions preserved to keep columns and signatories separate."""
import os
import shutil
import re
from collections import defaultdict
from statistics import median
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops, ImageStat
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
    return link_segments(segments)


def link_segments(segments):
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


def supplement_color_display_text(regions, source):
    """Read colorful poster bands without concatenating conflicting layouts.

    Preserve recognized mixed-case body/name lines. Color crops may replace
    overlapping uppercase display lines; new lines retain image coordinates.
    """
    color = ImageOps.exif_transpose(source).convert('RGB')
    chroma = ImageStat.Stat(ImageChops.difference(color, ImageOps.grayscale(color).convert('RGB'))).mean
    if sum(chroma) / len(chroma) < 10:
        return regions
    scale = min(3.0, 3600 / max(color.size))
    color = color.resize((round(color.width * scale), round(color.height * scale)), Image.Resampling.LANCZOS)
    base_scale = min(2.0, 3600 / max(source.size))
    ratio = scale / base_scale
    segments = []
    for region in regions:
        for line in region:
            if sum(c.isalnum() for c in line['text']) < 3:
                continue
            item = dict(line)
            for key in ('left', 'right', 'top', 'bottom', 'height'):
                item[key] *= ratio
            segments.append(item)
    for band in range(10):
        top = max(0, round((band / 10 - .02) * color.height))
        bottom = min(color.height, round(((band + 1) / 10 + .02) * color.height))
        crop = color.crop((0, top, color.width, bottom))
        data = pytesseract.image_to_data(crop, config='--psm 11', output_type=pytesseract.Output.DICT)
        # Drop low-confidence background fragments in supplemental readings.
        data['conf'] = [value if float(value) >= 65 else -1 for value in data['conf']]
        for region in regions_from_data(data, color.width):
            for line in region:
                text = line['text']
                words = [word for word in text.split() if sum(c.isalpha() for c in word) >= 3]
                letters = ''.join(c for c in text if c.isalpha())
                if not (len(words) >= 2 or (letters.isupper() and len(letters) >= 5)):
                    continue
                line = dict(line)
                line['top'] += top
                line['bottom'] += top
                overlaps = []
                for existing in segments:
                    width = max(0, min(existing['right'], line['right']) - max(existing['left'], line['left']))
                    height = max(0, min(existing['bottom'], line['bottom']) - max(existing['top'], line['top']))
                    area = min((existing['right'] - existing['left']) * (existing['bottom'] - existing['top']),
                               (line['right'] - line['left']) * (line['bottom'] - line['top']))
                    if area and width * height / area >= .6:
                        overlaps.append(existing)
                if not overlaps:
                    segments.append(line)
                elif letters.isupper():
                    old_letters = ''.join(c for item in overlaps for c in item['text'] if c.isalpha())
                    uppercase = sum(c.isupper() for c in old_letters) / max(1, len(old_letters))
                    if (uppercase >= .8 and len(letters) >= len(old_letters) * .8
                            and sum(c.isdigit() for c in text) >= sum(c.isdigit() for item in overlaps for c in item['text'])):
                        segments = [item for item in segments if item not in overlaps]
                        segments.append(line)
    return link_segments(segments)


def extract_image_text(file_path):
    try:
        with Image.open(file_path) as source:
            image = preprocess_image(source)
            data = pytesseract.image_to_data(image, config='--psm 3', output_type=pytesseract.Output.DICT)
            regions = regions_from_data(data, image.width)
            if sum(len(region) for region in regions) < 3:
                alternatives = [regions]
                for mode in (6, 11):
                    alternate = pytesseract.image_to_data(image, config=f'--psm {mode}', output_type=pytesseract.Output.DICT)
                    alternatives.append(regions_from_data(alternate, image.width))
                regions = max(alternatives, key=lambda candidate: sum(len(line['text']) for region in candidate for line in region))
            regions = supplement_color_display_text(regions, source)
        return '\n\n'.join(f'OCR region {index}:\n' + '\n'.join(line['text'] for line in region)
                            for index, region in enumerate(regions, 1))
    except Exception as exc:
        raise RuntimeError(f'Failed to extract image text: {exc}') from exc


def chunk_image_text(text, chunk_size=150, overlap=30):
    # Do not overlap chunks across spatial regions: that would rejoin columns.
    chunks = []
    months = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    for region in text.split('\n\n'):
        if re.search(rf'\b{months}\b', region, re.I) and re.search(r'\d', region):
            region = 'Dates / schedule (OCR text):\n' + region
        chunks.extend(chunk_text(region, chunk_size=chunk_size, overlap=overlap))
    return chunks
