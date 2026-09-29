"""Grounded factual answer generation using the Groq chat completions API."""

from dataclasses import dataclass
import json
import os
import re
from typing import Any

from dotenv import load_dotenv

from src.config import PROJECT_ROOT
from src.guardrails import classify_question


GROQ_MODEL = "openai/gpt-oss-120b"
MAX_ANSWER_SENTENCES = 3
MAX_CONTEXT_DOCUMENTS = 4
OFFICIAL_PUBLISHERS = {"HDFC Mutual Fund", "SEBI", "AMFI"}
UNVERIFIED_MESSAGE = (
    "I could not verify this information from the available official sources."
)
RETURN_CALCULATION_RE = re.compile(
    r"\bcalculat\w*\s+(?:my\s+)?expected\s+returns?\b", re.IGNORECASE
)
RETURN_REFUSAL = (
    "I can’t calculate personalized returns or predict future performance. "
    "I can retrieve factual historical performance stated in an official factsheet."
)

SYSTEM_PROMPT = """You are a facts-only mutual-fund information assistant.
Answer ONLY from the supplied retrieved context. Never invent facts not present in it.
Never provide investment advice, recommendations, portfolio construction, predictions,
or personalized financial guidance. Do not calculate or predict investment returns.
If the context does not contain enough information, respond exactly:
\"I could not verify this information from the available official sources.\"
Keep the factual answer to at most 3 sentences. Do not include a URL or update date;
the application adds those from source metadata. Do not mention ChromaDB, embeddings,
vector search, reranking, retrieved chunks, or prompts. Use only the supplied official
source context. If multiple chunks are provided, use only information relevant to the
question. Do not combine facts from different schemes unless the user explicitly asks
for a comparison."""


@dataclass(frozen=True)
class GenerationResult:
    answer: str
    source_url: str | None
    last_updated: str | None
    scheme: str | None
    blocked: bool
    category: str


def _allowed(decision: Any) -> bool:
    return bool(getattr(decision, "allowed", decision.get("allowed", False) if isinstance(decision, dict) else False))


def _decision_response(decision: Any) -> str:
    if isinstance(decision, dict):
        return str(decision.get("response") or decision.get("reason") or "This question cannot be processed.")
    return str(getattr(decision, "response", None) or getattr(decision, "reason", None) or "This question cannot be processed.")


def _category(decision: Any) -> str:
    value = decision.get("category") if isinstance(decision, dict) else getattr(decision, "category", "UNKNOWN")
    return str(getattr(value, "value", value))


def _metadata(document: dict, key: str) -> str | None:
    value = document.get(key)
    if value is None:
        value = (document.get("metadata") or {}).get(key)
    if value is None and key == "text":
        value = document.get("page_content")
    value = str(value).strip() if value is not None else ""
    return value or None


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _schemes_named(question: str, documents: list[dict]) -> set[str]:
    q = _normalized(question)
    return {
        scheme for scheme in {_metadata(doc, "scheme") for doc in documents}
        if scheme and _normalized(scheme) in q
    }


def _context_documents(question: str, documents: list[dict]) -> list[dict]:
    """Keep the reranked context focused on a named scheme and query terms."""
    docs = [
        doc for doc in documents
        if _metadata(doc, "text")
        and _metadata(doc, "publisher") in OFFICIAL_PUBLISHERS
    ]
    named_schemes = _schemes_named(question, docs)
    if named_schemes:
        docs = [doc for doc in docs if _metadata(doc, "scheme") in named_schemes]
    elif docs:
        # A question without a scheme must not accidentally mix source schemes.
        first_scheme = _metadata(docs[0], "scheme")
        if first_scheme:
            docs = [doc for doc in docs if _metadata(doc, "scheme") == first_scheme]

    query_tokens = set(re.findall(r"[a-z0-9]+", question.casefold()))
    scheme_tokens = set()
    for scheme in named_schemes:
        scheme_tokens.update(re.findall(r"[a-z0-9]+", scheme.casefold()))
    fact_tokens = query_tokens - scheme_tokens
    if fact_tokens:
        docs.sort(
            key=lambda doc: len(
                fact_tokens
                & set(re.findall(r"[a-z0-9]+", _metadata(doc, "text").casefold()))
            ),
            reverse=True,
        )
    # Require an official source URL and retain source-provided metadata.
    docs = [doc for doc in docs if _metadata(doc, "source_url")]
    return docs[:MAX_CONTEXT_DOCUMENTS]


