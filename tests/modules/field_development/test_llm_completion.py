# ABOUTME: Tests for LLM concept-completion gate + repair loop (issue #577).
# ABOUTME: Uses a fake injected client — no network / API key needed.
"""Tests for ``worldenergydata.field_development.llm_completion``.

The Anthropic client is dependency-injected, so these exercise the schema/sanity
gate and the repair loop deterministically with canned FieldConcept outputs.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from worldenergydata.field_development import (
    CompletionResult,
    ConceptType,
    FieldConcept,
    complete_concept,
)
from worldenergydata.field_development.enums import TreeType


class _FakeMessages:
    """Returns the next canned FieldConcept on each .parse() call."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(parsed_output=self._outputs.pop(0))


class _FakeClient:
    def __init__(self, outputs):
        self.messages = _FakeMessages(outputs)


def _clean():
    return FieldConcept(
        name="Demo",
        concept_type=ConceptType.SPAR,
        tree_type=TreeType.DRY,
        water_depth_m=2000.0,
    )


def _bad_tieback():
    # subsea_tieback with no distance → tieback_missing_distance violation
    return FieldConcept(name="Demo", concept_type=ConceptType.SUBSEA_TIEBACK)


# --------------------------------------------------------------------------- #
def test_clean_concept_first_try():
    client = _FakeClient([_clean()])
    result = complete_concept("a deepwater spar field", client=client)
    assert isinstance(result, CompletionResult)
    assert result.ok is True
    assert result.repairs_used == 0
    assert len(client.messages.calls) == 1


def test_repairs_then_succeeds():
    client = _FakeClient([_bad_tieback(), _clean()])
    result = complete_concept("a tieback", client=client, max_repairs=2)
    assert result.ok is True
    assert result.repairs_used == 1
    assert len(client.messages.calls) == 2


def test_repair_message_carries_violation():
    client = _FakeClient([_bad_tieback(), _clean()])
    complete_concept("a tieback", client=client)
    # The 2nd call's last user message should reference the violation.
    second_msgs = client.messages.calls[1]["messages"]
    last_user = second_msgs[-1]["content"]
    assert "tieback_missing_distance" in last_user


def test_exhausts_repairs_returns_violations():
    # Always invalid → never clears the gate.
    client = _FakeClient([_bad_tieback(), _bad_tieback(), _bad_tieback()])
    result = complete_concept("a tieback", client=client, max_repairs=2)
    assert result.ok is False
    assert any(v.code == "tieback_missing_distance" for v in result.violations)
    assert result.repairs_used == 2
    assert len(client.messages.calls) == 3  # initial + 2 repairs


def test_uses_structured_output_and_model():
    client = _FakeClient([_clean()])
    complete_concept("x", client=client, model="claude-opus-4-8")
    kw = client.messages.calls[0]
    assert kw["model"] == "claude-opus-4-8"
    assert kw["output_format"] is FieldConcept  # schema gate
    assert kw["thinking"] == {"type": "adaptive"}


def test_missing_anthropic_raises_helpful_error(monkeypatch):
    # With no client and anthropic unimportable, raise a clear error.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "anthropic":
            raise ImportError("no anthropic")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="anthropic"):
        complete_concept("x")  # client=None → tries to construct default
