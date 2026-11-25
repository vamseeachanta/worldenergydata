#!/usr/bin/env bash
# check-no-conflict-markers.sh — block commits staging files with unresolved
# git merge-conflict markers.
#
# Issue: workspace-hub#2722. T3 adversarial review consensus MAJOR; r3+r4
# inline patches in docs/plans/2026-05-16-issue-2722-pre-commit-conflict-marker-hook.md
# closed all 29 distinct findings.
#
# Design summary:
# - Stage-aware: reads `git diff --cached --name-only --diff-filter=ACMR -z`;
#   never scans the working tree directly.
# - NUL-delimited iteration handles filenames with spaces (Gemini r2 #8).
# - Co-occurrence required: both `^<<<<<<<(\s|$)` AND `^>>>>>>>(\s|$)` must
#   appear in the same staged blob before any per-line violation is emitted.
#   This defeats markdown 7-level blockquote false-positives (Gemini r2 #4).
# - Bare `=======` is NEVER a trigger (false-positive guard for markdown
#   setext H1 underline + shell `# =====` banner art).
# - NO active-merge skip: the original Codex r2 #1 fix removed the
#   `.git/MERGE_MSG` / `REBASE_HEAD` / `CHERRY_PICK_HEAD` skip — those are
#   exactly the commits where half-resolved markers are most likely to land.
# - Forensic-allowlist:
#   * Per-line (default): line ending with `# CONFLICT_MARKER_FORENSIC_OK`
#     or `// CONFLICT_MARKER_FORENSIC_OK` or `<!-- CONFLICT_MARKER_FORENSIC_OK -->`
#     exempts only that line. Matches scripts/enforcement/check-no-abs-paths.sh
#     prior art (Claude r1 #3).
#   * Per-file (path-restricted): file containing
#     `<!-- CONFLICT_MARKER_FORENSIC_FILE_OK -->` AND located in one of
#     {docs/plans/**, docs/governance/**, docs/standards/**,
#      scripts/review/results/**, scripts/review/prompts/**} is exempted
#     entirely (Gemini r2 #1). Bounds Claude r1 #3 blanket-backdoor concern.
# - Both sentinel and marker reads come from the SAME staged blob via
#   `git show <index-object-id>` — eliminates working-tree-vs-staged-blob TOCTOU
#   bypass surfaced by Codex r2 #2 + Claude r1 #4.
# - Binary policy: scan raw staged bytes as text, including NUL-containing
#   blobs; do not decompress archives. Keep bytes in a temporary file, never
#   a Bash variable. Escape control bytes only when rendering violations.

set -uo pipefail
# Marker delimiters and diagnostics use byte semantics in every caller locale.
export LC_ALL=C
# Note: not using `set -e` because we deliberately tolerate non-zero exit
# codes from grep (no-match) and similar; explicit branching is used instead.

PATH_RESTRICTED_PREFIXES=(
  "docs/plans/"
  "docs/governance/"
  "docs/standards/"
  "scripts/review/results/"
  "scripts/review/prompts/"
)

is_path_restricted() {
  local file="$1"
  local prefix
  for prefix in "${PATH_RESTRICTED_PREFIXES[@]}"; do
    case "$file" in
      "${prefix}"*) return 0 ;;
    esac
  done
  return 1
}

staged_blob="" staged_paths="" staged_entry=""
cleanup() {
  local snapshot
  for snapshot in "$staged_blob" "$staged_paths" "$staged_entry"; do
    if [[ -n "$snapshot" ]]; then rm -f -- "$snapshot"; fi
  done
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
if ! staged_blob="$(mktemp)"; then
  printf 'ERROR: Cannot create staged-content snapshot.\n' >&2
  exit 1
fi

if ! staged_paths="$(mktemp)"; then
  printf 'ERROR: Cannot create staged-path list.\n' >&2
  exit 1
fi
if ! staged_entry="$(mktemp)"; then
  printf 'ERROR: Cannot create staged-entry snapshot.\n' >&2
  exit 1
fi
if ! git diff --cached --name-only --diff-filter=ACMR -z > "$staged_paths" 2>/dev/null; then
  printf 'ERROR: Cannot enumerate staged paths.\n' >&2
  exit 1
fi

invalid_entry() {
  printf 'ERROR: Invalid staged index entry: %s\n' "$display_file" >&2
  exit 1
}

snapshot_read_error() {
  printf 'ERROR: Cannot read staged content: %s\n' "$display_file" >&2
  exit 1
}

snapshot_contains() {
  local status
  # Read the whole snapshot: grep -q can hide a read error after a match.
  grep -a "$@" "$staged_blob" > /dev/null
  status=$?
  case "$status" in
    0|1) return "$status" ;;
    *) snapshot_read_error ;;
  esac
}

violations=()
processed_paths=0

