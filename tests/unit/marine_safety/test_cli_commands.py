# ABOUTME: Tests for marine_safety CLI subcommands (db init/migrate/seed, export, scrape).
# ABOUTME: Uses tmp_path for database files to avoid side effects.

"""
Tests for marine_safety CLI subcommands.

Tests db init, migrate, seed, export, and scrape --help.
"""

import csv
import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from worldenergydata.marine_safety.cli_db import _create_schema, db
from worldenergydata.marine_safety.cli_export import export

runner = CliRunner()


# ---------------------------------------------------------------------------
# db init
# ---------------------------------------------------------------------------


class TestDbInit:
    """Test the 'db init' CLI subcommand."""

    def test_init_help(self):
        result = runner.invoke(db, ["init", "--help"])
        assert result.exit_code == 0
        assert "force" in result.output.lower()

    def test_init_creates_database(self, tmp_path):
        db_file = tmp_path / "test.db"
        result = runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])
        assert result.exit_code == 0
        assert db_file.exists()

        # Verify tables were created
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        assert "incidents" in tables
        assert "vessels" in tables
        assert "companies" in tables
        assert "locations" in tables
        assert "schema_version" in tables

    def test_init_force_recreates(self, tmp_path):
        db_file = tmp_path / "test.db"
        # First init
        runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])
        assert db_file.exists()

        # Insert a row to detect recreation
        conn = sqlite3.connect(str(db_file))
        conn.execute(
            "INSERT INTO incidents (source_agency, source_incident_id, incident_date, incident_type)"
            " VALUES ('test', 'T001', '2024-01-01', 'other')"
        )
        conn.commit()
        conn.close()

        # Force recreate (--force auto-confirms in non-interactive)
        result = runner.invoke(
            db, ["init", "--force", "--db-url", f"sqlite:///{db_file}"], input="y\n"
        )
        assert result.exit_code == 0

        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM incidents")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 0


# ---------------------------------------------------------------------------
# db migrate
# ---------------------------------------------------------------------------


