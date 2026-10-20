"""Independent hand calculations for the optional API12 royalty sidecar.

Synthetic inputs: capex USD 1000, volumes 100 and 200 bbl, gross revenue USD
1000 and 3000, opex USD 2/bbl, annual discount 1/10, royalty fraction 1/8.
No input describes an actual well, lease, price deck or statutory rate.
"""

from dataclasses import replace
from fractions import Fraction

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.production_api12 import ProductionAPI12Analysis
from worldenergydata.fdas.core.citations import (
    Citation,
    CitationResolutionError,
    CitedRoyalty,
)


@pytest.fixture
def inputs():
    cfg = {
        "economics": {"cost": {"CAPEX": 1000, "OPEX": 2, "discount_rate_annual": 0.1}}
    }
    revenue = pd.DataFrame(
        {
            "Month": [202401, 202402, ""],
            "Monthly Oil Production": [100, 200, ""],
            "Revenue (USD)": ["$1,000.00", "$3,000.00", "$4,000.00"],
        }
    )
    return cfg, revenue


@pytest.fixture
def royalty(tmp_path):
    page = tmp_path / "wikis/engineering/standards/example.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ncode_id: SYNTHETIC-ROYALTY\npublisher: Synthetic example\n"
        'revision: "1"\nsource_sibling: generic\nroyalty_rate: 0.125\n'
        "---\nAssumed example fraction: one eighth.\n",
        encoding="utf-8",
    )
    return CitedRoyalty(
        rate=1 / 8,
        citation=Citation(
            code_id="SYNTHETIC-ROYALTY",
            publisher="Synthetic example",
            revision="1",
            section="Worked example",
            wiki_path="wikis/engineering/standards/example.md",
        ),
    )


def test_cited_annual_npv(inputs, royalty, tmp_path):
    """-1000 + (1000*7/8-100*2)/1.1 + (3000*7/8-200*2)/1.1^2
    = -1000 + 6750/11 + 222500/121 = 175750/121 USD.
    Initial capex is at t=0; the blank summary row is excluded.
    """
    cfg, revenue = inputs
    original = revenue.copy(deep=True)
    result = ProductionAPI12Analysis().calculate_npv_with_citations(
        cfg, revenue, period="annual", royalty=royalty, wiki_root=tmp_path
    )
    assert result["npv"] == pytest.approx(float(Fraction(175750, 121)))
    assert result["royalty_status"] == "EVALUATED"
    assert result["royalty_rate"] == 1 / 8
    assert result["citations"][0]["code_id"] == "SYNTHETIC-ROYALTY"
    assert result["citations"][0]["source_sibling"] == "generic"
    pd.testing.assert_frame_equal(revenue, original)


def test_absent_royalty_is_not_evaluated(inputs):
    """Gross legacy formula: -1000 + 800/1.1 + 2600/1.1^2 = 227000/121.
    The difference from the royalty case is the discounted gross-revenue levy.
    """
    cfg, revenue = inputs
    analyzer = ProductionAPI12Analysis()
    result = analyzer.calculate_npv_with_citations(cfg, revenue, period="annual")
    assert result["npv"] == pytest.approx(float(Fraction(227000, 121)))
    assert result["npv"] == analyzer.calculate_npv(cfg, revenue, period="annual")
    assert result["royalty_status"] == "NOT_EVALUATED"
    assert result["royalty_rate"] is None
    assert result["citations"] == []


def test_missing_evidence_prevents_calculation(inputs, royalty, tmp_path, monkeypatch):
    analyzer = ProductionAPI12Analysis()
    monkeypatch.setattr(
        analyzer, "calculate_npv", lambda *a, **k: pytest.fail("calculated")
    )
    with pytest.raises(CitationResolutionError, match="SYNTHETIC-ROYALTY"):
        analyzer.calculate_npv_with_citations(
            *inputs, royalty=royalty, wiki_root=tmp_path / "missing"
        )


def test_explicit_wiki_root_required(inputs, royalty):
    with pytest.raises(ValueError, match="wiki_root"):
        ProductionAPI12Analysis().calculate_npv_with_citations(*inputs, royalty=royalty)


def test_monthly_period_is_preserved(inputs, royalty, tmp_path):
    """At zero discount, -1000 + 675 + 2225 = 1900 USD for either period."""
    cfg, revenue = inputs
    cfg["economics"]["cost"]["discount_rate_annual"] = 0
    result = ProductionAPI12Analysis().calculate_npv_with_citations(
        cfg, revenue, royalty=royalty, wiki_root=tmp_path
    )
    assert result["npv"] == pytest.approx(1900)


def test_monthly_compounding(inputs, royalty, tmp_path):
    """Hand calculation uses r_month=(1+1/10)^(1/12)-1, then
    -1000 + 675/(1+r_month) + 2225/(1+r_month)^2 USD.
    Decimal arithmetic provides an independent evaluation of the FDAS formula.
    """
    from decimal import Decimal

    factor = Decimal("1.1") ** (Decimal(1) / Decimal(12))
    expected = -Decimal(1000) + Decimal(675) / factor + Decimal(2225) / factor**2
    result = ProductionAPI12Analysis().calculate_npv_with_citations(
        *inputs, royalty=royalty, wiki_root=tmp_path
    )
    assert result["npv"] == pytest.approx(float(expected))


def test_explicit_zero_is_evaluated(inputs, royalty, tmp_path):
    """A cited zero levy recovers the gross hand calculation, 227000/121 USD."""
    page = tmp_path / royalty.citation.wiki_path
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "royalty_rate: 0.125", "royalty_rate: 0"
        ),
        encoding="utf-8",
    )
    result = ProductionAPI12Analysis().calculate_npv_with_citations(
        *inputs, period="annual", royalty=replace(royalty, rate=0), wiki_root=tmp_path
    )
    assert result["npv"] == pytest.approx(float(Fraction(227000, 121)))
    assert result["royalty_status"] == "EVALUATED"
    assert result["royalty_rate"] == 0


@pytest.mark.parametrize("column", ["Revenue (USD)", "Monthly Oil Production"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), ""])
def test_cited_result_rejects_missing_or_nonfinite_inputs(
    inputs, royalty, tmp_path, column, value
):
    cfg, revenue = inputs
    revenue[column] = revenue[column].astype(object)
    revenue.loc[0, column] = value
    with pytest.raises(ValueError, match="finite|missing"):
        ProductionAPI12Analysis().calculate_npv_with_citations(
            cfg, revenue, royalty=royalty, wiki_root=tmp_path
        )
