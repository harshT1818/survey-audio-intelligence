from src.audit_policy.models import DispositionNode


# Answer-validation trees are project configuration. Their shape decides
# which deterministic rule may select a disposition; anything not listed
# here gets no suggestion.

MATCH_MISMATCH = "MATCH_MISMATCH"
FLAT_PROMPTING = "FLAT_PROMPTING"
NESTED_PROMPTING = "NESTED_PROMPTING"
INTRODUCTION = "INTRODUCTION"
UNSUPPORTED = "UNSUPPORTED"

ASKED_RIGHT = "Asked Right"
MISMATCH = "Mismatch"
NO_PROMPTING_DONE = "Yes - No Prompting Done"
ANSWER_WITHOUT_PROMPTING = "Respondent answer without Prompting"
PERFECT_INTRODUCTION = "Yes - Perfect introduction"

# Shapes whose selection rules are not yet confirmed with the audit
# owners. They are reported explicitly instead of guessed.
PENDING_RULE_REASONS = {
    NESTED_PROMPTING: (
        "Nested prompting answer tree: the rule for choosing between "
        "'Yes - No Prompting Done' and 'Respondent says <entity>' is "
        "pending confirmation, so no answer disposition was suggested."
    ),
    INTRODUCTION: (
        "Introduction answer tree describes interviewer speech "
        "completeness; this rule is not implemented yet, so no answer "
        "disposition was suggested."
    ),
    UNSUPPORTED: (
        "Answer tree shape is not recognised, so no answer disposition "
        "was suggested."
    ),
}


def _top_level(nodes: list[DispositionNode]) -> set[str]:
    return {node.text.strip().lower() for node in nodes}


def classify_answer_tree(nodes: list[DispositionNode]) -> str:
    labels = _top_level(nodes)

    if ANSWER_WITHOUT_PROMPTING.lower() in labels:
        return NESTED_PROMPTING
    if PERFECT_INTRODUCTION.lower() in labels:
        return INTRODUCTION
    if NO_PROMPTING_DONE.lower() in labels:
        return FLAT_PROMPTING
    if ASKED_RIGHT.lower() in labels and MISMATCH.lower() in labels:
        return MATCH_MISMATCH
    return UNSUPPORTED


def answer_prompting_paths(
    nodes: list[DispositionNode],
) -> tuple[list[str] | None, list[str] | None]:
    """Prompting-aware answer paths for audit_question().

    Flat prompting trees map a matched, unprompted answer to
    "Yes - No Prompting Done". Selecting the prompted party node
    ("Prompting -<party>") is not implemented, so prompted answers
    stay with the auditor.
    """
    if classify_answer_tree(nodes) == FLAT_PROMPTING:
        return [NO_PROMPTING_DONE], None
    return None, None
