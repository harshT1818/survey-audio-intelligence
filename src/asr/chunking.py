from dataclasses import dataclass
import re
import unicodedata


@dataclass
class ASRChunk:
    chunk_id: str
    start_sec: float
    end_sec: float
    text: str


@dataclass
class TranscriptWindow:
    start_sec: float
    end_sec: float
    text: str


def _normalize_token(token: str) -> str:
    token = unicodedata.normalize(
        "NFKC",
        token,
    )

    token = token.lower().strip()

    token = re.sub(
        r"[^\w\u0900-\u097F]",
        "",
        token,
    )

    return token


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in text.split()
        if _normalize_token(token)
    ]


def _find_overlap_token_count(
    previous_text: str,
    current_text: str,
    max_tokens: int = 12,
) -> int:
    previous_tokens = _tokens(
        previous_text
    )

    current_tokens = _tokens(
        current_text
    )

    maximum = min(
        len(previous_tokens),
        len(current_tokens),
        max_tokens,
    )

    for size in range(
        maximum,
        0,
        -1,
    ):
        previous_tail = [
            _normalize_token(token)
            for token in previous_tokens[-size:]
        ]

        current_head = [
            _normalize_token(token)
            for token in current_tokens[:size]
        ]

        if previous_tail == current_head:
            return size

    return 0


def remove_repeated_overlap(
    previous_text: str,
    current_text: str,
    max_tokens: int = 12,
) -> str:
    overlap_count = (
        _find_overlap_token_count(
            previous_text=previous_text,
            current_text=current_text,
            max_tokens=max_tokens,
        )
    )

    if overlap_count == 0:
        return current_text.strip()

    current_tokens = current_text.split()

    remaining_tokens = (
        current_tokens[
            overlap_count:
        ]
    )

    return " ".join(
        remaining_tokens
    ).strip()


def merge_asr_chunks(
    chunks: list[ASRChunk],
) -> TranscriptWindow:
    if not chunks:
        return TranscriptWindow(
            start_sec=0,
            end_sec=0,
            text="",
        )

    chunks = sorted(
        chunks,
        key=lambda chunk: chunk.start_sec,
    )

    merged_text = (
        chunks[0].text.strip()
    )

    for chunk in chunks[1:]:
        new_text = (
            remove_repeated_overlap(
                previous_text=merged_text,
                current_text=chunk.text,
            )
        )

        if new_text:
            if merged_text:
                merged_text += " "

            merged_text += new_text

    return TranscriptWindow(
        start_sec=chunks[0].start_sec,
        end_sec=max(
            chunk.end_sec
            for chunk in chunks
        ),
        text=merged_text.strip(),
    )