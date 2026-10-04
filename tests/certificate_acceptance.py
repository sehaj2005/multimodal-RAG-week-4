"""Run: python -B tests/certificate_acceptance.py path/to/certificate.png.
Sends OCR text from the specified image to the configured Groq service.
Uses temporary database/files and in-memory Qdrant; never reindexes production data.
"""
import sys
import os
import secrets
import tempfile
import time
import unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run(source):
    source = Path(source).resolve()
    with tempfile.TemporaryDirectory(prefix='certificate-regression-') as directory:
        os.environ.update(SECRET_KEY=secrets.token_hex(32), QDRANT_IN_MEMORY='1',
                          DATABASE_URL='sqlite:///' + (Path(directory) / 'test.db').as_posix(),
                          UPLOAD_DIR=str(Path(directory) / 'uploads'))
        from fastapi.testclient import TestClient
        from main import app
        from services import qdrant
        from db.database import engine
        try:
            with TestClient(app) as client:
                credentials = {'username': 'Tester', 'email': 'test@example.com', 'password': 'temporary-password'}
                assert client.post('/auth/register', json=credentials).status_code == 201
                token = client.post('/auth/login', json=credentials).json()['access_token']
                headers = {'Authorization': 'Bearer ' + token}
                room = client.post('/rooms/', headers=headers, json={'name': 'Certificate regression'}).json()['id']
                uploaded = client.post(f'/upload/{room}', headers=headers, files={'file': (source.name, source.read_bytes(), 'image/png')})
                assert uploaded.status_code == 200, uploaded.text
                print('PASS certificate OCR/indexing', flush=True)
                questions = ['the certificate is issued to whom?', 'who is shilpa mahajan',
                             'raghuveer', 'certificate is authorized by whom', 'certificate is for whom',
                             'who is sehtej hanjra', 'who this certificate is issued to',
                             'for what?', 'who issued the certificate?', 'and raghuveer']
                for index, query in enumerate(questions):
                    # Keep this opt-in live check within the provider's token/minute limit.
                    if index:
                        time.sleep(float(os.getenv('CERTIFICATE_TEST_PAUSE_SECONDS', '25')))
                    response = client.post(f'/chat/{room}', headers=headers, json={'query': query})
                    assert response.status_code == 200, response.text
                    answer = response.json()['answer']
                    print(query + ' -> ' + answer, flush=True)
                    normalized = ''.join('-' if unicodedata.category(c) == 'Pd' else c for c in answer.lower())
                    lower = ' '.join(normalized.split())
                    if query in {'the certificate is issued to whom?', 'certificate is for whom',
                                 'who this certificate is issued to', 'who is sehtej hanjra'}:
                        assert 'sehtej' in lower and 'hanjra' in lower, answer
                    if query == 'certificate is authorized by whom':
                        assert 'chandigarh university' in lower, answer
                    if query == 'for what?':
                        assert 'python' in lower and 'core data tools' in lower, answer
                    if query == 'who issued the certificate?':
                        assert 'chandigarh university' in lower and 'coursera' in lower, answer
                        assert any(term in lower for term in ['cannot', "can't", 'not explicitly', 'not identify', 'not stated', 'unable']), answer
                    if query == 'who is shilpa mahajan':
                        assert 'assistant professor' in lower and 'pro-vc' not in lower and 'pro-vice' not in lower, answer
                    if query in {'and raghuveer', 'raghuveer'}:
                        assert ('pro-vc' in lower or 'pro-vice' in lower) and 'assistant professor' not in lower, answer
        finally:
            qdrant.client.close()
            engine.dispose()

if __name__ == '__main__':
    run(sys.argv[1])
