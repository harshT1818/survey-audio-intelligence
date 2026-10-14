# Agent context and repository map

Reviewed 2026-10-09. Read root [AGENTS.md](../AGENTS.md),
[business goals](BUSINESS_GOALS.md), and [architecture](TECH_ARCHITECTURE.md).
This is a handoff snapshot; current code and user instructions take precedence.

## State and product boundary

Offline survey audio auditing prototype: evidence, interpretation, configured
disposition suggestions, then human review. Existing CRM logic determines final
P3 validity. `AUTO_FILL` means a proposed question-level disposition, not sample
clearance or a CRM write. No production service or writeback is implemented.

At documentation creation: branch `feature/full-sample-audit`, HEAD `3c4065d`,
214 tests last verified passing. Recheck before work. Recent milestones: safe
speaker padding, unsafe-turn filtering, question anchoring, audit adapter
(`2c0b93e`), anchor regressions (`53c5ba5`), batch runner (`3c4065d`).

Current private development run (2026-10-12): the extension batch (214 turns,
143 clips, 71 skipped) was transcribed with no failures and 9 empty transcripts,
then merged, giving clean dialogue for all 25 windows. Audit: 3 PREFILL (question
side only, all matching the human label), 22 HUMAN_REVIEW, no answer suggestions.
These are single-sample observations, not accuracy claims. No respondent identifier needs to be copied into tracked documentation.

Expansion (2026-10-13): six more audited interviews from the same project
(about 47 minutes, mixing P3-rejected and prompting cases) are prepared to the
Colab boundary with Sortformer as their only diarization; question-level ASR is
skipped (`--without-asr`). Each still needs its survey definition export.

## Complete source-package map

Paths are relative to `src/`. Package `__init__.py` files provide structure.

| Package / files | Responsibility |
| --- | --- |
| `main.py` | Foundation request/policy validation CLI; not the complete pipeline |
| `domain/models.py` | Survey request/question schemas and optional paired timings |
| `ingestion/models.py`, `loader.py` | Private R2 survey, audit, timing and sample ingestion |
| `timing/loader.py` | Submission timing parsing; retain raw tag times |
| `audio/downloader.py`, `metadata.py`, `normalizer.py` | Retrieval, duration, FFmpeg 16 kHz mono PCM normalization |
| `audio/segment_refinement.py` | Energy/silence-based clip splitting and refinement manifests |
| `asr/models.py`, `manifest.py`, `chunking.py` | Transcript/chunk contracts, persistence, repeated-overlap removal and merging |
| `asr/whisper_baseline.py` | Transformers Whisper Small Hindi comparison baseline |
| `diarization/models.py`, `pyannote_runner.py`, `clip_export.py` | Speaker segments, direct PCM loading, Pyannote and speaker clip export |
| `diarization/comparison.py` | Score diarization outputs against listened-to agent/respondent/mixed checkpoints |
| `speaker_roles/models.py`, `rules.py` | Semantic/contextual role inference, mixed/unknown turns and diarization consistency |
| `dialogue/models.py`, `question_window.py` | Speech turns and agent question/initial response/follow-up/final response extraction |
| `resolver/models.py`, `option_parser.py`, `closed_set.py`, `question_resolver.py` | Canonical options, SurveyXpress parsing, spoken-answer matching and stored-answer comparison |
| `resolver/respondent_answer.py` | Respondent answers: whole-answer match, then unique name mention (consonant skeleton, negation/alternative guards), then small Hindi numbers; rule results are prefill strength (0.80) |
| `question_validation/models.py`, `fuzzy.py` | Question-text validation by fuzzy similarity (legacy and non-runner paths) |
| `question_validation/script_match.py` | Paraphrase-tolerant question check used by the runner: spoken-form script, weighted content coverage over interviewer passages, look-alike questions, options named on do-not-read questions |
| `prompting/models.py`, `rules.py` | Rule-based prompting evidence |
| `audit_policy/models.py`, `parser.py` | Project/tag policy and nested dispositions; external key is spelled `desposition` |
| `audit_policy/mapper.py`, `question_mapper.py`, `prompting_mapper.py` | Answer/question mapping and explicit nested prompting paths |
| `audit_policy/answer_tree.py` | Classify answer trees (match/mismatch, flat/nested prompting, introduction) and the paths each may use |
| `audit_engine/models.py`, `question_audit.py` | Core audit result/evidence and question orchestration |
| `evidence_quality/models.py`, `gate.py` | Per-answer evidence gating |
| `evidence_quality/corroboration_models.py`, `corroboration.py` | Direct/contextual support, conflicts, unsafe turn IDs and review reasons |
| `automation/models.py`, `decision.py` | AUTO_FILL/PREFILL/HUMAN_REVIEW proposals and unresolved sides |
| `evaluation/models.py`, `runner.py` | Synthetic evaluation fixtures, expected-result comparison and summaries |

