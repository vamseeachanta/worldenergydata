# ABOUTME: Skill demonstration script for metocean-data-fetcher.
# ABOUTME: Fetches real-time buoy data from NDBC stations and displays observations.

"""
Metocean Data Fetcher Skill Demonstration

This script demonstrates the metocean-data-fetcher skill by:
1. Connecting to NDBC (National Data Buoy Center)
2. Fetching station info for a Gulf of Mexico buoy
3. Retrieving real-time observations
4. Saving output to a test file

Station 42001 is located in the Mid-Gulf, 180 nm South of Southwest Pass, LA.
Fallback stations are provided in case the primary station has no data.
"""

import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from worldenergydata.modules.metocean.clients import (
    FetchResult,
    NDBCClient,
    NDBCObservation,
    NDBCStation,
)
from worldenergydata.modules.metocean.exceptions import (
    HTTPError,
    ParsingError,
    TimeoutError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Target stations (primary and fallbacks)
# 42001: Mid-Gulf buoy with reliable real-time data
# 42002: Western Gulf buoy
# 41009: Cape Canaveral buoy
STATION_IDS = ["42001", "42002", "41009"]

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"


def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def format_observation(obs: NDBCObservation) -> str:
    """Format a single observation for display."""
    lines = [
        f"  Time: {obs.observation_time.strftime('%Y-%m-%d %H:%M UTC')}",
    ]

    # Wind data
    if obs.wind_speed_ms is not None:
        wind_dir = f"{obs.wind_direction_deg:.0f}" if obs.wind_direction_deg else "N/A"
        gust = f", gust {obs.wind_gust_ms:.1f}" if obs.wind_gust_ms else ""
        lines.append(f"  Wind: {obs.wind_speed_ms:.1f} m/s from {wind_dir}{gust}")

    # Wave data
    if obs.wave_height_m is not None:
        period = (
            f", period {obs.dominant_wave_period_s:.1f}s"
            if obs.dominant_wave_period_s
            else ""
        )
        wave_dir = (
            f" from {obs.wave_direction_deg:.0f}" if obs.wave_direction_deg else ""
        )
        lines.append(f"  Waves: {obs.wave_height_m:.2f} m{period}{wave_dir}")

    # Temperature data
    temps = []
    if obs.air_temp_c is not None:
        temps.append(f"air {obs.air_temp_c:.1f}C")
    if obs.sea_surface_temp_c is not None:
        temps.append(f"sea {obs.sea_surface_temp_c:.1f}C")
    if temps:
        lines.append(f"  Temperature: {', '.join(temps)}")

    # Pressure
    if obs.pressure_hpa is not None:
        tendency = ""
        if obs.pressure_tendency_hpa is not None:
            sign = "+" if obs.pressure_tendency_hpa > 0 else ""
            tendency = f" ({sign}{obs.pressure_tendency_hpa:.1f} hPa/3hr)"
        lines.append(f"  Pressure: {obs.pressure_hpa:.1f} hPa{tendency}")

    return "\n".join(lines)


def format_station_info(station: NDBCStation) -> str:
    """Format station metadata for display."""
    lines = [
        f"Station ID: {station.station_id}",
        f"Name: {station.name}",
        f"Location: {station.latitude:.4f}N, {station.longitude:.4f}W",
        f"Type: {station.station_type.value}",
    ]

    if station.water_depth_m:
        lines.append(f"Water Depth: {station.water_depth_m:.0f} m")

    if station.owner:
        lines.append(f"Owner: {station.owner}")

    lines.append(f"Active: {'Yes' if station.is_active else 'No'}")

    return "\n".join(lines)


def fetch_station_data(station_id: str) -> dict:
    """
    Fetch station info and real-time data from NDBC.

    Args:
        station_id: NDBC station identifier

    Returns:
        Dictionary containing station info and observations
    """
    result = {
        "station_id": station_id,
        "fetch_time": datetime.utcnow().isoformat(),
        "station_info": None,
        "observations": [],
        "errors": [],
    }

    with NDBCClient() as client:
        # Fetch station info
        logger.info(f"Fetching station info for {station_id}...")
        try:
            station = client.get_station_info(station_id)
            if station:
                result["station_info"] = asdict(station)
                print("\n" + "=" * 60)
                print("STATION INFORMATION")
                print("=" * 60)
                print(format_station_info(station))
            else:
                msg = f"Station {station_id} not found in active stations list"
                result["errors"].append(msg)
                logger.warning(msg)
        except (HTTPError, TimeoutError, ParsingError) as e:
            msg = f"Failed to fetch station info: {e}"
            result["errors"].append(msg)
            logger.error(msg)

        # Fetch real-time observations
        logger.info(f"Fetching real-time data for {station_id}...")
        try:
            fetch_result: FetchResult[NDBCObservation] = client.fetch_realtime(
                station_id
            )

            if fetch_result.had_errors:
                result["errors"].extend(fetch_result.error_messages)

            observations = fetch_result.data
            result["observations"] = [asdict(obs) for obs in observations[:10]]

            print("\n" + "=" * 60)
            print(f"LATEST OBSERVATIONS ({fetch_result.records_count} total)")
            print("=" * 60)

            if observations:
                # Show latest 5 observations
                for i, obs in enumerate(observations[:5]):
                    print(f"\nObservation {i + 1}:")
                    print(format_observation(obs))
            else:
                print("No observations available")

        except (HTTPError, TimeoutError, ParsingError) as e:
            msg = f"Failed to fetch real-time data: {e}"
            result["errors"].append(msg)
            logger.error(msg)

    return result


def save_output(data: dict, output_path: Path) -> None:
    """Save fetch results to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=serialize_datetime)

    logger.info(f"Output saved to {output_path}")


def main() -> int:
    """
    Main entry point for the skill demonstration.

    Attempts to fetch data from multiple NDBC stations until one succeeds.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n" + "=" * 60)
    print("METOCEAN DATA FETCHER SKILL DEMONSTRATION")
    print("=" * 60)
    print(f"Target Stations: {', '.join(STATION_IDS)}")
    print(f"Fetch Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Try each station until we get data
    for station_id in STATION_IDS:
        print(f"\nAttempting station {station_id}...")

        try:
            # Fetch data
            data = fetch_station_data(station_id)

            obs_count = len(data.get("observations", []))
            error_count = len(data.get("errors", []))

            # Save output regardless of success
            output_file = OUTPUT_DIR / f"ndbc_{station_id}_data.json"
            save_output(data, output_file)

            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)

            print(f"Station: {station_id}")
            print(f"Observations retrieved: {obs_count}")
            print(f"Errors encountered: {error_count}")
            print(f"Output file: {output_file}")

            if error_count > 0:
                print("\nErrors:")
                for err in data["errors"]:
                    print(f"  - {err}")

            # If we got observations, we're done
            if obs_count > 0:
                print("\nSkill demonstration completed successfully.")
                return 0

            # Otherwise try next station
            print(f"\nNo observations from {station_id}, trying next station...")

        except Exception as e:
            logger.warning(f"Failed to fetch from {station_id}: {e}")
            continue

    # All stations failed
    logger.error("Failed to retrieve data from any station")
    return 1


if __name__ == "__main__":
    sys.exit(main())
