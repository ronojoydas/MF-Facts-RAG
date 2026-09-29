"""Table-driven smoke tests for deterministic pre-retrieval guardrails."""

import sys

from src.guardrails import Category, classify_question


TEST_CASES = [
    ("What is the expense ratio of HDFC Large Cap Fund?", Category.FACTUAL),
    ("What is the exit load for HDFC Flexi Cap Fund?", Category.FACTUAL),
    ("What is the minimum SIP for HDFC ELSS - Tax Saver Fund?", Category.FACTUAL),
    ("What is the minimum purchase amount for HDFC Small Cap Fund?", Category.FACTUAL),
    ("What is the ELSS lock-in for HDFC ELSS - Tax Saver Fund?", Category.FACTUAL),
    ("What is the benchmark of HDFC Balanced Advantage Fund?", Category.FACTUAL),
    ("What is the riskometer for HDFC Flexi Cap Fund?", Category.FACTUAL),
    ("Who is the fund manager of HDFC Small Cap Fund?", Category.FACTUAL),
    ("What is the historical performance in the HDFC Large Cap Fund factsheet?", Category.FACTUAL),
    ("What was the historical performance of HDFC Small Cap Fund?", Category.FACTUAL),
    ("What 1-year return is shown in the official HDFC Small Cap Fund factsheet?", Category.FACTUAL),
    ("What performance does the August 2026 factsheet report?", Category.FACTUAL),
    ("Which fund should I invest in?", Category.INVESTMENT_ADVICE),
    ("Which is the best fund?", Category.INVESTMENT_ADVICE),
    ("Where should I invest ₹10,000?", Category.INVESTMENT_ADVICE),
    ("Should I buy HDFC Small Cap Fund?", Category.INVESTMENT_ADVICE),
    ("Build me a portfolio.", Category.INVESTMENT_ADVICE),
    ("Which fund will give me the highest return?", Category.INVESTMENT_ADVICE),
    ("My PAN is ABCDE1234F; what does my account show?", Category.PERSONAL_SENSITIVE_INFO),
    ("Can I share my Aadhaar number to check my fund?", Category.PERSONAL_SENSITIVE_INFO),
    ("I received an OTP for a transaction; can you verify it?", Category.PERSONAL_SENSITIVE_INFO),
    ("What is the status of my bank account number 123456789?", Category.PERSONAL_SENSITIVE_INFO),
    ("Calculate my return on HDFC Large Cap Fund.", Category.PERFORMANCE),
    ("Predict future returns for HDFC Flexi Cap Fund.", Category.PERFORMANCE),
    ("Which fund will perform better?", Category.PERFORMANCE),
    ("Calculate CAGR for my investment.", Category.PERFORMANCE),
    ("What return can I expect from HDFC Small Cap Fund?", Category.PERFORMANCE),
    ("How much return will I get from HDFC Small Cap Fund?", Category.PERFORMANCE),
    ("What return should I expect from this fund?", Category.PERFORMANCE),
    ("What will HDFC Small Cap Fund return next year?", Category.PERFORMANCE),
    ("Can HDFC Small Cap Fund give me 20% returns?", Category.PERFORMANCE),
    ("What is the expense ratio of Axis Bluechip Fund?", Category.UNSUPPORTED_SCHEME),
    ("Tell me about SBI Small Cap Fund.", Category.UNSUPPORTED_SCHEME),
    ("What is the weather in Mumbai?", Category.OUT_OF_SCOPE),
    ("Explain photosynthesis.", Category.OUT_OF_SCOPE),
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    failures = []
    for question, expected in TEST_CASES:
        result = classify_question(question)
        status = "ALLOWED" if result.allowed else "BLOCKED"
        print(f"QUESTION: {question}")
        print(f"CATEGORY: {result.category.value}")
        print(f"{status}")
        print(f"REASON: {result.reason}\n")
        if result.category != expected:
            failures.append((question, expected.value, result.category.value))

    print(f"Tests run: {len(TEST_CASES)}")
    print(f"Failures: {len(failures)}")
    for question, expected, actual in failures:
        print(f"FAIL: {question!r}; expected {expected}, got {actual}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
