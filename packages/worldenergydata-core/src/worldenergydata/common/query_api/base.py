# ABOUTME: TypedQuery ABC + FilterSpec — reusable typed-query base (workspace-hub#3286).
# ABOUTME: Generalizes the marine_safety/bsee singular-plural + single-year normalization.
"""Typed-query base.

``TypedQuery`` subclasses declare a list of :class:`FilterSpec` filters and
implement :meth:`TypedQuery._execute`. The base handles:

* singular -> plural collapse (``source`` -> ``["source"]``; ``sources`` wins
  when both are given) for every ``kind="list"`` filter,
* the single-``year`` shorthand (``year=Y`` -> ``start_year=end_year=Y``) for a
  ``kind="year"`` filter, and
* forwarding of any unrecognized kwargs through a ``_passthrough`` bucket so a
  subclass ``_execute`` can apply extra filters (e.g. ``min_amount``).

The behavior is byte-for-byte equivalent to the hand-rolled marine_safety
normalization (see ``tests/marine_safety/test_api_on_base.py``).

``query_envelope()`` is OPTIONAL and lazily imports
``assetutilities.workflow_api`` (workspace-hub#3282); the plain ``query()`` path
has no assetutilities dependency at all.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


@dataclass(frozen=True)
class FilterSpec:
    """Declarative description of one query filter.

    Parameters
    ----------
    name:
        Canonical (plural) field name the normalized dict carries, e.g.
        ``"sources"``. For ``kind="year"`` this is documentary only (the
        normalized dict always emits ``start_year``/``end_year``).
    singular:
        Optional singular alias collapsed into ``name`` (``"source"``). ``None``
        means the filter has no singular alias.
    kind:
        ``"list"`` (singular/plural collapse to a list), ``"scalar"`` (passed
        through as-is), or ``"year"`` (enables the single-year shorthand).
    """

    name: str
    singular: Optional[str]
    kind: str  # "list" | "scalar" | "year"


def df_content_hash(df: "pd.DataFrame") -> str:
    """Content-sensitive, order-stable sha256 of a DataFrame.

    Canonicalizes to CSV bytes (index excluded) so an identical frame always
    hashes the same and a single changed cell flips the digest. Used for
    ``determinism.result_hash`` in :meth:`TypedQuery.query_envelope`.
    """
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


class TypedQuery(ABC):
    """Reusable typed-query base.

    Subclasses set the class attributes ``query_id``, ``filters`` and
    (optionally) ``result_columns``, and implement :meth:`_execute`.
    """

    # Subclasses override these.
    query_id: str = "typed_query"
    filters: List[FilterSpec] = []
    result_columns: List[str] = []

    def _normalize(self, **kwargs: Any) -> Dict[str, Any]:
        """Collapse singular/plural + year shorthand; bucket unknown kwargs.

        Returns a dict with one key per declared filter (``kind="year"`` emits
        ``start_year``/``end_year``) plus a ``_passthrough`` dict carrying every
        kwarg not consumed by a declared filter.
        """
        out: Dict[str, Any] = {}
        extra = dict(kwargs)
        for f in self.filters:
            if f.kind == "list":
                plural = extra.pop(f.name, None)
                single = extra.pop(f.singular, None) if f.singular else None
                if plural:
                    out[f.name] = list(plural)
                elif single is not None:
                    out[f.name] = [single]
                else:
                    out[f.name] = None
            elif f.kind == "year":
                year = extra.pop("year", None)
                start_year = extra.pop("start_year", None)
                end_year = extra.pop("end_year", None)
                if year is not None:
                    out["start_year"] = year
                    out["end_year"] = year
                else:
                    out["start_year"] = start_year
                    out["end_year"] = end_year
            else:  # scalar
                out[f.name] = extra.pop(f.name, None)
                if f.singular:
                    # A scalar filter may still declare a singular alias; the
                    # canonical name wins, the alias is consumed if present.
                    alias = extra.pop(f.singular, None)
                    if out[f.name] is None and alias is not None:
                        out[f.name] = alias
        out["_passthrough"] = extra
        return out

    @abstractmethod
    def _execute(self, normalized: Dict[str, Any]) -> "pd.DataFrame":
        """Run the underlying query from a normalized filter dict."""
        raise NotImplementedError

    def query(self, **kwargs: Any) -> "pd.DataFrame":
        """Run the query. Behavior-preserving for the legacy surfaces."""
        return self._execute(self._normalize(**kwargs))

    def query_envelope(self, *, data_as_of: Optional[str] = None, **kwargs: Any):
        """Run the query and wrap the result in a contract ``ResultEnvelope``.

        The envelope ``result`` carries the record count + column list (NOT the
        whole frame), ``provenance.input_hash`` is computed over the normalized
        filters, and ``determinism.result_hash`` is a content hash of the result
        frame. ``determinism.reproducible`` is ``None`` (query determinism is not
        asserted here). assetutilities is imported lazily so the base stays
        dependency-light until envelopes are requested.
        """
        from assetutilities.workflow_api import ResultEnvelope, make_provenance
        from assetutilities.workflow_api.envelope import input_hash

        norm = self._normalize(**kwargs)
        df = self._execute(norm)
        # input_hash prunes a fixed set of volatile top-level cfg keys; the
        # normalized filter dict shares none of them, so this is a plain content
        # hash of the (json-canonicalized) filters.
        ihash = input_hash({k: v for k, v in norm.items()})
        return ResultEnvelope(
            workflow_id=self.query_id,
            status="ok",
            result={
                "kind": "dataframe",
                "records": int(len(df)),
                "columns": list(df.columns),
            },
            provenance=make_provenance(
                ihash, package_name="worldenergydata", data_as_of=data_as_of
            ),
            determinism={"result_hash": df_content_hash(df), "reproducible": None},
            confidence=None,
            warnings=[],
        )
