"""Refresh public drilling and intervention HSE aggregates from a sealed manifest.

Use --fetch for a new data directory; an existing verified manifest is resumable.
Paths and scientific input assumptions are declared in the JSON configuration.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def workflow():
    """Load the stdlib workflow without optional HSE database dependencies."""
    path = (
        REPO / "packages/worldenergydata-bsee/src/worldenergydata/hse/public_refresh.py"
    )
    spec = importlib.util.spec_from_file_location("hse_public_refresh", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=REPO / "config/hse/public_refresh.json"
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args(argv)
    module = workflow()
    config = module.load_config(
        args.config, data_dir=args.data_dir, output_dir=args.output_dir
    )
    # Invalidate old outputs even if a new network request fails.
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    renderer_spec = importlib.util.spec_from_file_location(
        "drilling_hse_renderer", Path(__file__).with_name("drilling_hse_render_html.py")
    )
    renderer = importlib.util.module_from_spec(renderer_spec)
    renderer_spec.loader.exec_module(renderer)
    module.invalidate(config, "refresh incomplete")
    try:
        if args.fetch:
            try:
                module.fetch(config)
            except (module.NetworkError, module.QAError) as exc:
                module.invalidate(config, str(exc))
                raise
        result = module.analyze(config)
    finally:
        if (out / module.HEADLINES).exists():
            renderer.render(
                out / module.HEADLINES, out / "drilling-hse-patterns-2026-07-05.html"
            )
    print(
        f"QA passed; screened {result['incinv_total_records']} investigation records."
    )


if __name__ == "__main__":
    main()
