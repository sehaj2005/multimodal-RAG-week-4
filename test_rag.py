from services.ingestion_service import process_pdf
from services.qdrant import embed_and_store
from services.rag import retrieve_context


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


print("Question:", question)
print("\nRetrieved context:")

for item in context:
    print("\n--- Source ---")
    print("Filename:", item["filename"])
    print("File type:", item["file_type"])
    print("Chunk:", item["chunk_index"])
    print("Score:", item["score"])
    print("Text:", item["text"])