### Full-sample source files

All files below are in `src/full_sample/`.

| File | Responsibility |
| --- | --- |
| `audio_windows.py` | Validate/export question windows and manifest entries |
| `asr_batch.py` | Chunk durations, question overlap and clip export |
| `question_asr.py` | Join chunk results with completion/boundary diagnostics |
| `survey_definition.py` | CSV/TSV/encoding handling, grouped choices, metadata and dynamic catalog readiness |
| `survey_options.py` | Static canonical labels/aliases; avoid shared party aliases for candidate choices |
| `dialogue_segments.py` | Intersect question windows with speaker segments and context |
| `speaker_roles.py` | Full-sample role inference from question/core speech statistics; distinct from `src/speaker_roles/`. Agent = introduction-dominant speaker; respondent = non-agent speaker with ≥3× the next one's speech; further speakers `unknown`. If no respondent dominates, status `AGENT_ONLY` keeps the agent and marks all others `unknown` (answers stay with the auditor). `infer_real_speaker_roles.py --agent-speaker <id>` records a listened interviewer label as `human_agent_label` evidence |
| `speaker_turns.py` | Merge segments, attach roles, mark exportable turns |
| `speaker_safe_export.py` | Constrain padding against other speakers; retain genuine raw overlap |
| `interview_turns.py` | Whole-interview turns, unattributed-speech detection by loudness, per-question rows sharing clips |
| `prompting_dialogue.py` | Join manifest to ASR results, retaining source/status metadata |
| `dialogue_merge.py` | ASR coverage against a turn manifest; merge dialogues by tag, refusing duplicates |
| `prompting_benchmark.py` | Question anchors, baseline prompting, human-label parsing and option helpers |
| `turn_safety.py` | Shared rejection reasons and safe-turn selection |
| `safe_prompting.py` | Safety-aware prompting evaluation |
| `evidence_diagnostics.py` | Option mentions, stored-option support and interviewer-like evidence diagnostics |
| `audit_adapter.py` | Safe dialogue + corroboration + rejection trace; existing engine/automation integration |
| `audit_runner.py` | Per-tag orchestration, missing/inactive rows, human comparisons and summaries |

## Scripts

Run `python -m scripts.<name>` from the root. Most sample scripts take
`--response-id` and use `data/private/r2/<response-id>/`. Inspect help/source;
some defaults cover only experimental tags and some demo paths are hard-coded.

| Stage | Files in `scripts/` |
| --- | --- |
| Prepare | `split_audit_export.py` (audit_crm_responses export → per-response `audit_row.csv`; super-audit is primary, regular kept as `audit_row_regular.csv`), `prepare_real_sample.py`, `prepare_real_survey_definition.py` |
| Question audio | `export_real_question_windows.py`, `prepare_real_question_asr_batch.py` |
| ASR assembly | `inspect_asr_manifest.py`, `build_real_question_asr.py` (`--without-asr` builds windows from timing/overlap only, `asr_status` NOT_RUN; window transcripts are informational) |
| Colab batching | `colab_batch.py` (`pack-audio`/`unpack-diarization` for Sortformer, `pack-turns`/`unpack-asr` for Vaani; clips prefixed `<response_id>__`; never replaces different files without `--overwrite`) |
| Diarization/refinement | `run_diarization.py`, `export_diarization_clips.py`, `refine_problem_segments.py`, `compare_diarization.py` (`--checkpoints` + one or more diarization JSONs) |
| Role evidence | `build_real_question_dialogue_segments.py`, `infer_real_speaker_roles.py` |
| Turn export | `export_interview_turns.py` (recommended: every turn of the interview exported once as a whole utterance, plus loud stretches no diarized speaker covers as `unattributed`; writes `interview_turns.json` and per-question rows referencing shared clips), `export_real_prompting_turns.py` (legacy per-question clips; cuts turns at window edges and repeats boundary turns) |
| Dialogue assembly | `build_real_prompting_dialogue.py`, `build_real_prompting_dialogue_clean.py`, `merge_prompting_dialogue.py` (`--sample-dir`; builds a turn batch and merges it into the clean dialogue) |
| Prompting evaluation | `evaluate_real_prompting.py`, `evaluate_clean_prompting.py`, `diagnose_real_prompting_evidence.py` |
| Full audit | `evaluate_full_sample_audit.py` (`--sample-dir`, optional `--tags`) |
| Fixture evaluation | `run_evaluation_fixture.py` (fixture path) |
| Manual demos | `test_product_automation_decision.py`, `test_real_ambiguous_prompting.py`, `test_real_chunk_merge.py`, `test_real_corroboration.py`, `test_real_evidence_quality.py`, `test_real_location_mismatch.py`, `test_real_prompting_audio.py`, `test_real_third_speaker.py` |

