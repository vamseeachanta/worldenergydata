"""Validated HSE filters and explicit database connection ownership.

Connection lifecycle follows SQLAlchemy 2.0, asyncio extension documentation,
sections 'Synopsis - ORM' and 'Using AsyncSession with Concurrent Tasks':
https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
"""

from contextlib import contextmanager
from datetime import MAXYEAR, MINYEAR
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker


class HSEQueryConfig(BaseModel):
    """An existing SQLite database; no schema creation or sample fallback.

    Pool defaults are application resource settings, not engineering limits.
    Async access uses the ``aiosqlite`` driver.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    database_url: str = Field(repr=False)
    pool_size: int = Field(default=1, gt=0)
    max_overflow: int = Field(default=0, ge=0)

    @field_validator("database_url")
    @classmethod
    def validate_url(cls, value):
        try:
            url = make_url(value)
        except ArgumentError as exc:
            raise ValueError("A SQLite database URL is required") from exc
        if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise ValueError("A synchronous SQLite database URL is required")
        if not url.database or url.database == ":memory:" or url.query:
            raise ValueError("An existing SQLite file without URL options is required")
        return value


class QueryFilters(BaseModel):
    """Strict normalized filter types; unsupported evidence stays explicit."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    operators: list[str] | None = None
    incident_types: list[str] | None = None
    severities: list[str] | None = None
    fields: list[str] | None = None
    sources: list[Literal["bsee_inc", "osha"]] | None = None
    penalty_statuses: list[str] | None = None
    naics_codes: list[str] | None = None
    chemicals: list[str] | None = None
    states: list[str] | None = None
    start_year: int | None = Field(default=None, ge=MINYEAR, le=MAXYEAR)
    end_year: int | None = Field(default=None, ge=MINYEAR, le=MAXYEAR)
    min_amount: float | None = Field(default=None, ge=0)
    grouping: Literal["operator", "field_name", "report_date"] | None = None
    metric: str | None = None
    chemical_carcinogen: bool | None = None
    limit: int | None = Field(default=None, gt=0)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def ordered_years(self):
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError("start_year must not exceed end_year")
        return self


class HSEBackend:
    """Share engines, allocate one session per query, release owned pools."""

    def __init__(self, config: HSEQueryConfig):
        self.config = config
        url = make_url(config.database_url)
        path = Path(url.database).resolve()
        if not path.is_file():
            raise FileNotFoundError("Configured HSE database does not exist")
        # Resolve once so a later working-directory change cannot redirect reads.
        self.url = url.set(database=str(path))
        self.engine = create_engine(
            self.url, pool_size=config.pool_size, max_overflow=config.max_overflow
        )
        self.sessions = sessionmaker(self.engine)
        self.async_engine = None

    @contextmanager
    def session(self):
        with self.sessions() as session:
            yield session

    def async_session(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        if self.async_engine is None:
            self.async_engine = create_async_engine(
                self.url.set(drivername="sqlite+aiosqlite"),
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
            )
        return async_sessionmaker(self.async_engine)()

    def close(self):
        self.engine.dispose()

    async def aclose(self):
        if self.async_engine is not None:
            await self.async_engine.dispose()
            self.async_engine = None
        self.close()
