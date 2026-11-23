"""Run a scheduler refresh with synthetic rows and no upstream connections.

Inputs: the literal observations 'first' and 'second', plus a destination.
Method: write CSV through DataScheduler, then read the retained run copy.
Answer: two observations, success, identical live and timestamped CSV bytes.
The expected count is an independent count of the two literal observations;
there are no engineering coefficients or acceptance thresholds.
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import yaml
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.scheduler import DataScheduler

OBSERVATIONS = ("first", "second")


class ExampleRefreshJob(AbstractJob):
    """Write a supplied synthetic dataset through the shared output contract."""

    name = "example_refresh"

    def run(self, config: dict) -> JobResult:
        start = datetime.now()
        destination = Path(config["output_dir"])
        destination.mkdir(parents=True, exist_ok=True)
        with (destination / "observations.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["observation"])
            writer.writerows([value] for value in OBSERVATIONS)
        return JobResult(
            self.name, start, datetime.now(), "success", len(OBSERVATIONS), None
        )


def run_example(destination: Path) -> dict:
    """Use a caller-selected directory for all configuration, logs and outputs."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output_dir = destination / "data" / "modules" / "example"
    config_path = destination / "scheduler-example.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "jobs": [{"name": "example_refresh", "output_dir": str(output_dir)}],
                "monitoring": {
                    "log_dir": str(destination / "logs"),
                    "status_file": str(destination / "status.json"),
                },
            }
        )
    )
    scheduler = DataScheduler(str(config_path))
    scheduler.register_job(ExampleRefreshJob())
    result = scheduler.run_once("example_refresh")
    snapshots = sorted((output_dir / "runs").iterdir())
    retained = snapshots[-1] / "observations.csv"
    same_bytes = retained.read_bytes() == (output_dir / "observations.csv").read_bytes()
    return {
        "status": result.status,
        "records_updated": result.records_updated,
        "snapshot_matches_live": same_bytes,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_example(args.destination), sort_keys=True))
