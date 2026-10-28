"""Tests for lower_tertiary.npv financial calculation functions."""

import pandas as pd
import pytest
import yaml

from worldenergydata.lower_tertiary.npv import (
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

    def test_missing_capex_total_raises(self):
        profile = self._make_profile()
        profile["capex"] = {}
        with pytest.raises(ValueError, match="capex.total_mm_usd"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    # Input contract: issue 1269; no field date or investment is assumed.
    # Synthetic values below are test inputs, not engineering defaults.
    # OpenStax, Principles of Finance (2022), sections 7.2 and 16.2:
    # PV = CF / (1 + r)**t; NPV = PV(inflows) - PV(outflows).
    # https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method

    @pytest.mark.parametrize(
        "first_oil", [None, "", "NaT", pd.NaT, float("nan"), 0, False]
    )
    def test_summary_rejects_unknown_first_oil(self, first_oil):
        profile = self._make_profile()
        profile["first_oil"] = first_oil
        with pytest.raises((TypeError, ValueError), match="first_oil"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    def test_summary_rejects_absent_first_oil(self):
        profile = self._make_profile()
        del profile["first_oil"]
        with pytest.raises(ValueError, match="first_oil"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    @pytest.mark.parametrize(
        "capex",
        [
            None,
            {},
            {"total_mm_usd": None},
            {"total_mm_usd": ""},
            {"total_mm_usd": "unknown"},
            {"total_mm_usd": float("nan")},
            {"total_mm_usd": float("inf")},
            {"total_mm_usd": 0},
            {"total_mm_usd": -1},
            {"total_mm_usd": True},
        ],
    )
    def test_summary_requires_positive_finite_capex(self, capex):
        """Zero investment leaves the retained NPV/CAPEX ratio undefined.

        Positive investment is the outflow convention in OpenStax (2022),
        section 16.2, equation 16.1; zero/negative/nonfinite inputs are invalid.
        """
        profile = self._make_profile()
        profile["capex"] = capex
        with pytest.raises(ValueError, match="capex.total_mm_usd"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    def test_summary_rejects_absent_capex(self):
        profile = self._make_profile()
        del profile["capex"]
        with pytest.raises(ValueError, match="capex.total_mm_usd"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )

    def test_valid_inputs_retain_discounting_and_project_ratio(self):
        """Independent hand calculation using the cited PV and NPV equations.

        Synthetic scenario: first oil Jan 2024, cash flow USD 2.2 million in
        Jan 2025, annual effective rate 10 percent, CAPEX USD 1 million.
        A calendar year is 12 months: PV = 2.2 / 1.1 = 2 million USD;
        project NPV = 2 - 1 = 1 million USD; existing PI = 1 / 1 = 1.
        The existing PI is NPV/CAPEX, not the textbook PV/CAPEX convention
        (OpenStax, 2022, section 16.4); its definition is outside this fix.
        """
        monthly = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-01-01"]),
                "operating_cash_flow": [2_200_000.0],
            }
        )
        profile = {"first_oil": "2024-01-01", "capex": {"total_mm_usd": 1.0}}
        result = summarize_field_financials(monthly, profile, self._make_econ_config())
        assert result["First Oil"] == "2024-01"
        assert result["NPV Operations ($MM)"] == pytest.approx(2.0)
        assert result["NPV Project ($MM)"] == pytest.approx(1.0)
        assert result["PI"] == pytest.approx(1.0)

    def test_loader_preserves_unknown_first_oil_until_summary(self, tmp_path):
        (tmp_path / "sample.yml").write_text("field: {field_id: sample}\n")
        profile = load_field_inputs(tmp_path, {"fields": {}})["sample"]
        assert profile["first_oil"] is None
        with pytest.raises(ValueError, match="first_oil"):
            summarize_field_financials(
                self._make_monthly(), profile, self._make_econ_config()
            )
