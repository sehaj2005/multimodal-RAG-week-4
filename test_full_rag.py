from services.ingestion_service import process_pdf
from services.qdrant import embed_and_store
from services.rag import ask


chunks = process_pdf("sample.pdf")

embed_and_store(
    chunks=chunks,
    room_id=1,
    file_id=1,
    filename="sample.pdf",
    file_type="pdf"
)

question = "What is the capital of France?"

result = ask(
    query=question,
    room_id=1
)

print("Answer:")
print(result["answer"])

print("\nSources:")

for source in result["sources"]:
    print("\n--- Source ---")
    print("Filename:", source["filename"])
    print("File type:", source["file_type"])
    print("Chunk:", source["chunk_index"])
    print("Excerpt:", source["excerpt"])