"""Isolated acceptance tests: no production data, downloads, OCR binary, or LLM calls."""
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sandbox = tempfile.TemporaryDirectory(prefix='multimodal-rag-tests-')
os.environ.update(SECRET_KEY='isolated-test-secret-with-sufficient-length',
                  DATABASE_URL='sqlite:///' + (Path(sandbox.name) / 'test.db').as_posix(),
                  UPLOAD_DIR=str(Path(sandbox.name) / 'uploads'),
                  QDRANT_IN_MEMORY='1', MAX_UPLOAD_MB='1')

from fastapi.testclient import TestClient
from jose import jwt
from qdrant_client.models import Filter, FieldCondition, MatchValue
from db.database import Base, engine, SessionLocal
from db.models import User, ChatRoom, ChatMessage, UploadedFile
from services import qdrant, documents, auth, rag
from services.ingestion.chunker import chunk_text
from main import app


def tearDownModule():
    qdrant.client.close()
    engine.dispose()
    sandbox.cleanup()


class Week4Tests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        qdrant.client.delete(collection_name=qdrant.COLLECTION_NAME, points_selector=Filter(must=[]))
        documents.UPLOAD_DIR.mkdir(exist_ok=True)
        for path in documents.UPLOAD_DIR.iterdir():
            path.unlink()
        self.embedding = patch('services.qdrant.create_embedding', return_value=[1.0] + [0.0] * 383)
        self.embedding.start()
        fallback = patch('services.llm.LLM_FALLBACK_MODEL', '')
        fallback.start()
        self.addCleanup(fallback.stop)
        cooldowns = patch.dict('services.llm._model_cooldowns', {}, clear=True)
        cooldowns.start()
        self.addCleanup(cooldowns.stop)
        self.addCleanup(self.embedding.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        with SessionLocal() as db:
            db.add_all([User(id=1, username='Alice', email='alice@example.com', hashed_password='unused'),
                        User(id=2, username='Bob', email='bob@example.com', hashed_password='unused'),
                        ChatRoom(id=1, name='Alice room', owner_id=1), ChatRoom(id=2, name='Bob room', owner_id=2)])
            db.commit()
        self.alice = {'Authorization': 'Bearer ' + auth.create_access_token({'sub': '1'})}
        self.bob = {'Authorization': 'Bearer ' + auth.create_access_token({'sub': '2'})}

    def upload(self, name='test.txt', content=b'Winter term fee is 500.', room=1, headers=None, alternate=False):
        url = f'/rooms/{room}/upload' if alternate else f'/upload/{room}'
        return self.client.post(url, headers=headers or self.alice,
                                files={'file': (name, content, 'application/octet-stream')})

    def points(self, room=1):
        return qdrant.client.scroll(collection_name=qdrant.COLLECTION_NAME,
            scroll_filter=Filter(must=[FieldCondition(key='room_id', match=MatchValue(value=room))]), limit=1000)[0]

    def record(self, file_id):
        with SessionLocal() as db:
            return db.get(UploadedFile, file_id)

    def test_auth_registration_login_and_token_expiration(self):
        data = {'username': 'Carol', 'email': 'carol@example.com', 'password': 'good-password'}
        self.assertEqual(self.client.post('/auth/register', json=data).status_code, 201)
        self.assertEqual(self.client.post('/auth/register', json=data).status_code, 400)
        login = self.client.post('/auth/login', json=data)
        self.assertEqual(login.status_code, 200)
        token = login.json()['access_token']
        self.assertIn('exp', auth.decode_access_token(token))
        self.assertEqual(self.client.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code, 200)
        self.assertEqual(self.client.post('/auth/login', json={**data, 'password': 'wrong'}).status_code, 401)

    def test_password_limits_return_validation_errors(self):
        for password in ['short', 'x' * 73, '\u00e9' * 40]:
            response = self.client.post('/auth/register', json={'username': 'Test', 'email': 'test@example.com', 'password': password})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.post('/auth/login', json={'email': 'alice@example.com', 'password': 'x' * 73}).status_code, 422)

    def test_expired_invalid_missing_and_malformed_subject_tokens(self):
        self.assertIn(self.client.get('/rooms/').status_code, [401, 403])
        for claims in [{'sub': '1', 'exp': datetime.now(timezone.utc) - timedelta(seconds=5)},
                       {'sub': 'abc', 'exp': datetime.now(timezone.utc) + timedelta(minutes=1)}, {'sub': '1'}]:
            token = jwt.encode(claims, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
            self.assertEqual(self.client.get('/rooms/', headers={'Authorization': 'Bearer ' + token}).status_code, 401)
        self.assertEqual(self.client.get('/rooms/', headers={'Authorization': 'Bearer invalid'}).status_code, 401)

    def test_room_crud_and_ownership(self):
        response = self.client.post('/rooms/', headers=self.alice, json={'name': 'New room'})
        self.assertEqual(response.status_code, 200)
        room_id = response.json()['id']
        self.assertEqual(self.client.get(f'/rooms/{room_id}', headers=self.alice).status_code, 200)
        self.assertEqual(self.client.get(f'/rooms/{room_id}', headers=self.bob).status_code, 404)
        self.assertEqual(self.client.delete(f'/rooms/{room_id}', headers=self.bob).status_code, 404)
        self.assertEqual(len(self.client.get('/rooms/', headers=self.bob).json()), 1)

    def test_both_upload_routes_chunk_and_deduplicate(self):
        content = ' '.join(f'word{i}' for i in range(400)).encode()
        response = self.upload(content=content, alternate=True)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'ready')
        self.assertEqual(response.json()['chunks_created'], 4)
        self.assertEqual(self.upload(content=content).status_code, 409)
        self.assertEqual(len(self.points()), 4)
        self.assertEqual(self.upload(content=content, room=2, headers=self.bob).status_code, 200)

    def test_file_and_chat_access_cannot_cross_users(self):
        file_id = self.upload().json()['file_id']
        for prefix in ['files', 'upload']:
            self.assertEqual(self.client.get(f'/{prefix}/1', headers=self.bob).status_code, 404)
            self.assertEqual(self.client.delete(f'/{prefix}/1/{file_id}', headers=self.bob).status_code, 404)
        self.assertEqual(self.upload(headers=self.bob).status_code, 404)
        self.assertEqual(self.client.post('/chat/1', headers=self.bob, json={'query': 'fee?'}).status_code, 404)
        self.assertEqual(self.client.get('/chat/1/history', headers=self.bob).status_code, 404)
        self.assertEqual(self.client.delete('/chat/1/history', headers=self.bob).status_code, 404)
        self.assertTrue(Path(self.record(file_id).file_path).exists())

    def test_upload_validation_leaves_no_records(self):
        for name, content, expected in [('empty.txt', b'', 400), ('script.exe', b'x', 415),
                                        ('big.txt', b'x' * (documents.MAX_UPLOAD_BYTES + 1), 413)]:
            self.assertEqual(self.upload(name, content).status_code, expected)
        self.assertEqual(self.client.get('/files/1', headers=self.alice).json(), [])
        self.assertEqual(self.points(), [])

    def test_safe_paths_and_filename_collisions(self):
        first = self.upload('../../outside.txt', b'Alice data').json()['file_id']
        second = self.upload('outside.txt', b'Bob data', room=2, headers=self.bob).json()['file_id']
        a, b = self.record(first), self.record(second)
        self.assertEqual(a.filename, 'outside.txt')
        self.assertNotEqual(a.file_path, b.file_path)
        self.assertTrue(Path(a.file_path).resolve().is_relative_to(documents.UPLOAD_DIR.resolve()))
        self.assertEqual(Path(a.file_path).read_bytes(), b'Alice data')
        self.assertEqual(self.upload('file.txt:stream', b'x').status_code, 400)

    def test_extraction_failure_cleanup_and_retry(self):
        with patch('services.documents.extract_document', side_effect=RuntimeError('decoder failed')):
            self.assertEqual(self.upload().status_code, 500)
        files = self.client.get('/files/1', headers=self.alice).json()
        self.assertEqual(files[0]['status'], 'failed')
        self.assertFalse(Path(self.record(files[0]['file_id']).file_path).exists())
        self.assertEqual(self.points(), [])
        self.assertEqual(self.upload().status_code, 200)

    def test_no_text_failure_is_failed_not_processing(self):
        self.assertEqual(self.upload(content=b'   ').status_code, 422)
        files = self.client.get('/files/1', headers=self.alice).json()
        self.assertEqual(files[0]['status'], 'failed')
        self.assertFalse(Path(self.record(files[0]['file_id']).file_path).exists())

    def test_partial_vector_failure_cleanup(self):
        real_store = qdrant.embed_and_store
        def broken_store(**kwargs):
            real_store(**kwargs)
            raise RuntimeError('Index interrupted after storing')
        with patch('services.documents.embed_and_store', side_effect=broken_store):
            self.assertEqual(self.upload().status_code, 500)
        self.assertEqual(self.points(), [])
        self.assertEqual(self.client.get('/files/1', headers=self.alice).json()[0]['status'], 'failed')

    def test_file_delete_removes_all_three_stores(self):
        file_id = self.upload().json()['file_id']
        other = self.upload(room=2, headers=self.bob).json()['file_id']
        path = Path(self.record(file_id).file_path)
        response = self.client.delete(f'/upload/1/{file_id}', headers=self.alice)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.record(file_id))
        self.assertFalse(path.exists())
        self.assertEqual(self.points(), [])
        self.assertTrue(self.points(2))
        self.assertTrue(Path(self.record(other).file_path).exists())
        self.assertEqual(self.client.delete(f'/files/1/{file_id}', headers=self.alice).status_code, 404)

    def test_deletion_failure_can_be_retried(self):
        file_id = self.upload().json()['file_id']
        with patch('services.documents.delete_vectors', side_effect=RuntimeError('Unavailable')):
            self.assertEqual(self.client.delete(f'/files/1/{file_id}', headers=self.alice).status_code, 500)
        self.assertIsNotNone(self.record(file_id))
        self.assertTrue(Path(self.record(file_id).file_path).exists())
        self.assertEqual(self.client.delete(f'/files/1/{file_id}', headers=self.alice).status_code, 200)

    def test_room_delete_cleans_messages_files_and_orphan_vectors(self):
        file_id = self.upload().json()['file_id']
        other = self.upload(room=2, headers=self.bob).json()['file_id']
        path = Path(self.record(file_id).file_path)
        qdrant.embed_and_store(['Orphan'], room_id=1, file_id=999, filename='old.txt', file_type='txt')
        with SessionLocal() as db:
            db.add(ChatMessage(room_id=1, user_id=1, role='user', content='Hello'))
            db.commit()
        response = self.client.delete('/rooms/1', headers=self.alice)
        self.assertEqual(response.status_code, 200, response.text)
        with SessionLocal() as db:
            self.assertIsNone(db.get(ChatRoom, 1))
            self.assertEqual(db.query(ChatMessage).filter(ChatMessage.room_id == 1).count(), 0)
        self.assertFalse(path.exists())
        self.assertEqual(self.points(), [])
        self.assertTrue(self.points(2))
        self.assertIsNotNone(self.record(other))

    def test_legacy_shared_physical_path_retained(self):
        file_id = self.upload().json()['file_id']
        path = self.record(file_id).file_path
        with SessionLocal() as db:
            db.add(UploadedFile(room_id=2, filename='legacy.txt', file_type='txt', file_path=path, status='ready'))
            db.commit()
        self.assertEqual(self.client.delete(f'/files/1/{file_id}', headers=self.alice).status_code, 200)
        self.assertTrue(Path(path).exists())
        self.assertEqual(self.client.delete('/rooms/2', headers=self.bob).status_code, 200)
        self.assertFalse(Path(path).exists())

    def test_retrieval_is_room_filtered(self):
        self.upload(content=b'Alice private fee is 500.')
        self.upload(content=b'Bob private fee is 900.', room=2, headers=self.bob)
        contexts = rag.retrieve_context('fee', room_id=1)
        self.assertTrue(contexts)
        self.assertTrue(all('Alice' in item['text'] for item in contexts))

    def test_chat_sources_history_and_clear(self):
        self.upload()
        with patch('services.rag.generate_answer', return_value='The winter term fee is 500.'):
            response = self.client.post('/chat/1', headers=self.alice, json={'query': 'What is the fee?'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('file_id', response.json()['sources'][0])
        history = self.client.get('/chat/1/history', headers=self.alice).json()
        self.assertEqual([m['role'] for m in history], ['user', 'assistant'])
        self.assertEqual(self.client.get('/chat/1/history?skip=-1', headers=self.alice).status_code, 422)
        self.assertEqual(self.client.get('/chat/1/history?limit=201', headers=self.alice).status_code, 422)
        self.assertEqual(self.client.delete('/chat/1/history', headers=self.alice).status_code, 200)
        self.assertEqual(self.client.get('/chat/1/history', headers=self.alice).json(), [])

    def test_chat_failure_saves_no_incomplete_turn(self):
        self.upload()
        with patch('services.rag.generate_answer', side_effect=RuntimeError('LLM unavailable')):
            self.assertEqual(self.client.post('/chat/1', headers=self.alice, json={'query': 'fee?'}).status_code, 502)
        self.assertEqual(self.client.get('/chat/1/history', headers=self.alice).json(), [])
        self.assertEqual(self.client.post('/chat/1', headers=self.alice, json={'query': '   '}).status_code, 422)

    def test_no_context_and_unknown_answer_return_no_sources(self):
        with patch('services.rag.generate_answer') as model:
            response = self.client.post('/chat/1', headers=self.alice, json={'query': 'fee?'})
            self.assertEqual(response.json(), {'answer': "I don't know.", 'sources': []})
            model.assert_not_called()
        self.upload()
        with patch('services.rag.generate_answer', return_value="I don't know."):
            self.assertEqual(rag.ask('unsupported question', 1)['sources'], [])

    def test_follow_up_retrieval_uses_history(self):
        self.upload()
        history = [{'role': 'user', 'content': 'Who is Alice?'}]
        with patch('services.rag.retrieve_context', return_value=[]) as retrieve:
            rag.ask('What is her role?', 1, history)
        self.assertIn('Who is Alice?', retrieve.call_args.kwargs['query'])
        self.assertTrue(rag.build_prompt('question', []))

    def test_chunk_boundaries(self):
        text = ' '.join(str(i) for i in range(400))
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0].split()[-30:], chunks[1].split()[:30])
        self.assertTrue(all(len(chunk.split()) <= 150 for chunk in chunks))
        self.assertEqual(chunk_text(''), [])
        with self.assertRaises(ValueError):
            chunk_text('a b', overlap=150)

    def test_docx_tables_and_paragraphs_indexed(self):
        from docx import Document
        document = Document()
        document.add_paragraph('Certificate recipient Alice')
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = 'Course'
        table.cell(0, 1).text = 'Python'
        data = io.BytesIO()
        document.save(data)
        response = self.upload('sample.docx', data.getvalue())
        self.assertEqual(response.status_code, 200, response.text)
        text = self.points()[0].payload['text']
        self.assertIn('Alice', text)
        self.assertIn('Python', text)

    def test_markdown_upload_uses_chunks(self):
        response = self.upload('notes.md', ('# Notes ' + ' '.join(['content'] * 300)).encode())
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()['chunks_created'], 1)

    def test_csv_and_pdf_extraction(self):
        import pymupdf
        response = self.upload('fees.csv', b'Term,Fee\nWinter,500\nSummer,800\n')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('Winter', self.points()[0].payload['text'])
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((72, 72), 'Certificate recipient Alice. Course: Python. Fee: 500.')
        response = self.upload('certificate.pdf', pdf.tobytes())
        pdf.close()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any('Python' in point.payload['text'] for point in self.points()))

    @unittest.skipUnless(Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe').exists(), 'Tesseract not installed at the default Windows location')
    def test_real_image_ocr_and_chunking(self):
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new('RGB', (1400, 400), 'white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('arial.ttf', 38)
        draw.text((40, 60), 'Certificate recipient Alice', fill='black', font=font)
        draw.text((40, 130), 'Course Python and Core Data Tools', fill='black', font=font)
        data = io.BytesIO()
        image.save(data, format='PNG')
        response = self.upload('certificate.png', data.getvalue())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(any('Alice' in point.payload['text'] for point in self.points()))

    def test_streamlit_login_documents_chat_and_delete(self):
        from streamlit.testing.v1 import AppTest
        from urllib.parse import urlsplit
        import requests
        self.client.post('/auth/register', json={'username': 'Carol', 'email': 'carol@example.com', 'password': 'good-password'})
        file_id = self.upload().json()['file_id']
        def forward(method, url, **kwargs):
            kwargs.pop('timeout', None)
            parsed = urlsplit(url)
            path = parsed.path + ('?' + parsed.query if parsed.query else '')
            return self.client.request(method, path, **kwargs)
        with patch('requests.get', side_effect=lambda url, **kw: forward('GET', url, **kw)), \
             patch('requests.post', side_effect=lambda url, **kw: forward('POST', url, **kw)), \
             patch('requests.delete', side_effect=lambda url, **kw: forward('DELETE', url, **kw)):
            ui = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'streamlit_app.py'), default_timeout=30)
            ui.run()
            self.assertFalse(ui.exception)
            self.assertTrue(any(button.label == 'Login' for button in ui.button))
            # Verify an actual login through the frontend, then use Alice's room to test document actions.
            ui.text_input[0].set_value('carol@example.com')
            ui.text_input[1].set_value('good-password')
            next(button for button in ui.button if button.label == 'Login').click().run()
            self.assertFalse(ui.exception)
            self.assertTrue(ui.session_state['token'])
            ui.session_state['token'] = self.alice['Authorization'].split()[1]
            ui.session_state['room_id'] = None
            ui.run()
            self.assertFalse(ui.exception)
            self.assertTrue(any('test.txt' in element.value for element in ui.markdown))
            with patch('services.rag.generate_answer', return_value='The winter term fee is 500.'):
                ui.chat_input[0].set_value('What is the winter term fee?').run()
            self.assertFalse(ui.exception)
            self.assertEqual(len(ui.session_state['chat_history']), 2)
            self.assertTrue(ui.session_state['chat_history'][1]['sources'])
            from services.llm import AnswerRateLimitError
            with patch('services.rag.generate_answer', side_effect=AnswerRateLimitError(12)):
                ui.chat_input[0].set_value('What is the fee again?').run()
            self.assertFalse(ui.exception)
            self.assertEqual(ui.session_state['pending_question'], 'What is the fee again?')
            self.assertTrue(any('Wait 12 seconds' in warning.value for warning in ui.warning))
            self.assertEqual(len(ui.session_state['chat_history']), 2)
            with patch('services.rag.generate_answer', return_value='The fee is 500.'):
                next(button for button in ui.button if button.label == 'Retry last question').click().run()
            self.assertFalse(ui.exception)
            self.assertIsNone(ui.session_state['pending_question'])
            self.assertEqual(len(ui.session_state['chat_history']), 4)
            next(button for button in ui.button if button.key == f'delete_file_{file_id}').click().run()
            self.assertFalse(ui.exception)
            self.assertIsNone(self.record(file_id))

    def test_generic_recipient_retrieves_completion_without_name_or_history(self):
        chunks = ['OCR region 1: COURSE', 'OCR region 2: CERTIFICATE',
                  'OCR region 3: UNIVERSITY', 'OCR region 4: Discover Learn',
                  'OCR region 5: April 15, 2026\nMira Sen\nhas successfully completed\nData Tools',
                  'OCR region 6: Professor Arun Singh Pro-VC Academic Affairs',
                  'OCR region 7: Shilpa Mahajan Assistant Professor',
                  'OCR region 8: Verify at', 'OCR region 9: https://example.com',
                  'OCR region 10: Confirmed identity of this individual',
                  'OCR region 11: Participation in the course',
                  'OCR region 12: This certificate attests to completion of an online course',
                  'OCR region 13: Institutions may recognize this learning']
        qdrant.embed_and_store(chunks, 1, 501, 'certificate.png', 'image')
        qdrant.embed_and_store(['Certificate recipient Hidden Learner has successfully completed'],
                              2, 502, 'private.png', 'image')
        for query in ['the certificate is issued to whom?', 'certificate is for whom']:
            with self.subTest(query=query), patch('services.rag.generate_answer', return_value='Mira Sen.') as model:
                result = rag.ask(query, 1)
                prompt = model.call_args.args[0]
                self.assertIn('Mira Sen', prompt)
                self.assertNotIn('Hidden Learner', prompt)
                self.assertLessEqual(len(result['sources']), 5)
                self.assertTrue(any('Mira Sen' in source['excerpt'] for source in result['sources']))

    def test_recipient_intent_keeps_issuer_and_authorizer_distinct(self):
        for query in ['certificate is for whom', 'who was this certificate issued to?',
                      'Who received the certificate?', 'whose certificate is this?']:
            self.assertTrue(rag.is_certificate_recipient_question(query), query)
        for query in ['Who issued the certificate?', 'certificate is authorized by whom',
                      'who is shilpa mahajan', 'Who signed this certificate?']:
            self.assertFalse(rag.is_certificate_recipient_question(query), query)
        qdrant.embed_and_store(['Certificate\nShilpa Mahajan\nAssistant Professor'],
                              1, 503, 'certificate.png', 'image')
        with patch('services.rag.generate_answer', return_value="I don't know.") as model:
            self.assertEqual(rag.ask('certificate is for whom', 1)['sources'], [])
            self.assertIn('do not guess', model.call_args.args[0])

    def test_short_follow_up_keeps_certificate_context(self):
        history = [{'role': 'user', 'content': 'Who received the certificate?'},
                   {'role': 'assistant', 'content': 'The recipient is Sehtej Hanjra.'}]
        for query in ['for what?', 'who issued the certificate?']:
            self.assertTrue(rag.is_follow_up(query))
            with patch('services.rag.retrieve_context', return_value=[]) as retrieve:
                rag.ask(query, 1, history)
            self.assertIn('Sehtej Hanjra', retrieve.call_args.kwargs['query'])

    def test_ocr_columns_do_not_mix_name_and_titles(self):
        from services.ingestion.image import regions_from_data, chunk_image_text
        data = {key: [] for key in ['text', 'conf', 'left', 'top', 'width', 'height', 'block_num', 'par_num', 'line_num']}
        lines = [(1, 0, [('Shilpa', 10, 60), ('Mahajan', 80, 60), ('Prof.', 400, 40), ('Raghuveer', 450, 90)]),
                 (2, 30, [('Assistant', 10, 80), ('Professor', 100, 80), ('Pro-VC', 400, 70), ('Academic', 480, 80), ('Affairs', 570, 60)]),
                 (3, 60, [('UIC', 10, 30), ('Office', 400, 50), ('of', 460, 20), ('Academic', 490, 80), ('Affairs', 580, 60)])]
        for line, top, words in lines:
            for text, left, width in words:
                for key, value in {'text': text, 'conf': 95, 'left': left, 'top': top, 'width': width, 'height': 20,
                                   'block_num': 1, 'par_num': 1, 'line_num': line}.items():
                    data[key].append(value)
        regions = regions_from_data(data, 1000)
        self.assertEqual(len(regions), 2)
        text = '\n\n'.join('\n'.join(line['text'] for line in region) for region in regions)
        chunks = chunk_image_text(text)
        shilpa = next(chunk for chunk in chunks if 'Shilpa' in chunk)
        raghuveer = next(chunk for chunk in chunks if 'Raghuveer' in chunk)
        self.assertIn('Assistant Professor\nUIC', shilpa)
        self.assertNotIn('Pro-VC', shilpa)
        self.assertIn('Pro-VC Academic Affairs', raghuveer)
        self.assertNotIn('Assistant Professor', raghuveer)

    def test_reindex_replaces_vectors_and_preserves_original(self):
        file_id = self.upload().json()['file_id']
        original = self.record(file_id)
        old_ids = {point.id for point in self.points()}
        self.assertEqual(self.client.post(f'/files/1/{file_id}/reindex', headers=self.bob).status_code, 404)
        response = self.client.post(f'/files/1/{file_id}/reindex', headers=self.alice)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(self.points()), 1)
        self.assertFalse(old_ids.intersection({point.id for point in self.points()}))
        self.assertEqual(self.record(file_id).file_path, original.file_path)
        self.assertTrue(Path(original.file_path).exists())

    def test_reindex_failure_retains_original_for_retry(self):
        file_id = self.upload().json()['file_id']
        original = Path(self.record(file_id).file_path)
        with patch('services.documents.embed_and_store', side_effect=RuntimeError('Index unavailable')):
            self.assertEqual(self.client.post(f'/files/1/{file_id}/reindex', headers=self.alice).status_code, 500)
        self.assertTrue(original.exists())
        self.assertEqual(self.record(file_id).status, 'failed')
        self.assertFalse(self.points())
        self.assertEqual(self.client.post(f'/files/1/{file_id}/reindex', headers=self.alice).status_code, 200)

    def test_pptx_text_and_table_are_indexed(self):
        from pptx import Presentation
        from pptx.util import Inches
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = 'Training schedule'
        slide.placeholders[1].text = 'Workshop coordinator Mira Sen'
        table = slide.shapes.add_table(2, 2, Inches(1), Inches(3), Inches(6), Inches(1)).table
        for cell, text in zip([table.cell(0, 0), table.cell(0, 1), table.cell(1, 0), table.cell(1, 1)], ['Course', 'Seats', 'Python', '24']):
            cell.text = text
        data = io.BytesIO()
        deck.save(data)
        response = self.upload('schedule.pptx', data.getvalue())
        self.assertEqual(response.status_code, 200, response.text)
        text = self.points()[0].payload['text']
        self.assertIn('Slide 1', text)
        self.assertIn('Mira Sen', text)
        self.assertIn('Python | 24', text)

    def test_audio_transcription_is_indexed_with_metadata(self):
        from types import SimpleNamespace
        client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=lambda **kwargs: 'The Python workshop coordinator is Mira Sen.')))
        with patch('services.ingestion.audio.get_client', return_value=client):
            response = self.upload('orientation.wav', b'isolated mock audio')
        self.assertEqual(response.status_code, 200, response.text)
        payload = self.points()[0].payload
        self.assertEqual(payload['file_type'], 'wav')
        self.assertIn('Mira Sen', payload['text'])

    def test_visual_only_image_uses_vision_fallback(self):
        with patch('services.ingestion.image.extract_image_text', return_value=''), patch('services.ingestion.vision.extract_visual_description', return_value='There are three blue chairs in the room.') as vision:
            response = self.upload('room.png', b'mocked image')
        self.assertEqual(response.status_code, 200, response.text)
        vision.assert_called_once()
        self.assertIn('three blue chairs', self.points()[0].payload['text'])

    def test_video_missing_audio_is_failed_and_friendly(self):
        from unittest.mock import MagicMock
        clip = MagicMock()
        clip.__enter__.return_value = clip
        clip.duration = 10
        clip.audio = None
        with patch('moviepy.VideoFileClip', return_value=clip):
            response = self.upload('silent.mp4', b'mocked video')
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('no audio track', response.json()['detail'])
        self.assertEqual(self.record(1).status, 'failed')
        self.assertFalse(self.points())

    def test_video_extracts_audio_and_removes_temporary_file(self):
        from unittest.mock import MagicMock
        captured = []
        clip = MagicMock()
        clip.__enter__.return_value = clip
        clip.duration = 10
        def transcribe(path):
            captured.append(Path(path))
            return 'The workshop room is Cedar Hall.'
        with patch('moviepy.VideoFileClip', return_value=clip), patch('services.ingestion.video.extract_audio', side_effect=transcribe):
            response = self.upload('orientation.mp4', b'mocked video')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(captured[0].suffix, '.wav')
        self.assertFalse(captured[0].parent.exists())
        self.assertIn('Cedar Hall', self.points()[0].payload['text'])

    def test_groq_receives_six_prior_role_messages(self):
        from services.llm import generate_answer
        from unittest.mock import MagicMock
        client = MagicMock()
        client.with_options.return_value = client
        client.chat.completions.create.return_value.choices[0].message.content = 'Answer'
        history = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': str(i)} for i in range(8)]
        with patch('services.llm.get_client', return_value=client):
            self.assertEqual(generate_answer('Current evidence', history=history), 'Answer')
        messages = client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(messages[1:-1], history[-6:])
        self.assertEqual(messages[-1]['content'], 'Current evidence')

    def test_rate_limit_retries_then_saves_one_complete_turn(self):
        from unittest.mock import MagicMock
        from groq import RateLimitError
        import httpx
        from services.llm import generate_answer
        self.upload()
        provider = MagicMock()
        provider.with_options.return_value = provider
        error = RateLimitError('Limited', response=httpx.Response(429, headers={'retry-after': '2'},
            request=httpx.Request('POST', 'https://api.example.com')), body={})
        success = MagicMock()
        success.choices[0].message.content = 'The fee is 500.'
        provider.chat.completions.create.side_effect = [error, success]
        with patch('services.llm.get_client', return_value=provider), patch('services.llm.time.sleep') as sleep:
            response = self.client.post('/chat/1', headers=self.alice, json={'query': 'fee?'})
        self.assertEqual(response.status_code, 200, response.text)
        sleep.assert_called_once_with(2)
        self.assertEqual(provider.chat.completions.create.call_count, 2)
        self.assertEqual(len(self.client.get('/chat/1/history', headers=self.alice).json()), 2)

    def test_persistent_rate_limit_returns_wait_without_saving_turn(self):
        from unittest.mock import MagicMock
        from groq import RateLimitError
        import httpx
        self.upload()
        provider = MagicMock()
        provider.with_options.return_value = provider
        error = RateLimitError('Limited', response=httpx.Response(429, headers={'retry-after': '3'},
            request=httpx.Request('POST', 'https://api.example.com')), body={})
        provider.chat.completions.create.side_effect = error
        with patch('services.llm.get_client', return_value=provider), patch('services.llm.time.sleep') as sleep:
            response = self.client.post('/chat/1', headers=self.alice, json={'query': 'fee?'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['retry-after'], '3')
        self.assertIn('Wait 3 seconds', response.json()['detail'])
        self.assertEqual(provider.chat.completions.create.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(self.client.get('/chat/1/history', headers=self.alice).json(), [])

    def test_long_rate_limit_does_not_block_and_parses_provider_message(self):
        from unittest.mock import MagicMock
        from groq import RateLimitError
        import httpx
        from services.llm import generate_answer, AnswerRateLimitError, rate_limit_wait
        error = RateLimitError('Limited', response=httpx.Response(429,
            request=httpx.Request('POST', 'https://api.example.com')),
            body={'error': {'message': 'Please try again in 1m2.5s. Account private.'}})
        self.assertEqual(rate_limit_wait(error), 63)
        provider = MagicMock()
        provider.with_options.return_value = provider
        provider.chat.completions.create.side_effect = error
        with patch('services.llm.get_client', return_value=provider), patch('services.llm.time.sleep') as sleep:
            with self.assertRaises(AnswerRateLimitError) as caught:
                generate_answer('evidence')
        self.assertEqual(caught.exception.retry_after, 63)
        sleep.assert_not_called()
        self.assertEqual(provider.chat.completions.create.call_count, 1)

    def test_backup_model_answers_and_primary_cooldown_avoids_repeated_calls(self):
        from unittest.mock import MagicMock
        from groq import RateLimitError
        import httpx
        from services.llm import generate_answer
        provider = MagicMock()
        provider.with_options.return_value = provider
        error = RateLimitError('Daily limit', response=httpx.Response(429, headers={'retry-after': '900'},
            request=httpx.Request('POST', 'https://api.example.com')), body={})
        success = MagicMock()
        success.choices[0].message.content = 'Supported answer'
        provider.chat.completions.create.side_effect = [error, success, success]
        with patch('services.llm.LLM_FALLBACK_MODEL', 'backup-model'), \
             patch('services.llm.get_client', return_value=provider), patch('services.llm.time.sleep') as sleep:
            self.assertEqual(generate_answer('Evidence'), 'Supported answer')
            self.assertEqual(generate_answer('Other evidence'), 'Supported answer')
        calls = provider.chat.completions.create.call_args_list
        self.assertEqual([call.kwargs['model'] for call in calls][1:], ['backup-model', 'backup-model'])
        sleep.assert_not_called()

    def test_compact_prompt_retains_certificate_safety_with_smaller_instructions(self):
        prompt = rag.build_prompt('Who received the certificate?', [])
        self.assertLess(len(prompt), 2400)
        self.assertIn('ISSUER QUESTION', rag.build_prompt('Who issued the certificate?', []))
        self.assertNotIn('ISSUER QUESTION', rag.build_prompt('Who issued this report?', []))
        for phrase in ['has successfully completed', 'do not guess', 'signature columns',
                       'explicitly identified issuer', "I don't know.", 'unverified']:
            self.assertIn(phrase, prompt)

    def test_cost_judgment_guidance_requires_a_price_question(self):
        for query in ['is winter term fee expensive', 'Is the rent affordable?', 'Is this price reasonable?']:
            prompt = rag.build_prompt(query, [])
            self.assertIn('COST JUDGMENT', prompt)
            self.assertIn("user's budget", prompt)
            self.assertIn('Do not invent market prices', prompt)
            self.assertIn('If no relevant amount or comparison is supported', prompt)
            self.assertNotIn('6,350', prompt)
        for query in ['What is winter term fee?', 'Is the university prestigious?',
                      'What is the mode of payment?', 'Who issued the certificate?']:
            self.assertNotIn('COST JUDGMENT', rag.build_prompt(query, []))

    def test_sources_use_first_150_characters(self):
        content = 'The workshop coordinator is Mira Sen. ' * 12
        self.upload(content=content.encode())
        with patch('services.rag.generate_answer', return_value='Mira Sen.'):
            result = rag.ask('Who coordinates the workshop?', 1)
        self.assertEqual(result['sources'][0]['excerpt'], self.points()[0].payload['text'][:150])

    def test_fresh_and_preexisting_hash_migrations(self):
        import importlib.util
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import sqlalchemy as sa
        base = Path(__file__).resolve().parents[1] / 'alembic' / 'versions'
        def load(name):
            spec = importlib.util.spec_from_file_location(name, next(base.glob(name + '*.py')))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        first, second = load('5ff95bda6ec8'), load('6a4f2e8b91d0')
        for legacy_has_hash in [False, True]:
            migration_engine = sa.create_engine('sqlite:///:memory:')
            with migration_engine.begin() as connection:
                ops = Operations(MigrationContext.configure(connection))
                with patch.object(first, 'op', ops), patch.object(second, 'op', ops):
                    first.upgrade()
                    if legacy_has_hash:
                        ops.add_column('uploaded_files', sa.Column('file_hash', sa.String()))
                    second.upgrade()
                    self.assertIn('file_hash', {c['name'] for c in sa.inspect(connection).get_columns('uploaded_files')})
                    second.downgrade()
                    self.assertNotIn('file_hash', {c['name'] for c in sa.inspect(connection).get_columns('uploaded_files')})
            migration_engine.dispose()


if __name__ == '__main__':
    unittest.main()
