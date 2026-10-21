#!/usr/bin/env bash
# Install member extras only for the domain that exercises them.
set -euo pipefail

# SHARD is supplied by the reusable domain-matrix workflow to its test runner.
# Select both packages to retain root test tooling and enable the member extra.
if [[ "${SHARD:-}" == "unit-metocean" ]]; then
    export WED_REQUIRE_METOCEAN_STATS=1
    uv sync --frozen --all-extras \
        --package worldenergydata --package worldenergydata-metocean
fi

# Keep the exact environment installed above, including the optional backend.
exec uv run --no-sync --with pytest-xdist pytest "$@"