Demo scripts are separate from automated tests. Dialogue assembly does not perform
ASR. The clean builder uses fixed clean manifest/results filenames. The merge
script refuses missing, unexpected or duplicate ASR rows unless
`--allow-incomplete` is passed, refuses tags already present, and writes
`<dialogue>.before_merge.json` first (it stops if that backup already exists).

## Data artifacts

| Artifact | Purpose |
| --- | --- |
| `metadata.json`, `survey.json`, `human_audit.json`, `audit_policy_snapshot.json` | Context, stored responses, reference audit, policy |
| `question_windows.json`, `question_audio_manifest.json` | Timing windows and exports |
| `question_asr_batch_manifest.json`, `question_asr_chunk_results.json`, `question_asr.json` | Chunk export, ASR output, assembled question evidence |
| `question_dialogue_segments.json`, `speaker_roles.json` | Question/speaker intersections and role mapping |
| `prompting_turn_manifest[_clean].json` | Turn bounds, role, overlap, skip provenance and audio path |
| `prompting_turn_asr_results[_clean].json` | Turn results with `audio_file` and `transcript` |
| `prompting_dialogue[_clean].json` | Rich tagged dialogue with safety metadata |
| `prompting_benchmark*.json`, `prompting_evidence_diagnostics.json` | Prompting experiments/diagnostics |
| `full_sample_audit.json` | Audit, corroboration, automation, trace and human comparison |
| `full_sample_pending_turn_manifest.json`, `full_sample_pending_turn_audio/` | Extension turn batch and clips |
| `audit_row.csv`, `audit_row_regular.csv` | One audit_crm_responses row (no header, SELECT * order); regular audit kept when a super-audit exists |
| `data/private/exports/`, `data/private/colab/` | Raw portal/database exports; Colab batch zips and manifests |
| `full_sample_pending_turn_asr_results.json`, `full_sample_pending_turn_asr_report.json` | Colab Vaani results and coverage/runtime report |
| `prompting_dialogue_clean.before_merge.json` | Clean dialogue as it was before the merge |
| `full_sample_audit_diagnosis.md`, `full_sample_pending_export.log` | Private diagnosis and export log |

Keep private artifacts ignored. Raw timing exports are not automatically verified
audio offsets. Do not replace raw ASR with canonical/stored answers. Human labels
are comparison references, not input evidence for resolving the spoken answer.

## Safety and interpretation invariants

- Preserve exact policy IDs, hierarchy, comments requirements and project scope.
  `comments_required` flows into `SuggestedDisposition`; such nodes are capped
  at PREFILL. Tag `desposition_type` is kept as `disposition_type`
  (`multi_level_dropdown`, `no_validation`, `textbox`; multi-select exists in
  the CRM but not in the current project).
- Answer mapping depends on answer-tree shape; see `docs/full_sample_audit.md`.
  Prompting-aware answer dispositions are capped at PREFILL and are off by
  default in the batch runner (`--prompting-aware-answers` to experiment).
