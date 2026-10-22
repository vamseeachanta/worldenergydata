"""Tests for lower_tertiary.npv financial calculation functions."""

import pandas as pd
import pytest
import yaml

from worldenergydata.lower_tertiary.npv import (
    FinancialInputError,
    _normalize_lease,
    _read_yaml,
    _resolve_first_oil,
    calculate_monthly_financials,
    load_field_inputs,
    load_lease_mapping,
    summarize_field_financials,
)

# ---------------------------------------------------------------------------
# _normalize_lease
# ---------------------------------------------------------------------------


class TestNormalizeLease:
    def test_strips_whitespace(self):
        assert _normalize_lease("  g12345  ") == "G12345"

    def test_uppercases(self):
        assert _normalize_lease("g12345") == "G12345"

    def test_already_upper(self):
        assert _normalize_lease("G12345") == "G12345"


# ---------------------------------------------------------------------------
# _resolve_first_oil
# ---------------------------------------------------------------------------


class TestResolveFirstOil:
    def test_none(self):
        with pytest.raises(ValueError, match="first_oil"):
            _resolve_first_oil(None)

    def test_string(self):
        result = _resolve_first_oil("2020-06-01")
        assert result == pd.Timestamp("2020-06-01")

    def test_timestamp(self):
        ts = pd.Timestamp("2020-06-01")
        result = _resolve_first_oil(ts)
        assert result == ts


# ---------------------------------------------------------------------------
# _read_yaml
# ---------------------------------------------------------------------------


class TestReadYaml:
    def test_reads_yaml(self, tmp_path):
        yml = tmp_path / "test.yml"
        yml.write_text("key: value\ncount: 42\n")
        result = _read_yaml(yml)
        assert result["key"] == "value"
        assert result["count"] == 42

    def test_empty_file(self, tmp_path):
        yml = tmp_path / "empty.yml"
        yml.write_text("")
        result = _read_yaml(yml)
        assert result == {}


# ---------------------------------------------------------------------------
# load_lease_mapping
# ---------------------------------------------------------------------------


class TestLoadLeaseMapping:
    def test_basic(self, tmp_path):
        yml = tmp_path / "mapping.yml"
        data = {
            "fields": {
                "kaskida": {
                    "leases": ["g12345", "g67890"],
                    "display_name": "Kaskida",
                },
            },
            "lease_to_field": {
                "g12345": "kaskida",
                "g67890": "kaskida",
            },
        }
        yml.write_text(yaml.dump(data))
        result = load_lease_mapping(yml)
        assert "fields" in result
        assert "lease_to_field" in result
        assert "raw" in result
        # Leases normalized to uppercase
        assert result["fields"]["kaskida"]["leases"] == ["G12345", "G67890"]
        assert result["lease_to_field"]["G12345"] == "kaskida"

    def test_empty_mapping(self, tmp_path):
        yml = tmp_path / "empty.yml"
        yml.write_text("{}")
        result = load_lease_mapping(yml)
        assert result["fields"] == {}
        assert result["lease_to_field"] == {}

    def test_no_lease_to_field(self, tmp_path):
        yml = tmp_path / "no_l2f.yml"
        yml.write_text(yaml.dump({"fields": {"f1": {"leases": ["a"]}}}))
        result = load_lease_mapping(yml)
        assert result["lease_to_field"] == {}


# ---------------------------------------------------------------------------
# load_field_inputs
# ---------------------------------------------------------------------------


