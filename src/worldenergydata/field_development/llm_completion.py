# ABOUTME: LLM concept-completion — loose brief → schema+sanity-gated FieldConcept.
# ABOUTME: Issue #577 (epic #567) — the ONE place hallucination enters; gated hard.
"""
worldenergydata.field_development.llm_completion
================================================

Turn a loose natural-language brief ("32 MMbbl oil, 1,400 m, 18 km from an FPSO
with spare capacity") into a validated :class:`FieldConcept`.

This is the only non-deterministic surface in the playbook, so it is gated hard:

1. **Schema gate** — the model is called with structured outputs
   (``client.messages.parse(output_format=FieldConcept)``), so the API can only
   return JSON that conforms to the frozen ``field_concept`` schema and the SDK
   validates it into a :class:`FieldConcept` (Pydantic field validators run here).
2. **Sanity gate** — :func:`sanity_check` then catches cross-field *engineering*
   inconsistencies the schema can't express (a tieback with no distance, depth
   outside a host's envelope). Any violations drive a bounded **repair loop**:
   the violations are handed back to the model for a corrected concept.

Provider: Claude ``claude-opus-4-8`` with adaptive thinking (the engineering
reasoning — depth→concept, tieback logic — benefits from it). The Anthropic
client is injectable so the gate/repair logic is testable without a network or
API key; in real use it is constructed lazily (requires ``anthropic`` +
``ANTHROPIC_API_KEY``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.sanity import SanityViolation, sanity_check

DEFAULT_MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You are an offshore field-development engineer. Given a short brief about an "
    "offshore field, produce a structured FieldConcept (concept-select / FEL-1 "
    "fidelity). Fill only what the brief states or what standard engineering "
    "inference clearly implies; leave anything unstated as null — do NOT invent "
    "specific numbers (reserves, rates, depths, distances) that aren't given or "
    "clearly implied.\n"
    "concept_type must be one of: "
    + ", ".join(c.value for c in ConceptType)
    + ". A field produced via a tieback to an existing host is `subsea_tieback` "
    "(not the host's own type).\n"
    "Honour these engineering rules so the concept is internally consistent:\n"
    "- wet-tree (subsea) fields have one subsea tree per well (num_trees == num_wells);\n"
    "- a `subsea_tieback` requires a positive tieback_distance_km;\n"
    "- water depth must suit the concept — fixed_jacket <~450 m; TLP ~300–1500 m; "
    "spar ~600–2450 m; semisub_fps/fpso to ultra-deep; nui only very shallow;\n"
    "- tree_type must match the host (TLP/Spar = dry; subsea/FPSO = wet).\n"
    "Gulf of Mexico fields are hurricane-prone (metocean_regime = hurricane_cyclone)."
)


@dataclass
class CompletionResult:
    """Outcome of an LLM concept-completion run."""

    concept: FieldConcept
    violations: list[SanityViolation] = field(default_factory=list)
    repairs_used: int = 0

    @property
    def ok(self) -> bool:
        """True iff the final concept passed the engineering sanity gate."""
        return not self.violations


def _repair_message(violations: list[SanityViolation]) -> str:
    lines = "\n".join(f"- [{v.code}] {v.message}" for v in violations)
    return (
        "The proposed concept has these engineering sanity violations:\n"
        f"{lines}\n"
        "Return a corrected FieldConcept that resolves them while staying faithful "
        "to the original brief. Do not invent numbers that weren't implied."
    )


def _default_client() -> Any:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "complete_concept needs the 'anthropic' package and ANTHROPIC_API_KEY "
            "(or pass an explicit client=...)."
        ) from exc
    return anthropic.Anthropic()


def complete_concept(
    brief: str,
    client: Optional[Any] = None,
    model: str = DEFAULT_MODEL,
    max_repairs: int = 2,
    max_tokens: int = 4096,
) -> CompletionResult:
    """Complete a loose brief into a schema- and sanity-validated FieldConcept.

    Args:
        brief: Natural-language description of the field.
        client: An Anthropic client (or compatible). Constructed lazily if None.
        model: Claude model id (default ``claude-opus-4-8``).
        max_repairs: Max sanity-driven repair turns after the first attempt.
        max_tokens: Output token cap.

    Returns:
        A :class:`CompletionResult`. ``result.ok`` is True when the final concept
        cleared the sanity gate; otherwise ``result.violations`` lists what
        remained after exhausting repairs.
    """
    client = client or _default_client()
    messages: list[dict] = [{"role": "user", "content": brief}]
    concept: Optional[FieldConcept] = None
    violations: list[SanityViolation] = []
    attempt = 0

    for attempt in range(max_repairs + 1):
        resp = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=_SYSTEM,
            messages=messages,
            output_format=FieldConcept,
            thinking={"type": "adaptive"},
        )
        concept = resp.parsed_output
        violations = sanity_check(concept)
        if not violations:
            break
        if attempt < max_repairs:
            messages = messages + [
                {"role": "assistant", "content": concept.model_dump_json()},
                {"role": "user", "content": _repair_message(violations)},
            ]

    assert concept is not None  # the loop runs at least once
    return CompletionResult(
        concept=concept, violations=violations, repairs_used=attempt
    )
