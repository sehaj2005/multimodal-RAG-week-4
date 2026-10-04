# Fictional demo dataset

These original samples contain no real learner information. Education/training is a provisional sample theme; the approved capstone industry has not been provided.

Create a fresh room and upload the nine files listed in `manifest.json`. Ask each listed question and compare the answer and Sources against its expected facts. Upload the certificate separately to demonstrate explicit issuer wording. The WAV and MP4 are synthetic narration, not the final recorded project demo. `orientation_frame.png` is a media construction asset; do not upload it when demonstrating the nine formats.

Also ask “What is the academy director’s home address?” Expect “I don’t know.” and No sources found. Reload to verify saved history, switch rooms to demonstrate isolation, then delete a file and verify its facts are no longer available in a room containing only that file.

For a controlled format demonstration, create one room per format. This prevents another file containing the same facts from supplying the answer instead. Audio and video intentionally share narration. Visual-only images use Groq vision; this certificate uses spatial OCR. The CSV is an upload sample, not a workbook analysis deliverable.

Run `python -B tests/demo_acceptance.py` for an opt-in live check. It uses temporary SQLite/uploads and in-memory Qdrant, real Groq calls, and real embeddings. It never modifies your saved rooms. This consumes API usage. Use `--offline` to validate real local extraction and mocked API results.

`visual_shapes.png` is an optional diagnostic image, outside the nine-file manifest. The Groq model failed its count/layout accuracy check; use it to inspect the limitation, not as a passing demo example.
