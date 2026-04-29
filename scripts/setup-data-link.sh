#!/usr/bin/env bash
# Setup data symlink for worldenergydata
# Usage: ./scripts/setup-data-link.sh [/path/to/data]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_TARGET="/mnt/ace/worldenergydata/data"
TARGET="${1:-$DEFAULT_TARGET}"

if [ ! -d "$TARGET" ]; then
    echo "ERROR: Data directory does not exist: $TARGET"
    echo "Usage: $0 /path/to/worldenergydata/data"
    exit 1
fi

LINK="$PROJECT_ROOT/data"

if [ -L "$LINK" ]; then
    CURRENT=$(readlink -f "$LINK")
    if [ "$CURRENT" = "$(readlink -f "$TARGET")" ]; then
        echo "Symlink already correct: data -> $TARGET"
    else
        echo "Updating symlink: data -> $TARGET (was $CURRENT)"
        rm "$LINK"
        ln -s "$TARGET" "$LINK"
    fi
elif [ -d "$LINK" ]; then
    echo "WARNING: data/ is a real directory, not a symlink."
    echo "To use external data, remove it first: rm -rf $LINK"
    exit 1
else
    ln -s "$TARGET" "$LINK"
    echo "Created symlink: data -> $TARGET"
fi

for dir in modules/bsee modules/hse; do
    if [ -d "$TARGET/$dir" ]; then
        echo "  OK: $dir exists"
    else
        echo "  WARN: $dir not found in $TARGET"
    fi
done

echo "Done. Data root: $TARGET"
