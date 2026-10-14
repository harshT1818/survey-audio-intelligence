from src.evidence_quality.corroboration import (
    corroborate_answer_evidence,
)
from src.evidence_quality.corroboration_models import (
    CorroborationTurn,
)
from src.resolver.models import (
    CanonicalOption,
)


def show(
    name,
    result,
):
    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    print(
        f"Resolved:       "
        f"{result.resolved_option}"
    )

    print(
        f"Stored:         "
        f"{result.stored_option}"
    )

    print(
        f"Resolution:     "
        f"{result.resolution_status}"
    )

    print(
        f"Strength:       "
        f"{result.evidence_strength}"
    )

    print(
        f"Automation:     "
        f"{result.automation_status}"
    )

    print(
        f"Direct support: "
        f"{result.direct_support_turn_ids}"
    )

    print(
        f"Context support:"
        f" {result.contextual_support_turn_ids}"
    )

    print(
        f"Unsafe turns:   "
        f"{result.unsafe_turn_ids}"
    )

    print(
        f"Conflicts:      "
        f"{result.conflicting_turn_ids}"
    )

    print(
        f"Review:         "
        f"{result.review_required}"
    )

    for reason in result.reasons:
        print(
            f"Reason:         {reason}"
        )


def main():
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

    yes_no_options = [
        CanonicalOption(
            value="Yes",
            labels=["हाँ"],
        ),
        CanonicalOption(
            value="No",
            labels=["नहीं"],
        ),
    ]

    bijnor = (
        corroborate_answer_evidence(
            turns=[
                CorroborationTurn(
                    turn_id="segment_015",
                    role="respondent",
                    text="नहीं बिजनेस",
                ),
                CorroborationTurn(
                    turn_id="segment_016",
                    role="agent",
                    text="बिजनौर",
                ),
                CorroborationTurn(
                    turn_id="segment_017",
                    role="respondent",
                    text="हाँ बिजनौर",
                ),
            ],
            options=ac_options,
            stored_option="Badlapur",
        )
    )

    inflation = (
        corroborate_answer_evidence(
            turns=[
                CorroborationTurn(
                    turn_id="segment_019_part_03",
                    role="respondent",
                    text="महनाई",
                ),
                CorroborationTurn(
                    turn_id="segment_020",
                    role="unknown",
                    text="महंगाई कितने बजे है आपके",
                    upstream_review_required=True,
                ),
                CorroborationTurn(
                    turn_id="segment_021",
                    role="unknown",
                    text="कितने बजे है आपके",
                    upstream_review_required=True,
                ),
            ],
            options=problem_options,
            stored_option="Inflation",
        )
    )

    clear_prompting = (
        corroborate_answer_evidence(
            turns=[
                CorroborationTurn(
                    turn_id="segment_006",
                    role="respondent",
                    text="मुझे पता नहीं",
                ),
                CorroborationTurn(
                    turn_id="segment_007",
                    role="agent",
                    text="हाँ बोल दीजिए",
                ),
                CorroborationTurn(
                    turn_id="segment_008",
                    role="respondent",
                    text="हाँ",
                ),
            ],
            options=yes_no_options,
            stored_option="Yes",
        )
    )

    garbage = (
        corroborate_answer_evidence(
            turns=[
                CorroborationTurn(
                    turn_id="segment_020",
                    role="unknown",
                    text="कितने बजे है आपके",
                    upstream_review_required=True,
                ),
                CorroborationTurn(
                    turn_id="segment_023",
                    role="unknown",
                    text="इतनी अगर",
                    upstream_review_required=True,
                ),
            ],
            options=problem_options,
            stored_option="Inflation",
        )
    )

    show(
        "Bijnor correction exchange",
        bijnor,
    )

    show(
        "Inflation + third-speaker region",
        inflation,
    )

    show(
        "Prompted Yes answer evidence",
        clear_prompting,
    )

    show(
        "Only corrupted evidence",
        garbage,
    )


if __name__ == "__main__":
    main()