import argparse
import json
from pathlib import Path

from src.diarization.comparison import compare_diarization


def load(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Score diarization outputs against listened-to checkpoints "
            "(agent / respondent / mixed time ranges)."
        ),
    )
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("diarizations", type=Path, nargs="+")
    args = parser.parse_args()

    checkpoints = load(args.checkpoints)
    if not isinstance(checkpoints, list):
        raise ValueError("Checkpoints must be a JSON list.")

    for path in args.diarizations:
        report = compare_diarization(load(path), checkpoints)
        print("=" * 78)
        print(f"{path.name}  ({report['model_name']})")
        print(f"Speaker totals (s): {report['speaker_totals_sec']}")
        print(f"Agent speaker:      {report['agent_speaker']}")
        print(f"Passed:             {report['passed']} / {report['scored']}")
        for result in report["checkpoints"]:
            note = " (unsure, not scored)" if result["unsure"] else ""
            print(
                f"  {result['verdict']:18} {str(result['label'])[:26]:26} "
                f"expected={result['expected']:10} agent={result['agent_sec']:5.2f}s "
                f"other={result['other_sec']:5.2f}s{note}"
            )


if __name__ == "__main__":
    main()
