# ABOUTME: BSEE data query API — thin wrappers over existing loaders.
# ABOUTME: Provides ProductionQuery, WellsQuery, CompaniesQuery for programmatic access.

"""BSEE data query API.

Thin wrappers over existing BSEE loaders that provide a clean, discoverable
interface for programmatic data consumers.

Usage::

    import worldenergydata as wed

    # Query production data
    df = wed.bsee.production.query(lease="G12345", years=range(2020, 2026))

    # Query well/borehole data
    df = wed.bsee.wells.query(field="Thunder Horse")

    # Query company/operator data
    df = wed.bsee.companies.query(name="Shell")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

import pandas as pd


class ProductionQuery:
    """Query BSEE production data with optional filters.

    Wraps :class:`~worldenergydata.bsee.data.loaders.production.production_loader.ProductionLoader`
    with a simpler, filter-oriented interface.

    Examples
    --------
    >>> from worldenergydata.bsee.api import ProductionQuery
    >>> pq = ProductionQuery()
    >>> df = pq.query(lease="G12345", years=range(2020, 2023))
    >>> df = pq.query(year=2022)
    >>> summary = pq.annual_summary(year=2022)
    """

    def __init__(self, bin_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize with optional custom binary data directory.

        Parameters
        ----------
        bin_dir : str or Path, optional
            Path to directory containing production .bin files.
            Defaults to the standard BSEE data location.
        """
        from worldenergydata.bsee.data.loaders.production.production_loader import (
            ProductionLoader,
        )

        self._loader = ProductionLoader(bin_dir=bin_dir)

    def query(
        self,
        *,
        lease: Optional[str] = None,
        year: Optional[int] = None,
        years: Optional[Iterable[int]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Query BSEE production data with optional filters.

        Parameters
        ----------
        lease : str, optional
            BSEE lease number (e.g. ``"G12345"``).
        year : int, optional
            Single production year to filter on.
        years : iterable of int, optional
            Range or list of years (e.g. ``range(2020, 2026)``).
        **kwargs
            Reserved for future filter parameters.

        Returns
        -------
        pd.DataFrame
            Production records matching the filters. Returns empty
            DataFrame if no data is available or no records match.

        Examples
        --------
        >>> pq = ProductionQuery()
        >>> df = pq.query(lease="G12345")
        >>> df = pq.query(year=2022)
        >>> df = pq.query(lease="G12345", years=range(2020, 2023))
        """
        if lease and year:
            return self._loader.get_by_lease_and_year(lease, year)

        if lease and years:
            year_list = list(years)
            df = self._loader.load()
            if df is None:
                return pd.DataFrame()
            mask = (df["LEASE_NUMBER"] == lease) & (df["PROD_YEAR"].isin(year_list))
            return df[mask].reset_index(drop=True)

        if lease:
            return self._loader.get_by_lease(lease)

        if year:
            return self._loader.get_by_year(year)

        if years:
            year_list = list(years)
            df = self._loader.load()
            if df is None:
                return pd.DataFrame()
            return df[df["PROD_YEAR"].isin(year_list)].reset_index(drop=True)

        # No filters — return all data
        df = self._loader.load()
        return df if df is not None else pd.DataFrame()

    def annual_summary(self, year: int) -> Dict[str, Any]:
        """Compute annual production summary for a given year.

        Parameters
        ----------
        year : int
            The production year.

        Returns
        -------
        dict
            Keys: ``year``, ``total_oil_bbl``, ``total_gas_mcf``,
            ``total_water_bbl``, ``lease_count``.

        Examples
        --------
        >>> pq = ProductionQuery()
        >>> summary = pq.annual_summary(2022)
        >>> print(f"Oil: {summary['total_oil_bbl']:,.0f} BBL")
        """
        return self._loader.annual_summary(year)


class WellsQuery:
    """Query BSEE well/borehole data.

    Wraps :class:`~worldenergydata.bsee.data.loaders.well.borehole_acquirer.BoreholeDataAcquirer`
    with a filter-oriented interface. Since borehole data requires network
    download or cached files, the ``query()`` method returns an empty DataFrame
    when data is not available locally.

    Examples
    --------
    >>> from worldenergydata.bsee.api import WellsQuery
    >>> wq = WellsQuery()
    >>> df = wq.query(api_number="608114001200")
    >>> df = wq.query(field="MC 778")
    """

    def __init__(self, local_data_dir: Optional[Path] = None) -> None:
        """Initialize with optional local data cache directory.

        Parameters
        ----------
        local_data_dir : Path, optional
            Root of the .local/ cache directory for borehole data.
        """
        from worldenergydata.bsee.data.loaders.well.borehole_acquirer import (
            BoreholeDataAcquirer,
        )

        self._acquirer = BoreholeDataAcquirer(
            downloader=None, local_data_dir=local_data_dir
        )
        self._cache: Optional[pd.DataFrame] = None

    def _load(self) -> pd.DataFrame:
        """Load borehole data from cache. Returns empty DataFrame on failure."""
        if self._cache is not None:
            return self._cache
        df = self._acquirer.acquire_borehole_dataframe()
        if df is None:
            return pd.DataFrame()
        self._cache = df
        return self._cache

    def query(
        self,
        *,
        api_number: Optional[str] = None,
        field: Optional[str] = None,
        area_code: Optional[str] = None,
        water_depth_min: Optional[float] = None,
        water_depth_max: Optional[float] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Query BSEE well/borehole data with optional filters.

        Parameters
        ----------
        api_number : str, optional
            API well number to filter on (exact match).
        field : str, optional
            Area code and block (e.g. ``"MC 778"``). Matches against
            ``BOTM_AREA_CODE`` and ``BOTM_BLOCK_NUMBER`` columns.
        area_code : str, optional
            OCS area code (e.g. ``"MC"``, ``"GC"``).
        water_depth_min : float, optional
            Minimum water depth in feet.
        water_depth_max : float, optional
            Maximum water depth in feet.
        **kwargs
            Reserved for future filter parameters.

        Returns
        -------
        pd.DataFrame
            Well records matching the filters. Returns empty DataFrame
            if data is unavailable or no records match.

        Examples
        --------
        >>> wq = WellsQuery()
        >>> df = wq.query(area_code="MC")
        >>> df = wq.query(water_depth_min=5000)
        """
        df = self._load()
        if df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        if api_number is not None and "API_WELL_NUMBER" in df.columns:
            mask &= df["API_WELL_NUMBER"] == api_number

        if field is not None:
            # Parse "MC 778" → area_code="MC", block="778"
            parts = field.strip().split()
            if len(parts) >= 2 and "BOTM_AREA_CODE" in df.columns:
                ac = parts[0].upper()
                blk = parts[1]
                mask &= (
                    df["BOTM_AREA_CODE"].astype(str).str.strip().str.upper() == ac
                ) & (df["BOTM_BLOCK_NUMBER"].astype(str).str.strip() == blk)
            elif "BOTM_AREA_CODE" in df.columns:
                # Single value — try area code match
                mask &= (
                    df["BOTM_AREA_CODE"].astype(str).str.strip().str.upper()
                    == field.strip().upper()
                )

        if area_code is not None and "BOTM_AREA_CODE" in df.columns:
            mask &= (
                df["BOTM_AREA_CODE"].astype(str).str.strip().str.upper()
                == area_code.strip().upper()
            )

        if water_depth_min is not None and "WATER_DEPTH" in df.columns:
            mask &= df["WATER_DEPTH"] >= water_depth_min

        if water_depth_max is not None and "WATER_DEPTH" in df.columns:
            mask &= df["WATER_DEPTH"] <= water_depth_max

        return df[mask].reset_index(drop=True)


class CompaniesQuery:
    """Query BSEE company/operator data.

    Wraps :class:`~worldenergydata.bsee.data.loaders.company.company_loader.CompanyLoader`
    with a filter-oriented interface.

    Examples
    --------
    >>> from worldenergydata.bsee.api import CompaniesQuery
    >>> cq = CompaniesQuery()
    >>> df = cq.query(name="Shell")
    >>> df = cq.query(operator_id=2800)
    >>> df = cq.query(region="GOM")
    """

    def __init__(self, bin_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize with optional custom binary data directory.

        Parameters
        ----------
        bin_dir : str or Path, optional
            Path to directory containing company .bin files.
        """
        from worldenergydata.bsee.data.loaders.company.company_loader import (
            CompanyLoader,
        )

        self._loader = CompanyLoader(bin_dir=bin_dir)

    def query(
        self,
        *,
        name: Optional[str] = None,
        operator_id: Optional[int] = None,
        region: Optional[str] = None,
        include_inactive: bool = False,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Query BSEE company/operator data with optional filters.

        Parameters
        ----------
        name : str, optional
            Company name to search for (case-insensitive partial match).
        operator_id : int, optional
            BSEE/BOEM company number (``MMS_COMPANY_NUM``).
        region : str, optional
            OCS region code: ``"GOM"``, ``"PAC"``, ``"ALASKA"``, or ``"ATL"``.
        include_inactive : bool, default False
            If True, search all companies including terminated ones.
        **kwargs
            Reserved for future filter parameters.

        Returns
        -------
        pd.DataFrame
            Company records matching the filters. Returns empty
            DataFrame if data is unavailable or no records match.

        Examples
        --------
        >>> cq = CompaniesQuery()
        >>> df = cq.query(name="Shell")
        >>> df = cq.query(region="GOM")
        >>> df = cq.query(operator_id=2800)
        """
        if operator_id is not None:
            return self._loader.get_by_operator_id(operator_id)

        if name is not None:
            return self._loader.get_by_company_name(name)

        if region is not None:
            return self._loader.get_by_region(region)

        # No filters — return all data
        if include_inactive:
            df = self._loader.load_all()
        else:
            df = self._loader.load_active()
        return df if df is not None else pd.DataFrame()


# Module-level singleton instances for convenience attribute access
production = ProductionQuery()
wells = WellsQuery()
companies = CompaniesQuery()
