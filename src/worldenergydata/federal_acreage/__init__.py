"""Fixture-first federal lease-position and acreage evidence."""

from .evidence import evaluate
from .federal_acreage import FederalAcreage
from .models import (
    AcreageEvidenceResult,
    FederalLandRecord,
    SourcedValue,
    SourceRef,
    TractOfInterest,
)
from .provider import FederalLandRecordProvider, FixtureRecordProvider
from .report import write_outputs