- Separate speaker clustering from role attribution; allow unknown/extra speakers.
- Anchor before selecting evidence; exclude pre-anchor and unsafe decision turns.
- Preserve material unsafe evidence for review/corroboration, including raw overlap.
- Missing timestamps stay `None`; a timestamp-less agent cannot anchor near zero.
- Tiny skipped turns need not poison clean evidence. An unsafe anchor clears the
  safe dialogue; material upstream review can downgrade AUTO_FILL to PREFILL.
- Initial response/follow-up informs prompting; final respondent response informs
  answer resolution. Agent-only mentions are not direct respondent evidence.
- Respondent answers resolve only as a whole answer (`require_whole_answer`
  in the core resolver and evidence gate): an option word inside a longer
  statement ("नहीं अब बदलाव तो होना चाहिए") stays UNCERTAIN, because WRatio
  scores substrings at ~0.9. Agent contextual matching keeps substring matching.
  After that, `resolve_respondent_answer` may resolve a statement only through
  a word unique to one option (never honorifics or shared surnames), with no
  negation or "या" alternatives in the turn, or a single spoken number when the
  stored value is ≤120 (never phone numbers). These cap at prefill strength.
- Spoken party aliases (बसपा, सपा, भाजपा…) apply only to choices whose label
  is the party name, never to "Person [Party]" choices: whether the respondent
  named the party or the candidate matters to the audit.
- Anchor similarity and question validation use different scoring/normalization.
  Finding an anchor does not validate the question. Fuzzy scores are not probabilities.
- Only static, resolution-ready catalogs provide options in the full-sample path.
  Dynamic catalogs and unconfigured prompting paths must not be guessed.
- Human `selectedOptions` keys are ordering indices, not disposition IDs. Exact
  path agreement is not final P3 accuracy.

## Environment, supporting files and tests

`requirements.txt` is unpinned and does not fully capture the optional ML runtime.
The current `.venv` uses Python 3.12. FFmpeg is external. Pyannote requires model
access/`HF_TOKEN` and loads PCM waveform directly; never print the token or
reinstall working Torch/audio packages merely to run deterministic tests.

Vaani is the chosen experimental Hindi ASR baseline and runs in Google Colab.
NeMo was absent locally at the last check. `notebooks/vaani_baseline.ipynb`
uploads a clip zip and its turn manifest, checks clip coverage, and downloads
`<batch>_asr_results.json` (basename `audio_file` keys; failed clips omitted so
they surface as `MISSING`) plus `<batch>_asr_report.json`. Commit it with
outputs cleared; `tests/test_notebook_hygiene.py` enforces this. `experiments/asr_baseline/README.md`
records small-sample Whisper/Vaani observations, not a general model benchmark.

`configs/sample_audit_project.json` and `samples/sample_request.json` are foundation
examples. `.gitignore` excludes private data/configs/samples, audio, credentials,
environment/caches and runtime outputs. Verify staged paths regardless.
`docs/full_sample_audit.md` documents the runner. Git remotes `origin` and `gitlab`
are separate destinations; preserve both and publish only with authorization.

