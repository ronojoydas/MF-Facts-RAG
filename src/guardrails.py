"""Deterministic scope and safety classification for the facts-only assistant."""

from dataclasses import dataclass
from enum import Enum
import re

from src.config import SUPPORTED_SCHEMES


class Category(str, Enum):
    FACTUAL = "FACTUAL"
    INVESTMENT_ADVICE = "INVESTMENT_ADVICE / RECOMMENDATION"
    PERSONAL_SENSITIVE_INFO = "PERSONAL / SENSITIVE INFORMATION"
    PERFORMANCE = "PERFORMANCE / RETURN COMPUTATION"
    UNSUPPORTED_SCHEME = "UNSUPPORTED SCHEME"
    OUT_OF_SCOPE = "GENERAL / NON-MUTUAL-FUND"
    UNCLEAR = "UNCLEAR / NEEDS CLARIFICATION"


@dataclass(frozen=True)
class GuardrailDecision:
    category: Category
    allowed: bool
    reason: str
    response: str | None = None


SUPPORTED_SCHEMES = tuple(SUPPORTED_SCHEMES)  # Re-exported for callers/tests.
FACTUAL_FIELD_RE = re.compile(
    r"\b(?:expense\s+ratio|exit\s+load|minimum\s+(?:sip|purchase|application)|"
    r"sip\s+amount|lock[- ]?in|benchmark|riskometer|investment\s+objective|"
    r"fund\s+manager|historical\s+performance|past\s+performance|past\s+returns?|"
    r"\d+[- ]year\s+return)\b",
    re.IGNORECASE,
)
MUTUAL_FUND_CONTEXT_RE = re.compile(
    r"\b(?:mutual\s+funds?|funds?|scheme|sip|elss|nav|amc|portfolio|"
    r"equity\s+fund|debt\s+fund|index\s+fund)\b",
    re.IGNORECASE,
)
SENSITIVE_RE = re.compile(
    r"\b(?:pan|aadhaar|aadhar|otp|one[- ]time\s+password|bank\s+account|"
    r"account\s+number|account\s+details|transaction\s+details|"
    r"my\s+(?:bank|investment|fund)\s+account)\b",
    re.IGNORECASE,
)
ADVICE_RE = re.compile(
    r"\b(?:should\s+i\s+(?:buy|invest|switch|sell)|which\s+(?:fund|scheme)\s+"
    r"(?:should\s+i|is\s+best|to\s+invest|will\s+give)|best\s+fund|"
    r"where\s+should\s+i\s+invest|recommend(?:ation)?|advise\s+me|"
    r"build\s+(?:me\s+)?(?:a\s+)?portfolio|create\s+(?:me\s+)?(?:a\s+)?portfolio|"
    r"suitable\s+for\s+me|right\s+fund\s+for\s+me)\b",
    re.IGNORECASE,
)
RETURN_COMPUTE_RE = re.compile(
    r"\b(?:calculat\w*\s+(?:my\s+)?(?:return|cagr|gain|profit)|"
    r"predict\w*\s+(?:the\s+)?(?:future\s+)?returns?|"
    r"(?:expected|future|projected)\s+returns?|"
    r"which\s+fund\s+will\s+perform\s+better|"
    r"cagr\s+for\s+my\s+investment|estimate\s+(?:my\s+)?returns?)\b",
    re.IGNORECASE,
)
EXPECTED_RETURN_RE = re.compile(
    r"(?:"
    r"\bwhat\s+(?:kind\s+of\s+)?returns?\b.*\b(?:can|could|should)\s+i\s+expect\b|"
    r"\bhow\s+much\s+returns?\b.*\bwill\s+i\s+get\b|"
    r"\bwhat\s+returns?\b.*\bshould\s+i\s+expect\b|"
    r"\bwhat\b.*\bwill\b.*\b(?:fund|scheme|it)\b.*\breturn\b|"
    r"\b(?:can|could)\b.*\b(?:fund|scheme)\b.*\bgive\b.*\breturns?\b|"
    r"\breturns?\b.*\b(?:can|could)\b.*\b(?:fund|scheme)\b.*\bgive\b|"
    r"\breturns?\s+(?:can|could|should)\s+i\s+expect\b|"
    r"\bexpected\s+returns?\b|\bfuture\s+returns?\b|\bnext\s+year\b.*\breturn\b"
    r")",
    re.IGNORECASE,
)
HISTORICAL_PERFORMANCE_RE = re.compile(
    r"\b(?:historical|past|previous|factsheet|fact\s+sheet|as\s+of\s+\d{4})\b.*"
    r"\b(?:performance|returns?|cagr)\b|"
    r"\b(?:performance|returns?|cagr)\b.*"
    r"\b(?:historical|past|previous|factsheet|fact\s+sheet|as\s+of\s+\d{4})\b",
    re.IGNORECASE,
)
SCHEME_NAME_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z&'.-]*(?:\s+[A-Z][A-Za-z&'.-]*){0,5}\s+"
    r"(?:Mutual\s+)?Fund|[A-Z][A-Za-z&'.-]*\s+ELSS)\b"
)

