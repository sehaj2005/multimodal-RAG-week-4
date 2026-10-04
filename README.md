# Multimodal RAG — Week 4

FastAPI backend and Streamlit frontend for private document rooms. SQLite stores accounts, file status, and conversations; local Qdrant stores room-filtered document vectors. Text-heavy images use spatial OCR; visual-only images use a configurable Groq vision model. Audio uses Whisper, and video is transcribed from its extracted audio.

## Setup

Use Python 3.11 or 3.12 with the pinned dependencies. The earlier clean installation passed on Python 3.12.14; the updated requirements also resolve successfully. Recreate the virtual environment if its original Python installation has been removed:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` to a long random value and `GROQ_API_KEY` to your own key. Preserve an existing `.env` rather than overwriting it. Install Tesseract OCR separately and put it on PATH or set `TESSERACT_PATH`. The embedding model downloads on the first indexing/search request. Changing the embedding model/dimension requires reindexing into a matching Qdrant collection.

For a new database, run `.venv\Scripts\alembic upgrade head`. If the database was previously created by `main.py` and has no Alembic history, back it up and verify its tables match the initial migration before running `.venv\Scripts\alembic stamp 5ff95bda6ec8`, then `.venv\Scripts\alembic upgrade head`. The hash migration handles an existing `file_hash` column. Do not stamp an empty database.

```powershell
.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
# In a second terminal:
.venv\Scripts\python -m streamlit run streamlit_app.py
```

API docs: http://127.0.0.1:8000/docs. UI: http://localhost:8501. Use one backend worker because embedded Qdrant uses exclusive local storage.

## User flow and API

Register/login → create/select a room → upload documents → inspect/delete documents → ask questions → inspect sources and saved history.

| Operation | Endpoint |
|---|---|
| Register/login/profile | `/auth/register`, `/auth/login`, `/auth/me` |
| Create/list rooms | `POST/GET /rooms/` |
| Get/delete a room | `GET/DELETE /rooms/{room_id}` |
| Upload | `POST /upload/{room_id}` or `POST /rooms/{room_id}/upload` |
| List files | `GET /files/{room_id}` (also `/upload/{room_id}`) |
| Reindex existing file | `POST /files/{room_id}/{file_id}/reindex` |
| Delete file | `DELETE /files/{room_id}/{file_id}` (also `/upload/{room_id}/{file_id}`) |
| Ask | `POST /chat/{room_id}` with `{"query":"..."}` |
| Read/clear history | `GET/DELETE /chat/{room_id}/history` |

All room/file/chat operations require a bearer token and ownership. Tokens expire after 60 minutes by default. Sign in again after upgrading because old tokens without expiration are rejected. New passwords require at least 8 characters and at most 72 UTF-8 bytes. History supports `skip` and `limit` (maximum 200); the UI fetches every page of saved history.

Uploads support all nine required categories: PDF, DOCX, images (PNG/JPG/JPEG), audio (WAV/MP3/M4A/FLAC/OGG), video (MP4/MOV/WebM), PPTX, CSV, Markdown, and TXT. DOCX/PPTX include text and tables. Video processes its audio only; silent video has no searchable transcript. Image-only slides and scanned PDFs need a separate image upload. The default size limit is 10 MiB. Storage uses generated filenames, while the original basename is retained for display. Same content in a ready/processing room is rejected with 409. Failed uploads retain a `failed` record and may be retried. Text uses overlapping 150-word chunks with 30-word overlap and retains line boundaries. Image OCR uses word coordinates to keep separate columns in separate regions; chunks never overlap between image regions.

## Architecture

`Streamlit → FastAPI routers → document/RAG services → SQLite + Qdrant + Groq`

Upload: ownership → bounded read → content hash → unique storage → processing record → extraction/OCR → chunking → embeddings → Qdrant → ready status. Failure records failed status and attempts vector/file cleanup.

Chat: ownership → latest six messages → follow-up-aware retrieval → room-filtered semantic candidates → lexical/exact phrase reranking → document-grounded prompt → Groq → answer/sources → persisted user/assistant messages.

Deletion removes Qdrant vectors, the physical file, and its SQLite record. Room deletion also removes chat history and any remaining room vectors. These stores do not share a transaction: interruption can leave partial deletion. Retrying deletion is supported; cleanup failures are logged. Shared legacy physical files are retained until their final database reference is deleted.

Configuration is in `services/config.py` and `.env.example`. Logs contain operation IDs and exceptions rather than document text or conversation dumps. Prompt instructions reduce hallucinations but do not guarantee correct grounding; evaluate answers against source documents.

## Testing

```powershell
.venv\Scripts\python -B -m unittest discover -s tests -v
```

Automated tests use a temporary SQLite database, temporary upload directory, in-memory Qdrant, deterministic embeddings, and mocked answer generation. They never contact Groq or modify your stored documents. Root `test_*.py` scripts are legacy manual demos with external calls/storage side effects; do not collect them as an automated suite.

Validation: 46 automated tests passed, including real PDF/OCR and Streamlit AppTest, and a separate synthetic live check passed with real MiniLM embeddings and Groq. The complete Alembic migration command passed on a temporary database. See `TEST_MATRIX.md` for the detailed results and limits.

To repeat the live model check, run `python -B tests/live_acceptance.py`. It uses temporary storage and synthetic documents, and makes real Groq API requests using the configured key. It is deliberately separate from unittest discovery.

This working checkout uses `venv` with Python 3.11; its audio/video dependencies are installed and the 46-test suite passed there. The setup above creates `.venv` for a fresh checkout. Use `venv\Scripts\python` instead of `.venv\Scripts\python` when running commands in this existing checkout. Validation tools and dependencies in ignored directories are optional local artifacts, not application requirements.


## Applying OCR improvements to existing certificates

Restart/reload FastAPI and Streamlit, select the room, and click **Reindex** beside the certificate. Reindex replaces its vectors using the current extraction pipeline while retaining the original file and file ID. If it fails, the original remains available for retry. An ownership check protects the action.

Reindex does not rewrite saved assistant answers. Use **Delete Chat** to clear incorrect old answers before repeating the certificate questions. An unknown issuer answer now explains the uncertainty and can report explicitly supported course authorization/platform information without calling those organizations the certificate issuer.


The actual certificate question sequence also passed with real OCR and Groq: Shilpa Mahajan is Assistant Professor (UIC), while Prof. (Dr.) VR Raghuveer is Pro-VC Academic Affairs (Office of Academic Affairs). The issuer clarification reports the course authorizer and platform without guessing the certificate issuer. See `tests/certificate_acceptance.py` for the opt-in reproducible check.

## Capstone deliverables through the demo dataset

- `docs/architecture.png`: client, JWT/auth flow, endpoint groups, extraction, chunking, embedding, Qdrant, Groq, SQL and file storage.
- `docs/technical_document.docx` and `docs/technical_document.pdf`: implementation explanation, code excerpts, complete chat handler, frontend/history, challenges and limits.
- `demo/`: original fictional samples for all nine format categories; `demo/manifest.json` contains questions and expected facts.
- `tests/demo_acceptance.py`: isolated dataset checks (`--offline` for local extraction plus mocked external calls; omit for real MiniLM/Groq validation).

Industry approval is still awaiting the user's chosen pitch. The dataset uses a provisional education/training theme. Set `INDUSTRY`, `APP_TITLE`, and `APP_DESCRIPTION` in `.env` to the approved industry and tailor the problem statement before final submission. No approval is implied by the sample theme. Final submission preparation is underway. Industry and architecture approval, the recording link, and the GitHub destination still need confirmation. See `docs/demo_script.md` and `docs/submission_checklist.md`.

The text model defaults to the previously working `openai/gpt-oss-120b`; an existing `.env` override remains in effect. A live attempt with the model in the brief, `llama-3.3-70b-versatile`, returned model_not_found for this account, so it is replaced to keep chat working. `WHISPER_MODEL=whisper-large-v3`. `VISION_MODEL=qwen/qwen3.8-27b` replaces the retired LLaVA identifier and can be changed to a model enabled for your Groq account. Check [Groq vision documentation](https://console.groq.com/docs/vision) if the provider changes supported models. OCR is retained for certificates to preserve column relationships.

`MAX_MEDIA_SECONDS` defaults to 600 for video. Whisper attachments are limited to 25 MB after extraction; split large clips. `MAX_UPLOAD_MB` defaults to 10 for every uploaded file. A friendly failed upload is visible in the sidebar and may be deleted; reindex can retry only when the original file is retained.

Run format validation:

```powershell
.venv\Scripts\python -B tests/demo_acceptance.py --offline
# Opt-in: makes real Groq API calls using your configured key.
.venv\Scripts\python -B tests/demo_acceptance.py
```

The generated WAV and MP4 are synthetic dataset inputs, not your final project recording. Demo identities are fictional and use the reserved `.example` domain. Files already uploaded before these changes can be reindexed without altering their originals. Restart FastAPI and Streamlit after installing the new requirements.

### Observed vision limitation

Live visual-only testing found that the current Groq vision model miscounted a simple three-circle image and invented layout details. Visual fallback is implemented, but its generated descriptions are labelled unverified and require review. The nine-format dataset uses certificate OCR for its image check; that passed. This limitation is recorded separately rather than counted as a successful vision accuracy test.


## Certificate recipient questions

Questions such as "the certificate is issued to whom?" and "certificate is for whom" expand retrieval with learner/completion terms. The prompt treats a learner named above "has successfully completed" as the recipient, while keeping issuer, course authorizer, and signature titles separate. This correction does not require reindexing existing correctly extracted uploads. The user's six-question sequence and the earlier course/issuer follow-ups passed with actual OCR, MiniLM, Qdrant, and Groq; previous answers in saved history are not rewritten.


## Temporary answer-generation limits

Text generation uses a compact grounded prompt and retains the latest six history messages. LLM_MODEL remains the primary; LLM_FALLBACK_MODEL defaults to the account-enabled openai/gpt-oss-20b. A primary-model 429 switches immediately to the backup and puts the primary into cooldown for the provider's requested wait. Later requests skip models still in cooldown, avoiding repeated attempts against an exhausted daily allowance. Set LLM_FALLBACK_MODEL to an empty value to disable fallback. The backup uses bounded retries for waits up to 30 seconds. If both models are unavailable, HTTP 429 reports the shortest pending wait; provider limits still apply. No answers are fabricated to avoid a quota error.

Failed questions stay available in Streamlit with Retry last question. Only a successful answer saves the user/assistant pair, so retries do not create incomplete turns. The text client uses 25-second request timeouts with nested SDK retries disabled, bounding four possible calls and two short waits below the UI's 180-second timeout. Transcription and vision settings are unchanged.


## Grounded cost judgments

For price/fee questions such as "is winter term fee expensive", the assistant reports the relevant documented amount and currency. If no applicable budget or comparison is supplied, it explains that expense/affordability depends on budget and comparable fees and cannot be determined from the receipt alone. It does not invent market rates or an expensive/cheap verdict. Questions with no relevant amount or comparison still return the unsupported fallback. Repeat the isolated real-model check with `python -B tests/cost_judgment_acceptance.py`; it sends synthetic receipt text only.
