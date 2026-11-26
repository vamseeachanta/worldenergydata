"""Build the registry and reports from an explicitly normalized local snapshot."""

import argparse

from . import Policy, build_screen, load_bundle, write_outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Normalized JSON bundle")
    parser.add_argument("--as-of", required=True, help="Last analysis month, YYYY-MM")
    parser.add_argument("--output", required=True, help="External artifact directory")
    parser.add_argument(
        "--config", help="YAML with a complete operator_screen policy section"
    )
    parser.add_argument("--operator", help="Generate HTML only for this registry ID")
    args = parser.parse_args(argv)
    bundle = load_bundle(args.input)
    policy = bundle.get("policy")
    if args.config:
        from pathlib import Path

        import yaml

        policy = yaml.safe_load(Path(args.config).read_text())["operator_screen"]
    result = build_screen(bundle, Policy(**policy), as_of=args.as_of)
    write_outputs(result, args.output, args.operator)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
