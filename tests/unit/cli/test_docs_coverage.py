"""Static smoke tests for issue #355: CLI docs/examples alignment.

Non-networked: file-system reads only. No runtime imports.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_CLI_DOC = _REPO / "docs" / "CLI.md"
_COMMANDS_DOC = _REPO / "docs" / "COMMANDS.md"
_EXAMPLES_README = _REPO / "examples" / "README.md"
_EXAMPLES_DIR = _REPO / "examples"

_LLM_EXAMPLES = [
    _EXAMPLES_DIR / "llm_classification_demo.py",
    _EXAMPLES_DIR / "marine_safety" / "llm_detection_example.py",
    _EXAMPLES_DIR / "marine_safety" / "batch_llm_processing.py",
]

_SAFETY_CLASSES = {
    "bounded-safe",
    "fixture-only",
    "data-required",
    "credential-required",
    "network-required",
    "server-starting",
    "unsafe-unbounded",
}

# Sub-apps registered in CLI — must each have a section in CLI.md
_EXPECTED_CLI_SUBAPPS = {
    "bsee", "dashboard", "eia", "marine-safety", "fdas",
    "lower-tertiary", "sodir", "metocean", "ndbc", "texas-rrc",
    "canada", "mexico-cnh", "landman", "lng-terminals",
    "safety-analysis", "forecast",
}


class TestCommandsDocDisambiguation:
    """COMMANDS.md must carry a banner distinguishing slash-commands from the runtime CLI."""

    def test_commands_md_has_disambiguation_banner(self):
        text = _COMMANDS_DOC.read_text()
        assert "NOT" in text and "worldenergydata" in text, (
            "COMMANDS.md missing disambiguation banner — must clarify these are "
            "custom agent slash commands, not the worldenergydata runtime CLI"
        )


class TestCliDocSubappCoverage:
    """CLI.md must have a dedicated section for every registered sub-app."""

    def test_all_subapps_documented(self):
        text = _CLI_DOC.read_text()
        missing = set()
        for app in _EXPECTED_CLI_SUBAPPS:
            # Look for a markdown section header containing the sub-app name
            pattern = rf"worldenergydata {re.escape(app)}"
            if not re.search(pattern, text):
                missing.add(app)
        assert not missing, (
            f"Sub-apps missing from CLI.md documentation: {missing}"
        )

    def test_safety_classes_present_in_cli_doc(self):
        text = _CLI_DOC.read_text()
        found = {cls for cls in _SAFETY_CLASSES if cls in text}
        assert found, "CLI.md has no safety-class labels at all"

    def test_bounded_safe_commands_documented(self):
        text = _CLI_DOC.read_text()
        assert "bounded-safe" in text, (
            "CLI.md must mark at least one command as bounded-safe"
        )


class TestExamplesReadmeSafetyMatrix:
    """examples/README.md must exist and list all example Python files."""

    def test_readme_exists(self):
        assert _EXAMPLES_README.exists(), "examples/README.md is missing"

    def test_readme_has_safety_table(self):
        text = _EXAMPLES_README.read_text()
        assert "Safety Class" in text or "safety" in text.lower(), (
            "examples/README.md must contain a safety classification table"
        )

    def test_all_py_examples_listed(self):
        text = _EXAMPLES_README.read_text()
        py_files = [
            f for f in _EXAMPLES_DIR.rglob("*.py")
            if "__pycache__" not in str(f)
        ]
        missing = [f.name for f in py_files if f.name not in text]
        assert not missing, (
            f"Example Python files not listed in examples/README.md: {missing}"
        )

    def test_llm_guardrail_env_var_mentioned(self):
        text = _EXAMPLES_README.read_text()
        assert "WORLDENERGYDATA_RUN_LLM_EXAMPLES" in text, (
            "examples/README.md must document the WORLDENERGYDATA_RUN_LLM_EXAMPLES guard"
        )


class TestLlmExamplesGuardrails:
    """LLM example scripts must check WORLDENERGYDATA_RUN_LLM_EXAMPLES before loading models."""

    def test_guardrail_in_all_llm_examples(self):
        missing_guard = []
        for path in _LLM_EXAMPLES:
            if not path.exists():
                missing_guard.append(str(path.name) + " (file missing)")
                continue
            text = path.read_text()
            if "WORLDENERGYDATA_RUN_LLM_EXAMPLES" not in text:
                missing_guard.append(path.name)
        assert not missing_guard, (
            f"LLM example files missing WORLDENERGYDATA_RUN_LLM_EXAMPLES guard: "
            f"{missing_guard}"
        )

    def test_guardrail_is_at_entry_point(self):
        """Guard must appear in the __main__ block (not just as a comment)."""
        bad = []
        for path in _LLM_EXAMPLES:
            if not path.exists():
                continue
            text = path.read_text()
            # Find the position of __main__ and the guard
            main_pos = text.find('if __name__')
            guard_pos = text.find("WORLDENERGYDATA_RUN_LLM_EXAMPLES")
            if main_pos == -1 or guard_pos == -1:
                bad.append(path.name)
            elif guard_pos < main_pos:
                # Guard appears before __main__ block — acceptable only if also in __main__
                # Check if it also appears after __main__
                guard_after = text.find("WORLDENERGYDATA_RUN_LLM_EXAMPLES", main_pos)
                if guard_after == -1:
                    bad.append(path.name)
        assert not bad, (
            f"WORLDENERGYDATA_RUN_LLM_EXAMPLES guard not found in __main__ block: {bad}"
        )
