"""End-to-end generation checks; uses Groq when configured, otherwise a test double."""

import json
import os
import re
import sys
from types import SimpleNamespace

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL_NAME,
    PROJECT_ROOT,
)
from src.generation import GROQ_MODEL, generate_answer, generate_for_question
from src.guardrails import classify_question
from src.retrieval.rerank import retrieve


FACTUAL_QUESTIONS = [
    "What is the minimum purchase amount for HDFC ELSS - Tax Saver Fund?",
    "What is the benchmark of HDFC ELSS - Tax Saver Fund?",
    "What is the investment objective of HDFC Large Cap Fund?",
    "What is the investment objective of HDFC Small Cap Fund?",
    "What is the investment objective of HDFC Balanced Advantage Fund?",
    "What is the investment objective of HDFC Flexi Cap Fund?",
]
BLOCKED_QUESTIONS = [
    "Which HDFC fund should I invest in?",
    "Which fund will give me the highest return?",
    "Calculate my expected return.",
]
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "i",
    "in", "is", "it", "of", "on", "or", "the", "to", "what", "with",
}


class FakeGroqClient:
    """Extractive test double; its output is copied only from supplied context."""

    def __init__(self):
        self.calls = 0
        self.contexts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, *, messages, **kwargs):
        self.calls += 1
        user_content = messages[-1]["content"]
        context_text = user_content.split("Official source context (JSON): ", 1)[1]
        docs = json.loads(context_text)
        self.contexts.append(docs)
        extracted = docs[0]["text"]
        # Keep the test output concise while retaining verbatim sourced words.
        extracted = re.sub(r"\s+", " ", extracted).strip()
        answer = extracted[:450]
        message = SimpleNamespace(content=answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _answer_body(result):
    return result.answer.split("\n\nSource:", 1)[0]


def _sentence_count(text):
    return len([part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part])


def _grounded(body, contexts):
    answer_tokens = {
        token for token in re.findall(r"[a-z0-9]+", body.casefold())
        if token not in STOP_WORDS
    }
    source_tokens = set()
    for doc in contexts:
        source_tokens.update(re.findall(r"[a-z0-9]+", doc["text"].casefold()))
    return bool(answer_tokens) and len(answer_tokens & source_tokens) / len(answer_tokens) >= 0.8


def _retrieved_documents(model, collection, question):
    _, ranked = retrieve(question, model, collection, candidate_k=32, top_k=3)
    stored = collection.get(
        ids=[item.chunk_id for item in ranked], include=["metadatas"]
    )
    metadata_by_id = dict(zip(stored["ids"], stored["metadatas"]))
    return [
        {
            "scheme": item.scheme,
            "source_id": item.source_id,
            "source_url": item.source_url,
            "publisher": metadata_by_id[item.chunk_id].get("publisher"),
            "last_updated": metadata_by_id[item.chunk_id].get("last_updated"),
            "text": item.document,
        }
        for item in ranked
    ]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    live_groq = bool(os.getenv("GROQ_API_KEY", "").strip())
    fake_client = FakeGroqClient()
    print(f"Groq model: {GROQ_MODEL}")
    print(f"Live Groq API configured: {live_groq}")
    if not live_groq:
        print("WARNING: .env/GROQ_API_KEY is unavailable; factual generation uses an extractive test double.\n")

    client = None if live_groq else fake_client
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    collection = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR)).get_collection(
        CHROMA_COLLECTION_NAME
    )

    failures = []
    factual_results = []
    for question in FACTUAL_QUESTIONS:
        decision = classify_question(question)
        docs = _retrieved_documents(model, collection, question) if decision.allowed else []
        result = generate_answer(question, docs, decision, client=client, model=GROQ_MODEL)
        body = _answer_body(result)
        if not result.blocked:
            contexts = fake_client.contexts[-1] if not live_groq else [
                {"text": doc["text"]} for doc in docs
            ]
            checks = {
                "<=3 answer sentences": _sentence_count(body) <= 3,
                "source URL present": bool(result.source_url and result.source_url in result.answer),
                "update date present when available": (
                    not result.last_updated
                    or "Last updated from sources:" in result.answer
                ),
                "grounded token coverage": _grounded(body, contexts),
            }
            failed = [name for name, passed in checks.items() if not passed]
            if failed:
                failures.append((question, failed))
            factual_results.append((question, result, checks))
        else:
            failures.append((question, ["factual question unexpectedly blocked"]))

    print("FACTUAL TESTS")
    for question, result, checks in factual_results:
        print(f"\nQUESTION: {question}\nCATEGORY: {result.category}\nBLOCKED: {result.blocked}")
        print(f"ANSWER: {result.answer}")
        print("CHECKS:", checks)

    print("\nBLOCKED TESTS")
    for question in BLOCKED_QUESTIONS:
        calls_before = fake_client.calls
        retrieval_calls = []

        def should_not_retrieve(unused_question):
            retrieval_calls.append(unused_question)
            raise AssertionError("Blocked question reached retrieval")

        result = generate_for_question(question, should_not_retrieve, client=fake_client)
        no_model_call = fake_client.calls == calls_before
        no_retrieval = not retrieval_calls
        passed = result.blocked and no_model_call and no_retrieval
        print(
            f"\nQUESTION: {question}\nCATEGORY: {result.category}\nBLOCKED: {result.blocked}"
            f"\nGROQ NOT CALLED: {no_model_call}\nRETRIEVAL NOT CALLED: {no_retrieval}"
            f"\nRESPONSE: {result.answer}"
        )
        if not passed:
            failures.append((question, ["blocked request reached retrieval/Groq or was allowed"]))

    print(f"\nFactual tests: {len(FACTUAL_QUESTIONS)}")
    print(f"Blocked tests: {len(BLOCKED_QUESTIONS)}")
    print(f"Failures: {len(failures)}")
    if failures:
        for question, issues in failures:
            print(f"FAIL: {question}: {', '.join(issues)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
