"""Build a registry from two selected local snapshots, without downloads."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from .io import load_operator_inputs, write_operator_registry
from .registry import RegistryPolicy, build_operator_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--wells", type=Path, required=True)
    parser.add_argument("--as-of", required=True, help="Last calendar month, YYYY-MM")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/texas_rrc.yml"))
    parser.add_argument(
        "--code-revision", help="Revision of the code used for this run"
    )
    parser.add_argument(
        "--allow-non-catalog-root",
        action="store_true",
        help="Allow an isolated example or test output root",
    )
    args = parser.parse_args(argv)
    settings = yaml.safe_load(args.config.read_text())["operator_registry"]
    policy = RegistryPolicy(
        as_of=args.as_of,
        size_bands=tuple(
            (item["max_wells"], item["label"]) for item in settings["size_bands"]
        ),
        stripper_bopd=settings["stripper_bopd"],
    )
    inputs = load_operator_inputs(args.production, args.wells)
    result = build_operator_registry(inputs.production, inputs.wells, policy)
    write_operator_registry(
        result,
        args.output_root,
        policy,
        inputs=inputs.provenance,
        code_revision=args.code_revision,
        allow_non_catalog_root=args.allow_non_catalog_root,
    )
    print(f"Registry operators: {len(result.registry)}")
    print(f"Usable last12: {result.quality['operators_usable_last12']}")


if __name__ == "__main__":
    main()
