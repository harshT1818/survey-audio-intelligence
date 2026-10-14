# Survey Audio Intelligence

Prototype of **Auditor Assist**: it turns recorded Hindi survey interviews into
question-by-question evidence and suggested Audit CRM dispositions. An auditor
confirms every suggestion, and the Audit CRM keeps the final P3 decision.

To see it, open [`demo/index.html`](demo/index.html) in a browser. It walks
through a fictional interview, showing the decisions the real audit engine
returns for it.

## What it does

For each audited question in an interview:

1. **Who spoke when.** Speaker diarization (NVIDIA Sortformer, run in Google
   Colab) splits the call into voices. The interviewer is the voice that reads
   the introduction. Voices that cannot be placed stay `unknown`, and loud
   speech that no diarized speaker covers is kept as *unattributed*.
2. **What was said.** Each turn is transcribed once, as a whole utterance, with
   Vaani FastConformer Hindi (Colab). Speaker, timestamps and overlap flags stay
   with the text.
3. **Was the question asked right.** The interviewer's speech around the
   question is compared with the script on its content words. Fillers,
   paraphrase, honorifics and years said aloud do not count against the
   interviewer. Look-alike questions, a missing question word, overlapping
   voices and options read aloud lower the decision to prefill or review.
   Naming one answer option on a do-not-read question blocks "Asked Right".
4. **What the respondent answered.** Respondent speech is matched with the
   survey's choices (whole answer, a unique name mention, or a small number)
   and compared with the recorded answer.
5. **What the auditor gets.** For each audited side, a disposition from the
   project's policy marked `AUTO_FILL`, `PREFILL` or `HUMAN_REVIEW`, with the
   reasons and the quotes behind it.

The engine never uses the stored answer as evidence, never suggests "Not
Audible", never auto-fills a disposition that needs a comment, and treats
auditor labels as a comparison only.

## Status

Offline prototype. On seven audited interviews from one project (175 questions,
run 2026-10-14):

| Side | Audited | Suggested | Agrees with the auditor | Disagrees |
| --- | --- | --- | --- | --- |
| Question | 91 | 51 (20 auto-fill, 31 prefill) | 51 | 0 |
| Answer | 175 | 2 | 2 | 0 |

The six questions auditors marked as not asked right got no suggestion. Most
answer sides have no suggestion because 98 of 175 use prompting or introduction
answer trees whose rules await the audit team, and because diarization often
misses or misattributes short respondent answers. These are development
findings on a small sample, not accuracy claims.

Not built yet: a production service, CRM writeback or sample auto-clear; answer
rules for nested-prompting, introduction and flat-prompting trees; voice matching
for respondent speech that diarization misses; one command for the whole
pipeline.

## Setup

- Python 3.12 in `.venv`, then `pip install -r requirements.txt`. Requirements
  are unpinned; the optional ML runtime needs separate setup.
- FFmpeg on `PATH`.
- Diarization and transcription run in Google Colab with the notebooks in
  [`notebooks/`](notebooks/).

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Run an interview through the pipeline

Run every command from the repository root. Each interview lives in
`data/private/r2/<id>/`, which is ignored by git.

| Step | Command |
| --- | --- |
| Split the Audit CRM export into one row per interview | `python -m scripts.split_audit_export data/private/exports/<export>.csv` |
| Prepare answers, auditor labels, policy and question timings | `python -m scripts.prepare_real_sample --response-id <id>` |
| Read the SurveyXpress questionnaire | `python -m scripts.prepare_real_survey_definition --response-id <id> --input <questionnaire export>` |
| Add the recording | Save it as 16 kHz mono `interview_16k_mono.wav` (helpers in `src/audio/`; no script wraps this yet) |
| Build question windows | `python -m scripts.export_real_question_windows --response-id <id>` then `python -m scripts.build_real_question_asr --response-id <id> --without-asr` |
| Diarize in Colab | `python -m scripts.colab_batch pack-audio --response-ids <id> ...`, run `notebooks/sortformer_diarization.ipynb`, then `python -m scripts.colab_batch unpack-diarization <zip>` |
| Assign speaker roles | `python -m scripts.build_real_question_dialogue_segments --response-id <id>` then `python -m scripts.infer_real_speaker_roles --response-id <id>` (add `--agent-speaker <speaker>` after listening, if needed) |
| Export interview turns | `python -m scripts.export_interview_turns --response-id <id>` |
| Transcribe in Colab | `python -m scripts.colab_batch pack-turns --response-ids <id> ...`, run `notebooks/vaani_baseline.ipynb`, then `python -m scripts.colab_batch unpack-asr <results.json>` |
| Build the dialogue | `python -m scripts.build_real_prompting_dialogue_clean --response-id <id>` |
| Audit | `python -m scripts.evaluate_full_sample_audit --sample-dir data/private/r2/<id>` |
| View it in the demo page | `python -m scripts.build_demo --sample-dir data/private/r2/<id>`, then "Open interview" in `demo/index.html` |

The audit writes `full_sample_audit.json` beside its inputs; see the
[runner guide](docs/full_sample_audit.md). The demo page reads the generated
JSON and any recording you add locally in the browser and uploads nothing. After
changing the fictional interview, the runner or the view model, regenerate the
committed demo data with `python -m scripts.build_demo --synthetic`.

`python -m src.main --request samples/sample_request.json --policy configs/sample_audit_project.json`
validates the original foundation inputs only.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | Pipeline packages: audio, diarization, speaker roles, ASR assembly, question validation, answer resolution, evidence quality, policy mapping, automation, the full-sample runner and the demo view model |
| `scripts/` | One command per pipeline step, run as `python -m scripts.<name>` |
| `tests/` | Automated tests on synthetic fixtures |
| `notebooks/` | Colab notebooks for Sortformer diarization and Vaani transcription, committed with outputs cleared |
| `demo/` | Static demo page and the fictional interview's data |
| `docs/` | Product goals, architecture, repository map and runner guide |
| `experiments/` | ASR baseline observations |
| `configs/`, `samples/` | Foundation examples |

## Data rules

Real audio, exports, respondent data, transcripts, policy snapshots,
credentials and generated reports stay in ignored `data/private/` and never go
into version control. Tests use synthetic fixtures, and the demo uses a fictional
interview. Stage explicit paths when committing.

## Documentation

- [Business goals](docs/BUSINESS_GOALS.md)
- [Technical architecture](docs/TECH_ARCHITECTURE.md)
- [Repository map and handoff](docs/AGENT_CONTEXT.md)
- [Agent working rules](AGENTS.md)
- [Full-sample audit runner](docs/full_sample_audit.md)
- [ASR baseline observations](experiments/asr_baseline/README.md)
