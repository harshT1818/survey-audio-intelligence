from src.evidence_quality.gate import (
    evaluate_answer_evidence,
)
from src.resolver.models import (
    CanonicalOption,
)


def show(
    name,
    result,
):
    print()
    print("=" * 70)
    print(name)
    print("=" * 70)

    print(
        f"Raw:         {result.raw_text}"
    )

    print(
        f"Evidence:    "
        f"{result.evidence_status}"
    )

    print(
        f"Automation:  "
        f"{result.automation_status}"
    )

    print(
        f"Resolved:    "
        f"{result.resolved_option}"
    )

    print(
        f"Resolution:  "
        f"{result.resolution_status}"
    )

    print(
        f"Score:       "
        f"{result.resolution_score}"
    )

    print(
        f"Review:      "
        f"{result.review_required}"
    )

    for reason in result.reasons:
        print(
            f"Reason:      {reason}"
        )


def main():
    yes_no = [
        CanonicalOption(
            value="Yes",
            labels=["हाँ"],
        ),
        CanonicalOption(
            value="No",
            labels=["नहीं"],
        ),
    ]

    ac_options = [
        CanonicalOption(
            value="Badlapur",
            labels=["बदलापुर"],
        ),
        CanonicalOption(
            value="Bijnor",
            labels=["बिजनौर"],
        ),
    ]

    problem_options = [
        CanonicalOption(
            value="Inflation",
            labels=["महंगाई"],
        ),
        CanonicalOption(
            value="Unemployment",
            labels=["बेरोजगारी"],
        ),
    ]

    cases = [
        (
            "Clean respondent answer",
            evaluate_answer_evidence(
                raw_text="हाँ",
                options=yes_no,
                stored_option="Yes",
            ),
        ),
        (
            "Bad Bijnor ASR",
            evaluate_answer_evidence(
                raw_text="नहीं बिजनेस",
                options=ac_options,
                stored_option="Badlapur",
            ),
        ),
        (
            "Refined Bijnor",
            evaluate_answer_evidence(
                raw_text="बिजनौर",
                options=ac_options,
                stored_option="Badlapur",
            ),
        ),
        (
            "Minor inflation ASR error",
            evaluate_answer_evidence(
                raw_text="महनाई",
                options=problem_options,
                stored_option="Inflation",
            ),
        ),
        (
            "Third-speaker corruption",
            evaluate_answer_evidence(
                raw_text=(
                    "कितने बजे है आपके"
                ),
                options=problem_options,
                upstream_review_required=True,
            ),
        ),
        (
            "Mixed dialogue segment",
            evaluate_answer_evidence(
                raw_text=(
                    "छत्तीस साल ठीक है "
                    "आपके हिसाब से "
                    "सबसे बड़ी समस्या क्या है"
                ),
                options=[
                    CanonicalOption(
                        value="36",
                        labels=["छत्तीस साल"],
                    ),
                ],
                source_is_mixed=True,
            ),
        ),
    ]

    for name, result in cases:
        show(
            name,
            result,
        )


if __name__ == "__main__":
    main()