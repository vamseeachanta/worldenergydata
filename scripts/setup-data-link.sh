#!/usr/bin/env bash
# Setup partial data symlinks for worldenergydata.
#
# Per the 2026-03-24 relocation (RELOCATION-LOG.md at /mnt/ace/worldenergydata),
# bulk public data (~9.4 GB across HSE raw + BSEE bin/zip) lives outside the
# git repo. Smaller modules (BSEE current, paleowells, marine_safety,
# vessel_hull_models, etc.) stay in the repo. This script wires the three
# relocated subtrees as per-path symlinks INTO the repo's data/ tree, leaving
# everything else untouched.
#
# Usage:
#   ./scripts/setup-data-link.sh                                 # use default /mnt/ace
#   ./scripts/setup-data-link.sh /custom/path/worldenergydata/data
#   ./scripts/setup-data-link.sh --check                         # verify-only, no changes
#
# Refs: #359 (this fix), #298/#299 (prior whole-tree approach that didn't fit
# the actual relocation topology), #369 (test that catches drift live).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_TARGET="/mnt/ace/worldenergydata/data"

CHECK_ONLY=0
TARGET=""
for arg in "$@"; do
    case "$arg" in
        --check) CHECK_ONLY=1 ;;
        -h|--help)
            sed -n '2,16p' "$0"
            exit 0
            ;;
        *) TARGET="$arg" ;;
    esac
done
TARGET="${TARGET:-$DEFAULT_TARGET}"

# Subtrees that were relocated. Each entry is "<repo-relative-path>:<target-relative-path>".
# Paths are repo-relative under data/ and target-relative under TARGET/.
RELOCATED_SUBTREES=(
    "data/modules/bsee/bin:modules/bsee/bin"
    "data/modules/bsee/zip:modules/bsee/zip"
    "data/modules/hse/raw:modules/hse/raw"
)

if [ ! -d "$TARGET" ]; then
    echo "ERROR: Relocation root does not exist: $TARGET" >&2
    echo "       (default is $DEFAULT_TARGET; pass a different path as the first arg)" >&2
    exit 1
fi

errors=0
created=0
verified=0
repaired=0

for entry in "${RELOCATED_SUBTREES[@]}"; do
    repo_rel="${entry%%:*}"
    target_rel="${entry##*:}"
    link="$PROJECT_ROOT/$repo_rel"
    target="$TARGET/$target_rel"
    parent="$(dirname "$link")"

    if [ ! -d "$target" ]; then
        echo "ERROR: Target missing for $repo_rel: $target" >&2
        errors=$((errors + 1))
        continue
    fi

    if [ ! -d "$parent" ]; then
        echo "ERROR: Repo parent dir missing for $repo_rel: $parent" >&2
        echo "       This script does not create parent directories — fix the repo layout first." >&2
        errors=$((errors + 1))
        continue
    fi

    # Refuse to clobber a real directory with content (data loss risk).
    if [ -d "$link" ] && [ ! -L "$link" ]; then
        if [ -n "$(ls -A "$link" 2>/dev/null)" ]; then
            echo "ERROR: $repo_rel is a real directory with content; refusing to replace." >&2
            echo "       If this content is safe to discard, remove it manually then re-run." >&2
            errors=$((errors + 1))
            continue
        else
            # Empty real dir — safe to remove and replace.
            if [ "$CHECK_ONLY" = "1" ]; then
                echo "  WOULD REPAIR (empty dir): $repo_rel -> $target"
            else
                rmdir "$link"
                ln -s "$target" "$link"
                echo "  REPAIRED (was empty dir): $repo_rel -> $target"
                repaired=$((repaired + 1))
            fi
            continue
        fi
    fi

    if [ -L "$link" ]; then
        current="$(readlink -f "$link")"
        if [ "$current" = "$(readlink -f "$target")" ]; then
            echo "  OK: $repo_rel -> $target"
            verified=$((verified + 1))
        else
            if [ "$CHECK_ONLY" = "1" ]; then
                echo "  WOULD REPAIR (wrong target): $repo_rel -> $target (was $current)"
            else
                rm "$link"
                ln -s "$target" "$link"
                echo "  REPAIRED (wrong target): $repo_rel -> $target (was $current)"
                repaired=$((repaired + 1))
            fi
        fi
        continue
    fi

    if [ "$CHECK_ONLY" = "1" ]; then
        echo "  WOULD CREATE: $repo_rel -> $target"
    else
        ln -s "$target" "$link"
        echo "  CREATED: $repo_rel -> $target"
        created=$((created + 1))
    fi
done

echo
if [ "$errors" -gt 0 ]; then
    echo "FAILED: $errors error(s); $created created, $repaired repaired, $verified verified." >&2
    exit 1
fi

if [ "$CHECK_ONLY" = "1" ]; then
    echo "Check complete. (use without --check to apply changes)"
else
    echo "Done. $created created, $repaired repaired, $verified already-correct."
    echo "Verify: uv run pytest tests/integration/test_data_symlink.py -v"
fi
