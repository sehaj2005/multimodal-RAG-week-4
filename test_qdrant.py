from services.ingestion_service import process_pdf
from services.qdrant import embed_and_store, search_similar


# 1. Process PDF
chunks = process_pdf("sample.pdf")


# 2. Store chunks in Qdrant
embed_and_store(
    chunks=chunks,
    room_id=1,
    file_id=1,
    filename="sample.pdf",
    file_type="pdf"
)


# 3. Ask a question
question = "What is the winter term fee?"


# 4. Retrieve relevant chunks
results = search_similar(
    query=question,
    room_id=1,
    limit=5
)


print("Question:", question)
print("\nRetrieved results:")

for result in results:
    print("\n--- Result ---")
    print("Score:", result.score)
    print("Filename:", result.payload["filename"])
    print("Text:", result.payload["text"])