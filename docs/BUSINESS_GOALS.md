# Business goals

## Purpose

Reduce human P3 survey-audit effort by turning interview audio into traceable,
question-level evidence and suggested Audit CRM dispositions. The initial
product is **Auditor Assist**: reliable suggestions can be prefilled, while
uncertain findings remain visible for a human auditor.

The existing Audit CRM business logic remains responsible for final P3 validity.
An `AUTO_FILL` decision in this repository is a proposed question-level action;
it is not sample clearance and does not itself write to the CRM.

## Users and value

| User | Intended benefit |
| --- | --- |
| P3 auditor | Less searching/listening; relevant evidence and reasons alongside suggestions |
| Audit operations lead | Consistent review routing and measurable disposition agreement |
| Engineering/data team | Reproducible experiments with explicit provenance and failure cases |

Initial evaluation focuses on Hindi/Hinglish survey interviews, including UP
accents, short answers, constituency names, parties, and candidates. Political
survey content is handled as neutral transcription and answer-validation data.

## Scope and safeguards

- Validate what was asked separately from what the respondent answered.
- Compare spoken answers with configured choices and the recorded response.
- Detect prompting where supported by dialogue and configured disposition paths.
- Preserve raw overlap, third/unknown speakers, missing audio, and uncertainty.
- Suggest only dispositions available in the correct project's policy.

P1/P2 eligibility, P3 sampling, P4 televerification, autonomous fraud decisions,
and production auto-clear are outside the current implementation. Broader
interview-level fraud/quality signals and auto-clear remain future evaluation work.

## Success measures and rollout

Measure auditor time saved, question/answer/prompting agreement, disposition
agreement, review rate, coverage, and unsafe automatic suggestions. ASR word
error rate alone is insufficient: critical entities and short answers matter.
False clearance is a future high-risk metric, not a capability established here.

Progress from small manually reviewed smoke samples to a larger labeled benchmark
before choosing deployment targets. No production accuracy, time-saving, or
auto-clear claims have been established. The current repository is an offline
prototype; its small sample results are development evidence, not validation
of production readiness.
