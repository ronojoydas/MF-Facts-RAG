"""Semantic candidate retrieval with generic lexical and scheme-aware reranking."""

import re
from dataclasses import dataclass

from src.config import SUPPORTED_SCHEMES


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "the", "to", "what",
    "which", "with",
}
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
HEADING_RE = re.compile(
    r"(?im)^\s*(?:#+\s*(?:investment\s+objective|benchmark(?:\s+index)?|"
    r"minimum\s+application\s+amount|purchase|additional\s+purchase)\b|"
    r"(?:Investment\s+Objective|Minimum\s+Application\s+Amount)\s*$)"
)
PURCHASE_ROW_RE = re.compile(r"(?im)^\s*HDFC\b.*\b(?:Fund|FOF)\b.*\bPurchase\b")
FACT_FIELD_RE = re.compile(
    r"\b(?:benchmark|investment\s+objective|minimum\s+purchase|purchase\s+amount|"
    r"exit\s+load|riskometer|lock[- ]in|expense\s+ratio)\b",
    re.IGNORECASE,
)


def normalize(value):
    return " ".join(TOKEN_RE.findall(value.casefold()))


def detect_scheme(question):
    """Return the longest supported scheme name found in the user question."""
    question_norm = normalize(question)
    aliases = []
    for scheme in SUPPORTED_SCHEMES:
        aliases.append((normalize(scheme), scheme))
        # Permit punctuation variants such as "ELSS - Tax Saver".
        aliases.append((normalize(scheme.replace("ELSS Tax Saver", "ELSS - Tax Saver")), scheme))
    for alias, canonical in sorted(set(aliases), key=lambda pair: len(pair[0]), reverse=True):
        if alias and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", question_norm):
            # Use the metadata spelling used by the source corpus.
            return canonical.replace("HDFC ELSS Tax Saver Fund", "HDFC ELSS - Tax Saver Fund")
    return None


def _fact_tokens(question, scheme):
    tokens = [t for t in TOKEN_RE.findall(question.casefold()) if t not in STOP_WORDS]
    if scheme:
        scheme_tokens = set(TOKEN_RE.findall(scheme.casefold()))
        tokens = [token for token in tokens if token not in scheme_tokens]
    return set(tokens)


def _lexical_components(question, scheme, document):
    wanted = _fact_tokens(question, scheme)
    doc_tokens = set(TOKEN_RE.findall(document.casefold()))
    overlap = len(wanted & doc_tokens) / len(wanted) if wanted else 0.0

    normalized_question = normalize(question)
    normalized_doc = normalize(document)
    # Phrase checks use the query after removing its detected scheme name.
    fact_phrase = normalized_question
    if scheme:
        fact_phrase = normalize(re.sub(re.escape(scheme), " ", question, flags=re.IGNORECASE))
    phrase_tokens = [t for t in fact_phrase.split() if t not in STOP_WORDS]
    phrase = " ".join(phrase_tokens)
    phrase_match = bool(len(phrase_tokens) > 1 and phrase in normalized_doc)

    question_words = set(phrase_tokens)
    heading_match = False
    for match in HEADING_RE.finditer(document):
        heading = set(TOKEN_RE.findall(match.group(0).casefold()))
        if heading and question_words & heading:
            heading_match = True
            break

    normalized_scheme = normalize(scheme) if scheme else ""
    body = re.sub(r"(?im)^\s*Scheme:\s*[^\n]+\n?", "", document)
    scheme_match = bool(normalized_scheme and normalized_scheme in normalize(body))
    conflicting_purchase_row = bool(scheme and PURCHASE_ROW_RE.search(document) and not scheme_match)
    return (
        overlap,
        float(phrase_match),
        float(heading_match),
        float(scheme_match),
        float(conflicting_purchase_row),
    )


@dataclass
class RankedResult:
    chunk_id: str
    scheme: str
    source_id: str
    source_url: str
    document: str
    distance: float
    score: float
    components: dict


def rerank(question, results):
    """Rerank Chroma query results; no fact values or answers are embedded here."""
    requested_scheme = detect_scheme(question)
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ranked = []
    for i, chunk_id in enumerate(ids):
        document = documents[i] or ""
        metadata = metadatas[i] or {}
        distance = float(distances[i]) if i < len(distances) and distances[i] is not None else 1.0
        semantic = max(0.0, 1.0 - distance)
        overlap, phrase, heading, body_scheme_match, conflicting_purchase_row = _lexical_components(
            question, requested_scheme, document
        )
        metadata_scheme_match = bool(
            requested_scheme
            and normalize(metadata.get("scheme", "")) == normalize(requested_scheme)
        )
        # Semantic similarity remains a signal; query terms and section labels
        # promote candidates that contain the requested kind of fact.
        score = (
            0.20 * semantic
            + 0.43 * overlap
            + 0.12 * phrase
            + 0.20 * heading
            + 0.05 * float(body_scheme_match)
            - 0.30 * conflicting_purchase_row
        )
        ranked.append(RankedResult(
            chunk_id=chunk_id,
            scheme=metadata.get("scheme", ""),
            source_id=metadata.get("source_id", ""),
            source_url=metadata.get("source_url", ""),
            document=document,
            distance=distance,
            score=score,
            components={
                "semantic": semantic,
                "token_overlap": overlap,
                "phrase_match": phrase,
                "section_heading": heading,
                "requested_scheme_in_content": body_scheme_match,
                "conflicting_table_row": conflicting_purchase_row,
            },
        ))
    ranked.sort(key=lambda result: result.score, reverse=True)
    return ranked


def retrieve(question, model, collection, candidate_k=8, top_k=3):
    embedding = model.encode(
        question, convert_to_numpy=True, normalize_embeddings=True
    )
    requested_scheme = detect_scheme(question)
    # Exact fact-heading chunks can sit below table-heavy semantic matches.
    # Broaden only factual-field queries so the heading signal can rerank them.
    if FACT_FIELD_RE.search(question):
        candidate_k = max(candidate_k, 64)
    query_args = {}
    if requested_scheme:
        # Chroma applies the metadata filter before vector ranking. This keeps
        # the semantic candidate pool focused when a supported fund is named.
        query_args["where"] = {"scheme": requested_scheme}
    semantic_candidates = collection.query(
        query_embeddings=[embedding.tolist()],
        n_results=min(candidate_k, collection.count()),
        include=["documents", "metadatas", "distances"],
        **query_args,
    )
    return semantic_candidates, rerank(question, semantic_candidates)[:top_k]