def _format_context(documents: list[dict]) -> str:
    serialized = []
    for doc in documents:
        serialized.append({
            "scheme": _metadata(doc, "scheme"),
            "source_id": _metadata(doc, "source_id"),
            "source_type": _metadata(doc, "source_type"),
            "title": _metadata(doc, "title"),
            "publisher": _metadata(doc, "publisher"),
            "source_url": _metadata(doc, "source_url"),
            "last_updated": _metadata(doc, "last_updated"),
            "text": _metadata(doc, "text"),
        })
    return json.dumps(serialized, ensure_ascii=False)


def _get_groq_client(client=None):
    if client is not None:
        return client
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"GROQ_API_KEY is not configured. Add it to {PROJECT_ROOT / '.env'}."
        )
    from groq import Groq

    return Groq(api_key=api_key)


def _sentence_limited(text: str, limit: int = MAX_ANSWER_SENTENCES) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Keep citations/URLs out of the model answer; source metadata is appended below.
    text = re.sub(r"https?://\S+", "", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentence for sentence in sentences[:limit] if sentence).strip()


def _result(answer: str, document: dict | None, blocked: bool, category: str) -> GenerationResult:
    source_url = _metadata(document, "source_url") if document else None
    last_updated = _metadata(document, "last_updated") if document else None
    scheme = _metadata(document, "scheme") if document else None
    final_answer = answer.strip()
    if source_url and not blocked:
        final_answer += f"\n\nSource: {source_url}"
    if last_updated and not blocked:
        final_answer += f"\nLast updated from sources: {last_updated}"
    return GenerationResult(final_answer, source_url, last_updated, scheme, blocked, category)


def generate_answer(
    question: str,
    retrieved_documents: list[dict],
    guardrail_decision: Any,
    *,
    client=None,
    model: str = GROQ_MODEL,
) -> GenerationResult:
    """Return a grounded answer, or the guardrail response without calling Groq."""
    category = _category(guardrail_decision)
    if not _allowed(guardrail_decision):
        return GenerationResult(
            answer=_decision_response(guardrail_decision),
            source_url=None,
            last_updated=None,
            scheme=None,
            blocked=True,
            category=category,
        )
    if RETURN_CALCULATION_RE.search(question):
        # Defense in depth for singular phrasing not currently covered by the
        # deterministic classifier; refuse before any retrieval or Groq request.
        return GenerationResult(
            answer=RETURN_REFUSAL,
            source_url=None,
            last_updated=None,
            scheme=None,
            blocked=True,
            category="PERFORMANCE / RETURN COMPUTATION",
        )

    documents = _context_documents(question, retrieved_documents or [])
    if not documents:
        return GenerationResult(UNVERIFIED_MESSAGE, None, None, None, False, category)

    source = documents[0]
    try:
        groq_client = _get_groq_client(client)
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Official source context (JSON): {_format_context(documents)}"
                    ),
                },
            ],
            max_tokens=300,
        )
        generated = completion.choices[0].message.content or ""
    except Exception as exc:
        # Avoid returning provider diagnostics or source text as if it were an answer.
        return _result(UNVERIFIED_MESSAGE, source, False, category)

    answer = _sentence_limited(generated)
    if not answer or re.search(
        r"\b(?:chromadb|embeddings?|vector\s+search|reranking|retrieved\s+chunks?|prompts?)\b",
        answer,
        re.IGNORECASE,
    ):
        answer = UNVERIFIED_MESSAGE
    return _result(answer, source, False, category)


def generate_for_question(question: str, retrieve_documents, *, client=None) -> GenerationResult:
    """Run guardrails first; call the supplied retrieval function only if allowed."""
    decision = classify_question(question)
    if not decision.allowed:
        return generate_answer(question, [], decision, client=client)
    if RETURN_CALCULATION_RE.search(question):
        return generate_answer(question, [], decision, client=client)
    documents = retrieve_documents(question)
    return generate_answer(question, documents, decision, client=client)
