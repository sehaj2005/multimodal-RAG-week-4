# Final submission checklist

## Prepared locally

- [x] FastAPI and Streamlit application, authentication, rooms, uploads, chat, history, and sources.
- [x] Nine sample format categories in demo/ with questions in demo/manifest.json.
- [x] Architecture PNG: docs/architecture.png. Approval is a separate pending item.
- [x] Technical explanation: docs/technical_document.docx and docs/technical_document.pdf.
- [x] README, requirements.txt, .env.example, and ignore rules for local data and secrets.
- [x] 40 passing automated tests; real certificate, audio, and video validation documented in TEST_MATRIX.md.
- [x] Recording walkthrough: docs/demo_script.md.

## Complete before publishing

- [ ] Confirm the approved industry and tailor the final pitch, UI copy, system industry context, and samples.
- [ ] Confirm approval of the architecture diagram; revise it if the reviewer requires changes.
- [ ] Update the technical document for the final approved industry and latest recipient fix.
- [ ] Choose the GitHub repository destination and reviewer access.
- [ ] Review the exact files included in the repository. Personal certificates, .env, SQLite databases, uploads, Qdrant storage, virtual environments, and temporary render files belong outside the published package.
- [ ] Commit and publish the prepared source and deliverables to GitHub.
- [ ] Record and review the application demo using docs/demo_script.md; save its shareable link.
- [ ] Submit the repository link, approved architecture PNG, technical document, and recording link through the required channel.

## Known limits to explain accurately

Visual-only image descriptions are unverified: the current vision model failed a count/layout diagnostic. Certificate OCR passed. Video ingestion uses audio, and image-only slides/scanned PDFs require separate image uploads. The brief's text/vision model identifiers were unavailable or retired; configured alternatives and the reasons are documented in README.md. Confirm any required model substitution with the reviewer.

## Submission message template

Project: Multimodal RAG
Approved industry: [confirmed industry]
GitHub: [published repository URL]
Architecture: [approved PNG attachment or repository link]
Technical document: [Word/PDF attachment]
Recorded demo: [shareable recording link]

Do not replace placeholders with guessed approval or nonexistent links.
