"""Opt-in, isolated checks for the nine demo formats. No user storage is accessed."""
from pathlib import Path
import argparse, json, os, re, sys, tempfile
from contextlib import ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'.runtime-deps'))
parser=argparse.ArgumentParser(); parser.add_argument('--offline',action='store_true'); args=parser.parse_args()
os.environ['LOG_LEVEL']='ERROR'
def normalize(text):
    return re.sub(r'[^a-z0-9]+','',text.lower())
with tempfile.TemporaryDirectory(prefix='rag-demo-check-') as directory:
    os.environ.update(SECRET_KEY='isolated-demo-check-secret-with-sufficient-length',
        DATABASE_URL='sqlite:///'+(Path(directory)/'test.db').as_posix(),
        UPLOAD_DIR=str(Path(directory)/'uploads'),QDRANT_IN_MEMORY='1')
    from fastapi.testclient import TestClient
    from main import app
    from services import qdrant
    from db.database import engine
    from services.documents import document_chunks
    results=[]
    with ExitStack() as stack:
        stack.callback(engine.dispose)
        stack.callback(qdrant.client.close)
        if args.offline:
            narration='The evening Python workshop starts on November 9, 2026 at six PM. The workshop coordinator is Alex Morgan. Learners must bring a laptop.'
            stack.enter_context(patch('services.qdrant.create_embedding',return_value=[1.0]+[0.0]*383))
            stack.enter_context(patch('services.ingestion.audio.get_client'))
            # Replace the external transcription boundary, retaining real MP4 decoding.
            stack.enter_context(patch('services.ingestion.audio.extract_audio',return_value=narration))
            stack.enter_context(patch('services.ingestion.video.extract_audio',return_value=narration))
        with TestClient(app) as client:
            credentials={'username':'Demo Reviewer','email':'reviewer@cedar.example','password':'isolated-demo-password'}
            assert client.post('/auth/register',json=credentials).status_code==201
            token=client.post('/auth/login',json={'email':credentials['email'],'password':credentials['password']}).json()['access_token']
            headers={'Authorization':'Bearer '+token}
            manifest=json.loads((ROOT/'demo/manifest.json').read_text())
            for item in manifest:
                path=ROOT/'demo'/item['file']
                room=client.post('/rooms/',headers=headers,json={'name':item['file']}).json()['id']
                with path.open('rb') as source:
                    uploaded=client.post(f'/upload/{room}',headers=headers,files={'file':(path.name,source,'application/octet-stream')})
                assert uploaded.status_code==200,(item['file'],uploaded.text)
                if args.offline:
                    # Verify real local extractors preserve expected facts. No generation claims in offline mode.
                    points=qdrant.client.scroll(collection_name=qdrant.COLLECTION_NAME,scroll_filter=qdrant.Filter(must=[qdrant.FieldCondition(key='room_id',match=qdrant.MatchValue(value=room))]),limit=100)[0]
                    answer=' '.join(point.payload['text'] for point in points)
                    sources=[{'file_type':path.suffix[1:]}]
                else:
                    response=client.post(f'/chat/{room}',headers=headers,json={'query':item['question']})
                    assert response.status_code==200,(item['file'],response.text)
                    answer=response.json()['answer']; sources=response.json()['sources']
                    assert sources,(item['file'],'missing sources')
                    assert all(source['filename']==item['file'] and len(source['excerpt'])<=150 for source in sources)
                for expected in item['expected']:
                    # Models may render six PM as 6 PM.
                    if expected=='six' and '6pm' in normalize(answer): continue
                    assert normalize(expected) in normalize(answer),(item['file'],expected,answer)
                results.append({'file':item['file'],'chunks_created':uploaded.json()['chunks_created'],'passed':True})
                print('PASS',item['file'],flush=True)
                assert client.delete(f'/rooms/{room}',headers=headers).status_code==200
            if not args.offline:
                empty=client.post('/rooms/',headers=headers,json={'name':'Unsupported question check'}).json()['id']
                result=client.post(f'/chat/{empty}',headers=headers,json={'query':'What is the academy director home address?'}).json()
                assert result=={'answer':"I don't know.",'sources':[]},result
                client.delete(f'/rooms/{empty}',headers=headers)
    target=ROOT/'docs'/('demo_offline_results.json' if args.offline else 'demo_live_results.json')
    target.write_text(json.dumps({'mode':'offline' if args.offline else 'live','results':results},indent=2),encoding='utf-8')
    print('All nine formats passed; results:',target,flush=True)
