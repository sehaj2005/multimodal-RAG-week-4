# Week 4 acceptance matrix

Validated on 5 October 2026 with Python 3.12.14 and isolated project dependencies. The updated dependency set also passed a clean pip resolution check:

- 38/38 automated tests passed in 22.1 seconds, including real local PDF extraction, Tesseract OCR, DOCX tables, and Streamlit AppTest.
- Complete `alembic upgrade head` passed on a fresh temporary SQLite database. The suite also tested hash migration with and without a pre-existing hash column.
- Live MiniLM + Qdrant + Groq acceptance passed with synthetic documents: supported answer, pronoun follow-up, unsupported question, unknown certificate issuer, and no retrieval after file deletion.
- All application and acceptance-test source files passed syntax parsing.

Tests used temporary SQLite/files and in-memory Qdrant. Existing project data and secrets were not changed. Run `python -B -m unittest discover -s tests -v` to repeat the isolated suite.

| Case | Expected | Verification |
|---|---|---|
| Cross-user room/file/chat access | 404 without exposing data | Automated |
| Upload via either URL | Same chunking, hash checks, ready status | Automated |
| Duplicate / empty / oversized / unsupported upload | 409 / 400 / 413 / 415 | Automated |
| Traversal filename and equal filenames | Storage stays inside uploads; no overwrite | Automated |
| Extraction/indexing failure and retry | Failed record, partial vectors/file removed, retry allowed | Automated |
| Reindex existing file | Replace vectors, retain original/ID, owner-only, retry after failure | Automated |
| OCR signature columns | Keep each name with its own title; never overlap region chunks | Automated and checked against the real certificate |
| Short follow-up | “For what?” retrieves prior certificate context | Automated and checked with Groq |
| Delete file | DB, file, vectors removed; other room survives | Automated |
| Delete room | Files, vectors, chat removed; other room survives | Automated |
| Invalid/expired token | Rejected | Automated |
| Chunk overlap, room-filtered retrieval | Correct boundaries and isolated sources | Automated |
| Chat and history | Sources returned, messages saved and cleared | Automated with mocked LLM |
| PDF, CSV, TXT, Markdown, image, DOCX | Meaningful extracted text; ready status | Automated, including real PDF/CSV/OCR |
| Grounding and follow-up references | Supported answer or “I don't know”; no person mixing | Passed with real MiniLM + Groq and synthetic documents |
| Streamlit login/upload/delete/chat/history | Usable flow and visible failures | Streamlit AppTest passed; visual browser review optional |
| Clean installation and migrations | Requirements install; migrations reach head | Exact requirements installed; full migration command passed |

To repeat the live check, run `python -B tests/live_acceptance.py`. It uses the configured Groq key and sends synthetic test content only; it may make four Groq requests. A production-data review remains useful: test representative documents for OCR quality, long-document relevance, conflicting statements, and answer accuracy. Passing synthetic checks does not guarantee correctness for every document.


## Certificate accuracy regression

The exact five-question sequence passed against `coursera certficate_01 (2).png` using real OCR, MiniLM embeddings, Qdrant, and Groq in temporary storage:

- Recipient: sehtej hanjra.
- “For what?”: Python & Core Data Tools; the short follow-up retains certificate context.
- Issuer: cannot determine the certificate issuer; the course was authorized by Chandigarh University and offered through Coursera. No inferred issuer or speculative signatory.
- Shilpa Mahajan: Assistant Professor, UIC.
- Prof. (Dr.) VR Raghuveer: Pro-VC Academic Affairs, Office of Academic Affairs.

Repeat explicitly with `python -B tests/certificate_acceptance.py "path/to/certificate.png"`. This sends the image's extracted text to the configured Groq service. The automated suite also tests column isolation, reindex replacement, owner checks, and retention of the original file after a failed reindex. The final follow-up/issuer-context regression passed again after the last prompt update.

Existing production vectors were preserved. The earlier OCR column correction requires the room's **Reindex** button for older uploads. The recipient-query correction below works with existing correctly extracted uploads.

## Capstone completion through demo dataset

- 38 automated checks passed, including PPTX tables, audio transcription boundary, real video decoding in separate dataset checks, silent-video failure, temporary media cleanup, prior-role messages, and 150-character excerpts.
- All nine sample formats passed offline extraction and the opt-in live MiniLM/Qdrant/Groq check. Live checks verified expected facts, filenames, excerpt bounds, room deletion, and the empty-room unsupported fallback. Results: docs/demo_offline_results.json and docs/demo_live_results.json.
- Groq models available to this account were inspected. The brief's llama-3.3-70b-versatile returned model_not_found; openai/gpt-oss-120b remains the text default. Whisper large-v3 passed real WAV and MP4 transcription.
- The preview vision model qwen/qwen3.8-27b accepted image requests but failed the optional visual count/layout diagnostic. This is an accuracy limitation, not a passing test. Generated descriptions are explicitly unverified. See docs/vision_live_results.json.
- Updated requirements resolved successfully with pip --dry-run --ignore-installed. MoviePy/Pillow compatibility is reflected in requirements.txt.
- Architecture PNG created. Technical DOCX rendered to PDF and page images for layout inspection. DOCX demo sample rendered separately.
- Industry approval remains unspecified; sample education/training content is provisional. Recorded demo and GitHub submission are deferred by request.


## Certificate recipient wording regression (5 October 2026)

- 40/40 automated checks passed in 27.3 seconds in the application's Python 3.11 environment.
- Real OCR, MiniLM, Qdrant, and Groq passed the user's six-question sequence: generic recipient, Shilpa Mahajan, Raghuveer, course authorizer, generic recipient again, and Sehtej Hanjra by name.
- Both "the certificate is issued to whom?" and "certificate is for whom" returned Sehtej Hanjra. Before the fix, the completion passage was absent from the top five results for these questions.
- Recipient questions now add learner/completion search terms; the answer prompt explicitly recognizes the learner named above "has successfully completed" as the recipient. No certificate-specific recipient name is hardcoded.
- Automated checks cover room isolation, the five-source limit, recipient/issuer/authorizer intent separation, and an unsupported recipient answer.
- Live regression requests are spaced 25 seconds apart to respect provider token limits; configure CERTIFICATE_TEST_PAUSE_SECONDS to change test pacing.
- No reupload or reindex is needed for this query/prompt correction. Previously saved chat answers remain in history; ask the questions again to see corrected answers.
