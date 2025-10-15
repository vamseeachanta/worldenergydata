"""Pytest configuration and fixtures for marine_safety module tests.

This module provides reusable fixtures for testing marine safety incident
database operations, parsers, and API interactions.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.modules.marine_safety.fixtures.sample_data import (
  generate_incident,
  generate_vessel,
  SAMPLE_USCG_REPORT,
  SAMPLE_USCG_PDF_TEXT,
  SAMPLE_INCIDENT_DATA
)


@pytest.fixture(scope='function')
def test_db():
  """Create an in-memory SQLite database for testing.

  Returns:
    SQLAlchemy Engine: In-memory database engine
  """
  engine = create_engine(
    'sqlite:///:memory:',
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
    echo=False
  )

  # Enable foreign key support for SQLite
  @event.listens_for(engine, "connect")
  def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

  yield engine

  engine.dispose()


@pytest.fixture(scope='function')
def test_session(test_db):
  """Create a database session for testing.

  Args:
    test_db: Test database engine fixture

  Returns:
    SQLAlchemy Session: Database session with automatic rollback
  """
  from src.modules.marine_safety.models import Base

  # Create all tables
  Base.metadata.create_all(test_db)

  # Create session
  Session = sessionmaker(bind=test_db)
  session = Session()

  yield session

  # Cleanup
  session.close()
  Base.metadata.drop_all(test_db)


@pytest.fixture
def sample_incident():
  """Generate a sample incident with realistic data.

  Returns:
    dict: Complete incident data dictionary
  """
  return generate_incident()


@pytest.fixture
def sample_incident_batch():
  """Generate multiple sample incidents.

  Returns:
    list: List of incident dictionaries
  """
  from tests.modules.marine_safety.fixtures.sample_data import generate_batch
  return generate_batch(count=5)


@pytest.fixture
def sample_vessel():
  """Generate a sample vessel with realistic data.

  Returns:
    dict: Complete vessel data dictionary
  """
  return generate_vessel()


@pytest.fixture
def mock_uscg_html():
  """Sample USCG incident report HTML.

  Returns:
    str: HTML content of a realistic USCG report
  """
  return SAMPLE_USCG_REPORT


@pytest.fixture
def mock_uscg_pdf_text():
  """Sample USCG PDF report extracted text.

  Returns:
    str: Extracted text content from a USCG PDF report
  """
  return SAMPLE_USCG_PDF_TEXT


@pytest.fixture
def temp_data_dir():
  """Create a temporary directory for test data files.

  Yields:
    Path: Temporary directory path
  """
  with tempfile.TemporaryDirectory() as tmpdir:
    yield Path(tmpdir)


@pytest.fixture
def mock_uscg_api_response():
  """Mock USCG API response data.

  Returns:
    dict: Simulated API response with incident data
  """
  return {
    'status': 'success',
    'data': {
      'incidents': [generate_incident() for _ in range(3)],
      'total': 3,
      'page': 1,
      'per_page': 10
    },
    'timestamp': datetime.utcnow().isoformat()
  }


@pytest.fixture
def sample_incident_variations():
  """Generate incidents with various edge cases and scenarios.

  Returns:
    dict: Dictionary of named incident variations
  """
  return {
    'minimal': {
      'incident_id': 'MIN-2024-001',
      'date': datetime(2024, 1, 15),
      'location': 'Gulf of Mexico',
      'incident_type': 'Unknown'
    },
    'complete': SAMPLE_INCIDENT_DATA,
    'with_casualties': {
      **generate_incident(),
      'fatalities': 2,
      'injuries': 5,
      'casualties_description': 'Two crew members lost, five injured during storm'
    },
    'pollution_event': {
      **generate_incident(),
      'incident_type': 'Pollution',
      'pollution_type': 'Oil Spill',
      'pollution_volume': 5000.0,
      'pollution_volume_unit': 'gallons',
      'environmental_impact': 'Significant impact to marine wildlife'
    },
    'collision': {
      **generate_incident(),
      'incident_type': 'Collision',
      'vessels_involved': 2,
      'collision_type': 'Vessel-to-Vessel',
      'weather_conditions': 'Poor visibility, heavy fog'
    },
    'future_date': {
      **generate_incident(),
      'date': datetime.utcnow() + timedelta(days=30)
    },
    'historical': {
      **generate_incident(),
      'date': datetime(1990, 6, 15),
      'legacy_system_id': 'LEGACY-1990-123'
    }
  }


@pytest.fixture
def mock_database_error():
  """Fixture to simulate database errors.

  Returns:
    Exception: Database-related exception
  """
  from sqlalchemy.exc import OperationalError
  return OperationalError("Database connection failed", None, None)


@pytest.fixture
def sample_coordinates():
  """Sample geographic coordinates for testing.

  Returns:
    list: List of (latitude, longitude) tuples
  """
  return [
    (29.7604, -95.3698),  # Houston, TX
    (25.7617, -80.1918),  # Miami, FL
    (47.6062, -122.3321),  # Seattle, WA
    (37.7749, -122.4194),  # San Francisco, CA
    (61.2181, -149.9003),  # Anchorage, AK
    (21.3099, -157.8581),  # Honolulu, HI
  ]


@pytest.fixture
def performance_test_data():
  """Generate large dataset for performance testing.

  Returns:
    list: Large list of incident dictionaries
  """
  from tests.modules.marine_safety.fixtures.sample_data import generate_batch
  return generate_batch(count=1000)


@pytest.fixture(autouse=True)
def reset_test_state():
  """Reset any global state before each test.

  This fixture runs automatically before each test function.
  """
  # Clear any caches
  # Reset singleton instances
  # Clean up global state
  yield
  # Cleanup after test
  pass