The `tests/` suite covers schemas/policy, answer/options/question resolution,
prompting and disposition mapping, dialogue/audit orchestration, chunk/manifest
handling, windows, diarization clips, refinement, role inference, survey catalogs,
speaker safety, diagnostics, corroboration, automation, adapter and batch runner.
Regression tests include missing timestamps, unsafe anchors, overlap downgrade,
tiny skipped turns, duplicate tags, project mismatch and explicit missing inputs.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
.\.venv\Scripts\python.exe -m scripts.evaluate_full_sample_audit --sample-dir data/private/r2/<response-id>
```

Sandbox temporary-directory permission failures are environment failures, not
assertion failures. Use an authorized context; do not weaken tests.
`-p no:cacheprovider` avoids cache writes but does not fix temp-directory access.
Use `python -X utf8 -m ...` for redirected Hindi/Unicode output on Windows.

## Next work and limitations

1. Answer resolution produced no suggestions on any of 25 tags. Diagnosis
   (2026-10-12, one sample):
   - 13 tags have prompting-shaped answer trees ("Yes - No Prompting Done",
     "Respondent says <party>", "Prompting -<party>") with no "Asked Right".
     Tree shapes are now classified (`answer_tree.py`); nested-prompting and
     introduction rules await client confirmation (see item 2).
   - Final respondent text was empty for 14 tags (no anchor, no safe respondent
     turn, or gender not asked aloud) and a back-channel ("हाँ हाँ", "मतलब",
     "कौन से") for most others; the real answer is often an earlier turn.
   - Role errors are the main bottleneck: after anchoring, most real answers
     sit in SPEAKER_00 (agent) turns (age, major problems, party, CM choice,
     past candidate, MLA satisfaction), sometimes merged with the question in
     one turn. Diarization gave SPEAKER_00 364 s vs SPEAKER_01 71 s. Better
     final-answer turn selection would not change any result on this sample;
     the remaining respondent turns are back-channels or statements. Listening
     confirmed 4 of 6 checked answers are respondent speech labelled agent (one
     more unclear). Private `diarization_checkpoints.json` records those
     moments; pyannote community-1 passes 2 of 6 (only the agent ones).
     Experiment: `notebooks/sortformer_diarization.ipynb` (Colab, NVIDIA
     streaming Sortformer) writes `interview_16k_mono_diarization_sortformer.json`
     for `compare_diarization`. Six checkpoints are a smoke test, not a DER.
     Sortformer passed 6 of 6 (pyannote 2 of 6) and found two bystander
     speakers. A side-by-side run lives in private
     `data/private/r2/<response-id>__sortformer/` (copied base inputs, Sortformer
     diarization, clean-named turn export: 224 clips, 110 respondent vs 55
     with pyannote). Audit result (2026-10-13): 4 PREFILL / 21 review (was
     3 / 22), still no answer suggestions, but the final respondent text is now
     the real answer for about 9 tags (age, party, MLA, past vote, awareness,
     MLA satisfaction, CM choice). Two interviewer-style option lists
     ("या तो X हो या Y") are labelled respondent; listen before adopting.
     Rule-based respondent resolution then gave the first answer suggestion
     (age, prefill, matching the human label) and correct resolutions for
     party, MLA and LS party; none contradicted stored or human labels.
     Still unresolved by design: yes/no and scale meaning ("जानते हैं",
     "संतुष्ट नहीं है") and garbled entities. LLM extraction (prefill-only,
     verified quotes) is designed but deferred: no budget for paid API use as
     of 2026-10-13, although external LLM use was approved.
   - Cross-question leakage: overlapping windows (`overlap_review_required`,
     e.g. LS candidate fully containing LS party while the interviewer moved
     back and forth) can hold another question's answer. Answer proposals are
     now withheld for such windows (question side kept). Cutting evidence at
     the next anchor would be wrong for interleaved dialogue (the real
     "can't remember" came after the party question); per-turn ownership by
     nearest matching agent question is deferred until more samples show
     how common this is.
     The existing pyannote JSON for this sample carries a stale `audio_id`
     (`manual_dialogue_test_01`); regenerate rather than trust that field.
   - Some windows start after the question was spoken (no anchor found).
   - Numeric/free-text tags (age, phone, dissatisfaction reason) and dynamic
     choices have no resolver. Statement and verb-echo answers ("जानते हैं")
     stay UNCERTAIN by design (see whole-answer invariant).
2. Pending business rules (owner: product, with client): when nested trees use
   "Yes - No Prompting Done" versus "Respondent says <entity>"; which child a
   candidate answer takes (party or generic); and how the response
   standardisation toggle ("use console options") exposes survey options under
   "Mismatch" in the policy JSON, so the matching option can be prefilled. No
   current export contains that toggle; a sample export is needed.
3. Prompting detection: `detect_prompting` now returns UNCERTAIN instead of
   "no prompting" when there is no respondent answer or when material turns
   were dropped upstream (`evidence_complete`, from the adapter's
   `material_for_review` rejections). On the current sample this removed both
   wrong "no prompting" calls; the remaining ones (2 per run) agree with the
   human labels, at the cost of more UNCERTAIN results. Still not covered:
   prompting before the first respondent answer and agent speech after the
   last respondent turn. Keep `--prompting-aware-answers` off by default until
   more labelled interviews are checked.
4. Expand manually reviewed evaluation beyond this one sample before changing
   thresholds.

Remaining gaps: dynamic choices, configurable tag mapping, prompted-party
selection, introduction completeness, broad evaluation and production integration. Timestamp
absence limits chronology; rich dicts have weaker contracts than core models.
There is no deployment/locked runtime or demonstrated production accuracy.
