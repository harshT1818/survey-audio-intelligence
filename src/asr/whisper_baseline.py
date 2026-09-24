from pathlib import Path

import torch
from transformers import (
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
    pipeline,
)


MODEL_NAME = "openai/whisper-small"


def transcribe_audio(
    audio_path: str | Path,
) -> dict:

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = (
        torch.float16
        if torch.cuda.is_available()
        else torch.float32
    )

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
    )

    model.to(device)

    processor = AutoProcessor.from_pretrained(
        MODEL_NAME
    )

    asr = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )

    return asr(
        str(audio_path),
        return_timestamps=False,
        generate_kwargs={
            "language": "hindi",
            "task": "transcribe",
            "condition_on_prev_tokens": False,
        },
    )