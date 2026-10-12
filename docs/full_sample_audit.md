# Full-sample audit evaluation

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_full_sample_audit --sample-dir data/private/r2/<response-id>
```

Optional: `--tags state_govt_change mla_choice`. Without tags, every question
in `question_asr.json` is included, even when inputs are missing.

The sample directory must contain `prompting_dialogue_clean.json`,
`question_asr.json`, `survey_definition.json`, `audit_policy_snapshot.json`,
and `human_audit.json`, produced by the existing preparation workflows.

The runner writes `full_sample_audit.json` beside these inputs. Keep it in
the ignored private data directory: it contains transcript evidence.
The report includes audit results, corroboration, rejected-turn traces,
automation decisions, and human disposition comparisons. Missing inputs
and inactive policies appear explicitly instead of being silently skipped.
Duplicate tags and mismatched policy projects are rejected.

Comparisons use exact ordered human `selectedOptions` labels against suggested
disposition paths (or the single disposition text when no path is supplied).
These keys are indices, not disposition IDs. Unlabeled and unsupported labels
are distinct from mismatches; no suggestion is not counted as agreement.
This is disposition agreement, not a measure of final P3 validity or accuracy.

Only static, resolution-ready choice catalogs supply canonical options.
Dynamic catalogs remain unresolved. Answer dispositions depend on the shape of
the tag's answer tree (`src/audit_policy/answer_tree.py`):

| Shape | Recognised by | Suggestion |
| --- | --- | --- |
| Match/mismatch | top-level "Asked Right" and "Mismatch" | "Asked Right" on match, "Mismatch" on mismatch |
| Flat prompting | top-level "Yes - No Prompting Done" | none by default; with `--prompting-aware-answers`, "Yes - No Prompting Done" for an unprompted match (prefill only) |
| Nested prompting | "Respondent answer without Prompting" | none; selection rule pending client confirmation |
| Introduction | "Yes - Perfect introduction" | none; speech-completeness rule not implemented |

"Not Audible" is never suggested, because missing transcripts can be a
pipeline failure. Prompted-party nodes ("Prompting -<party>") and
combinations are left to the auditor. A node that requires a comment is
never auto-filled; it can at most be prefilled.
The runner is offline and does not update the CRM.
