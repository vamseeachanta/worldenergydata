"""Execute the guide's exact-arithmetic example without recreating its inputs."""

import re
from pathlib import Path

import pytest

GUIDE = (
    Path(__file__).resolve().parents[2]
    / "docs/analysis-guides/probabilistic-resource-estimation.md"
)
EXAMPLE_HEADING = "## Worked example: exact arithmetic"


def _exact_arithmetic_example(markdown):
    sections = re.findall(
        rf"^{re.escape(EXAMPLE_HEADING)}\n(.*?)(?=^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert len(sections) == 1, (
        "Expected exactly one exact-arithmetic section in the guide; "
        f"found {len(sections)}"
    )
    blocks = re.findall(
        r"^```python\n(.*?)^```[ \t]*$",
        sections[0],
        flags=re.MULTILINE | re.DOTALL,
    )
    assert len(blocks) == 1, (
        "Expected exactly one Python block in the exact-arithmetic section; "
        f"found {len(blocks)}"
    )
    return blocks[0]


def test_documented_exact_arithmetic_example():
    """Guide hand calculation: 7758 * 1 * 1 * 0.5 * 0.5 / 1 = 1939.5 STB.

    Half recovery gives 1939.5 * 0.5 = 969.75 STB EUR, including every
    percentile and the mean. The guide chooses four deterministic draws.
    These expectations are independent of the example's own assertions.
    """
    source = _exact_arithmetic_example(GUIDE.read_text(encoding="utf-8"))
    namespace = {"__name__": "__documented_example__"}
    exec(compile(source, GUIDE.as_posix(), "exec"), namespace)

    result = namespace["result"]
    assert result["ooip_distribution"] == [1939.5] * 4
    assert result["eur_distribution"] == [969.75] * 4
    for key in ("p90", "p50", "p10", "mean"):
        assert result[key] == 969.75
    assert result["units"] == "STB"
    assert result["reserves_classification"] == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "markdown, message",
    [
        ("", "exactly one exact-arithmetic section"),
        (
            "## Worked example: renamed\n\n```python\npass\n```\n",
            "exactly one exact-arithmetic section",
        ),
        (
            f"{EXAMPLE_HEADING}\n\n" * 2,
            "exactly one exact-arithmetic section",
        ),
        (f"{EXAMPLE_HEADING}\n\n", "exactly one Python block"),
        (
            f"{EXAMPLE_HEADING}\n\n" + "```python\npass\n```\n" * 2,
            "exactly one Python block",
        ),
    ],
    ids=[
        "missing-section",
        "renamed-section",
        "duplicate-section",
        "missing-block",
        "duplicate-block",
    ],
)
def test_example_selection_rejects_missing_or_ambiguous_content(markdown, message):
    with pytest.raises(AssertionError, match=message):
        _exact_arithmetic_example(markdown)
