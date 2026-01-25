"""WorldEnergyData CLI Entry Point

Unified command-line interface for global energy market data operations.

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
    python -m worldenergydata.engine <config.yaml>

Contact:
--------
More information is available at:
- https://pypi.org/project/worldenergydata/
- https://github.com/vamseeachanta/worldenergydata

Version:
--------
- worldenergydata v0.1.0
"""

from worldenergydata.cli.main import app

if __name__ == "__main__":
    app()
