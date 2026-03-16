from services.embedding_service import embed_text, _get_s3v, VECTOR_BUCKET_NAME, VECTOR_INDEX_NAME
from services.bedrock_service import bedrock, MODEL_ID
from services.dynamo_service import get_material
from services.material_service import get_presigned_url


def retrieve_chunks(
    user_id: str,
    query_embedding: list[float],
    week_number: int | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Query S3 Vectors for top-K chunks filtered by user_id (and optionally week_number).
    Returns list of vector dicts: [{"key": ..., "metadata": {...}}, ...]
    """
    s3v = _get_s3v()
    if week_number is not None:
        filter_expr = {"$and": [
            {"user_id": {"$eq": user_id}},
            {"week_number": {"$eq": week_number}},
        ]}
    else:
        filter_expr = {"user_id": {"$eq": user_id}}
    response = s3v.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        topK=top_k,
        queryVector={"float32": query_embedding},
        filter=filter_expr,
        returnMetadata=True,   # requires s3vectors:GetVectors in IAM
        returnDistance=False,
    )
    return response.get("vectors", [])


def build_citations(chunk_vectors: list[dict], user_id: str) -> list[dict]:
    """Deduplicate chunks by material_id, fetch filename and presigned URL per unique material."""
    seen: dict[str, dict] = {}
    for v in chunk_vectors:
        meta = v.get("metadata", {})
        mid = meta.get("material_id")
        if mid and mid not in seen:
            item = get_material(mid, user_id)
            if item:
                url = get_presigned_url(mid, user_id)
                seen[mid] = {
                    "material_id": mid,
                    "filename": item.get("filename", mid),
                    "week_number": meta.get("week_number"),
                    "url": url,
                }
    return list(seen.values())


def generate_answer(
    question: str,
    context_chunks: list[dict],
    history: list[dict],  # [{"role": "user"|"assistant", "content": str}, ...]
) -> str:
    """Build messages list and call Bedrock converse. Returns answer text string."""
    TUTOR_SYSTEM_PROMPT = (
        "You are a helpful study assistant for a university course. "
        "Answer questions clearly and concisely using only the course material provided in the context. "
        "Use course terminology from the materials. Do not add filler or generic advice. "
        "Stay grounded in the retrieved content."
    )

    # Build context block from retrieved chunk source_text fields
    context_lines = []
    for chunk in context_chunks:
        meta = chunk.get("metadata", {})
        context_lines.append(
            f"[Source: {meta.get('material_id', '?')}, Week {meta.get('week_number', '?')}]\n"
            f"{meta.get('source_text', '')}"
        )
    context_block = "\n\n---\n\n".join(context_lines)

    # Normalize history: ensure it starts with user role and strictly alternates.
    # Take last 10 messages (5 turns). If first message is assistant, drop it.
    normalized = [m for m in history[-10:]]
    if normalized and normalized[0]["role"] == "assistant":
        normalized = normalized[1:]
    # Ensure strict alternation: remove consecutive same-role messages
    clean_history = []
    for m in normalized:
        if clean_history and clean_history[-1]["role"] == m["role"]:
            clean_history[-1] = m  # keep the later one of consecutive same-role
        else:
            clean_history.append(m)

    messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in clean_history
    ]
    messages.append({
        "role": "user",
        "content": [{"text": f"Context from course materials:\n{context_block}\n\nQuestion: {question}"}],
    })

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": TUTOR_SYSTEM_PROMPT}],
        messages=messages,
    )
    return response["output"]["message"]["content"][0]["text"]


def ask(
    question: str,
    user_id: str,
    history: list[dict],
    week_number: int | None = None,
) -> dict:
    """Full RAG pipeline. Returns {"answer": str, "citations": list[dict]}.
    Short-circuits before calling Bedrock if no chunks are found.
    """
    query_embedding = embed_text(question)
    chunks = retrieve_chunks(user_id, query_embedding, week_number=week_number)

    if not chunks:
        return {
            "answer": (
                "I couldn't find relevant content in your materials for this question. "
                "Make sure your materials have finished processing (check the Library tab)."
            ),
            "citations": [],
        }

    answer = generate_answer(question, chunks, history)
    citations = build_citations(chunks, user_id)
    return {"answer": answer, "citations": citations}
