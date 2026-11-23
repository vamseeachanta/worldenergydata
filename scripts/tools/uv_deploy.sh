#!/bin/bash
# Compatibility entry point; keep deployment behavior in the canonical helper.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/../uv_deploy.sh" "$@"
