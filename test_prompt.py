from services.ingestion_service import process_pdf
from services.qdrant import embed_and_store
from services.rag import retrieve_context, build_prompt


chunks = process_pdf("sample.pdf")

embed_and_store(
    chunks=chunks,
    room_id=1,
    file_id=1,
    filename="sample.pdf",
    file_type="pdf"
)


question = "What is the winter term fee?"

context = retrieve_context(
    query=question,
    room_id=1,
    limit=5
)


prompt = build_prompt(
    query=question,
    context=context
)


print(prompt)