"""Small Streamlit chat UI for the facts-only mutual-fund assistant."""

import os

import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.config import (
    EMBEDDING_MODEL_NAME,
    PROJECT_ROOT,
)
from src.generation import UNVERIFIED_MESSAGE, generate_answer
from src.guardrails import classify_question
from src.retrieval.embed_and_store import get_or_build_collection
from src.retrieval.rerank import retrieve


EXAMPLE_QUESTIONS = (
    "What is the benchmark of HDFC ELSS - Tax Saver Fund?",
    "What is the investment objective of HDFC Large Cap Fund?",
    "What is the minimum purchase amount for HDFC ELSS - Tax Saver Fund?",
)

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

# Streamlit Community Cloud exposes configured values through st.secrets.
# Preserve an existing local environment/.env value if both are configured.
try:
    _groq_secret = st.secrets.get("GROQ_API_KEY")
except Exception:
    _groq_secret = None
if _groq_secret and not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = str(_groq_secret)


@st.cache_resource(show_spinner="Loading the local facts index…")
def load_retrieval_resources():
    # Downloads and caches the model on first use in a fresh deployment.
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    collection = get_or_build_collection(model=model)
    return model, collection


def retrieve_documents(question):
    model, collection = load_retrieval_resources()
    _, ranked = retrieve(question, model, collection, candidate_k=32, top_k=3)
    if not ranked:
        return []

    stored = collection.get(ids=[item.chunk_id for item in ranked], include=["metadatas"])
    metadata_by_id = dict(zip(stored["ids"], stored["metadatas"]))
    documents = []
    for item in ranked:
        metadata = metadata_by_id.get(item.chunk_id, {})
        documents.append({
            "scheme": item.scheme,
            "source_id": item.source_id,
            "source_url": item.source_url,
            "publisher": metadata.get("publisher"),
            "last_updated": metadata.get("last_updated"),
            "text": item.document,
        })
    return documents


def process_question(question):
    """Use the existing backend in order; guardrails run before retrieval."""
    decision = classify_question(question)
    if not decision.allowed:
        return generate_answer(question, [], decision)

    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError("Groq API key is missing. Configure GROQ_API_KEY in the project .env file.")

    documents = retrieve_documents(question)
    return generate_answer(question, documents, decision)


def render_answer(result):
    answer = result.answer
    if result.source_url and "\n\nSource:" in answer:
        answer = answer.split("\n\nSource:", 1)[0]
    if result.last_updated and "\nLast updated from sources:" in answer:
        answer = answer.split("\nLast updated from sources:", 1)[0]

    if not result.blocked and result.answer.startswith(UNVERIFIED_MESSAGE):
        st.info(UNVERIFIED_MESSAGE)
    else:
        st.markdown(answer)
    if result.source_url:
        st.markdown(f"[Source]({result.source_url})")
    if result.last_updated:
        st.caption(f"Last updated from sources: {result.last_updated}")


def main():
    st.set_page_config(page_title="Facts-Only MF Assistant", page_icon="📄", layout="centered")
    st.title("Facts-Only MF Assistant")
    st.write(
        "This assistant answers factual questions about selected HDFC Mutual Fund schemes using official sources."
    )
    st.info("Facts-only. No investment advice.")

    st.markdown("**Example questions**")
    button_cols = st.columns(3)
    selected_example = None
    for index, question in enumerate(EXAMPLE_QUESTIONS):
        if button_cols[index].button(question, key=f"example_{index}", use_container_width=True):
            selected_example = question

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("source_url"):
                st.markdown(message["answer"])
                st.markdown(f"[Source]({message['source_url']})")
                if message.get("last_updated"):
                    st.caption(f"Last updated from sources: {message['last_updated']}")
            else:
                st.markdown(message["answer"])

    typed_question = st.chat_input("Ask a factual question about a supported HDFC scheme")
    question = selected_example or typed_question
    if not question:
        return

    st.session_state.messages.append({"role": "user", "answer": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Checking official scheme information…"):
                result = process_question(question)
            render_answer(result)
            st.session_state.messages.append({
                "role": "assistant",
                "answer": result.answer.split("\n\nSource:", 1)[0],
                "source_url": result.source_url,
                "last_updated": result.last_updated,
                "blocked": result.blocked,
            })
        except RuntimeError as error:
            message = str(error)
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "answer": message})
        except Exception:
            # Keep provider and local-service diagnostics out of the user-facing UI.
            message = "I couldn’t complete that request right now. Please try again shortly."
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "answer": message})


if __name__ == "__main__":
    main()
