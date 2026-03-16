import json

from services.embedding_service import embed_text
from services.tutor_service import retrieve_chunks
from services.bedrock_service import bedrock, MODEL_ID
from services.dynamo_service import get_material
from services.material_service import get_presigned_url

QUIZ_SYSTEM_PROMPT = (
    "You are a quiz generator for university courses. Generate quiz questions based ONLY on the provided course material context.\n"
    "Respond with ONLY a valid JSON array. No explanation. No markdown code fences. No text before or after the array.\n"
    "Each element must have exactly these keys: \"question\" (string), \"choices\" (array of 4 strings, each prefixed \"A. \", \"B. \", \"C. \", \"D. \"), "
    "\"correct_index\" (integer 0-3), \"explanation\" (string, 1-2 sentences citing the source), "
    "\"material_id\" (string — copy EXACTLY from the [material_id: ...] tag in the source chunk this question is based on)."
)


def _build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a labeled context block for Bedrock."""
    parts = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        parts.append(
            f"[material_id: {meta.get('material_id', '?')}]\n"
            f"Week {meta.get('week_number', '?')}\n"
            f"{meta.get('source_text', '')}"
        )
    return "\n\n---\n\n".join(parts)


def _attach_citations(questions_raw: list[dict], user_id: str) -> list[dict]:
    """Attach per-question citation dicts, using a cache to avoid repeated DynamoDB lookups."""
    url_cache: dict[str, dict] = {}
    for q in questions_raw:
        mid = q.get("material_id")
        if not mid:
            q["citation"] = None
            continue
        if mid not in url_cache:
            item = get_material(mid, user_id)
            if item:
                url = get_presigned_url(mid, user_id)
                url_cache[mid] = {
                    "filename": item.get("filename", mid),
                    "week_number": item.get("week_number"),
                    "url": url,
                }
            else:
                url_cache[mid] = None  # type: ignore[assignment]
        q["citation"] = url_cache[mid]
    return questions_raw


def generate_quiz(user_id: str, week_number: int | None, count: int) -> dict:
    """Full quiz generation pipeline.

    Returns {"questions": [QuestionDict, ...]} where each QuestionDict contains
    question, choices, correct_index, explanation, material_id, and citation.
    Returns {"questions": []} immediately if no chunks are found for the scope.
    """
    # Step 1 — embed generic query
    query_embedding = embed_text("key concepts, definitions, and important topics")

    # Step 2 — retrieve chunks
    top_k = min(count * 2, 20)
    chunks = retrieve_chunks(user_id, query_embedding, week_number=week_number, top_k=top_k)
    if not chunks:
        return {"questions": []}

    # Step 3 — build context block with material_id labels
    context_block = _build_context_block(chunks)

    # Step 4 — call Bedrock converse
    user_message = (
        f"Context from course materials:\n{context_block}\n\n"
        f"Generate exactly {count} multiple-choice quiz questions based on the content above. "
        f"Each question must be based on a specific chunk and reference its exact material_id."
    )
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": QUIZ_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
    )

    # Step 5 — parse JSON response, stripping markdown fences if present
    raw = response["output"]["message"]["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    try:
        questions_raw = json.loads(raw)
        if not isinstance(questions_raw, list):
            raise ValueError("Bedrock did not return a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError("Quiz generation returned invalid JSON — please retry") from exc

    # Step 6 — attach per-question citations
    questions_with_citations = _attach_citations(questions_raw, user_id)

    return {"questions": questions_with_citations}
