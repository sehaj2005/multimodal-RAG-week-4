from pptx import Presentation

def extract_pptx(path):
    """Read slide text and tables in slide order; images need separate upload."""
    presentation = Presentation(str(path))
    slides = []
    def read_shapes(shapes):
        parts = []
        for shape in shapes:
            if hasattr(shape, 'shapes'):
                parts.extend(read_shapes(shape.shapes))
            if shape.has_text_frame:
                parts.append(shape.text)
            if shape.has_table:
                parts.extend(' | '.join(cell.text for cell in row.cells) for row in shape.table.rows)
        return parts
    for index, slide in enumerate(presentation.slides, 1):
        parts = [part for part in read_shapes(slide.shapes) if part.strip()]
        if parts:
            slides.append(f'Slide {index}:\n' + '\n'.join(parts))
    return '\n\n'.join(slides)
