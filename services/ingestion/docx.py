from docx import Document

def extract_docx(path):
    document = Document(str(path))
    parts = [paragraph.text for paragraph in document.paragraphs]
    parts.extend(' | '.join(cell.text for cell in row.cells)
                 for table in document.tables for row in table.rows)
    return '\n'.join(parts)
