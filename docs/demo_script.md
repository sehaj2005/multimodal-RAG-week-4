# Recording walkthrough

Target duration: 4 to 5 minutes; maximum allowed by the brief: 10 minutes.
Use the approved industry name in the introduction and room name. The current Education sample pitch is provisional until approval is confirmed.

## Before recording

Start the backend and Streamlit. For this existing checkout use:

```powershell
venv\Scripts\python -m uvicorn main:app --reload
# In another terminal:
venv\Scripts\python -m streamlit run streamlit_app.py
```

Open Streamlit and http://127.0.0.1:8000/docs in separate browser tabs. Keep the demo folder ready in File Explorer. Use a new demo account and room, not a room with personal certificates. Keep API keys, passwords, and token values out of the recording.

Rehearse once using these files: syllabus.pdf, learner_policy.docx, certificate.png, courses.csv, and orientation.wav. These cover the mandatory PDF, DOCX, image, CSV, and one extra format. All nine format samples remain available in demo/ for reproduction. Pace chat questions if the provider returns a temporary rate-limit error.

## 0:00 to 0:30 — Explain the use case

Provisional Education narration: "This assistant helps students and academic staff find answers across course documents, policies, certificates, and spoken announcements. Users upload materials into private rooms and receive document-based answers with source references."

State the approved industry once confirmed; do not claim approval without it.

## 0:30 to 1:10 — Register, log in, and create a room

Show registration with a new account, then login. Create a room named for the approved use case, for example Education — Course Information. Explain that each user's rooms are private.

## 1:10 to 2:05 — Upload five formats

Upload the five rehearsal files individually and click Upload and index. Pause on the document list to show every file in ready status. Mention that audio is transcribed and videos use their narrated audio. Do not describe silent video as searchable.

## 2:05 to 3:30 — Answers and sources

Ask these questions separately. Expand Sources after each supported answer and pause so the filename, file type, chunk index, and excerpt are readable.

1. How long does Python Foundations last and who is the lead instructor?
   Expected: four weeks; Dev Rao. Source should include syllabus.pdf.
2. What is the fee in INR and seat count for Data Analysis Basics?
   Expected: 3200 INR; 18 seats. Source should include courses.csv.
3. Who coordinates the evening workshop?
   Expected: Alex Morgan. Source should include orientation.wav.
4. What is the academy director's home address?
   Expected: I don't know. Expand Sources to show No sources found.

Optional image question: Who received certificate CLA-PY-026 and who explicitly issued it?
Expected: Aria Mehta; Cedar Learning Academy. Use the fictional certificate.png, not a personal certificate.

## 3:30 to 4:10 — Persistent history and Swagger

Reload the Streamlit page or switch rooms and return. Scroll through the saved questions and answers to show that history persists.

Open FastAPI /docs. Point out /auth/register, /auth/login, /rooms, /upload/{room_id}, /chat/{room_id}, and /chat/{room_id}/history. No token needs to be revealed.

## 4:10 to 4:30 — Close

Explain the flow briefly: extraction, chunking, embeddings, room-scoped retrieval, Groq answer generation, and stored history. Mention that the repository includes all nine sample formats, an architecture PNG, and technical documentation.

Record using your chosen screen recorder and retain the resulting shareable link. A synthetic audio/video sample is not the required recording of the application walkthrough.
