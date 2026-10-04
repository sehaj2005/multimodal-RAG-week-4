"""Opt-in real OCR/MiniLM/Groq regression for the supplied football poster.
Uses in-memory vectors and never reindexes production uploads.
"""
import os
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['QDRANT_IN_MEMORY'] = '1'
sys.stdout.reconfigure(encoding='utf-8')


def run(source):
    from services import qdrant
    from services.rag import ask
    from services.ingestion.image import extract_image_text, chunk_image_text
    try:
        chunks = chunk_image_text(extract_image_text(source))
        combined = ' '.join(chunks).lower()
        assert '6.7.8 april' in combined or '6, 7, 8 april' in combined, combined
        assert 'venue: uic main ground' in combined, combined
        assert any('chandigarh' in c.lower() and 'university' in c.lower() for c in chunks), chunks
        faculty = next(c for c in chunks if 'Palwinder' in c)
        assert 'Jagvinder' in faculty and 'Shaurya' not in faculty, faculty
        print('PASS poster OCR, dates, venue, university and faculty isolation', flush=True)
        qdrant.embed_and_store(chunks, 905, 905, 'football tournament.jpeg', 'image')
        history = []
        questions = ['who is the organizing team', 'what is the venue', 'any dates?',
                     'any faculty member', 'it is hosted by?', 'which university?']
        for query in questions:
            result = ask(query, 905, history=history[-6:])
            answer = ' '.join(result['answer'].lower().split())
            if query == questions[0]:
                assert all(name in answer for name in ['shaurya', 'harsh', 'pushveer', 'arudh']), answer
            elif query == questions[1]:
                assert 'uic main ground' in answer and 'north campus' in answer and 'vic main' not in answer, answer
            elif query == questions[2]:
                assert 'april' in answer and all(re.search(rf'\b{day}\b', answer) for day in [6, 7, 8]), answer
                assert not re.search(r'\b(?:19|20)\d{2}\b', answer), answer
            elif query == questions[3]:
                assert 'jagvinder singh' in answer and 'palwinder kaur mangat' in answer, answer
                assert 'shaurya' not in answer, answer
            elif query == questions[4]:
                assert 'uic sports club' in answer and 'vic sports' not in answer, answer
            else:
                assert 'chandigarh university' in answer and 'institute of computing' not in answer, answer
            assert result['sources'] and all(s['file_id'] == 905 for s in result['sources']), result
            history.extend([{'role': 'user', 'content': query}, {'role': 'assistant', 'content': result['answer']}])
            print('PASS', query, '->', result['answer'], flush=True)
    finally:
        qdrant.client.close()


if __name__ == '__main__':
    run(sys.argv[1])