class TestLoadFieldInputs:
    def _make_lease_mapping(self):
        return {
            "fields": {
                "kaskida": {
                    "leases": ["G12345"],
                    "display_name": "Kaskida",
                },
            },
            "lease_to_field": {"G12345": "kaskida"},
        }

    def test_basic(self, tmp_path):
        field_yml = tmp_path / "kaskida.yml"
        field_yml.write_text(
            yaml.dump(
                {
                    "field": {
                        "field_id": "kaskida",
                        "display_name": "Kaskida Field",
                        "status": "producing",
                        "first_oil": "2020-06-01",
                        "capex": {"total_mm_usd": 500},
                        "opex_per_boe": 18.0,
                    }
                }
            )
        )
        result = load_field_inputs(tmp_path, self._make_lease_mapping())
        assert "kaskida" in result
        assert result["kaskida"]["display_name"] == "Kaskida Field"
        assert result["kaskida"]["first_oil"] == pd.Timestamp("2020-06-01")

    def test_status_filter(self, tmp_path):
        for name, status in [("f1", "producing"), ("f2", "abandoned")]:
            (tmp_path / f"{name}.yml").write_text(
                yaml.dump({"field": {"field_id": name, "status": status}})
            )
        result = load_field_inputs(
            tmp_path, self._make_lease_mapping(), status_filter="producing"
        )
        assert "f1" in result
        assert "f2" not in result

    def test_missing_directory(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_field_inputs(tmp_path / "nonexistent", self._make_lease_mapping())

    def test_leases_from_mapping(self, tmp_path):
        field_yml = tmp_path / "kaskida.yml"
        field_yml.write_text(
            yaml.dump(
                {
                    "field": {
                        "field_id": "kaskida",
                        "status": "producing",
                        "leases_key": "kaskida",
                    }
                }
            )
        )
        result = load_field_inputs(tmp_path, self._make_lease_mapping())
        assert result["kaskida"]["leases"] == ["G12345"]

    def test_display_name_fallbacks(self, tmp_path):
        # Test name fallback
        (tmp_path / "f1.yml").write_text(
            yaml.dump(
                {
                    "field": {
                        "field_id": "f1",
                        "name": "Field One",
                        "status": "producing",
                    }
                }
            )
        )
        result = load_field_inputs(tmp_path, {"fields": {}})
        assert result["f1"]["display_name"] == "Field One"

    def test_data_through(self, tmp_path):
        (tmp_path / "f1.yml").write_text(
            yaml.dump(
                {
                    "field": {
                        "field_id": "f1",
                        "status": "producing",
                        "data_through": "2024-12-01",
                    }
                }
            )
        )
        result = load_field_inputs(tmp_path, {"fields": {}})
        assert result["f1"]["data_through"] == pd.Timestamp("2024-12-01")


# ---------------------------------------------------------------------------
# calculate_monthly_financials
# ---------------------------------------------------------------------------


class TestCalculateMonthlyFinancials:
    def _make_econ_config(self):
        return {
            "commodity_prices": {
                "oil": {"base_case": {"wti_usd_per_bbl": 75.0}},
                "gas": {"base_case": {"henry_hub_usd_per_mcf": 3.50}},
            },
            "fiscal_terms": {
                "royalty": {"rate": 0.1875},
                "taxes": {"federal_income_tax": {"rate": 0.21}},
            },
        }

    def test_basic(self):
        df = pd.DataFrame(
            {
                "oil_bbl": [10000, 9500, 9000],
                "gas_mcf": [50000, 48000, 45000],
            }
        )
        result = calculate_monthly_financials(df, self._make_econ_config(), 18.0)
        assert "oil_revenue" in result.columns
        assert "gas_revenue" in result.columns
        assert "total_revenue" in result.columns
        assert "net_revenue" in result.columns
        assert "operating_cash_flow" in result.columns
        assert result["oil_revenue"].iloc[0] == pytest.approx(750000.0)

    def test_empty_dataframe(self):
        result = calculate_monthly_financials(
            pd.DataFrame(), self._make_econ_config(), 18.0
        )
        assert result.empty

    def test_boe_calculation(self):
        df = pd.DataFrame({"oil_bbl": [6000], "gas_mcf": [36000]})
        result = calculate_monthly_financials(df, self._make_econ_config(), 18.0)
        # BOE = 6000 + 36000/6 = 12000
        assert result["boe"].iloc[0] == pytest.approx(12000.0)


# ---------------------------------------------------------------------------
# summarize_field_financials
# ---------------------------------------------------------------------------


class TestSummarizeFieldFinancials:
    def _make_monthly(self):
        dates = pd.date_range("2022-01-01", periods=12, freq="MS")
        return pd.DataFrame(
            {
                "date": dates,
                "oil_bbl": [10000] * 12,
                "gas_mcf": [50000] * 12,
                "total_revenue": [925000] * 12,
                "royalty": [173437.5] * 12,
                "opex": [180000] * 12,
                "operating_cash_flow": [400000] * 12,
            }
        )

    def _make_profile(self):
        return {
            "field_id": "test_field",
            "display_name": "Test Field",
            "first_oil": "2020-01-01",
            "capex": {"total_mm_usd": 500.0},
        }

    def _make_econ_config(self):
        return {
            "financial_metrics": {
                "discount_rates": {"primary_discount_rate": 0.10},
            },
        }

    def test_basic(self):
        result = summarize_field_financials(
            self._make_monthly(), self._make_profile(), self._make_econ_config()
        )
        assert result["Field"] == "Test Field"
        assert result["Months"] == 12
        assert result["Oil (MMBO)"] == pytest.approx(0.12)
        assert result["CAPEX ($MM)"] == 500.0
        assert "NPV Operations ($MM)" in result
        assert "PI" in result

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="at least one record"):
            summarize_field_financials(
                pd.DataFrame(), self._make_profile(), self._make_econ_config()
            )

    @pytest.mark.parametrize("capex", [None, {}, {"total_mm_usd": None}])
    def test_missing_capex(self, capex):
        """Issue 1269: an unknown investment cannot establish project NPV or PI."""
        profile = self._make_profile()
        profile["capex"] = capex
        with pytest.raises(ValueError, match="capex.total_mm_usd"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    @pytest.mark.parametrize("date", [None, "", "not-a-date", "NaT", pd.NaT, 0])
    def test_missing_or_invalid_first_oil(self, date):
        """Issue 1269 requires an observed calendar origin, never an epoch guess."""
        profile = self._make_profile()
        profile["first_oil"] = date
        with pytest.raises(ValueError, match="first_oil"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    @pytest.mark.parametrize(
        "investment", [0, -1, float("nan"), float("inf"), "bad", True]
    )
    def test_invalid_capex(self, investment):
        """A finite positive denominator is necessary for the retained PI ratio."""
        profile = self._make_profile()
        profile["capex"] = {"total_mm_usd": investment}
        with pytest.raises(ValueError, match="capex.total_mm_usd"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    @pytest.mark.parametrize("cashflow", [None, float("nan"), float("inf")])
    def test_unknown_cashflow_is_not_zero(self, cashflow):
        """A missing or non-finite money observation cannot establish NPV."""
        monthly = self._make_monthly()
        if cashflow is None:
            monthly = monthly.drop(columns="operating_cash_flow")
        else:
            monthly["operating_cash_flow"] = monthly["operating_cash_flow"].astype(
                float
            )
            monthly.loc[0, "operating_cash_flow"] = cashflow
        with pytest.raises(ValueError, match="operating_cash_flow"):
            summarize_field_financials(
                monthly, self._make_profile(), self._make_econ_config()
            )

    @pytest.mark.parametrize("rate", [-0.1, float("nan"), float("inf")])
    def test_invalid_discount_rate(self, rate):
        """Rate inputs follow the non-negative finite convention of issue 1324."""
        config = self._make_econ_config()
        config["financial_metrics"]["discount_rates"]["primary_discount_rate"] = rate
        with pytest.raises(ValueError, match="discount_rate"):
            summarize_field_financials(
                self._make_monthly(), self._make_profile(), config
            )


def test_inventory_preserves_unknown_first_oil(tmp_path):
    """Inventory may contain unknown dates; financial evaluation must refuse them."""
    (tmp_path / "synthetic.yml").write_text("field_id: synthetic\n")
    profile = load_field_inputs(tmp_path, {"fields": {}})["synthetic"]
    assert profile["first_oil"] is None


@pytest.mark.parametrize(
    "annual_rate, expected_operations, expected_project",
    [(0.0, 150.0, 50.0), (1.1**12 - 1, 16600 / 121, 4500 / 121)],
)
def test_three_month_worked_example(annual_rate, expected_operations, expected_project):
    """Independent hand calculation; all amounts are synthetic MM USD.

    Cashflows [100,-50,100] at first-oil months t=[0,1,2], investment 100.
    Zero discount: PV=100-50+100=150; project NPV=150-100=50.
    Monthly r=0.1: PV=100-50/1.1+100/1.21=16600/121;
    NPV=4500/121. Annual effective r=1.1**12-1 matches this monthly rate.
    Source: NumPy v1.17 npv Notes (2020), citing Principles of Managerial
    Finance, Brief, third edition (2003), page 346; t counts months here.
    """
    monthly = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="MS"),
            "operating_cash_flow": [100_000_000.0, -50_000_000.0, 100_000_000.0],
        }
    )
    profile = {"first_oil": "2024-01-01", "capex": {"total_mm_usd": 100.0}}
    config = {
        "financial_metrics": {
            "discount_rates": {
                "primary_discount_rate": annual_rate,
            }
        }
    }
    result = summarize_field_financials(monthly, profile, config)
    assert result["NPV Operations ($MM)"] == pytest.approx(expected_operations)
    assert result["NPV Project ($MM)"] == pytest.approx(expected_project)
    assert result["PI"] == pytest.approx(expected_project / 100)
    profile.pop("first_oil")
    with pytest.raises(FinancialInputError) as caught:
        summarize_field_financials(monthly, profile, config)
    assert caught.value.field == "first_oil"
