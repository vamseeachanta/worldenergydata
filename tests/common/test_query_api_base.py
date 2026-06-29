# ABOUTME: TDD for the reusable TypedQuery base (workspace-hub#3286).
# ABOUTME: Normalization (singular/plural, year shorthand, passthrough) + query_envelope contract.

"""Tests for ``worldenergydata.common.query_api.TypedQuery``."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.common.query_api import FilterSpec, TypedQuery


class _StubQuery(TypedQuery):
    query_id = "stub.query"
    filters = [
        FilterSpec("sources", "source", "list"),
        FilterSpec("vessel_types", "vessel_type", "list"),
        FilterSpec("years", None, "year"),
    ]
    result_columns = ["a", "b"]

    def __init__(self, frame: pd.DataFrame | None = None):
        self._frame = (
            frame if frame is not None else pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        )
        self.last_normalized = None

    def _execute(self, normalized):
        self.last_normalized = normalized
        return self._frame


def test_filterspec_list_collapses_singular_and_plural():
    q = _StubQuery()
    n = q._normalize(source="maib")
    assert n["sources"] == ["maib"]
    # plural wins when both present
    n2 = q._normalize(source="maib", sources=["imo", "emsa"])
    assert n2["sources"] == ["imo", "emsa"]


def test_filterspec_year_shorthand():
    q = _StubQuery()
    n = q._normalize(year=2022)
    assert n["start_year"] == 2022 and n["end_year"] == 2022
    n2 = q._normalize(start_year=2019, end_year=2023)
    assert n2["start_year"] == 2019 and n2["end_year"] == 2023


def test_normalize_passthrough_extra_kwargs():
    q = _StubQuery()
    n = q._normalize(min_amount=1000)
    assert n["_passthrough"]["min_amount"] == 1000


def test_query_delegates_to_execute():
    q = _StubQuery()
    out = q.query(source="maib", vessel_type="tanker")
    assert isinstance(out, pd.DataFrame)
    assert q.last_normalized["sources"] == ["maib"]
    assert q.last_normalized["vessel_types"] == ["tanker"]


def test_query_envelope_shape():
    q = _StubQuery()
    env = q.query_envelope(source="maib")
    # contract dataclass
    from assetutilities.workflow_api import ResultEnvelope

    assert isinstance(env, ResultEnvelope)
    assert env.workflow_id == "stub.query"
    assert env.status == "ok"
    assert env.result["kind"] == "dataframe"
    assert env.result["records"] == 2
    assert env.result["columns"] == ["a", "b"]
    assert env.provenance["input_hash"] is not None
    # wed stamps its OWN package version, not assetutilities'
    assert env.provenance["code_version"]["package_version"] is not None
    assert env.determinism["result_hash"] is not None
    assert env.determinism["reproducible"] is None


def test_query_envelope_result_hash_content_sensitive():
    f1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    f2 = pd.DataFrame({"a": [1, 2], "b": [3, 999]})  # one cell changed
    h1 = _StubQuery(f1).query_envelope().determinism["result_hash"]
    h1b = _StubQuery(f1.copy()).query_envelope().determinism["result_hash"]
    h2 = _StubQuery(f2).query_envelope().determinism["result_hash"]
    assert h1 == h1b  # identical frames -> identical hash
    assert h1 != h2  # changed cell -> different hash


def test_typed_query_is_abstract():
    with pytest.raises(TypeError):
        TypedQuery()  # abstract _execute
