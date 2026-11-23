"""CLI tests for Texas RRC GoDrive directory dry-run options."""

from __future__ import annotations


def test_raw_refresh_cli_directory_dry_run_shows_fanout(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    import worldenergydata.texas_rrc.raw_refresh as raw_refresh
    from worldenergydata.cli.commands.texas_rrc import app

    class FakeRefresher:
        def __init__(self, output_root):
            self.output_root = output_root
            self.catalog = {
                "well_gis_layers": {
                    "download_strategy": "official_godrive_directory",
                },
                "production_pdq": {
                    "download_strategy": "official_godrive_file",
                },
            }

        def plan_sources(self, source_ids=None):
            return []

        def discover_directory_source(self, source_id, selection, rows_per_page=1000):
            assert source_id == "well_gis_layers"
            assert rows_per_page == 1000
            return raw_refresh.DirectoryRefreshPlan(
                source_id="well_gis_layers",
                refreshable=True,
                download_strategy="official_godrive_directory",
                source_url="https://www.rrc.texas.gov/resource-center/research/",
                download_url="https://mft.rrc.texas.gov/link/example",
                target_path=tmp_path / "raw" / "gis" / "wells",
                refresh_cadence="twice_weekly",
                row_count=255,
                selected_files=(
                    raw_refresh.DirectoryRefreshFile(
                        filename="well001.zip",
                        command_id="fileTable:0:j_id_2f",
                        modified_label="6/29/26 6:14:59 PM",
                        size_label="610.56 KB",
                        page_first=0,
                        target_path=tmp_path / "raw" / "gis" / "wells" / "well001.zip",
                    ),
                ),
            )

    monkeypatch.setattr(raw_refresh, "RawSnapshotRefresher", FakeRefresher)

    result = CliRunner().invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "well_gis_layers",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "well_gis_layers" in result.output
    assert "255" in result.output
    assert "well001.zip" in result.output
    assert not any(tmp_path.rglob("*"))


def test_raw_refresh_cli_mixed_source_dry_run_shows_directory_and_file_sources(
    monkeypatch,
    tmp_path,
):
    from typer.testing import CliRunner

    import worldenergydata.texas_rrc.raw_refresh as raw_refresh
    from worldenergydata.cli.commands.texas_rrc import app

    class FakeRefresher:
        def __init__(self, output_root):
            self.output_root = output_root
            self.catalog = {
                "well_gis_layers": {
                    "download_strategy": "official_godrive_directory",
                },
                "production_pdq": {
                    "download_strategy": "official_godrive_file",
                },
            }

        def plan_sources(self, source_ids=None):
            assert source_ids == ["production_pdq"]
            return [
                raw_refresh.RefreshPlan(
                    source_id="production_pdq",
                    refreshable=True,
                    download_strategy="official_godrive_file",
                    source_url="https://www.rrc.texas.gov/resource-center/research/",
                    download_url="https://mft.rrc.texas.gov/link/example",
                    target_path=tmp_path / "raw" / "production" / "PDQ_DSV.zip",
                    refresh_cadence="monthly",
                )
            ]

        def discover_directory_source(self, source_id, selection, rows_per_page=1000):
            assert source_id == "well_gis_layers"
            return raw_refresh.DirectoryRefreshPlan(
                source_id="well_gis_layers",
                refreshable=True,
                download_strategy="official_godrive_directory",
                source_url="https://www.rrc.texas.gov/resource-center/research/",
                download_url="https://mft.rrc.texas.gov/link/example",
                target_path=tmp_path / "raw" / "gis" / "wells",
                refresh_cadence="twice_weekly",
                row_count=255,
                selected_files=(),
            )

    monkeypatch.setattr(raw_refresh, "RawSnapshotRefresher", FakeRefresher)

    result = CliRunner().invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "well_gis_layers",
            "--source",
            "production_pdq",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "well_gis_layers" in result.output
    assert "production_pdq" in result.output


def test_raw_refresh_cli_rejects_date_window_for_single_file(tmp_path):
    from typer.testing import CliRunner

    from worldenergydata.cli.commands.texas_rrc import app

    result = CliRunner().invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "production_pdq",
            "--since-date",
            "2026-06-01",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "date-window options only apply to directory sources" in result.output


def test_raw_refresh_cli_rejects_date_window_for_gis_directory(tmp_path):
    from typer.testing import CliRunner

    from worldenergydata.cli.commands.texas_rrc import app

    result = CliRunner().invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "well_gis_layers",
            "--since-date",
            "2026-06-01",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "date-window options only apply to dated directory sources" in result.output


def test_raw_refresh_cli_rejects_unknown_directory_selection(tmp_path):
    from typer.testing import CliRunner

    from worldenergydata.cli.commands.texas_rrc import app

    result = CliRunner().invoke(
        app,
        [
            "refresh",
            "--dry-run",
            "--source",
            "well_gis_layers",
            "--selection",
            "yesterday",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "selection must be one of" in result.output
