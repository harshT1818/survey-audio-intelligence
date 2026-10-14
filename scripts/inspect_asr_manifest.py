import argparse

from src.asr.chunking import (
    ASRChunk,
    merge_asr_chunks,
)
from src.asr.manifest import (
    load_asr_manifest,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "manifest_path"
    )

    args = parser.parse_args()

    manifest = load_asr_manifest(
        args.manifest_path
    )

    print()
    print(
        f"Audio: {manifest.audio_id}"
    )

    print(
        f"Model: {manifest.model_name}"
    )

    print()

    for chunk in manifest.chunks:
        print(
            f"[{chunk.start_sec:05.1f}"
            f" → {chunk.end_sec:05.1f}] "
            f"{chunk.chunk_id}"
        )

        print(
            chunk.text
        )

        print()

    merged = merge_asr_chunks(
        [
            ASRChunk(
                chunk_id=chunk.chunk_id,
                start_sec=chunk.start_sec,
                end_sec=chunk.end_sec,
                text=chunk.text,
            )
            for chunk in manifest.chunks
        ]
    )

    print(
        "=" * 80
    )

    print(
        "MERGED VIEW"
    )

    print(
        "=" * 80
    )

    print()

    print(
        merged.text
    )


if __name__ == "__main__":
    main()