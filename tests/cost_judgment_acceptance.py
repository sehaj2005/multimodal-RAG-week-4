"""Opt-in real MiniLM/Groq check using synthetic receipts and in-memory vectors."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['QDRANT_IN_MEMORY'] = '1'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def run():
    from services import qdrant
    from services.rag import ask
    try:
        for room, amount in [(801, '6,350'), (802, '2,450')]:
            qdrant.embed_and_store([f'Receipt: Winter Term Fee is INR {amount}. Mode of payment: online.'],
                                  room, room, 'synthetic_receipt.txt', 'txt')
            result = ask('is winter term fee expensive', room,
                         history=[{'role': 'assistant', 'content': 'The fee is INR 99999.'}])
            answer = result['answer']
            compact = answer.replace(',', '').replace(' ', '')
            assert amount.replace(',', '') in compact, answer
            assert '99999' not in compact, answer
            assert 'budget' in answer.lower() and 'compar' in answer.lower(), answer
            assert result['sources'] and result['sources'][0]['file_id'] == room, result
            print('PASS', amount, '->', answer, flush=True)
        qdrant.embed_and_store(['Receipt: payment was made online. No fee amount is recorded.'],
                              803, 803, 'no_amount.txt', 'txt')
        result = ask('is winter term fee expensive', 803)
        assert result == {'answer': "I don't know.", 'sources': []}, result
        print('PASS missing fee stays unsupported', flush=True)
        assert ask('is winter term fee expensive', 804) == {'answer': "I don't know.", 'sources': []}
        print('PASS empty room stays unsupported', flush=True)
    finally:
        qdrant.client.close()


if __name__ == '__main__':
    run()
