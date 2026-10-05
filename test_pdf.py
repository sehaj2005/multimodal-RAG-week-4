from services.ingestion_service import process_pdf

file_path = "sample.pdf"

chunks = process_pdf(file_path)

print("Total chunks:", len(chunks))

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)