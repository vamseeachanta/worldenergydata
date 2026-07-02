#!/usr/bin/env bash
# Scan tracked repository files for legally denied client/proprietary terms.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DENY_LIST="$REPO_ROOT/.legal-deny-list.yaml"
DIFF_ONLY=true

usage() {
  cat <<'EOF'
Usage: legal-sanity-scan.sh [--diff-only] [--all] [--repo=<ignored>]

Scans changed and untracked files against .legal-deny-list.yaml by default. Markdown,
data files, generated review results, and paths listed under the deny-list
exclusions block are skipped. Use --all for a full-repository debt scan.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --diff-only) DIFF_ONLY=true ;;
    --all) DIFF_ONLY=false ;;
    --repo=*) ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$DENY_LIST" ]]; then
  echo "legal-sanity-scan: missing $DENY_LIST" >&2
  exit 1
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "legal-sanity-scan: ripgrep (rg) is required" >&2
  exit 2
fi

parse_patterns() {
  awk '
    /^[[:space:]]*- pattern:/ {
      value = $0
      sub(/^[[:space:]]*- pattern:[[:space:]]*/, "", value)
      gsub(/^"/, "", value)
      gsub(/"$/, "", value)
      pattern = value
    }
    /^[[:space:]]*case_sensitive:/ {
      value = $0
      sub(/^[[:space:]]*case_sensitive:[[:space:]]*/, "", value)
      print pattern "|" value
    }
  ' "$DENY_LIST"
}

parse_exclusions() {
  awk '
    /^exclusions:/ { active=1; next }
    active && /^[^[:space:]#-]/ { active=0 }
    active && /^[[:space:]]*- / {
      value = $0
      sub(/^[[:space:]]*- /, "", value)
      gsub(/^"/, "", value)
      gsub(/"$/, "", value)
      print value
    }
  ' "$DENY_LIST"
}

is_excluded() {
  local path="$1"
  local pattern
  [[ "$path" == scripts/review/results/* ]] && return 0
  while IFS= read -r pattern; do
    [[ -z "$pattern" ]] && continue
    case "$pattern" in
      */)
        [[ "$path" == "$pattern"* ]] && return 0
        ;;
      *"*"*)
        [[ "$path" == $pattern ]] && return 0
        ;;
      *)
        [[ "$path" == "$pattern" || "$path" == */"$pattern" ]] && return 0
        ;;
    esac
  done < <(parse_exclusions)
  return 1
}

candidate_files() {
  if [[ "$DIFF_ONLY" == true ]]; then
    {
      git -C "$REPO_ROOT" diff --name-only HEAD
      git -C "$REPO_ROOT" ls-files --others --exclude-standard
    } | sort -u
  else
    git -C "$REPO_ROOT" ls-files
  fi
}

files=()
while IFS= read -r file; do
  [[ -f "$REPO_ROOT/$file" ]] || continue
  is_excluded "$file" && continue
  files+=("$REPO_ROOT/$file")
done < <(candidate_files)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "legal-sanity-scan: no files to scan"
  exit 0
fi

violations=0
while IFS='|' read -r pattern case_sensitive; do
  [[ -z "$pattern" ]] && continue
  flags=(--fixed-strings --line-number --no-heading --color never)
  [[ "$case_sensitive" == "false" ]] && flags+=(-i)
  if matches="$(rg "${flags[@]}" -- "$pattern" "${files[@]}")" && [[ -n "$matches" ]]; then
    echo "BLOCK pattern=$pattern"
    echo "$matches"
    violations=$((violations + 1))
  fi
done < <(parse_patterns)

if [[ "$violations" -gt 0 ]]; then
  echo "legal-sanity-scan: FAILED ($violations denied pattern group(s) matched)" >&2
  exit 1
fi

echo "legal-sanity-scan: PASS"
