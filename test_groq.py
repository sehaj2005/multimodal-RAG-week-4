from services.llm import generate_answer


prompt = "Explain what RAG means in one simple paragraph."


answer = generate_answer(prompt)

print("Groq Response:")
print(answer)