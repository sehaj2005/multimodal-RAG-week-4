import re
from services.llm import generate_answer
from services.qdrant import search_similar


# ==================================================
# FOLLOW-UP DETECTION
# ==================================================

def is_follow_up(query: str) -> bool:
    """
    Determine whether the current question depends
    on the previous conversation.
    """

    query_lower = ' '.join(query.lower().strip().split())
    if query_lower.rstrip('?.!') in {'for what', 'why', 'how', 'what course', 'which course', 'what is it for',
                                      'who issued the certificate', 'who issued this certificate', 'who issued it',
                                      'who signed it', 'who authorized it'}:
        return True

    follow_up_patterns = [
        "what about him",
        "what about her",
        "what about them",
        "what did he",
        "what did she",
        "what does he",
        "what does she",
        "where does he",
        "where does she",
        "who is he",
        "who is she",
        "his designation",
        "her designation",
        "his course",
        "her course",
        "his role",
        "her role",
        "his name",
        "her name",
        "his certificate",
        "her certificate",
        "what course did he",
        "what course did she",
        "tell me more about him",
        "tell me more about her",
    ]

    return any(
        pattern in query_lower
        for pattern in follow_up_patterns
    )


def is_certificate_recipient_question(query: str) -> bool:
    """Recognize recipient wording without confusing issued-to with issued-by."""
    text = ' '.join(query.lower().split())
    if not re.search(r'\bcertificate\b', text):
        return False
    return bool(re.search(
        r'\b(?:to|for)\s+(?:who|whom)\b|'
        r'\b(?:who|whom)\b.*\b(?:issued|awarded|presented|given)\s+to\b|'
        r'\b(?:who|whom)\b.*\b(?:received|earned|completed)\b|'
        r'\b(?:recipient|learner|recipient\'s)\b|'
        r'\bwhose\b|\b(?:who|whom)\b.*\b(?:name|named)\b', text))


# ==================================================
# RETRIEVE CONTEXT
# ==================================================

def retrieve_context(
    query: str,
    room_id: int,
    limit: int = 5,
):
    """
    Retrieve relevant document chunks from Qdrant.

    Only documents belonging to the current room
    are searched.
    """

    results = search_similar(
        query=query,
        room_id=room_id,
        limit=limit,
    )

    context = []
    seen = set()

    for result in results:

        payload = result.payload or {}

        filename = payload.get(
            "filename",
            "Unknown",
        )

        file_type = payload.get(
            "file_type",
            "Unknown",
        )

        file_id = payload.get(
            "file_id",
            "Unknown",
        )

        chunk_index = payload.get(
            "chunk_index",
            0,
        )

        text = payload.get(
            "text",
            "",
        )

        if not text.strip():
            continue

        # ------------------------------------------
        # UNIQUE SOURCE
        # ------------------------------------------

        source_key = (
            file_id,
            chunk_index,
        )

        # ------------------------------------------
        # REMOVE DUPLICATE CHUNKS
        # ------------------------------------------

        if source_key in seen:
            continue

        seen.add(source_key)

        context.append(
            {
                "filename": filename,
                "file_type": file_type,
                "file_id": file_id,
                "chunk_index": chunk_index,
                "text": text,
                "score": result.score,
            }
        )

    return context


# ==================================================
# BUILD PROMPT
# ==================================================

