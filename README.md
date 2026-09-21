# Survey Audio Intelligence

Experimental AI-assisted survey audio auditing pipeline.

The project explores how survey interview audio can be converted into structured evidence for Audit CRM, with the long-term goal of:

- reducing human P3 audit effort
- pre-filling high-confidence audit dispositions
- routing uncertain cases to human auditors
- evaluating whether a highly reliable subset of samples can eventually be auto-cleared

## Current Scope

The current foundation supports:

- validated survey-audit request schemas
- Audit CRM project policy parsing
- nested audit disposition trees
- question and answer validation configuration
- console/local audit-tag distinction
- filtering inactive audit tags
- synthetic test fixtures
- CLI project/request validation

No transcription or automated audit decisions are implemented yet.

## Planned Pipeline

```text
Survey Audio
    ↓
Question Segmentation
    ↓
Hindi ASR
    ↓
Speaker Analysis
    ↓
Answer Resolution
    ↓
Question / Answer Validation
    ↓
Audit Disposition Suggestions
    ↓
Human Review / Future Auto-Clear Eligibility