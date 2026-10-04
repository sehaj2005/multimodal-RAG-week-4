"""Generate fictional capstone assets. Uses bundled Python for authoring."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.runtime-deps'))
import ast, json, textwrap
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pymupdf
from pptx import Presentation
from pptx.util import Inches as SlideInches
from moviepy import AudioFileClip, ImageClip
DEMO=ROOT/'demo'; DOCS=ROOT/'docs'
DEMO.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True)
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),size)
# Clear, original diagram with deliberately distinct upload and query paths.
im=Image.new('RGB',(1600,1120),'#f5f7fb'); d=ImageDraw.Draw(im)
d.text((55,30),'Multimodal RAG | system architecture',font=font(36,True),fill='#18243a')
d.text((55,83),'Owner-scoped rooms • local storage • grounded answers with sources',font=font(22),fill='#46546a')
def box(x,y,w,h,title,lines,color='#e6edf7'):
    d.rounded_rectangle((x,y,x+w,y+h),radius=16,fill=color,outline='#65809f',width=2)
    d.text((x+18,y+15),title,font=font(23,True),fill='#172640')
    for i,line in enumerate(lines): d.text((x+18,y+53+i*29),line,font=font(19),fill='#243a50')
def arrow(points,label=None,at=None):
    d.line(points,fill='#506982',width=4)
    x,y=points[-1]; px,py=points[-2]
    if y>py: tri=[(x,y),(x-8,y-13),(x+8,y-13)]
    elif y<py: tri=[(x,y),(x-8,y+13),(x+8,y+13)]
    elif x>px: tri=[(x,y),(x-13,y-8),(x-13,y+8)]
    else: tri=[(x,y),(x+13,y-8),(x+13,y+8)]
    d.polygon(tri,fill='#506982')
    if label: d.text(at,label,font=font(17),fill='#354a65')
box(60,145,430,155,'Streamlit client',['Login / registration → JWT session','Sidebar: rooms, uploads, file statuses','Chat: history + collapsible Sources'])
box(620,145,850,155,'FastAPI boundary',['Auth: /auth/register, /auth/login, /auth/me','Room ownership on /rooms, /upload, /files, /chat','Chat history: GET/DELETE /chat/{room_id}/history'])
arrow([(490,223),(620,223)],'Bearer JWT',(500,183))
box(60,405,430,215,'Upload pipeline',['Validate size / type / filename','Hash duplicate check; unique file path','PDF / DOCX / CSV / TXT / MD / PPTX','Images: spatial OCR → vision fallback','Audio: Whisper; video → audio only'])
box(620,405,395,215,'Text indexing',['150 words; 30-word overlap','Image regions chunked separately','MiniLM embeddings (384 dims)','Qdrant upsert with file metadata'])
box(1080,405,390,215,'SQL + file storage',['SQLite: users, owned rooms,','messages/sources, file statuses','Uploads: generated physical paths','Statuses: processing / ready / failed'])
arrow([(750,300),(750,350),(275,350),(275,405)],'Upload route',(320,320))
arrow([(490,510),(620,510)])
arrow([(1275,300),(1275,405)],'Auth, metadata, history',(1290,332))
arrow([(490,585),(550,585),(550,675),(1275,675),(1275,620)])
box(60,780,430,190,'Chat pipeline',['Current query + last 6 role messages','Follow-up-aware retrieval query','Room-filtered top 5 relevant chunks','Build document-grounded prompt'])
box(620,780,395,190,'Qdrant local collection',['Cosine search + lexical reranking','Payload: room_id, file_id, filename,','file_type, chunk_index, text','Owner filter applied before answering'])
box(1080,780,390,190,'Groq inference',['Text: configured LLM','Audio: whisper-large-v3','Vision: configured multimodal model','Answer + first 150-char excerpts'])
arrow([(620,265),(550,265),(550,725),(275,725),(275,780)],'Chat route',(320,695))
arrow([(818,620),(818,780)],'Stored vectors',(832,705))
arrow([(490,854),(620,854)],'Query',(513,816))
arrow([(620,920),(490,920)],'Evidence',(495,933))
arrow([(490,970),(490,1015),(1275,1015),(1275,970)],'Prompt → answer + sources',(660,1025))
d.text((60,1070),'Responses return to Streamlit; chat turns persist in SQLite. Deletion removes vectors, files, and records.',font=font(21),fill='#354a65')
im.save(DOCS/'architecture.png')
# All facts and identities below are fictional and shareable.
(DEMO/'support.txt').write_text('Cedar Learning Academy — fictional demonstration data.\nThe learner support desk opens Monday to Friday from 09:00 to 17:00.\nSupport contact: support@cedar.example.\nThe library lending period is 14 days.\n',encoding='utf-8')
(DEMO/'enrollment.md').write_text('# Cedar enrollment guide\n\nFictional demonstration data.\n\nThe enrollment deadline is 30 October 2026.\nThe application code is CEDAR-PY-26.\nApplicants submit a completed form and a short statement of learning goals.\n',encoding='utf-8')
(DEMO/'courses.csv').write_text('course,fee_inr,seats\nPython Foundations,2400,24\nData Analysis Basics,3200,18\nPresentation Skills,1500,20\n',encoding='utf-8')
policy=Document(); policy.add_heading('Cedar Learning Academy',0); policy.add_paragraph('Fictional learner policy | demonstration dataset')
policy.add_heading('Attendance and completion',1); policy.add_paragraph('Learners need at least 75 percent attendance to receive a completion certificate. They must submit the final project by 27 November 2026.')
policy.add_heading('Refund policy',1); policy.add_paragraph('A full refund is available up to seven days before the course starts. The policy contact is Noor Das, Learner Services Coordinator.')
for style_name in ['Title','Subtitle','Heading 1','Heading 2','Heading 3']:
    policy.styles[style_name].font.color.rgb=RGBColor(0,0,0)
for style in policy.styles:
    for border in style.element.findall('.//'+qn('w:pBdr')):
        border.getparent().remove(border)
policy.save(DEMO/'learner_policy.docx')
pdf=pymupdf.open(); page=pdf.new_page(); page.insert_text((55,60),'Cedar Learning Academy — Python Foundations',fontsize=18)
page.insert_textbox(pymupdf.Rect(55,110,540,650),'Fictional demonstration syllabus\n\nThe course lasts four weeks.\nWeek 1: variables and data types.\nWeek 2: loops and functions.\nWeek 3: CSV files and data cleaning.\nWeek 4: a final data analysis project.\nThe lead instructor is Dev Rao.\nThe final project uses a fictional bookstore sales dataset.',fontsize=12)
pdf.save(DEMO/'syllabus.pdf'); pdf.close()
cert=Image.new('RGB',(1600,1050),'white'); cd=ImageDraw.Draw(cert); cd.rectangle((25,25,1575,1025),outline='#174777',width=6)
for y,line,size in [(95,'CEDAR LEARNING ACADEMY',45),(190,'CERTIFICATE OF COMPLETION',40),(305,'Issued to: Aria Mehta',38),(400,'Course: Python Foundations',38),(495,'Completed on: 21 October 2026',34),(590,'Issued by: Cedar Learning Academy',34),(685,'Certificate ID: CLA-PY-026',34),(820,'FICTIONAL DEMONSTRATION DATA',30)]:
    cd.text((115,y),line,font=font(size, y in [95,190]),fill='#163757')
cert.save(DEMO/'certificate.png')
deck=Presentation(); slide=deck.slides.add_slide(deck.slide_layouts[1]); slide.shapes.title.text='Cedar Python workshop'
slide.placeholders[1].text='Fictional training dataset\nWorkshop venue: Cedar Hall\nLab capacity: 24 learners\nEquipment: laptop, charger, and notebook'
slide=deck.slides.add_slide(deck.slide_layouts[1]); slide.shapes.title.text='Assessment plan'; slide.placeholders[1].text='Final project contributes 60 percent of the grade.\nWeekly quizzes contribute 40 percent.\nAssessment lead: Noor Das.'
deck.save(DEMO/'workshop.pptx')
voice=DEMO/'orientation.wav'
if not voice.exists(): raise RuntimeError('Generate demo/orientation.wav with local speech synthesis first')
# A narrated media sample, not the final project demonstration recording.
frame=Image.new('RGB',(1280,720),'#102b46'); fd=ImageDraw.Draw(frame)
for y,line,size in [(100,'Cedar Learning Academy',48),(225,'Workshop orientation',40),(330,'Fictional demonstration dataset',28),(435,'Video ingestion transcribes the narrated audio.',26)]: fd.text((75,y),line,font=font(size),fill='white')
frame.save(DEMO/'orientation_frame.png')
with AudioFileClip(str(voice)) as audio:
    clip=ImageClip(str(DEMO/'orientation_frame.png')).with_duration(audio.duration).with_audio(audio)
    clip.write_videofile(str(DEMO/'orientation.mp4'),fps=10,codec='libx264',audio_codec='aac',logger=None)
    clip.close()
manifest=[
 {'file':'syllabus.pdf','question':'How long does Python Foundations last and who is the lead instructor?','expected':['four weeks','Dev Rao']},
 {'file':'learner_policy.docx','question':'What attendance percentage is needed for a completion certificate?','expected':['75']},
 {'file':'certificate.png','question':'Who received certificate CLA-PY-026 and who explicitly issued it?','expected':['Aria Mehta','Cedar Learning Academy']},
 {'file':'orientation.wav','question':'Who coordinates the evening workshop and when does it start?','expected':['Alex Morgan','November','six']},
 {'file':'orientation.mp4','question':'What must learners bring to the evening workshop?','expected':['laptop']},
 {'file':'workshop.pptx','question':'What venue is used and what percentage of the grade is the final project?','expected':['Cedar Hall','60']},
 {'file':'courses.csv','question':'What is the fee in INR and seat count for Data Analysis Basics?','expected':['3200','18']},
 {'file':'enrollment.md','question':'What is the enrollment deadline and application code?','expected':['30 October 2026','CEDAR-PY-26']},
 {'file':'support.txt','question':'What is the library lending period?','expected':['14']},
]
(DEMO/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(DEMO/'README.md').write_text('''# Fictional demo dataset

These original samples contain no real learner information. Education/training is a provisional sample theme; the approved capstone industry has not been provided.

Create a fresh room and upload the nine files listed in `manifest.json`. Ask each listed question and compare the answer and Sources against its expected facts. Upload the certificate separately to demonstrate explicit issuer wording. The WAV and MP4 are synthetic narration, not the final recorded project demo. `orientation_frame.png` is a media construction asset; do not upload it when demonstrating the nine formats.

Also ask “What is the academy director’s home address?” Expect “I don’t know.” and No sources found. Reload to verify saved history, switch rooms to demonstrate isolation, then delete a file and verify its facts are no longer available in a room containing only that file.

For a controlled format demonstration, create one room per format. This prevents another file containing the same facts from supplying the answer instead. Audio and video intentionally share narration. Visual-only images use Groq vision; this certificate uses spatial OCR. The CSV is an upload sample, not a workbook analysis deliverable.

Run `python -B tests/demo_acceptance.py` for an opt-in live check. It uses temporary SQLite/uploads and in-memory Qdrant, real Groq calls, and real embeddings. It never modifies your saved rooms. This consumes API usage. Use `--offline` to validate real local extraction and mocked API results.
''',encoding='utf-8')
# Technical manual: prose explains the real implementation; code is sourced from the repo.
doc=Document(); sec=doc.sections[0]; sec.top_margin=sec.bottom_margin=Inches(.7); sec.left_margin=sec.right_margin=Inches(.72)
normal=doc.styles['Normal']; normal.font.name='Calibri'; normal.font.size=Pt(10); normal.paragraph_format.space_after=Pt(6)
for name in ['Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
    doc.styles[name].font.color.rgb=RGBColor(0,0,0)
code_style=doc.styles.add_style('Source Code',1); code_style.font.name='Consolas'; code_style.font.size=Pt(7.5); code_style.paragraph_format.space_after=Pt(0); code_style.paragraph_format.line_spacing=1
footer=sec.footer.paragraphs[0]; footer.text='Multimodal RAG | technical implementation | '
fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)
def heading(title,new=True):
    if new: doc.add_page_break()
    doc.add_heading(title,1)
def para(text): doc.add_paragraph(text)
def code(path, function=None, lines=None, compact=False):
    source=(ROOT/path).read_text(encoding='utf-8')
    if function:
        tree=ast.parse(source)
        node=next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==function)
        source='\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
    if compact: source=ast.unparse(ast.parse(source))
    if lines: source='\n'.join(source.splitlines()[slice(*lines)])
    doc.add_paragraph(path,style='Caption')
    for line in source.splitlines():
        for wrapped in textwrap.wrap(line,width=98,replace_whitespace=False,drop_whitespace=False) or ['']:
            doc.add_paragraph(wrapped,style='Source Code')
doc.add_heading('Multimodal RAG',0); doc.add_paragraph('Technical implementation and demo dataset',style='Subtitle')
para('This capstone gives authenticated users private rooms for querying documents, images, presentation slides, audio, and narrated video. Answers include source metadata and short excerpts. The code and assets are prepared through the demo dataset stage; recording and GitHub submission are deferred at the user’s request.')
para('The sample problem is fragmented training information: learners need facts from syllabi, policies, certificates, slides, and orientation recordings. The fictional Cedar Learning Academy dataset demonstrates this workflow. This is a provisional education/training example, not a claim that the industry pitch was approved. INDUSTRY, APP_TITLE, and APP_DESCRIPTION support the final approved positioning.')
doc.add_heading('Scope and reading guide',1)
para('The following sections explain the system boundary, authentication, data model, format extraction, indexing, grounded chat, history, frontend state, operational limits, and reproducible validation. Code excerpts are taken from the current repository. The chat handler is included in full; utility excerpts are labelled by their source path.')
para('The local stores remain authoritative for persisted accounts and files. External Groq services perform generation, transcription, and visual fallback. Text embeddings are produced locally with all-MiniLM-L6-v2. The default generation model is openai/gpt-oss-120b; existing .env overrides remain intact. Groq rejected the model in the brief, llama-3.3-70b-versatile, with model_not_found for this account, so the working model is retained.')
heading('Architecture and request flows'); doc.add_picture(str(DOCS/'architecture.png'),width=Inches(6.8))
para('Registration hashes the password; login issues a signed JWT with expiration. Streamlit sends the bearer token on each protected request. The backend validates the user and verifies room ownership before reading history, uploading, retrieving vectors, or deleting data.')
para('Uploads produce text before embedding. Video audio is extracted locally and the video binary is never sent to Whisper. The chat path uses the latest six messages as role messages, retrieves up to five room-filtered chunks, and stores the answer and its source list alongside the user question.')
heading('Authentication and authorization')
para('bcrypt hashes passwords with a fresh salt. Registration returns HTTP 201, duplicate emails return 400, and invalid credentials or JWTs return 401. Password input is bounded to bcrypt’s 72-byte limit. Tokens include the user ID as sub and an explicit exp claim. Room checks return 404 for absent or inaccessible rooms, limiting disclosure across accounts.')
code('services/auth.py','hash_password'); code('services/auth.py','create_access_token'); code('services/documents.py','require_room')
para('decode_access_token requires expiration and permits only HS256. get_current_user converts the subject to an integer and loads the account from SQLite. Logout clears Streamlit state; expired sessions prompt a new login through the client’s centralized request wrapper.')
heading('Database models and relationships')
para('User is the account root. ChatRoom.owner_id references User.id. Each ChatMessage references its room and user and stores role, content, timestamp, and sources as JSON. UploadedFile references its room and stores original display filename, extension, generated physical path, hash, timestamp, and processing status. Ownership is enforced by queries rather than public room membership.')
table=doc.add_table(rows=1,cols=3); table.style='Light Shading Accent 1'
for cell,text in zip(table.rows[0].cells,['Model','Foreign keys','Persisted purpose']): cell.text=text
for row in [('User','—','Email, username, password hash'),('ChatRoom','owner_id → User','Private retrieval scope'),('ChatMessage','room_id → ChatRoom; user_id → User','Ordered conversation and sources'),('UploadedFile','room_id → ChatRoom','Upload state, hash and stored path')]:
    for cell,text in zip(table.add_row().cells,row): cell.text=text
para('SQLAlchemy metadata creates tables for fresh databases. Alembic records schema evolution. Existing databases created before Alembic must be backed up and inspected before stamping the matching baseline. No production schema mutation is required by this phase. See db/models.py for the complete model declarations.')
code('db/models.py', compact=True)
heading('Document extractors: PDF, DOCX, and slides')
para('PDF uses pymupdf4llm to preserve readable structure as Markdown. DOCX extracts paragraphs and table rows. PPTX walks slides in order and recursively reads grouped shapes, text frames, and tables. Each slide is labelled. Scanned PDFs and image-only slides do not have a dedicated raster OCR pipeline; upload their images separately for OCR/vision.')
code('services/ingestion/pdf.py'); code('services/ingestion/docx.py'); code('services/ingestion/pptx.py')
heading('Document extractors: text, Markdown, and CSV')
para('TXT and Markdown read UTF-8 with an optional byte-order mark. Markdown source is preserved as text. CSV uses pandas to present a table representation for retrieval; this is intended for small demo tables. The bounded upload prevents unrestricted input size. This version does not promise spreadsheet arithmetic or exhaustive analytical queries across large CSVs.')
code('services/ingestion/text.py'); code('services/ingestion/markdown.py'); code('services/ingestion/csv.py')
para('Extraction returns a string, then document_chunks applies the common chunker. Empty text yields HTTP 422 and marks the upload failed. An extraction or embedding failure removes partial vectors and attempts physical file cleanup while leaving a failed record visible for deletion.')
heading('Image extraction and certificate relationships')
para('Spatial OCR is primary for images with sufficient readable text. Tesseract word coordinates split wide horizontal gaps and link nearby left-aligned lines. Signature columns become separate regions and are chunked independently. This avoids joining one person’s name to another person’s title. Sparse OCR or unavailable OCR triggers Groq vision instead, with bounded image dimensions and explicit uncertainty instructions.')
code('services/ingestion/image.py','extract_image_text'); code('services/ingestion/image.py','chunk_image_text')
para('The fallback in services/ingestion/vision.py uses a JPEG data URL and VISION_MODEL. The capstone’s old LLaVA identifier is retired; the current documented Groq vision default is configurable. Certificate answers must distinguish recipient, explicitly stated issuer, course authorizer, platform, and signer. Branding alone does not establish an issuer.')
heading('Audio and video extraction')
para('Audio uploads are sent to Groq Whisper large-v3. Video is opened locally with MoviePy, checked for an audio track and duration, and converted to mono PCM at 16 kHz in a temporary directory. The directory and clip handles are closed even if transcription fails. Transcription has a 25 MB direct-attachment cap; longer media must be split. Videos without speech cannot supply document facts through this audio-only path.')
code('services/ingestion/audio.py'); code('services/ingestion/video.py')
heading('Chunking, embeddings, and vector payloads')
para('Text is divided into 150-word windows with a 30-word overlap. Source slicing preserves line boundaries. Image regions use the same chunker without overlap between separate regions. A cached SentenceTransformer generates 384-dimensional MiniLM vectors. Qdrant uses cosine distance; each point has a UUID and metadata needed for room isolation and source attribution.')
code('services/ingestion/chunker.py',compact=True); code('services/embedder.py')
para('embed_and_store in services/qdrant.py upserts text plus room_id, file_id, filename, file_type, and chunk_index. Search retrieves room-filtered candidates and combines semantic similarity with lexical matches and an exact phrase bonus before selecting the top five. A file deletion filters by both room_id and file_id; room deletion removes remaining vectors for the room.')
heading('Grounded chat: complete POST handler')
para('The handler verifies room ownership, loads the last six messages in reverse chronological order, restores chronological roles, and calls the RAG service. Only after successful generation does it persist both user and assistant messages. Model failures return a friendly 502 and leave no half-finished conversation turn.')
code('routers/chat.py','chat')
para('rag.ask expands short follow-up queries with recent conversational references for retrieval. Previous assistant messages are never a factual source. The generated answer is checked for the canonical unknown response, which returns an empty source list. Other responses include filename, file_type, file_id, chunk_index, score, and the first 150 characters of each retrieved chunk. Sources represent retrieved evidence, not a verified per-sentence citation map.')
heading('Conversation history and Groq role messages')
para('History is owner-scoped, ordered by timestamp then message ID, and accepts nonnegative skip with limit from 1 to 200. Streamlit fetches successive pages until the final short page, so saved history is not limited to the first 200 messages. Clearing history is idempotent and does not remove uploaded files.')
code('routers/chat.py','get_chat_history'); code('services/llm.py','generate_answer')
para('Groq receives a system instruction, the six prior user/assistant role messages, and a current user message containing retrieved evidence and the question. INDUSTRY supplies domain context without allowing outside facts. Configuration overrides let the deployment retain an already functioning model.')
heading('Streamlit JWT, room state, and source rendering')
para('The client stores token, room_id, loaded_room, and chat_history in session state. It sends the JWT on every protected request. A room change reloads persisted history. Logout clears room and chat state. New questions update the visible conversation only after the API returns successfully, preventing stale local messages after a failed generation.')
code('streamlit_app.py','render_message'); code('streamlit_app.py','load_history')
para('The left sidebar contains room selection, upload, file status badges, reindex, and delete actions. The main pane renders chat. Every assistant message has a Sources expander with filename, uppercase file type, chunk index, and excerpt; an empty list shows No sources found. Successful uploads show the number of indexed chunks, and failed uploads display the API’s friendly error.')
heading('Vector upsert and source payloads')
para('Each point contains room/file identity and source text. Qdrant enforces the configured collection dimension when storing vectors. The function returns the indexed count.')
code('services/qdrant.py','embed_and_store')
heading('Visual image fallback: Groq request')
para('Sparse OCR uses a bounded JPEG data URL. The configured model describes visible counts, colors, layout, and readable text without inferring identities.')
code('services/ingestion/vision.py','extract_visual_description')
heading('Operations, challenges, and limitations')
para('The existing virtual environment referenced a missing Python installation. Validation therefore used the bundled Python 3.12 runtime and an isolated dependency target. README setup uses a fresh .venv so normal project commands work without relying on that validation target. MoviePy 2.2 requires Pillow below version 12; requirements were aligned to Pillow 11.3.')
para('SQLite, filesystem uploads, and Qdrant do not share a distributed transaction. Processing cleanup is best effort and logged; retrying deletion helps recover partial failures. Reindex retains the original physical file if it fails. Embedded Qdrant requires one backend process per storage directory. The application is a local capstone prototype rather than a hardened hosted service.')
para('Live visual-only testing found that the current Groq vision model miscounted a simple three-circle image and invented layout details. Visual fallback is implemented, but its generated descriptions are labelled unverified and require review. The nine-format dataset uses certificate OCR for its image check; that passed. This limitation is recorded separately rather than counted as a successful vision accuracy test.')
para('OCR and generative extraction can introduce errors. The certificate tests explicitly protect name/title separation and issuer uncertainty. Unsupported questions return the grounded fallback. Image-only presentations, scanned PDFs, non-speech video, very large CSVs, and long media remain stated limits. Prompt grounding reduces errors but does not guarantee them away.')
heading('Demo dataset and validation plan')
para('demo/manifest.json lists one sample per required format with a question and expected facts. All identities and institutions are fictional. For reliable evidence attribution, create a fresh room for each format during automated checks. The MP4 is synthesized sample media, distinct from the deferred final project recording. Tests use temporary SQLite/uploads and in-memory Qdrant, preserving the user’s saved data.')
para('The automated suite covers authentication, cross-user isolation, upload bounds and duplicates, real PDF/DOCX/PPTX/CSV/OCR extraction, mocked media APIs, vector cleanup, history, source rendering, and frontend login/chat/delete. The opt-in demo acceptance script separately exercises actual media decoding, real embeddings, and Groq when enabled. Current pass counts and live model results are recorded in TEST_MATRIX.md after execution.')
para('Before final submission: supply the approved industry pitch and apply matching branding, review the technical document, record the complete demonstration, and submit the GitHub repository. Recording and repository submission are intentionally outside the current authorized phase.')
para('Primary API references: console.groq.com/docs/speech-to-text, console.groq.com/docs/vision, console.groq.com/docs/models. MoviePy API: zulko.github.io/moviepy/user_guide/loading.html. These references explain the model substitution and local video/audio extraction.')
for style in doc.styles:
    for border in style.element.findall('.//'+qn('w:pBdr')):
        border.getparent().remove(border)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs: run.font.color.rgb=RGBColor(0,0,0)
doc.save(DOCS/'technical_document.docx')
print('Created architecture, nine-format fictional demo dataset, and technical Word document.')
