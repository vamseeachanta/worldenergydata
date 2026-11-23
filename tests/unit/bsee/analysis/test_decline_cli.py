"""Tests for decline curve CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.forecasting.decline_cli import main


@pytest.fixture
def production_bin(tmp_path):
    """Create a temp .bin file with synthetic production data."""
    qi = 40000
    D = 0.03
    n = 25
    rng = np.random.default_rng(88)
    df = pd.DataFrame(
        {
            "PRODUCTION_DATE": list(range(200001, 200001 + n)),
            "FIELD_NAME_CODE": ["TEST_CLI"] * n,
            "LEASE_NUMBER": ["OCS-G-99999"] * n,
            "MON_O_PROD_VOL": [
                qi * np.exp(-D * t) * 30 + rng.normal(0, 3000) for t in range(n)
            ],
            "MON_G_PROD_VOL": [
                qi * 5 * np.exp(-D * t) * 30 + rng.normal(0, 10000) for t in range(n)
            ],
            "DAYS_ON_PROD": [30] * n,
        }
    )
    path = tmp_path / "test_production.bin"
    df.to_pickle(path)
    return path


class TestCLIFieldMode:
    def test_field_analysis(self, production_bin, capsys):
        main(
            [
                "--field",
                "TEST_CLI",
                "--data-file",
                str(production_bin),
            ]
        )
        captured = capsys.readouterr()
        assert "Decline Curve Analysis" in captured.out
        assert "TEST_CLI" in captured.out
        assert "Best model:" in captured.out

    def test_gas_product(self, production_bin, capsys):
        main(
            [
                "--field",
                "TEST_CLI",
                "--product",
                "gas",
                "--data-file",
                str(production_bin),
            ]
        )
        captured = capsys.readouterr()
        assert "TEST_CLI" in captured.out

    def test_custom_forecast_periods(self, production_bin, capsys):
        main(
            [
                "--field",
                "TEST_CLI",
                "--forecast-periods",
                "20",
                "--data-file",
                str(production_bin),
            ]
        )
        captured = capsys.readouterr()
        assert "Forecast (20 periods)" in captured.out


class TestCLILeaseMode:
    def test_lease_analysis(self, production_bin, capsys):
        main(
            [
                "--lease",
                "OCS-G-99999",
                "--data-file",
                str(production_bin),
            ]
        )
        captured = capsys.readouterr()
        assert "Decline Curve Analysis" in captured.out
        assert "OCS-G-99999" in captured.out


class TestCLIOutput:
    def test_html_output(self, production_bin, tmp_path):
        output = tmp_path / "report.html"
        main(
            [
                "--field",
                "TEST_CLI",
                "--data-file",
                str(production_bin),
                "--output",
                str(output),
            ]
        )
        assert output.exists()
        html = output.read_text()
        assert "<html>" in html
        assert "Decline Curve Analysis" in html

    def test_eur_in_output(self, production_bin, capsys):
        main(
            [
                "--field",
                "TEST_CLI",
                "--data-file",
                str(production_bin),
            ]
        )
        captured = capsys.readouterr()
        assert "EUR by model:" in captured.out
        assert "exponential:" in captured.out


class TestCLIErrors:
    def test_missing_data_file(self, tmp_path):
        with pytest.raises(SystemExit):
            main(
                [
                    "--field",
                    "X",
                    "--data-file",
                    str(tmp_path / "nonexistent.bin"),
                ]
            )

    def test_mutual_exclusion(self):
        with pytest.raises(SystemExit):
            main(["--field", "A", "--lease", "B"])
