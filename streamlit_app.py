"""Streamlit client. The API performs authentication and room ownership checks."""
import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title=os.getenv('APP_TITLE', 'Multimodal Knowledge Assistant'), layout='wide')
for key, value in {'token': None, 'room_id': None, 'chat_history': [], 'loaded_room': None, 'pending_question': None, 'pending_room': None, 'pending_error': None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

def reset_login():
    for key, value in {'token': None, 'room_id': None, 'chat_history': [], 'loaded_room': None, 'pending_question': None, 'pending_room': None, 'pending_error': None}.items():
        st.session_state[key] = value

def api(method, path, timeout=30, **kwargs):
    headers = {'Authorization': f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    try:
        response = getattr(requests, method)(API_URL + path, headers=headers, timeout=(5, timeout), **kwargs)
    except requests.RequestException:
        if method == 'post' and path.startswith('/chat/'):
            st.session_state.pending_error = 'Cannot reach the backend. Start FastAPI and try again.'
        st.error('Cannot reach the backend. Start FastAPI and try again.')
        return None
    if response.status_code == 401 and st.session_state.token:
        reset_login()
        st.rerun()
    if response.status_code >= 400:
        try:
            detail = response.json().get('detail', 'Request failed')
        except ValueError:
            detail = 'Request failed. Check the backend logs.'
        if method == 'post' and path.startswith('/chat/'):
            st.session_state.pending_error = str(detail)
        if response.status_code == 429:
            st.warning(str(detail))
        else:
            st.error(str(detail))
        return None
    return response

def load_history(room_id):
    messages = []
    while True:
        response = api('get', f'/chat/{room_id}/history?skip={len(messages)}&limit=200')
        if response is None:
            return None
        page = response.json()
        messages.extend(page)
        if len(page) < 200:
            return messages

def render_message(message):
    role = message.get('role', 'assistant')
    with st.chat_message(role):
        st.write(message.get('content', ''))
        if role == 'assistant':
            with st.expander('Sources'):
                sources = message.get('sources') or []
                if not sources:
                    st.caption('No sources found')
                for source in sources:
                    st.write(source.get('filename', 'Unknown'))
                    st.caption(f"Type: {source.get('file_type', 'unknown').upper()} | Chunk index: {source.get('chunk_index', 0)}")
                    st.caption(source.get('excerpt', ''))

st.title(os.getenv('APP_TITLE', 'Multimodal Knowledge Assistant'))
st.caption(os.getenv('APP_DESCRIPTION', 'Ask grounded questions across documents, images, slides, audio, and video.'))
if not st.session_state.token:
    login, register = st.tabs(['Login', 'Register'])
    with login:
        with st.form('login'):
            email = st.text_input('Email', key='login_email')
            password = st.text_input('Password', type='password', key='login_password')
            submitted = st.form_submit_button('Login')
        if submitted:
            response = api('post', '/auth/login', json={'email': email, 'password': password})
            if response is not None:
                st.session_state.token = response.json()['access_token']
                st.rerun()
    with register:
        with st.form('register'):
            username = st.text_input('Name')
            email = st.text_input('Email', key='register_email')
            password = st.text_input('Password (8+ characters)', type='password', key='register_password')
            submitted = st.form_submit_button('Register')
        if submitted:
            response = api('post', '/auth/register', json={'username': username, 'email': email, 'password': password})
            if response is not None:
                st.success('Account created. Log in using the Login tab.')
    st.stop()

with st.sidebar:
    st.header('Your workspace')
    if st.button('Logout'):
        reset_login()
        st.rerun()
    rooms_response = api('get', '/rooms/')
    if rooms_response is None:
        st.stop()
    rooms = rooms_response.json()
    ids = [room['id'] for room in rooms]
    if ids:
        current = st.session_state.room_id
        selected = st.selectbox('Room', ids, index=ids.index(current) if current in ids else 0,
                                format_func=lambda value: next(room['name'] for room in rooms if room['id'] == value))
        st.session_state.room_id = selected
    else:
        st.session_state.room_id = None
    with st.expander('Create a room', expanded=not rooms):
        with st.form('new_room'):
            name = st.text_input('Room name')
            description = st.text_input('Description (optional)')
            create = st.form_submit_button('Create room')
        if create:
            response = api('post', '/rooms/', json={'name': name, 'description': description})
            if response is not None:
                st.session_state.room_id = response.json()['id']
                st.rerun()
    room_id = st.session_state.room_id
    if room_id is not None:
        with st.expander('Room actions'):
            confirm = st.checkbox('Delete this room and its files/history', key=f'confirm_room_{room_id}')
            if st.button('Delete room', disabled=not confirm):
                if api('delete', f'/rooms/{room_id}') is not None:
                    st.session_state.room_id = None
                    st.session_state.loaded_room = None
                    st.rerun()
        st.divider()
        st.subheader('Upload files')
        uploaded = st.file_uploader('Choose a file', type=['pdf', 'docx', 'pptx', 'csv', 'txt', 'md',
                                                          'png', 'jpg', 'jpeg', 'wav', 'mp3', 'm4a', 'flac', 'ogg', 'mp4', 'mov', 'webm'])
        st.caption('Video answers use its narrated audio. File limit follows backend MAX_UPLOAD_MB.')
        if st.button('Upload and index', disabled=uploaded is None):
            with st.spinner('Extracting and indexing…'):
                response = api('post', f'/upload/{room_id}', timeout=300,
                               files={'file': (uploaded.name, uploaded.getvalue(), uploaded.type)})
            if response is not None:
                st.success(f"Indexed {response.json()['chunks_created']} chunks")
                st.rerun()
        st.subheader('Documents in this room')
        response = api('get', f'/files/{room_id}')
        if response is not None:
            documents = response.json()
            if not documents:
                st.caption('No uploaded documents yet.')
            for document in documents:
                st.write(document['filename'])
                status = document['status']
                st.badge(status, color={'ready': 'green', 'completed': 'green', 'processing': 'orange', 'failed': 'red'}.get(status, 'gray'))
                st.caption(document['file_type'].upper())
                if status == 'failed':
                    st.caption('Processing failed. Check the upload error and configuration, delete this entry, and upload again.')
                reindex, delete = st.columns(2)
                if reindex.button('Reindex', key=f"reindex_file_{document['file_id']}"):
                    with st.spinner('Reindexing…'):
                        response = api('post', f"/files/{room_id}/{document['file_id']}/reindex", timeout=300)
                    if response is not None:
                        st.rerun()
                if delete.button('Delete', key=f"delete_file_{document['file_id']}"):
                    if api('delete', f"/files/{room_id}/{document['file_id']}") is not None:
                        st.rerun()
                st.divider()

room_id = st.session_state.room_id
if room_id is None:
    st.info('Create a room from the sidebar, then upload your documents.')
    st.stop()
if st.session_state.loaded_room != room_id:
    history = load_history(room_id)
    if history is None:
        st.stop()
    st.session_state.chat_history = history
    st.session_state.loaded_room = room_id
st.subheader(next(room['name'] for room in rooms if room['id'] == room_id))
st.caption('Answers use documents from this room. Unsupported questions return “I don’t know.”')
if st.session_state.chat_history and st.button('Delete chat history'):
    if api('delete', f'/chat/{room_id}/history') is not None:
        st.session_state.chat_history = []
        st.rerun()
for message in st.session_state.chat_history:
    render_message(message)
query = st.chat_input('Ask about the uploaded files.')
if st.session_state.pending_question and st.session_state.pending_room == room_id:
    st.warning(st.session_state.pending_error or 'The last question has not been answered yet.')
    st.caption('Unanswered question: ' + st.session_state.pending_question)
    if st.button('Retry last question'):
        query = st.session_state.pending_question
if query and query.strip():
    st.session_state.pending_question = query.strip()
    st.session_state.pending_room = room_id
    st.session_state.pending_error = None
    with st.spinner('Reading relevant sources; temporary AI limits may take a moment.'):
        response = api('post', f'/chat/{room_id}', timeout=180, json={'query': query.strip()})
    if response is not None:
        st.session_state.pending_question = None
        st.session_state.pending_room = None
        st.session_state.pending_error = None
        data = response.json()
        st.session_state.chat_history.extend([{'role': 'user', 'content': query.strip()},
            {'role': 'assistant', 'content': data['answer'], 'sources': data['sources']}])
    st.rerun()
