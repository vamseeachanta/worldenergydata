# ABOUTME: CLI commands for database management operations.
# ABOUTME: Provides init, migrate, and seed commands for the marine safety database.

"""
Marine Safety CLI - Database Commands

Commands for database management operations using SQLite.
"""

import csv
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import click

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.marine_safety.cli_utils import (
    console,
    create_progress_spinner,
)

# Schema version tracked inside the database
_CURRENT_SCHEMA_VERSION = 1


def _default_db_path() -> Path:
    """Return the default SQLite database path.

    Resolves the marine_safety data dir via ``worldenergydata.common``'s data
    resolver (WED_DATA_ROOT / workspace-root ``data/``) instead of a
    ``__file__``-relative parent walk — the latter pointed at the repo root
    only while this domain lived under ``src/``; after the Phase 2 carve into
    ``packages/worldenergydata-marine_safety/`` (#529) it would resolve to the
    member root, so use the carve-safe resolver.
    """
    return get_module_data_safe("marine_safety") / "marine_safety.db"


def _resolve_db_path(db_url: Optional[str]) -> Path:
    """Resolve a db-url string to a concrete Path."""
    if db_url:
        path_str = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        return Path(path_str)
    return _default_db_path()


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables from scratch."""
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS companies (
            company_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE,
            country      TEXT,
            company_type TEXT,
            is_active    INTEGER DEFAULT 1,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vessels (
            vessel_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            vessel_name TEXT NOT NULL,
            vessel_type TEXT,
            imo_number  TEXT UNIQUE,
            flag_state  TEXT,
            year_built  INTEGER,
            gross_tonnage REAL,
            company_id  INTEGER REFERENCES companies(company_id),
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS locations (
            location_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT,
            latitude      REAL CHECK(latitude >= -90 AND latitude <= 90),
            longitude     REAL CHECK(longitude >= -180 AND longitude <= 180),
            water_depth_meters REAL,
            region_code   TEXT,
            country_code  TEXT
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source_agency      TEXT NOT NULL,
            source_incident_id TEXT NOT NULL,
            incident_date      DATE NOT NULL,
            incident_type      TEXT NOT NULL DEFAULT 'other',
            severity_level     INTEGER DEFAULT 3,
            status             TEXT DEFAULT 'reported',
            title              TEXT,
            description        TEXT,
            vessel_id          INTEGER REFERENCES vessels(vessel_id),
            company_id         INTEGER REFERENCES companies(company_id),
            location_id        INTEGER REFERENCES locations(location_id),
            fatalities         INTEGER DEFAULT 0,
            injuries           INTEGER DEFAULT 0,
            missing_persons    INTEGER DEFAULT 0,
            data_quality_score REAL,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_agency, source_incident_id)
        );

        CREATE INDEX IF NOT EXISTS idx_incident_date ON incidents(incident_date);
        CREATE INDEX IF NOT EXISTS idx_incident_source ON incidents(source_agency);
        CREATE INDEX IF NOT EXISTS idx_incident_type ON incidents(incident_type);

        CREATE TABLE IF NOT EXISTS incident_causes (
            cause_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id    INTEGER NOT NULL REFERENCES incidents(incident_id),
            cause_category TEXT NOT NULL,
            cause_description TEXT,
            is_primary     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS incident_documents (
            document_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id   INTEGER NOT NULL REFERENCES incidents(incident_id),
            document_type TEXT NOT NULL,
            document_url  TEXT NOT NULL,
            document_title TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(incident_id, document_url)
        );

        CREATE TABLE IF NOT EXISTS scrape_logs (
            scrape_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source_agency    TEXT NOT NULL,
            scrape_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status           TEXT NOT NULL,
            records_found    INTEGER DEFAULT 0,
            records_created  INTEGER DEFAULT 0,
            records_updated  INTEGER DEFAULT 0,
            records_failed   INTEGER DEFAULT 0,
            error_message    TEXT
        );

        CREATE TABLE IF NOT EXISTS incident_links (
            link_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id_1 INTEGER NOT NULL REFERENCES incidents(incident_id),
            incident_id_2 INTEGER NOT NULL REFERENCES incidents(incident_id),
            confidence_score REAL NOT NULL,
            match_type    TEXT NOT NULL,
            verified      INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(incident_id_1, incident_id_2)
        );
        """
    )

    # Record schema version
    cur.execute("DELETE FROM schema_version")
    cur.execute(
        "INSERT INTO schema_version (version) VALUES (?)", (_CURRENT_SCHEMA_VERSION,)
    )
    conn.commit()


@click.group()
def db():
    """Database management operations"""
    pass


