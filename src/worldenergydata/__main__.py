"""WorldEnergyData module entry point.

Supports two invocation modes:

- ``python -m worldenergydata path/to/input.yml`` routes YAML files through
  ``worldenergydata.engine.engine`` for durable workflow execution.
- All other invocations fall through to the Typer command-line interface.

Usage:
------
    worldenergydata <module> <command> [options]

    # Or using Python module syntax:
    python -m worldenergydata <module> <command> [options]

Modules:
--------
    bsee          - BSEE data operations and analysis
    marine-safety - Marine safety incident data
    fdas          - Field Development Analysis System

Examples:
---------
    worldenergydata bsee analyze --block 759
    worldenergydata marine-safety stats --source uscg
    worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]"

For legacy YAML-based engine usage:
    python -m worldenergydata <config.yaml>

Contact:
--------
More information is available at:
- https://pypi.org/project/worldenergydata/
- https://github.com/vamseeachanta/worldenergydata

Version:
--------
- worldenergydata v0.1.0
"""

import sys
from pathlib import Path


def _is_yaml_input(argument: str) -> bool:
    path = Path(argument)
    return path.suffix.lower() in {".yml", ".yaml"} and path.is_file()


def main():
    if len(sys.argv) > 1 and _is_yaml_input(sys.argv[1]):
        from worldenergydata.engine import engine

        engine()
        return

    from worldenergydata.cli.main import app

    app()


if __name__ == "__main__":
    main()