class TestDbMigrate:
    """Test the 'db migrate' CLI subcommand."""

    def test_migrate_help(self):
        result = runner.invoke(db, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output.lower() or "dry" in result.output.lower()

    def test_migrate_check_up_to_date(self, tmp_path):
        db_file = tmp_path / "test.db"
        runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])

        result = runner.invoke(
            db, ["migrate", "--check", "--db-url", f"sqlite:///{db_file}"]
        )
        assert result.exit_code == 0
        assert "up to date" in result.output.lower()

    def test_migrate_no_db_fails(self, tmp_path):
        db_file = tmp_path / "nonexistent.db"
        result = runner.invoke(
            db, ["migrate", "--check", "--db-url", f"sqlite:///{db_file}"]
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# db seed
# ---------------------------------------------------------------------------


class TestDbSeed:
    """Test the 'db seed' CLI subcommand."""

    def test_seed_help(self):
        result = runner.invoke(db, ["seed", "--help"])
        assert result.exit_code == 0
        assert "data-dir" in result.output.lower() or "clear" in result.output.lower()

    def test_seed_loads_data(self, tmp_path):
        # Create a database
        db_file = tmp_path / "test.db"
        runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])

        # Create a small seed CSV
        seed_dir = tmp_path / "seeds"
        seed_dir.mkdir()
        seed_csv = seed_dir / "test_incidents.csv"
        seed_csv.write_text(
            "incident_id,date,vessel_name,description,fatalities,location\n"
            "T001,2024-01-01,MV Test,Test incident,0,North Atlantic\n"
            "T002,2024-02-01,SS Example,Another incident,1,Gulf of Mexico\n"
        )

        result = runner.invoke(
            db,
            ["seed", "--data-dir", str(seed_dir), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code == 0
        assert "2" in result.output  # 2 records loaded

        # Verify data in database
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM incidents")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 2

    def test_seed_no_db_fails(self, tmp_path):
        db_file = tmp_path / "nonexistent.db"
        result = runner.invoke(
            db,
            ["seed", "--data-dir", str(tmp_path), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


class TestExport:
    """Test the 'export' CLI subcommand."""

    def test_export_help(self):
        result = runner.invoke(export, ["--help"])
        assert result.exit_code == 0
        assert "csv" in result.output.lower()
        assert "json" in result.output.lower()

    def test_export_csv(self, tmp_path):
        # Set up a database with data
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        _create_schema(conn)
        conn.execute(
            "INSERT INTO incidents (source_agency, source_incident_id, incident_date, incident_type, title)"
            " VALUES ('uscg', 'U001', '2024-03-01', 'collision', 'Test collision')"
        )
        conn.commit()
        conn.close()

        out_file = tmp_path / "out.csv"
        result = runner.invoke(
            export,
            ["csv", "--output", str(out_file), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code == 0
        assert out_file.exists()

        with open(out_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["source_incident_id"] == "U001"

    def test_export_json(self, tmp_path):
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        _create_schema(conn)
        conn.execute(
            "INSERT INTO incidents (source_agency, source_incident_id, incident_date, incident_type)"
            " VALUES ('ntsb', 'N001', '2024-05-01', 'grounding')"
        )
        conn.commit()
        conn.close()

        out_file = tmp_path / "out.json"
        result = runner.invoke(
            export,
            ["json", "--output", str(out_file), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code == 0
        assert out_file.exists()

        with open(out_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["source_incident_id"] == "N001"

    def test_export_source_filter(self, tmp_path):
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        _create_schema(conn)
        conn.execute(
            "INSERT INTO incidents (source_agency, source_incident_id, incident_date, incident_type)"
            " VALUES ('uscg', 'U001', '2024-01-01', 'collision')"
        )
        conn.execute(
            "INSERT INTO incidents (source_agency, source_incident_id, incident_date, incident_type)"
            " VALUES ('ntsb', 'N001', '2024-01-01', 'grounding')"
        )
        conn.commit()
        conn.close()

        out_file = tmp_path / "filtered.csv"
        result = runner.invoke(
            export,
            [
                "csv",
                "--output",
                str(out_file),
                "--source",
                "uscg",
                "--db-url",
                f"sqlite:///{db_file}",
            ],
        )
        assert result.exit_code == 0

        with open(out_file) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["source_agency"] == "uscg"

    def test_export_no_db_fails(self, tmp_path):
        db_file = tmp_path / "nonexistent.db"
        out_file = tmp_path / "out.csv"
        result = runner.invoke(
            export,
            ["csv", "--output", str(out_file), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# scrape (help only -- actual scraping requires network)
# ---------------------------------------------------------------------------


class TestScrapeHelp:
    """Test scrape subcommands show help without crashing."""

    def test_scrape_group_help(self):
        from worldenergydata.marine_safety.cli_scrape import scrape

        result = runner.invoke(scrape, ["--help"])
        assert result.exit_code == 0
        assert "uscg" in result.output.lower()
        assert "ntsb" in result.output.lower()

    def test_scrape_uscg_help(self):
        from worldenergydata.marine_safety.cli_scrape import scrape

        result = runner.invoke(scrape, ["uscg", "--help"])
        assert result.exit_code == 0
        assert "start-year" in result.output.lower()
        assert "dry-run" in result.output.lower()

    def test_scrape_ntsb_help(self):
        from worldenergydata.marine_safety.cli_scrape import scrape

        result = runner.invoke(scrape, ["ntsb", "--help"])
        assert result.exit_code == 0

    def test_scrape_atsb_help(self):
        from worldenergydata.marine_safety.cli_scrape import scrape

        result = runner.invoke(scrape, ["atsb", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Integration: init + seed + export round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Test full round-trip: init -> seed -> export."""

    def test_init_seed_export_csv(self, tmp_path):
        db_file = tmp_path / "roundtrip.db"

        # Create seed data
        seed_dir = tmp_path / "seeds"
        seed_dir.mkdir()
        seed_csv = seed_dir / "test_incidents.csv"
        seed_csv.write_text(
            "incident_id,date,vessel_name,description,fatalities,location\n"
            "RT001,2024-06-01,MV RoundTrip,Round trip test,0,Pacific\n"
            "RT002,2024-06-02,SS Journey,Another test,2,Atlantic\n"
            "RT003,2024-06-03,TS Voyage,Third test,0,Caribbean\n"
        )

        # Init
        result = runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])
        assert result.exit_code == 0

        # Seed
        result = runner.invoke(
            db,
            ["seed", "--data-dir", str(seed_dir), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code == 0
        assert "3" in result.output

        # Export
        out_file = tmp_path / "exported.json"
        result = runner.invoke(
            export,
            ["json", "--output", str(out_file), "--db-url", f"sqlite:///{db_file}"],
        )
        assert result.exit_code == 0
        assert out_file.exists()

        with open(out_file) as f:
            data = json.load(f)
        assert len(data) == 3

    def test_init_seed_export_with_limit(self, tmp_path):
        db_file = tmp_path / "limited.db"
        seed_dir = tmp_path / "seeds"
        seed_dir.mkdir()
        seed_csv = seed_dir / "incidents.csv"
        rows = ["incident_id,date,vessel_name,description,fatalities,location"]
        for i in range(10):
            rows.append(f"L{i:03d},2024-01-{i+1:02d},Vessel {i},Desc {i},0,Atlantic")
        seed_csv.write_text("\n".join(rows) + "\n")

        runner.invoke(db, ["init", "--db-url", f"sqlite:///{db_file}"])
        runner.invoke(
            db,
            ["seed", "--data-dir", str(seed_dir), "--db-url", f"sqlite:///{db_file}"],
        )

        out_file = tmp_path / "limited.csv"
        result = runner.invoke(
            export,
            [
                "csv",
                "--output",
                str(out_file),
                "--limit",
                "3",
                "--db-url",
                f"sqlite:///{db_file}",
            ],
        )
        assert result.exit_code == 0

        with open(out_file) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3