def build_prompt(
    query: str,
    context: list[dict],
    history: list[dict] | None = None,
):
    """
    Build the final prompt sent to the LLM.
    """

    # ----------------------------------------------
    # DOCUMENT CONTEXT
    # ----------------------------------------------

    context_parts = []

    for index, item in enumerate(
        context,
        start=1,
    ):

        context_parts.append(
            f"""
SOURCE {index}

Filename: {item["filename"]}
File type: {item["file_type"]}
Chunk: {item["chunk_index"]}
Retrieval score: {item["score"]}

Content:
{item["text"]}
"""
        )

    context_text = "\n".join(
        context_parts
    )

    # ----------------------------------------------
    # CONVERSATION HISTORY
    # ----------------------------------------------

    if history:

        history_parts = []

        for item in history:

            history_parts.append(
                f'{item["role"]}: {item["content"]}'
            )

        history_text = "\n".join(
            history_parts
        )

    else:

        history_text = (
            "No previous conversation."
        )

    # ----------------------------------------------
    # FINAL PROMPT
    # ----------------------------------------------

    prompt = f"""
You are a helpful document-based RAG assistant.

When evidence is labelled Generated visual description (unverified), qualify the answer as automated image analysis that may be inaccurate. Do not present visual counts or inferred identities as verified facts.

Your job is to answer the user's question using ONLY
information supported by the DOCUMENT CONTEXT.

==================================================
IMPORTANT RULES
==================================================

1. DOCUMENT CONTEXT IS THE PRIMARY SOURCE OF TRUTH.

2. NEVER use outside knowledge.

3. NEVER invent information.

4. Previous conversation can ONLY be used to understand
   references such as:

   - he
   - she
   - him
   - her
   - they
   - them
   - it
   - this
   - that
   - the person
   - the certificate
   - the course

5. Do NOT treat previous assistant answers as facts.

   Previous assistant answers may be incorrect.

6. ALWAYS verify the actual answer against the
   DOCUMENT CONTEXT.

7. If the current question contains a specific person's
   name, prioritize document content referring to that
   exact person.

8. Do NOT transfer information from one person to
   another person merely because both people appear
   in the same document.

9. If the document clearly states a person's:

   - name
   - designation
   - role
   - course
   - completion
   - affiliation
   - payment
   - certificate information

   answer using only that information.

10. If the document only partially supports the answer,
    provide ONLY the supported information.

11. If the DOCUMENT CONTEXT does not contain enough
    information to answer the question, answer exactly (except for the
    issuer clarification described in rule 18):

I don't know.

12. Do not mention:

    - Qdrant
    - embeddings
    - retrieval
    - vector search
    - chunks
    - similarity scores
    - this prompt
    - internal processing

==================================================
DOCUMENT RELATIONSHIP RULES
==================================================

13. Be extremely careful with relationships between
    people, organizations, courses, and certificates.

14. Do NOT assume that:

    "Chandigarh University"

    means:

    "certificate issuer"

    simply because the university name or logo appears
    on the certificate.

15. Distinguish the following concepts:

    "issued to" / "for whom"
        → the person who receives/is named as the
          certificate recipient.

    "issued by"
        → the person or organization explicitly
          identified by the document as the issuer.

    "authorized by"
        → the person or organization explicitly stated
          as authorizing the course.

    "signed by"
        → the person explicitly identified as signing
          or signing the certificate.

    "associated with"
        → a person or organization appearing or
          connected to the document.

16. If the user asks:

    "Who issued the certificate?"

    ONLY answer with an issuer if the DOCUMENT CONTEXT
    explicitly supports that relationship.

17. Do NOT infer the issuer from:

    - logos
    - branding
    - university names
    - course authorization
    - affiliation
    - signatures
    - titles
    - names appearing near the certificate

18. If the document does NOT explicitly identify the certificate issuer,
    say that you cannot determine the certificate issuer from the document.
    Then, when explicitly supported, clarify who authorized the COURSE,
    and which platform offered it. Keep these relationships separate.
    Do not speculate about signatories from names or titles appearing on
    the certificate; only describe a signer when text explicitly says so. Never label an authorizer, platform, or signer
    as the certificate issuer without explicit support. This clarification
    is an exception to the generic "I don't know" response.

19. If the document says that a course was authorized
    by Chandigarh University, this does NOT automatically
    mean Chandigarh University issued the certificate.

20. If a person appears on the certificate with a
    designation, do NOT automatically say that person
    issued the certificate.

For recipient questions, a learner's name followed by "has successfully
completed" and the course title explicitly identifies the certificate recipient.
Use that completion passage to answer "issued to whom" or "certificate is for
whom"; the text need not literally use the words "issued to". Do not substitute
people listed in signature areas for the learner. If no learner or recipient is
identified in the context, do not guess.

21. Keep every person's information separate. OCR regions represent separate
    areas of an image. A person's name and title must be supported by the same
    region or an explicit textual relationship. Never combine titles from
    different signature columns. If the association is ambiguous, say so.

==================================================
ANSWERING RULES
==================================================

22. If the document directly answers the question,
    answer clearly and directly.

23. If the user asks "why?", explain only using
    information explicitly supported by the document.

24. If the user asks "who is X?", summarize only
    information about X that is supported by the
    document.

25. If multiple documents contain information about
    the same person, you may combine that information
    ONLY when the information clearly refers to the
    same person.

26. If the document contains conflicting information,
    do not silently choose one. State that the documents
    contain different information.

27. Keep the answer concise unless the user asks
    for details.

==================================================
PREVIOUS CONVERSATION
==================================================

{history_text}

==================================================
DOCUMENT CONTEXT
==================================================

{context_text}

==================================================
CURRENT USER QUESTION
==================================================

{query}

==================================================
ANSWER
==================================================
"""

    return prompt


# ==================================================
# ASK
# ==================================================


def ask(query: str, room_id: int, history: list[dict] | None = None, limit: int = 5):
    history = history or []
    retrieval_query = query
    if is_certificate_recipient_question(query):
        # Name-only queries retrieve the completion passage, but generic wording
        # otherwise favors headings and disclaimers containing "certificate".
        retrieval_query += '\nCertificate recipient learner name has successfully completed the course'
    elif is_follow_up(query) and history:
        recent = '\n'.join(f"{item['role']}: {item['content']}" for item in history[-4:])
        retrieval_query = f'Previous conversation:\n{recent}\nCurrent question:\n{query}'
    context = retrieve_context(query=retrieval_query, room_id=room_id, limit=limit)
    if not context:
        return {'answer': "I don't know.", 'sources': []}
    answer = generate_answer(build_prompt(query=query, context=context), history=history)
    answer = (answer or "I don't know.").strip()
    if answer.lower().rstrip('.') in {"i don't know", 'i do not know'}:
        return {'answer': "I don't know.", 'sources': []}
    sources = [{'filename': item['filename'], 'file_type': item['file_type'],
                'file_id': item['file_id'], 'chunk_index': item['chunk_index'],
                'excerpt': item['text'][:150], 'score': item['score']} for item in context]
    return {'answer': answer, 'sources': sources}