# Consume only a complete, successfully acquired path list; ACMR excludes deletions.
while IFS= read -r -d '' file; do
  processed_paths=$((processed_paths + 1))
  # Keep each diagnostic on one line, including paths ending in a newline.
  if ! display_file="$(printf '%s' "${file//$'\n'/^J}" | cat -vT)"; then
    printf 'ERROR: Cannot render staged path.\n' >&2
    exit 1
  fi

  if ! git --literal-pathspecs ls-files -s -z --full-name -- "$file" > "$staged_entry" 2>/dev/null; then
    printf 'ERROR: Cannot read staged index entry: %s\n' "$display_file" >&2
    exit 1
  fi
  # Require exactly one complete stage-zero record, preserving tabs in its path.
  {
    entry="" extra=""
    if ! IFS= read -r -d '' entry || IFS= read -r -d '' extra || [[ -n "$extra" ]]; then
      invalid_entry
    fi
  } < "$staged_entry"
  [[ "$entry" == *$'\t'* ]] || invalid_entry
  header="${entry%%$'\t'*}"
  entry_path="${entry#*$'\t'}"
  if [[ "$entry_path" != "$file" ||
        ! "$header" =~ ^(100644|100755|120000|160000)\ ([[:xdigit:]]+)\ 0$ ]]; then
    invalid_entry
  fi
  mode="${BASH_REMATCH[1]}" oid="${BASH_REMATCH[2]}"
  # A gitlink's object belongs to its submodule, not necessarily this object store.
  if [[ "$mode" == 160000 ]]; then continue; fi
  if ! object_type="$(git cat-file -t "$oid" 2>/dev/null)" || [[ "$object_type" != blob ]]; then
    printf 'ERROR: Cannot inspect staged object: %s\n' "$display_file" >&2
    exit 1
  fi

  # Read the staged blob ONCE. This is the single source of truth used by
  # both the per-file sentinel check AND the per-line marker scan.
  if ! git show "$oid" > "$staged_blob" 2>/dev/null; then
    printf 'ERROR: Cannot snapshot staged content: %s\n' "$display_file" >&2
    exit 1
  fi

  # Path-restricted per-file sentinel.
  if is_path_restricted "$file"; then
    if snapshot_contains -F "<!-- CONFLICT_MARKER_FORENSIC_FILE_OK -->"; then
      continue
    fi
  fi

  # Co-occurrence pre-check: skip files that don't contain BOTH anchors.
  # Avoids markdown 7-level blockquote false-positive (`>>>>>>> ` alone).
  if ! snapshot_contains -E '^<<<<<<<([[:space:]]|$)'; then
    continue
  fi
  if ! snapshot_contains -E '^>>>>>>>([[:space:]]|$)'; then
    continue
  fi

  # Match and exempt raw bytes before escaping diagnostic text for Bash.
  # grep -n retains the original line numbers, including a final partial line.
  # Capture every pipeline status in the subshell; a no-match from either
  # grep is valid, but read/filter/render errors must reach the parent.
  if ! matches="$(
    grep -anE '^(<<<<<<<|>>>>>>>)([[:space:]]|$)' "$staged_blob" |
      grep -avE '(# CONFLICT_MARKER_FORENSIC_OK|// CONFLICT_MARKER_FORENSIC_OK|<!-- CONFLICT_MARKER_FORENSIC_OK -->)$' |
      LC_ALL=C cat -v
    pipeline_status=("${PIPESTATUS[@]}")
    [[ ${pipeline_status[0]} -le 1 && ${pipeline_status[1]} -le 1 &&
       ${pipeline_status[2]} -eq 0 ]]
  )"; then
    snapshot_read_error
  fi
  if [[ -n "$matches" ]]; then
    while IFS= read -r line; do
      violations+=("${display_file}:${line}")
    done <<< "$matches"
  fi

done < "$staged_paths" || {
  printf 'ERROR: Cannot enumerate staged paths.\n' >&2
  exit 1
}

# A failed read must not look like EOF, including after a skipped entry.
if ! expected_paths="$(tr -cd '\0' < "$staged_paths" | wc -c)" ||
   [[ "$processed_paths" -ne "$expected_paths" ]]; then
  printf 'ERROR: Cannot enumerate staged paths.\n' >&2
  exit 1
fi

if [[ ${#violations[@]} -eq 0 ]]; then
  exit 0
fi

cat >&2 <<'EOF'
ERROR: Unresolved merge-conflict markers detected in staged content:
EOF
printf '  %s\n' "${violations[@]}" >&2
cat >&2 <<'EOF'

To resolve: edit each file, remove the <<<<<<<, =======, >>>>>>> markers,
keep the intended content, re-stage, and retry the commit.

For legitimate forensic documentation, either:
  - append `# CONFLICT_MARKER_FORENSIC_OK` (or `//` / `<!-- -->` variant) at
    end of the marker-bearing line (per-line exemption); OR
  - if the file is under docs/plans/, docs/governance/, docs/standards/,
    scripts/review/results/, or scripts/review/prompts/, add
    `<!-- CONFLICT_MARKER_FORENSIC_FILE_OK -->` anywhere in the file
    (path-restricted whole-file exemption).
EOF
exit 1
