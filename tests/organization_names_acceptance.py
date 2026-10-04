"""Opt-in real retrieval/AI check; pass a receipt PDF, using isolated vectors."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['QDRANT_IN_MEMORY'] = '1'
sys.stdout.reconfigure(encoding='utf-8')


def run(source):
    from services import qdrant
    from services.rag import ask
    from services.ingestion.pdf import extract_pdf
    from services.ingestion.chunker import chunk_text
    try:
        qdrant.embed_and_store(chunk_text(extract_pdf(source)), 901, 901, 'receipt.pdf', 'pdf')
        history = [{'role': 'assistant', 'content': 'University Institute of Computing (UIC).'}]
        for query, expected in [('what is the name of university', 'chandigarh university'),
                                ('name of institute', 'university institute of computing')]:
            result = ask(query, 901, history=history)
            answer = ' '.join(result['answer'].lower().split())
            assert expected in answer, result
            if query == 'what is the name of university':
                assert 'institute of computing' not in answer, result
            assert result['sources'], result
            print('PASS', query, '->', result['answer'], flush=True)
        qdrant.embed_and_store(['UNIVERSITY INSTITUTE OF COMPUTING (UIC). Tuition receipt.'],
                              902, 902, 'institute_only.txt', 'txt')
        result = ask('name of university', 902)
        assert result == {'answer': "I don't know.", 'sources': []}, result
        print('PASS unnamed parent university is not invented', flush=True)
    finally:
        qdrant.client.close()


if __name__ == '__main__':
    run(sys.argv[1])
