# Survey Audio Intelligence

Offline prototype for AI-assisted P3 survey audio auditing. It turns interview
audio and survey context into question-level evidence, configured disposition
suggestions, and conservative human-review decisions. Final P3 validity remains
with existing Audit CRM business logic.

## Documentation

- [Business goals](docs/BUSINESS_GOALS.md)
- [Technical architecture](docs/TECH_ARCHITECTURE.md)
- [AI agent context and repository map](docs/AGENT_CONTEXT.md)
- [Agent working rules](AGENTS.md)
- [Full-sample audit runner](docs/full_sample_audit.md)
- [ASR baseline observations](experiments/asr_baseline/README.md)

## Implemented

Audio normalization and clip preparation; ASR manifests/chunk assembly and Whisper
baseline; diarization and role inference; static survey choice catalogs; question,
answer and prompting evaluation; nested policy mapping; evidence corroboration;
speaker-safe audit adaptation; and offline per-question batch reports.

Vaani transcription uses a separate experimental workflow. There is no production
service, CRM writeback, or sample auto-clear implementation.

## Verify and run

Use the existing Python environment from the repository root:

```powershell
python -m pytest -q
python -m src.main --request samples/sample_request.json --policy configs/sample_audit_project.json
python -m scripts.evaluate_full_sample_audit --sample-dir data/private/r2/<response-id>
```

The full-sample command requires prepared private artifacts; see its
[usage guide](docs/full_sample_audit.md). `src.main` validates foundation inputs
only. Python requirements are unpinned; FFmpeg and the optional ML runtime need
separate setup. Consult the architecture before changing packages.

Real audio, respondent data, transcripts, credentials and generated reports must
remain outside version control. Use synthetic fixtures for automated tests.
