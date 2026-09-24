# ASR Baseline

## Dataset

UP CAPI R2 private sample.

Real audio and transcripts derived from respondent data are not committed.

## Models

### Whisper Small

Model:
`openai/whisper-small`

Observed behavior:
- partially recognized Hindi introduction
- severe repetition/hallucination loops
- repetition persisted even on isolated 20-second clips

### Vaani FastConformer Hindi

Model:
`ARTPARK-IISc/Vaani-FastConformer-Hindi`

Observed behavior:
- substantially better transcription on the first 20-second clip
- coherent Hindi survey introduction recovered
- no repetition collapse observed
- later clips require human audio-quality review

## Current Decision

Vaani FastConformer Hindi is the primary ASR baseline for further experiments.

Whisper Small is retained as a comparison baseline.

## Next Evaluation

Evaluate Vaani on:
- clear survey questions
- short respondent answers
- constituency/locality names
- candidate names
- Hindi-English mixed speech
- noisy audio