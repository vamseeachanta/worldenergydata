"""Unqualified SI lift-riser design-basis and load-case template.

Public rationale: https://www.mdpi.com/2075-163X/12/10/1319 describes hydraulic
lifting components; https://www.mdpi.com/2077-1312/12/5/788 describes environmental,
platform and internal-flow excitation. These sources motivate the fields, not
acceptance limits. All engineering criteria and input provenance are supplied
by the caller. Zero/positivity and ordering rules below are mathematical/domain
constraints, not sourced design factors. No design qualification is performed.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Template completeness categories motivated by the public reviews above.
# These are not code-prescribed acceptance criteria or numerical design limits.
REQUIRED_CHECKS = (
    "strength_and_stability",
    "fatigue_and_vibration",
    "transport_and_pressure_transients",
    "pump_and_shutdown",
    "motion_and_clearance",
)


class StrictModel(BaseModel):
    """Reject undocumented fields; nested input is validated on construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Quantity(StrictModel):
    """Finite SI scalar with explicit unit and traceable caller evidence.

    Source text records provenance, but its truth and suitability are not checked.
    """

    value: float = Field(strict=True, allow_inf_nan=False)
    unit: Text
    source: Text


def _quantity(unit: str, requirement: str, *, positive: bool = True):
    return Field(
        json_schema_extra={
            "unit": unit,
            "source_requirement": requirement,
            "positive": positive,
        }
    )


class QuantitySection(StrictModel):
    """Enforce declared SI dimensions and mathematical sign constraints."""

    @model_validator(mode="after")
    def validate_units_and_signs(self):
        for name, field in type(self).model_fields.items():
            metadata = field.json_schema_extra
            if not metadata or "positive" not in metadata:
                continue
            quantity = getattr(self, name)
            if quantity.unit != metadata["unit"]:
                raise ValueError(f"{name} requires {metadata['unit']}")
            if quantity.value < 0 or (metadata["positive"] and quantity.value == 0):
                raise ValueError(f"{name} has an invalid sign or zero")
        return self


class Environment(QuantitySection):
    """Case envelope; a profile/spectrum must accompany the evidence references."""

    water_depth_m: Quantity = _quantity("m", "Bathymetry and datum")
    water_density_kg_m3: Quantity = _quantity("kg/m3", "Water property basis")
    significant_wave_height_m: Quantity = _quantity(
        "m", "Metocean spectrum and return condition", positive=False
    )
    peak_wave_period_s: Quantity = _quantity(
        "s", "Metocean spectrum; period retained for calm cases"
    )
    current_speed_m_s: Quantity = _quantity(
        "m/s", "Governing current profile and direction", positive=False
    )


class Motion(QuantitySection):
    """Motion amplitudes are unsigned; source shall identify axes and phase."""

    surge_amplitude_m: Quantity = _quantity(
        "m", "Motion response and heading", positive=False
    )
    sway_amplitude_m: Quantity = _quantity(
        "m", "Motion response and heading", positive=False
    )
    heave_amplitude_m: Quantity = _quantity(
        "m", "Motion response and compensation", positive=False
    )
    roll_amplitude_rad: Quantity = _quantity(
        "rad", "Rotational response and axes", positive=False
    )
    pitch_amplitude_rad: Quantity = _quantity(
        "rad", "Rotational response and axes", positive=False
    )
    yaw_amplitude_rad: Quantity = _quantity(
        "rad", "Rotational response and axes", positive=False
    )
    response_period_s: Quantity = _quantity("s", "Response time history or spectrum")


class RiserString(QuantitySection):
    """Equivalent string input; evidence must resolve joints and attachments."""

    length_m: Quantity = _quantity("m", "String tally and end geometry")
    outer_diameter_m: Quantity = _quantity("m", "Section drawing")
    inner_diameter_m: Quantity = _quantity("m", "Section drawing")
    mass_per_length_kg_m: Quantity = _quantity("kg/m", "Mass and buoyancy schedule")
    young_modulus_pa: Quantity = _quantity("Pa", "Material property qualification")
    allowable_stress_pa: Quantity = _quantity(
        "Pa", "Applicable criterion and material basis"
    )

    @model_validator(mode="after")
    def validate_hollow_section(self):
        if self.inner_diameter_m.value >= self.outer_diameter_m.value:
            raise ValueError("Inner diameter must be less than outer diameter")
        return self


class AuxiliaryLine(RiserString):
    """Optional attached line; same SI section checks, no stiffness aggregation."""

    function: Text
    attachment_reference: Text


