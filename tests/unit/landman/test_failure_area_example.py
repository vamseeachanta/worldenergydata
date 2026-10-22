"""Execute the documented offline provider/cache/parcel worked example."""

from pathlib import Path
from runpy import run_path


def test_failure_and_area_worked_example(tmp_path):
    """The example embeds independent request counts and rectangle arithmetic."""
    document = (
        Path(__file__).resolve().parents[3]
        / "packages/worldenergydata-landman/src/worldenergydata/landman/docs/failure-and-area-example.md"
    )
    text = document.read_text()
    (code,) = [part.split("```", 1)[0] for part in text.split("```python\n")[1:]]
    script = tmp_path / "worked_example.py"
    script.write_text(code)
    run_path(str(script))
