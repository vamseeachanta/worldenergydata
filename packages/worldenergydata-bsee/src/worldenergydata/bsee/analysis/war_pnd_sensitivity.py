"""Paired interim rig-day reports while the WAR PND definition is unvalidated.

Policy: issue #1065, Action 2, and the repository's
``docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md``
(2026-10-12, Interpretation rule and enquiry). Neither the BSEE eWell WAR
Field Definitions page nor the separate borehole-status domain establishes
a meaning for PND. Inclusion in completion is a sensitivity assumption.

This module reuses ``war_rig_days`` for all arithmetic and coverage handling.
It does not select an authoritative basis or define an activity code.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    BASIS_DRL_COM_PND,
    rig_days_by_bore,
    rig_days_by_well,
)

__all__ = ["rig_days_pnd_sensitivity"]


def rig_days_pnd_sensitivity(
    war: pd.DataFrame,
    *,
    grain: Literal["bore", "well"] = "bore",
    population: list[str] | None = None,
) -> pd.DataFrame:
    """Return both PND scenarios as rows, preserving the engine's columns.

    Input is ``mv_war_main`` joined to ``mv_war_main_prop`` on ``SN_WAR``:
    API_WELL_NUMBER, WAR_START_DT, WAR_END_DT and WELL_ACTIVITY_CD are required.
    ``population`` always selects API12 bores, including at well grain.

    ``grain='bore'`` emits API12 rows; ``grain='well'`` emits API10 rows after
    unioning intervals across the selected bores. All excluded rows precede
    all included rows. Every row carries ``basis``, ``pnd_treatment`` and
    ``pnd_definition_status='unvalidated'``, including rows without PND.

    DRL supplies drilling in both scenarios. Completion uses COM alone for
    ``excluded`` and the union of COM and PND for ``included_in_completion``.
    Inclusive calendar-day counting, null coverage and diagnostic columns
    follow ``war_rig_days`` unchanged. In particular, adding ``pnd_days`` to
    excluded completion is incorrect when the intervals overlap.

    The result is a sensitivity comparison, not an uncertainty bound or an
    official definition. No PND-to-completion interpretation is validated.
    """
    calculators = {"bore": rig_days_by_bore, "well": rig_days_by_well}
    if grain not in calculators:
        raise ValueError("grain must be 'bore' or 'well'")
    calculate = calculators[grain]
    reports = []
    for treatment, basis in (
        ("excluded", BASIS_DRL_COM),
        ("included_in_completion", BASIS_DRL_COM_PND),
    ):
        report = calculate(war, basis=basis, population=population)
        report["pnd_treatment"] = treatment
        # Source: publication_status.md (2026-10-12), Interpretation rule and
        # enquiry. This labels the definition, regardless of PND row count.
        report["pnd_definition_status"] = "unvalidated"
        reports.append(report)
    return pd.concat(reports, ignore_index=True)
