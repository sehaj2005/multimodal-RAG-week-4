"""Opt-in live check using synthetic documents, real MiniLM, and real Groq requests.
Run separately: python -B tests/live_acceptance.py
"""
import os
import sys
import secrets
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def run():
    with tempfile.TemporaryDirectory(prefix='multimodal-rag-live-') as directory:
        os.environ.update(SECRET_KEY=secrets.token_hex(32), QDRANT_IN_MEMORY='1',
                          DATABASE_URL='sqlite:///' + (Path(directory) / 'live.db').as_posix(),
                          UPLOAD_DIR=str(Path(directory) / 'uploads'))
        from fastapi.testclient import TestClient
        from main import app
        from services import qdrant
        from db.database import engine
        try:
            with TestClient(app) as client:
                credentials = {'username': 'Live tester', 'email': 'live@example.com', 'password': 'live-test-password'}
                assert client.post('/auth/register', json=credentials).status_code == 201
                token = client.post('/auth/login', json=credentials).json()['access_token']
                headers = {'Authorization': 'Bearer ' + token}
                room = client.post('/rooms/', headers=headers, json={'name': 'Synthetic acceptance'}).json()['id']
                text = (b'Certificate recipient: Alice Example. '
                        b'Alice Example completed Python and Core Data Tools. '
                        b'Shilpa Mahajan is Assistant Professor. '
                        b'Prof. VR Raghuveer is Pro-Vice Chancellor Academic Affairs. '
                        b'The document does not identify the certificate issuer.')
                upload = client.post(f'/upload/{room}', headers=headers, files={'file': ('synthetic.txt', text)})
                assert upload.status_code == 200, upload.text
                print('PASS real embedding and vector indexing', flush=True)
                for query, expected in [('Who is Shilpa Mahajan?', 'assistant professor'),
                                        ('What is her designation?', 'assistant professor'),
                                        ('What is the capital of France?', "i don't know"),
                                        ('Who issued the certificate?', 'issuer')]:
                    response = client.post(f'/chat/{room}', headers=headers, json={'query': query})
                    assert response.status_code == 200, response.text
                    result = response.json()
                    assert expected in result['answer'].lower(), result['answer']
                    if expected == 'issuer':
                        assert any(word in result['answer'].lower() for word in ['cannot', "can't", 'not', 'unable']), result['answer']
                    if expected == "i don't know":
                        assert not result['sources']
                    else:
                        assert result['sources']
                    print('PASS', query, flush=True)
                file_id = upload.json()['file_id']
                assert client.delete(f'/files/{room}/{file_id}', headers=headers).status_code == 200
                result = client.post(f'/chat/{room}', headers=headers, json={'query': 'Who is Shilpa Mahajan?'}).json()
                assert result == {'answer': "I don't know.", 'sources': []}
                assert client.delete(f'/rooms/{room}', headers=headers).status_code == 200
                print('PASS deletion removes subsequent retrieval', flush=True)
        finally:
            qdrant.client.close()
            engine.dispose()

if __name__ == '__main__':
    run()
