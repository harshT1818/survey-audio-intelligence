import json
from pathlib import Path

NOTEBOOK_DIR = Path(__file__).resolve().parents[1] / "notebooks"


def test_tracked_notebooks_have_no_saved_outputs():
    # Colab outputs can contain respondent transcripts; notebooks are
    # committed as code only.
    for path in sorted(NOTEBOOK_DIR.glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))

        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue

            assert cell.get("outputs", []) == [], (
                f"{path.name} cell {index} has saved outputs"
            )
            assert cell.get("execution_count") is None, (
                f"{path.name} cell {index} has an execution count"
            )
