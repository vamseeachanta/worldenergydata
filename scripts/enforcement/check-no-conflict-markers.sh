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
#   `git show ":$file"` — eliminates the working-tree-vs-staged-blob TOCTOU
#   bypass surfaced by Codex r2 #2 + Claude r1 #4.
# - Binary policy: scan raw staged bytes as text, including NUL-containing
#   blobs; do not decompress archives. Keep bytes in a temporary file, never
#   a Bash variable. Escape control bytes only when rendering violations.

set -uo pipefail
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

staged_blob="$(mktemp)" || exit 1
trap 'rm -f -- "$staged_blob"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

violations=()

# Stage-aware iteration. NUL-delimited form handles filenames with spaces.
while IFS= read -r -d '' file; do
  # Skip deletions (no staged blob to read).
  if ! git cat-file -e ":$file" 2>/dev/null; then
    continue
  fi

  # Read the staged blob ONCE. This is the single source of truth used by
  # both the per-file sentinel check AND the per-line marker scan.
  if ! git show ":$file" > "$staged_blob" 2>/dev/null; then
    printf 'ERROR: Cannot snapshot staged content: %s\n' "$file" >&2
    exit 1
  fi

  # Path-restricted per-file sentinel.
  if is_path_restricted "$file"; then
    if grep -aqF "<!-- CONFLICT_MARKER_FORENSIC_FILE_OK -->" "$staged_blob"; then
      continue
    fi
  fi

  # Co-occurrence pre-check: skip files that don't contain BOTH anchors.
  # Avoids markdown 7-level blockquote false-positive (`>>>>>>> ` alone).
  if ! grep -aqE '^<<<<<<<([[:space:]]|$)' "$staged_blob"; then
    continue
  fi
  if ! grep -aqE '^>>>>>>>([[:space:]]|$)' "$staged_blob"; then
    continue
  fi

  # Match and exempt raw bytes before escaping diagnostic text for Bash.
  # grep -n retains the original line numbers, including a final partial line.
  while IFS= read -r line; do
    violations+=("${file}:${line}")
  done < <(
    grep -anE '^(<<<<<<<|>>>>>>>)([[:space:]]|$)' "$staged_blob" |
      grep -avE '(# CONFLICT_MARKER_FORENSIC_OK|// CONFLICT_MARKER_FORENSIC_OK|<!-- CONFLICT_MARKER_FORENSIC_OK -->)$' |
      LC_ALL=C cat -v
  )

done < <(git diff --cached --name-only --diff-filter=ACMR -z 2>/dev/null)

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
