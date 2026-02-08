#!/usr/bin/env python3
"""
Database Initialization Script for Marine Safety Incidents Database

This script deploys database schemas optimized for each database type:
- PostgreSQL: Full-featured schema with partitioning, PostGIS, advanced indexes
- SQLite: Compatible schema for development with simplified features

PostgreSQL Features:
- Core tables with partitioning
- PostGIS spatial indexes
- Materialized views
- Triggers and functions
- Row-level security
- Database roles
- Reference data seeding

SQLite Features:
- Core tables (no partitioning)
- Basic indexes
- Views (no materialized views)
- Reference data seeding

Usage:
    # PostgreSQL (production)
    python init_db.py --db-url postgresql://user:pass@localhost/marine_safety

    # SQLite (development) - uses schema_sqlite.sql
    python init_db.py --dev-mode --db-url sqlite:///marine_safety.db

    # Verify only (dry-run)
    python init_db.py --verify-only --db-url postgresql://user:pass@localhost/marine_safety

    # With environment variable
    export DATABASE_URL=postgresql://user:pass@localhost/marine_safety
    python init_db.py

Author: WorldEnergyData Project
Date: 2025-10-03
Version: 2.1.0
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize and deploy the marine safety incidents database schema."""

    def __init__(
        self,
        db_url: str,
        dev_mode: bool = False,
        verify_only: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize the database deployment manager.

        Args:
            db_url: Database connection URL
            dev_mode: Use SQLite for development
            verify_only: Only verify schema, don't create
            dry_run: Print SQL without executing
        """
        self.db_url = db_url
        self.dev_mode = dev_mode
        self.verify_only = verify_only
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None

        # Determine database type
        self.is_postgresql = db_url.startswith('postgresql://') or db_url.startswith('postgres://')
        self.is_sqlite = db_url.startswith('sqlite:///')

        # Path to SQL schema file
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        schema_dir = project_root / 'specs' / 'modules' / 'analysis' / 'marine' / 'sub-specs'

        # Select appropriate schema file based on database type or dev mode
        if dev_mode or self.is_sqlite:
            self.schema_path = schema_dir / 'schema_sqlite.sql'
            logger.info("Using SQLite-compatible schema")
        else:
            self.schema_path = project_root / 'specs' / 'modules' / 'analysis' / 'marine' / 'sub-specs' / 'database-schema-optimized.sql'
            logger.info("Using PostgreSQL optimized schema")

        logger.info(f"Database type: {'PostgreSQL' if self.is_postgresql else 'SQLite'}")
        logger.info(f"Schema path: {self.schema_path}")
        logger.info(f"Mode: {'VERIFY ONLY' if verify_only else 'DRY RUN' if dry_run else 'DEPLOY'}")

    def connect(self) -> None:
        """Establish database connection."""
        try:
            if self.is_postgresql:
                if not PSYCOPG2_AVAILABLE:
                    raise ImportError("psycopg2 not available. Install with: pip install psycopg2-binary")

                # Parse PostgreSQL URL
                # Format: postgresql://user:password@host:port/database
                url_parts = self.db_url.replace('postgresql://', '').replace('postgres://', '')

                if '@' in url_parts:
                    auth, location = url_parts.split('@', 1)
                    if ':' in auth:
                        user, password = auth.split(':', 1)
                    else:
                        user = auth
                        password = None
                else:
                    user = 'postgres'
                    password = None
                    location = url_parts

                if '/' in location:
                    host_port, database = location.split('/', 1)
                else:
                    host_port = location
                    database = 'marine_safety'

                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host = host_port
                    port = 5432

                self.conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                )
                self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                self.cursor = self.conn.cursor()
                logger.info(f"✓ Connected to PostgreSQL: {host}:{port}/{database}")

            elif self.is_sqlite:
                if not SQLITE_AVAILABLE:
                    raise ImportError("sqlite3 not available")

                db_path = self.db_url.replace('sqlite:///', '')
                self.conn = sqlite3.connect(db_path)
                self.cursor = self.conn.cursor()
                logger.info(f"✓ Connected to SQLite: {db_path}")

            else:
                raise ValueError(f"Unsupported database URL format: {self.db_url}")

        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✓ Disconnected from database")

    def execute_sql(self, sql_statement: str, description: str = "") -> None:
        """
        Execute SQL statement with error handling.

        Args:
            sql_statement: SQL to execute
            description: Human-readable description
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] {description}")
            logger.debug(f"SQL: {sql_statement[:200]}...")
            return

        try:
            if description:
                logger.info(f"Executing: {description}")
            self.cursor.execute(sql_statement)
            if description:
                logger.info(f"✓ {description}")
        except Exception as e:
            logger.error(f"✗ Failed: {description}")
            logger.error(f"Error: {e}")
            if not self.dry_run:
                raise

    def read_schema_file(self) -> str:
        """Read the SQL schema file appropriate for the database type."""
        if not self.schema_path.exists():
            schema_type = "SQLite" if (self.dev_mode or self.is_sqlite) else "PostgreSQL"
            error_msg = f"Schema file not found: {self.schema_path}\n"
            error_msg += f"Expected {schema_type} schema at: {self.schema_path}\n"

            # Provide helpful suggestions
            if schema_type == "SQLite":
                alt_path = self.schema_path.parent / 'database-schema-optimized.sql'
                if alt_path.exists():
                    error_msg += f"\nPostgreSQL schema found at: {alt_path}\n"
                    error_msg += "Create schema_sqlite.sql or use PostgreSQL mode (remove --dev-mode)"

            raise FileNotFoundError(error_msg)

        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        schema_type = "SQLite" if (self.dev_mode or self.is_sqlite) else "PostgreSQL"
        logger.info(f"✓ Read {schema_type} schema file: {len(schema_sql)} bytes")
        return schema_sql

    def parse_sql_statements(self, sql_content: str) -> List[Tuple[str, str]]:
        """
        Parse SQL content into individual statements with descriptions.

        Returns:
            List of (statement, description) tuples
        """
        statements = []
        current_statement = []
        current_description = ""
        in_comment = False

        for line in sql_content.split('\n'):
            stripped = line.strip()

            # Extract description from comments
            if stripped.startswith('--') and not stripped.startswith('---'):
                comment_text = stripped[2:].strip()
                if comment_text and not comment_text.startswith('='):
                    current_description = comment_text

            # Skip comment-only lines and separator lines
            if stripped.startswith('--') or not stripped:
                continue

            current_statement.append(line)

            # Statement ends with semicolon
            if stripped.endswith(';'):
                statement = '\n'.join(current_statement)
                statements.append((statement, current_description))
                current_statement = []
                current_description = ""

        logger.info(f"✓ Parsed {len(statements)} SQL statements")
        return statements

    def create_schema(self) -> None:
        """Deploy the complete database schema."""
        logger.info("=" * 80)
        logger.info("DEPLOYING DATABASE SCHEMA")
        logger.info("=" * 80)

        # Read schema file
        schema_sql = self.read_schema_file()

        # For SQLite, we need to adapt the schema
        if self.is_sqlite:
            logger.warning("SQLite mode: Some PostgreSQL-specific features will be skipped")
            schema_sql = self._adapt_schema_for_sqlite(schema_sql)

        # Parse into individual statements
        statements = self.parse_sql_statements(schema_sql)

        # Execute statements
        success_count = 0
        skip_count = 0
        error_count = 0

        for i, (statement, description) in enumerate(statements, 1):
            try:
                # Skip certain statements in SQLite mode
                if self.is_sqlite and self._should_skip_for_sqlite(statement):
                    skip_count += 1
                    logger.debug(f"[{i}/{len(statements)}] Skipped (SQLite): {description}")
                    continue

                desc = description or f"Statement {i}"
                self.execute_sql(statement, f"[{i}/{len(statements)}] {desc}")
                success_count += 1

            except Exception as e:
                error_count += 1
                logger.warning(f"Statement {i} failed (continuing): {e}")
                if self.dry_run:
                    break  # In dry run, stop after first error

        logger.info("=" * 80)
        logger.info(f"Schema deployment complete: {success_count} success, {skip_count} skipped, {error_count} errors")
        logger.info("=" * 80)

    def _adapt_schema_for_sqlite(self, schema_sql: str) -> str:
        """Adapt PostgreSQL schema for SQLite compatibility."""
        # SQLite adaptations (basic - full compatibility requires significant changes)
        adaptations = {
            'TIMESTAMPTZ': 'TIMESTAMP',
            'GEOGRAPHY(POINT, 4326)': 'TEXT',  # Store as WKT
            'SERIAL': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'BIGSERIAL': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'SMALLINT': 'INTEGER',
            'DECIMAL': 'REAL',
            '::geography': '',
            'GENERATED ALWAYS AS': '-- GENERATED ALWAYS AS',
            'PARTITION BY': '-- PARTITION BY',
            'ENABLE ROW LEVEL SECURITY': '-- ENABLE ROW LEVEL SECURITY',
        }

        adapted = schema_sql
        for pg_syntax, sqlite_syntax in adaptations.items():
            adapted = adapted.replace(pg_syntax, sqlite_syntax)

        return adapted

    def _should_skip_for_sqlite(self, statement: str) -> bool:
        """Check if statement should be skipped in SQLite mode."""
        skip_patterns = [
            'CREATE EXTENSION',
            'CREATE TYPE',
            'CREATE POLICY',
            'ALTER TABLE.*ENABLE ROW LEVEL SECURITY',
            'CREATE ROLE',
            'GRANT',
            'PARTITION OF',
            'CONCURRENTLY',
            'USING gin',
            'USING gist',
            'USING btree',
        ]

        statement_upper = statement.upper()
        for pattern in skip_patterns:
            if pattern.upper() in statement_upper:
                return True
        return False

    def verify_schema(self) -> Dict[str, int]:
        """
        Verify that the schema was created correctly.

        Returns:
            Dictionary with counts of database objects
        """
        logger.info("=" * 80)
        logger.info("VERIFYING SCHEMA")
        logger.info("=" * 80)

        verification = {
            'tables': 0,
            'indexes': 0,
            'views': 0,
            'materialized_views': 0,
            'triggers': 0,
            'functions': 0,
            'types': 0,
        }

        if self.is_postgresql:
            # Query PostgreSQL system catalogs
            queries = {
                'tables': """
                    SELECT count(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """,
                'views': """
                    SELECT count(*) FROM information_schema.views
                    WHERE table_schema = 'public'
                """,
                'materialized_views': """
                    SELECT count(*) FROM pg_matviews
                    WHERE schemaname = 'public'
                """,
                'indexes': """
                    SELECT count(*) FROM pg_indexes
                    WHERE schemaname = 'public'
                """,
                'triggers': """
                    SELECT count(*) FROM information_schema.triggers
                    WHERE trigger_schema = 'public'
                """,
                'functions': """
                    SELECT count(*) FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname = 'public'
                """,
                'types': """
                    SELECT count(*) FROM pg_type t
                    JOIN pg_namespace n ON t.typnamespace = n.oid
                    WHERE n.nspname = 'public' AND t.typtype = 'e'
                """,
            }

            for obj_type, query in queries.items():
                try:
                    self.cursor.execute(query)
                    count = self.cursor.fetchone()[0]
                    verification[obj_type] = count
                    logger.info(f"✓ {obj_type.capitalize()}: {count}")
                except Exception as e:
                    logger.error(f"✗ Could not verify {obj_type}: {e}")

        elif self.is_sqlite:
            # Query SQLite master table
            try:
                self.cursor.execute("SELECT type, count(*) FROM sqlite_master GROUP BY type")
                for obj_type, count in self.cursor.fetchall():
                    if obj_type == 'table':
                        verification['tables'] = count
                    elif obj_type == 'index':
                        verification['indexes'] = count
                    elif obj_type == 'view':
                        verification['views'] = count
                    elif obj_type == 'trigger':
                        verification['triggers'] = count
                    logger.info(f"✓ {obj_type.capitalize()}s: {count}")
            except Exception as e:
                logger.error(f"✗ Verification failed: {e}")

        logger.info("=" * 80)
        return verification

    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        logger.info("=" * 80)
        logger.info("DATABASE TABLES")
        logger.info("=" * 80)

        tables = []

        if self.is_postgresql:
            self.cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in self.cursor.fetchall()]

        elif self.is_sqlite:
            self.cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """)
            tables = [row[0] for row in self.cursor.fetchall()]

        for i, table in enumerate(tables, 1):
            logger.info(f"{i:3d}. {table}")

        logger.info(f"\nTotal tables: {len(tables)}")
        logger.info("=" * 80)
        return tables

    def seed_reference_data(self) -> None:
        """Seed reference data (incident types and data sources)."""
        logger.info("=" * 80)
        logger.info("SEEDING REFERENCE DATA")
        logger.info("=" * 80)

        # Check if data already exists
        if not self.dry_run:
            self.cursor.execute("SELECT COUNT(*) FROM incident_types")
            type_count = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM data_sources")
            source_count = self.cursor.fetchone()[0]

            if type_count > 0 or source_count > 0:
                logger.warning(f"Reference data already exists (types: {type_count}, sources: {source_count})")
                logger.info("Skipping seed (use --force to override)")
                return

        # The reference data is already in the SQL schema file
        # This is executed as part of create_schema()
        logger.info("✓ Reference data seeded via schema")
        logger.info("=" * 80)

    def create_admin_user(self, username: str = 'admin', password: Optional[str] = None) -> None:
        """
        Create initial admin user (PostgreSQL only).

        Args:
            username: Admin username
            password: Admin password (prompts if not provided)
        """
        if not self.is_postgresql:
            logger.info("Admin user creation only supported for PostgreSQL")
            return

        logger.info("=" * 80)
        logger.info("CREATING ADMIN USER")
        logger.info("=" * 80)

        try:
            # Check if user exists
            self.cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s",
                (username,)
            )

            if self.cursor.fetchone():
                logger.warning(f"User '{username}' already exists")
                return

            # Create user with password
            if password:
                create_sql = sql.SQL("CREATE USER {} WITH PASSWORD %s IN ROLE marine_safety_admin").format(
                    sql.Identifier(username)
                )
                self.execute_sql(create_sql.as_string(self.conn), f"Creating user: {username}")
                self.cursor.execute(create_sql, (password,))
            else:
                # Create user without password (must be set later)
                create_sql = sql.SQL("CREATE USER {} IN ROLE marine_safety_admin").format(
                    sql.Identifier(username)
                )
                self.execute_sql(create_sql.as_string(self.conn), f"Creating user: {username}")
                logger.warning(f"User '{username}' created without password - set with ALTER USER")

            logger.info(f"✓ Admin user '{username}' created")

        except Exception as e:
            logger.error(f"✗ Failed to create admin user: {e}")

        logger.info("=" * 80)

    def print_summary(self, verification: Dict[str, int]) -> None:
        """Print deployment summary."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Database URL: {self.db_url}")
        logger.info(f"Database Type: {'PostgreSQL' if self.is_postgresql else 'SQLite'}")
        logger.info(f"Schema File: {self.schema_path}")
        logger.info("")
        logger.info("Objects Created:")
        logger.info(f"  Tables:              {verification.get('tables', 0):3d}")
        logger.info(f"  Indexes:             {verification.get('indexes', 0):3d}")
        logger.info(f"  Views:               {verification.get('views', 0):3d}")
        logger.info(f"  Materialized Views:  {verification.get('materialized_views', 0):3d}")
        logger.info(f"  Triggers:            {verification.get('triggers', 0):3d}")
        logger.info(f"  Functions:           {verification.get('functions', 0):3d}")
        logger.info(f"  Custom Types:        {verification.get('types', 0):3d}")
        logger.info("")
        logger.info("✓ Database initialization complete!")
        logger.info("=" * 80)

    def run(self) -> None:
        """Execute the complete initialization workflow."""
        try:
            # Connect to database
            self.connect()

            if self.verify_only:
                # Verification mode only
                verification = self.verify_schema()
                self.list_tables()
                self.print_summary(verification)
            else:
                # Full deployment
                self.create_schema()
                verification = self.verify_schema()
                self.list_tables()

                # Seed reference data (already in schema)
                # self.seed_reference_data()  # Commented - data in schema

                self.print_summary(verification)

        except Exception as e:
            logger.error(f"✗ Initialization failed: {e}")
            raise
        finally:
            self.disconnect()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Initialize Marine Safety Incidents Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # PostgreSQL production deployment
  python init_db.py --db-url postgresql://user:pass@localhost/marine_safety

  # SQLite development mode
  python init_db.py --dev-mode --db-url sqlite:///marine_safety.db

  # Verify existing database
  python init_db.py --verify-only --db-url postgresql://user:pass@localhost/marine_safety

  # Dry run (print SQL without executing)
  python init_db.py --dry-run --db-url postgresql://user:pass@localhost/marine_safety

  # Use environment variable
  export DATABASE_URL=postgresql://user:pass@localhost/marine_safety
  python init_db.py
        """
    )

    parser.add_argument(
        '--db-url',
        type=str,
        default=os.getenv('DATABASE_URL'),
        help='Database connection URL (default: $DATABASE_URL)'
    )

    parser.add_argument(
        '--dev-mode',
        action='store_true',
        help='Use SQLite schema (schema_sqlite.sql) for development (limited features)'
    )

    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify schema, do not create (read-only)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL statements without executing'
    )

    parser.add_argument(
        '--create-admin',
        action='store_true',
        help='Create admin user after deployment (PostgreSQL only)'
    )

    parser.add_argument(
        '--admin-user',
        type=str,
        default='admin',
        help='Admin username (default: admin)'
    )

    parser.add_argument(
        '--admin-password',
        type=str,
        help='Admin password (prompts if not provided)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Configure logging verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.db_url:
        logger.error("Database URL required: use --db-url or set DATABASE_URL environment variable")
        return 1

    # Check dependencies
    if args.db_url.startswith('postgresql') and not PSYCOPG2_AVAILABLE:
        logger.error("PostgreSQL support requires psycopg2: pip install psycopg2-binary")
        return 1

    if args.db_url.startswith('sqlite') and not SQLITE_AVAILABLE:
        logger.error("SQLite support not available")
        return 1

    # Initialize database
    try:
        initializer = DatabaseInitializer(
            db_url=args.db_url,
            dev_mode=args.dev_mode,
            verify_only=args.verify_only,
            dry_run=args.dry_run
        )

        initializer.run()

        # Create admin user if requested
        if args.create_admin and not args.verify_only and not args.dry_run:
            initializer.connect()
            initializer.create_admin_user(
                username=args.admin_user,
                password=args.admin_password
            )
            initializer.disconnect()

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
