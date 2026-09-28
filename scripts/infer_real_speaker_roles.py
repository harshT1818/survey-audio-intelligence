import json
from pathlib import Path

from src.speaker_roles.models import (
    RawSpeakerTurn,
)
from src.speaker_roles.rules import (
    infer_speaker_roles,
)


ASR_PATH = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_segment_asr.json"
)

CLIP_MANIFEST_PATH = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_speaker_clips.json"
)

OUTPUT_PATH = Path(
    "data/private/manual/"
    "manual_dialogue_test_01_inferred_turns.json"
)


def load_json(
    path: Path,
):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def main():
    asr_payload = load_json(
        ASR_PATH
    )

    clip_manifest = load_json(
        CLIP_MANIFEST_PATH
    )

    timing_by_clip_id = {
        clip["clip_id"]: clip
        for clip in clip_manifest[
            "clips"
        ]
    }

    raw_turns = []

    for item in asr_payload:
        clip_id = item[
            "clip_id"
        ]

        clip = timing_by_clip_id.get(
            clip_id
        )

        if clip is None:
            raise ValueError(
                f"Missing timing for {clip_id}"
            )

        raw_turns.append(
            RawSpeakerTurn(
                segment_id=clip_id,
                speaker_id=(
                    item["speaker_id"]
                ),
                text=item["text"],
                start_sec=(
                    clip["start_sec"]
                ),
                end_sec=(
                    clip["end_sec"]
                ),
            )
        )

    result = infer_speaker_roles(
        raw_turns
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "=== SPEAKER ROLE INFERENCE ==="
    )
    print()

    print(
        "Dominant agent speaker:",
        result.dominant_agent_speaker_id,
    )

    print(
        "Dominant respondent speaker:",
        result.dominant_respondent_speaker_id,
    )

    print()

    counts = {
        "agent": 0,
        "respondent": 0,
        "unknown": 0,
    }

    review_count = 0

    for turn in result.turns:
        counts[
            turn.role
        ] += 1

        if turn.review_required:
            review_count += 1

        review = (
            " REVIEW"
            if turn.review_required
            else ""
        )

        print(
            f"{turn.segment_id:28} "
            f"{turn.start_sec:6.2f}"
            f" → "
            f"{turn.end_sec:6.2f}  "
            f"{turn.speaker_id:10} "
            f"→ "
            f"{turn.role:10} "
            f"{turn.role_score:.2f}"
            f"{review}"
        )

        print(
            f"    {turn.text}"
        )

        print()

    print(
        "=" * 70
    )

    print(
        "RESULT"
    )

    print(
        "=" * 70
    )

    print(
        f"Total turns:       "
        f"{len(result.turns)}"
    )

    print(
        f"Agent turns:       "
        f"{counts['agent']}"
    )

    print(
        f"Respondent turns:  "
        f"{counts['respondent']}"
    )

    print(
        f"Unknown turns:     "
        f"{counts['unknown']}"
    )

    print(
        f"Review required:   "
        f"{review_count}"
    )

    print()
    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()