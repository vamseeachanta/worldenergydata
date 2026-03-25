"""
Database Package for Marine Safety Module

Provides database models, connection management, and ORM functionality.
"""

from typing import List

__all__: List[str] = ["models", "db_manager"]

from worldenergydata.marine_safety.database import models
from worldenergydata.marine_safety.database import db_manager
