"""Core LNGTerminal Pydantic model.

Composes all sub-models (hull design, pipeline, process equipment,
storage, marine infrastructure) and data quality tracking into a
single terminal record suitable for the global LNG terminal dataset.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from ..constants import Region, TerminalFunction, TerminalStatus, TerminalType
from .data_quality import QualityScore, SourceCitation
from .design import (
    HullDesign,
    MarineInfrastructure,
    PipelineSpec,
    ProcessEquipment,
    StorageSpec,
)

logger = logging.getLogger(__name__)

_MAX_FLAT_PIPELINES = 8


class LNGTerminal(BaseModel):
    """A single LNG terminal record with full engineering design data.

    Attributes:
        terminal_id: Generated slug from name and country code.
            Auto-populated by a model validator when left empty.
        terminal_name: Official facility name.
        aliases: Alternative / historical names for deduplication.
        country: ISO 3166-1 alpha-3 country code (e.g. ``USA``).
        region: Broad geographic region.
        latitude: WGS-84 latitude (-90 to 90).
        longitude: WGS-84 longitude (-180 to 180).
        terminal_type: Physical facility classification.
        function: Import / export / bidirectional.
        status: Current operational status.
        capacity_mtpa: Nameplate capacity in million tonnes per annum.
        year_commissioned: Year the facility entered service.
        operator: Current operating company.
        owner: Asset owner (may differ from operator).
        epc_contractor: Engineering / procurement / construction lead.
        capex_usd_million: Capital expenditure estimate in USD millions.
        hull_design: Floater hull details (FSRU / FLNG only).
        pipelines: Full pipeline inventory.
        process_equipment: Liquefaction / regasification equipment.
        storage: LNG storage tank specifications.
        marine_infrastructure: Jetty, berths, loading arms.
        metocean_notes: Environmental / metocean context notes.
        sources: Provenance citations for populated fields.
        data_quality_score: Computed completeness / reliability score.
        last_updated: Timestamp of last record update.
    """

    terminal_id: str = Field(
        default="",
        description="Generated slug (name + country). Auto-populated if empty.",
    )
    terminal_name: str = Field(
        ...,
        min_length=1,
        description="Official terminal name.",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for this terminal.",
    )
    country: str = Field(
        ...,
        description="ISO 3166-1 alpha-3 country code.",
    )
    region: Region | None = Field(
        default=None,
        description="Geographic region.",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="WGS-84 latitude in decimal degrees.",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="WGS-84 longitude in decimal degrees.",
    )
    terminal_type: TerminalType = Field(
        ...,
        description="Physical facility classification.",
    )
    function: TerminalFunction = Field(
        ...,
        description="Import / export / bidirectional.",
    )
    status: TerminalStatus = Field(
        ...,
        description="Current operational status.",
    )
    capacity_mtpa: float | None = Field(
        default=None,
        ge=0,
        le=200,
        description="Nameplate capacity in MTPA.",
    )
    year_commissioned: int | None = Field(
        default=None,
        ge=1960,
        le=2040,
        description="Year facility entered service.",
    )
    operator: str | None = Field(
        default=None,
        description="Current operating company.",
    )
    owner: str | None = Field(
        default=None,
        description="Asset owner.",
    )
    epc_contractor: str | None = Field(
        default=None,
        description="EPC lead contractor.",
    )
    capex_usd_million: float | None = Field(
        default=None,
        ge=0,
        description="Capital expenditure estimate (USD millions).",
    )

    # Engineering sub-models
    hull_design: HullDesign | None = Field(
        default=None,
        description="Floater hull details (FSRU / FLNG).",
    )
    pipelines: list[PipelineSpec] = Field(
        default_factory=list,
        description="Full pipeline inventory.",
    )
    process_equipment: ProcessEquipment | None = Field(
        default=None,
        description="Liquefaction / regasification equipment.",
    )
    storage: StorageSpec | None = Field(
        default=None,
        description="LNG storage specifications.",
    )
    marine_infrastructure: MarineInfrastructure | None = Field(
        default=None,
        description="Jetty, berths, loading arms.",
    )

    metocean_notes: str | None = Field(
        default=None,
        description="Environmental / metocean context.",
    )

    # Data quality tracking
    sources: list[SourceCitation] = Field(
        default_factory=list,
        description="Provenance citations.",
    )
    data_quality_score: QualityScore | None = Field(
        default=None,
        description="Computed data quality score.",
    )

    last_updated: datetime = Field(
        ...,
        description="Timestamp of last record update.",
    )

    # -- Field validators ------------------------------------------------

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        """Enforce ISO 3166-1 alpha-3 format (three uppercase letters)."""
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError(
                f"Country code must be exactly 3 uppercase letters, got '{value}'"
            )
        return value

    # -- Model validators ------------------------------------------------

    @model_validator(mode="after")
    def auto_generate_terminal_id(self) -> LNGTerminal:
        """Populate *terminal_id* when the caller leaves it empty."""
        if not self.terminal_id:
            self.terminal_id = LNGTerminal.generate_terminal_id(
                self.terminal_name,
                self.country,
            )
        return self

    @model_validator(mode="after")
    def warn_hull_design_on_non_floating(self) -> LNGTerminal:
        """Log a warning when hull_design is set on a non-floating type."""
        floating_types = {TerminalType.FSRU, TerminalType.FLNG}
        if self.hull_design is not None and self.terminal_type not in floating_types:
            logger.warning(
                "hull_design is set but terminal_type is %s "
                "(expected FSRU or FLNG) for terminal '%s'",
                self.terminal_type.value,
                self.terminal_name,
            )
        return self

    # -- Static helpers --------------------------------------------------

    @staticmethod
    def generate_terminal_id(name: str, country: str) -> str:
        """Create a URL-safe slug from *name* and *country*.

        Steps:
            1. NFKD-normalise and strip accents.
            2. Lowercase.
            3. Replace whitespace runs with a single hyphen.
            4. Strip non-alphanumeric characters (keep hyphens).
            5. Collapse consecutive hyphens and trim edges.
            6. Append the lowercase country code.

        Args:
            name: Terminal name (e.g. ``"Sabine Pass LNG"``).
            country: ISO 3166-1 alpha-3 code (e.g. ``"USA"``).

        Returns:
            Slug string such as ``"sabine-pass-lng-usa"``.
        """
        normalised = unicodedata.normalize("NFKD", name)
        ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
        lowered = ascii_only.lower()
        slug = re.sub(r"\s+", "-", lowered)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        country_suffix = country.strip().lower()
        return f"{slug}-{country_suffix}"

    # -- Export helpers ---------------------------------------------------

    def to_flat_dict(self) -> dict:
        """Flatten the terminal record for CSV / tabular export.

        Sub-model fields are prefixed so that each column name is unique:

        * ``hull_<field>`` for :pyclass:`HullDesign`
        * ``pipeline_<n>_<field>`` for each :pyclass:`PipelineSpec`
        * ``process_<field>`` for :pyclass:`ProcessEquipment`
        * ``storage_<field>`` for :pyclass:`StorageSpec`
        * ``marine_<field>`` for :pyclass:`MarineInfrastructure`
        * ``source_<n>_<field>`` for each :pyclass:`SourceCitation`
        * ``quality_<field>`` for :pyclass:`QualityScore`

        Returns:
            A single-level dictionary suitable for a DataFrame row.
        """
        flat: dict = {}

        # Scalar top-level fields
        flat["terminal_id"] = self.terminal_id
        flat["terminal_name"] = self.terminal_name
        flat["aliases"] = "|".join(self.aliases) if self.aliases else None
        flat["country"] = self.country
        flat["region"] = self.region.value if self.region else None
        flat["latitude"] = self.latitude
        flat["longitude"] = self.longitude
        flat["terminal_type"] = self.terminal_type.value
        flat["function"] = self.function.value
        flat["status"] = self.status.value
        flat["capacity_mtpa"] = self.capacity_mtpa
        flat["year_commissioned"] = self.year_commissioned
        flat["operator"] = self.operator
        flat["owner"] = self.owner
        flat["epc_contractor"] = self.epc_contractor
        flat["capex_usd_million"] = self.capex_usd_million
        flat["metocean_notes"] = self.metocean_notes
        flat["last_updated"] = self.last_updated.isoformat()

        # Hull design
        flat.update(self._flatten_sub_model(self.hull_design, "hull", HullDesign))

        # Pipelines (indexed columns up to _MAX_FLAT_PIPELINES)
        for idx in range(_MAX_FLAT_PIPELINES):
            prefix = f"pipeline_{idx + 1}"
            if idx < len(self.pipelines):
                flat.update(
                    self._flatten_sub_model(self.pipelines[idx], prefix, PipelineSpec)
                )
            else:
                # Emit None placeholders so every row has the same columns
                flat.update(self._empty_sub_model_columns(PipelineSpec, prefix))

        # Process equipment
        flat.update(
            self._flatten_sub_model(self.process_equipment, "process", ProcessEquipment)
        )

        # Storage
        flat.update(self._flatten_sub_model(self.storage, "storage", StorageSpec))

        # Marine infrastructure
        flat.update(
            self._flatten_sub_model(
                self.marine_infrastructure, "marine", MarineInfrastructure
            )
        )

        # Sources (indexed)
        for idx, source in enumerate(self.sources):
            prefix = f"source_{idx + 1}"
            flat.update(self._flatten_sub_model(source, prefix, SourceCitation))

        # Quality score
        flat.update(
            self._flatten_sub_model(self.data_quality_score, "quality", QualityScore)
        )

        return flat

    # -- Private helpers --------------------------------------------------

    @staticmethod
    def _flatten_sub_model(
        instance: BaseModel | None,
        prefix: str,
        model_cls: type[BaseModel] | None = None,
    ) -> dict:
        """Dump a sub-model with prefixed keys.

        Returns ``{prefix}_{field}: value`` pairs.  If *instance* is
        ``None`` all fields are emitted as ``None`` using *model_cls*
        to determine the expected columns.
        """
        if instance is None:
            return LNGTerminal._empty_sub_model_columns(model_cls, prefix)
        data = instance.model_dump()
        return {f"{prefix}_{key}": value for key, value in data.items()}

    @staticmethod
    def _empty_sub_model_columns(
        model_cls: type[BaseModel] | None,
        prefix: str,
    ) -> dict:
        """Return ``{prefix}_{field}: None`` for every field in *model_cls*.

        When *model_cls* is ``None`` (the sub-model was never set and we
        lack type info), return an empty dict -- the caller should use the
        concrete class directly where column alignment matters.
        """
        if model_cls is None:
            return {}
        return {f"{prefix}_{name}": None for name in model_cls.model_fields}