class Pump(QuantitySection):
    """Single equivalent pump duty; performance curve and arrangement in source."""

    installation_depth_m: Quantity = _quantity(
        "m", "Pump arrangement and vertical datum", positive=False
    )
    head_m: Quantity = _quantity("m", "Slurry pump curve and reference density")
    volume_flow_m3_s: Quantity = _quantity("m3/s", "Duty flow and solids basis")
    power_w: Quantity = _quantity("W", "Pump efficiency and duty curve")


class RequiredCheck(StrictModel):
    """A required review task, never a passed result or computed utilization."""

    name: Text
    criterion_reference: Text


class LoadCase(QuantitySection):
    """Operating/survival envelope with explicit input-set references.

    Checks are a template checklist, not a complete code compliance assessment.
    Additional cases (shutdown, blockage, installation) require caller definition.
    """

    name: Text
    kind: Literal["operating", "survival"]
    source: Text
    environment_reference: Literal["environment"]
    motion_reference: Literal["motion"]
    internal_pressure_pa: Quantity = _quantity(
        "Pa", "Absolute pressure envelope and datum", positive=False
    )
    external_pressure_pa: Quantity = _quantity(
        "Pa", "Absolute pressure envelope and datum", positive=False
    )
    top_tension_n: Quantity = _quantity(
        "N", "Tensioning arrangement and load condition", positive=False
    )
    mixture_velocity_m_s: Quantity = _quantity(
        "m/s", "Transport duty or explicit zero-flow state", positive=False
    )
    checks: tuple[RequiredCheck, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_check_coverage(self):
        names = [check.name for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("Check names must be unique")
        if not set(REQUIRED_CHECKS).issubset(names):
            raise ValueError("Each case requires every template check category")
        return self


class LiftDesignBasis(StrictModel):
    """Validated completeness and basic consistency, not engineering acceptance.

    One common envelope is used by all cases. Different operating/survival
    environmental envelopes require separate basis records. A single equivalent
    string and pump are represented; distributed properties remain in references.
    """

    basis_reference: Text
    environment: Environment
    motion: Motion
    string: RiserString
    pump: Pump
    auxiliary_lines: tuple[AuxiliaryLine, ...]
    auxiliary_lines_reference: Text
    cases: tuple[LoadCase, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_case_coverage_and_depth(self):
        if {case.kind for case in self.cases} != {"operating", "survival"}:
            raise ValueError("Both operating and survival cases are required")
        if len({case.name for case in self.cases}) != len(self.cases):
            raise ValueError("Case names must be unique")
        if self.pump.installation_depth_m.value > self.environment.water_depth_m.value:
            raise ValueError("Pump depth cannot exceed water depth")
        return self


_SECTIONS = {
    "environment": Environment,
    "motion": Motion,
    "string": RiserString,
    "pump": Pump,
    "case": LoadCase,
}


def field_requirements(*, include_structural: bool = False) -> dict:
    """Return quantitative field units and source requirements without defaults.

    With include_structural=True, enumerate EVERY field including collections,
    labels and references (dimensionless unit ``1``). Source requirements for
    quantities are attached to the containing named field. Metadata is a record
    requirement, not a claim that an evidence reference was verified.
    """
    models = dict(_SECTIONS)
    if include_structural:
        models.update(
            basis=LiftDesignBasis,
            auxiliary_line=AuxiliaryLine,
            check=RequiredCheck,
            quantity=Quantity,
        )
    return {
        section: {
            name: (
                dict(field.json_schema_extra)
                if field.json_schema_extra
                else {
                    "unit": "1",
                    "source_requirement": (
                        "Caller basis record must identify this field and its "
                        "evidence; nested quantities retain their named SI units"
                    ),
                }
            )
            for name, field in model.model_fields.items()
            if include_structural
            or (field.json_schema_extra and "unit" in field.json_schema_extra)
        }
        for section, model in models.items()
    }


def blank_template() -> dict:
    """Return a fresh, explicitly unfilled input worksheet, never valid input.

    Checklist categories follow the public component/excitation reviews cited in
    the module docstring. Their selection is a template aid, not sourced limits
    or a claim that the checklist alone establishes engineering qualification.
    """
    requirements = field_requirements()
    template = {
        section: dict.fromkeys(requirements[section])
        for section in ("environment", "motion", "string", "pump")
    }
    template.update(
        basis_reference=None,
        auxiliary_lines=None,
        auxiliary_lines_reference=None,
        cases=[],
    )
    for kind in ("operating", "survival"):
        case = dict.fromkeys(requirements["case"])
        case.update(
            name=kind,
            kind=kind,
            source=None,
            environment_reference=None,
            motion_reference=None,
            checks=[
                {"name": name, "criterion_reference": None} for name in REQUIRED_CHECKS
            ],
        )
        template["cases"].append(case)
    return template