@db.command()
@click.option("--force", is_flag=True, help="Force recreation of existing database")
@click.option("--db-url", help="Database connection URL (defaults to SQLite)")
def init(force: bool, db_url: Optional[str]):
    """
    Initialize database schema for marine safety data

    Creates all necessary tables, indexes, and constraints.

    Examples:
        marine-safety db init
        marine-safety db init --force
        marine-safety db init --db-url sqlite:///my.db
    """
    try:
        db_path = _resolve_db_path(db_url)

        if force and db_path.exists():
            if not click.confirm(
                "This will drop all existing tables. Continue?", default=False
            ):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
            db_path.unlink()

        db_path.parent.mkdir(parents=True, exist_ok=True)

        with create_progress_spinner("Initializing") as progress:
            task = progress.add_task(
                "[cyan]Initializing database schema...", total=None
            )

            conn = sqlite3.connect(str(db_path))
            try:
                _create_schema(conn)
            finally:
                conn.close()

            progress.update(task, completed=True)

        console.print(f"Database: {db_path}")
        console.print(
            "[green]v[/green] Database initialized successfully", style="bold"
        )

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@db.command()
@click.option("--check", is_flag=True, help="Only check schema version (no changes)")
@click.option("--dry-run", is_flag=True, help="Show migration plan without executing")
@click.option("--db-url", help="Database connection URL (defaults to SQLite)")
def migrate(check: bool, dry_run: bool, db_url: Optional[str]):
    """
    Run database migrations to update schema

    Examples:
        marine-safety db migrate --check
        marine-safety db migrate --dry-run
    """
    try:
        db_path = _resolve_db_path(db_url)

        if not db_path.exists():
            console.print("[red]Database not found.[/red] Run 'db init' first.")
            sys.exit(1)

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        try:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            has_version_table = cur.fetchone() is not None

            if not has_version_table:
                current_version = 0
            else:
                cur.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
                current_version = cur.fetchone()[0]

            console.print(f"Current schema version: {current_version}")
            console.print(f"Target schema version:  {_CURRENT_SCHEMA_VERSION}")

            if current_version >= _CURRENT_SCHEMA_VERSION:
                console.print("[green]v[/green] Schema is up to date", style="bold")
                return

            if check:
                console.print(
                    f"[yellow]Schema needs migration from v{current_version} "
                    f"to v{_CURRENT_SCHEMA_VERSION}[/yellow]"
                )
                return

            if dry_run:
                console.print("[dim]DRY RUN - would apply migrations[/dim]")
                return

            # Apply migrations by re-running schema (CREATE IF NOT EXISTS is safe)
            with create_progress_spinner("Migrating") as progress:
                task = progress.add_task(
                    "[cyan]Running database migrations...", total=None
                )
                _create_schema(conn)
                progress.update(task, completed=True)

            console.print(
                "[green]v[/green] Migrations completed successfully", style="bold"
            )

        finally:
            conn.close()

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@db.command()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Directory containing CSV seed files",
)
@click.option(
    "--clear-existing", is_flag=True, help="Clear existing data before seeding"
)
@click.option("--db-url", help="Database connection URL (defaults to SQLite)")
def seed(data_dir: Optional[Path], clear_existing: bool, db_url: Optional[str]):
    """
    Seed database with incident data from CSV files

    Loads CSV files from data/modules/marine_safety/input/ by default.

    Examples:
        marine-safety db seed
        marine-safety db seed --data-dir ./my-data
        marine-safety db seed --clear-existing
    """
    try:
        db_path = _resolve_db_path(db_url)

        if not db_path.exists():
            console.print("[red]Database not found.[/red] Run 'db init' first.")
            sys.exit(1)

        if data_dir is None:
            # Carve-safe data resolution (#529): resolve via the common data
            # resolver rather than a __file__-relative parent walk.
            data_dir = get_module_data_safe("marine_safety") / "input"

        csv_files = sorted(data_dir.glob("*.csv"))
        if not csv_files:
            console.print(f"[yellow]No CSV files found in {data_dir}[/yellow]")
            return

        if clear_existing:
            if not click.confirm(
                "This will delete all existing incident data. Continue?",
                default=False,
            ):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()

            if clear_existing:
                cur.execute("DELETE FROM incident_causes")
                cur.execute("DELETE FROM incident_documents")
                cur.execute("DELETE FROM incidents")
                conn.commit()
                console.print("[dim]Cleared existing incident data[/dim]")

            total_loaded = 0

            with create_progress_spinner("Seeding") as progress:
                task = progress.add_task("[cyan]Loading seed data...", total=None)

                for csv_file in csv_files:
                    file_count = _load_csv_seed(conn, csv_file)
                    total_loaded += file_count
                    console.print(f"  Loaded {file_count} records from {csv_file.name}")

                progress.update(task, completed=True)

            console.print(
                f"[green]v[/green] Seeded {total_loaded} total records",
                style="bold",
            )

        finally:
            conn.close()

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


def _load_csv_seed(conn: sqlite3.Connection, csv_path: Path) -> int:
    """Load a CSV seed file into the incidents table. Returns row count."""
    cur = conn.cursor()
    count = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incident_id = row.get("incident_id", "")
            source = _detect_source(csv_path.stem, incident_id)
            date_val = row.get("date", "")
            description = row.get("description", "")
            vessel_name = row.get("vessel_name", "")
            fatalities = int(row.get("fatalities", 0) or 0)
            row.get("location", "")
            row.get("severity", "")
            incident_type = _detect_type(csv_path.stem)

            title = f"{vessel_name} - {incident_type}" if vessel_name else incident_type

            try:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO incidents
                        (source_agency, source_incident_id, incident_date,
                         incident_type, title, description, fatalities)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source,
                        incident_id,
                        date_val,
                        incident_type,
                        title,
                        description,
                        fatalities,
                    ),
                )
                if cur.rowcount > 0:
                    count += 1
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    return count


def _detect_source(stem: str, incident_id: str) -> str:
    """Guess the source agency from filename or incident ID prefix."""
    stem_lower = stem.lower()
    if "uscg" in stem_lower or "misle" in stem_lower:
        return "uscg"
    if "ntsb" in stem_lower:
        return "ntsb"
    if "maib" in stem_lower:
        return "maib"
    if "bsee" in stem_lower:
        return "bsee"
    return "other"


def _detect_type(stem: str) -> str:
    """Guess the incident type from the CSV filename."""
    stem_lower = stem.lower()
    if "hatch" in stem_lower:
        return "equipment_failure"
    if "fatality" in stem_lower or "fatal" in stem_lower:
        return "fatality"
    if "founder" in stem_lower or "sinking" in stem_lower:
        return "capsizing"
    if "collision" in stem_lower:
        return "collision"
    if "fire" in stem_lower:
        return "fire"
    if "grounding" in stem_lower:
        return "grounding"
    return "other"