ADVICE_RESPONSE = (
    "I can provide factual information from official scheme documents, but I can’t "
    "recommend investments or build a portfolio. Please review the official factsheet "
    "and consult a SEBI-registered investment adviser for advice suited to you."
)
SENSITIVE_RESPONSE = (
    "Please don’t share PAN, Aadhaar, OTPs, bank details, or personal account/transaction "
    "information here. I can’t process or disclose personal financial information."
)
PERFORMANCE_RESPONSE = (
    "I can’t calculate personalized returns or predict future performance. I can retrieve "
    "factual historical performance stated in an official factsheet if you ask for a period."
)
UNSUPPORTED_RESPONSE = (
    "I currently support factual questions only about HDFC Large Cap Fund, HDFC Flexi Cap "
    "Fund, HDFC ELSS - Tax Saver Fund, HDFC Small Cap Fund, and HDFC Balanced Advantage Fund."
)
SCOPE_RESPONSE = "I can help with factual information about the five supported HDFC mutual fund schemes only."


def _supported_scheme_in(question: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip()
    for name in SUPPORTED_SCHEMES:
        alias = re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
        if alias and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
            return True
    # The configured canonical name omits punctuation; accept the factsheet spelling.
    if re.search(r"\bhdfc\s+elss\s+tax\s+saver\s+fund\b", normalized):
        return True
    return False


def classify_question(question: str) -> GuardrailDecision:
    """Classify a question before retrieval; never generates factual answers."""
    text = (question or "").strip()
    if not text:
        return GuardrailDecision(Category.UNCLEAR, False, "The question is empty.", SCOPE_RESPONSE)

    if SENSITIVE_RE.search(text):
        return GuardrailDecision(
            Category.PERSONAL_SENSITIVE_INFO, False,
            "The question contains a sensitive identifier or personal account detail.",
            SENSITIVE_RESPONSE,
        )

    if EXPECTED_RETURN_RE.search(text):
        return GuardrailDecision(
            Category.PERFORMANCE, False,
            "The question asks what return may be expected from a fund, which would require a prediction or personalized estimate.",
            PERFORMANCE_RESPONSE,
        )

    if ADVICE_RE.search(text):
        return GuardrailDecision(
            Category.INVESTMENT_ADVICE, False,
            "The question asks for a personalized recommendation, opinion, or portfolio decision.",
            ADVICE_RESPONSE,
        )

    if RETURN_COMPUTE_RE.search(text):
        return GuardrailDecision(
            Category.PERFORMANCE, False,
            "The question asks for a return calculation, comparison, estimate, or prediction.",
            PERFORMANCE_RESPONSE,
        )

    supported = _supported_scheme_in(text)
    named_funds = SCHEME_NAME_RE.findall(text)
    if named_funds and not supported:
        return GuardrailDecision(
            Category.UNSUPPORTED_SCHEME, False,
            "The named mutual fund scheme is outside the five supported schemes.",
            UNSUPPORTED_RESPONSE,
        )

    if supported or FACTUAL_FIELD_RE.search(text) or HISTORICAL_PERFORMANCE_RE.search(text):
        # Historical return questions are factual only when explicitly framed as
        # past/factsheet information and contain no computation/prediction cue.
        return GuardrailDecision(
            Category.FACTUAL, True,
            "The question requests factual scheme information and may proceed to retrieval.",
        )

    if MUTUAL_FUND_CONTEXT_RE.search(text):
        return GuardrailDecision(
            Category.UNSUPPORTED_SCHEME, False,
            "No supported HDFC scheme was identified in the mutual-fund question.",
            UNSUPPORTED_RESPONSE,
        )

    return GuardrailDecision(
        Category.OUT_OF_SCOPE, False,
        "The question is outside factual information about the supported mutual funds.",
        SCOPE_RESPONSE,
    )
