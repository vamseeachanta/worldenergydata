# Required knowledge pack lint

`required-pack-lint.json` is an importable supplemental branch ruleset for
the `Lint Changed Knowledge Packs` job in `../workflows/pr-validation.yml`.
It prepares the missing protection identified by issue #1353. Committing
this file does not activate it on GitHub; hosted enforcement remains
**NOT_EVALUATED** until a maintainer imports it and checks merge blocking.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Prepare a supplemental required check because lint failures alone do not prevent merging. |

## Policy and sources

- The rule is active, targets the default branch and grants no bypasses.
  `~DEFAULT_BRANCH` and the required-check fields follow the
  [GitHub REST ruleset schema, API version 2022-11-28](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset).
- It adds only `Lint Changed Knowledge Packs`, using the job's display name.
  Existing checks remain in the existing ruleset. GitHub combines matching
  rulesets and retains the strongest applicable requirements; see
  [About rule layering](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets#about-rule-layering).
- The supplemental rule does not require an up-to-date branch, matching the
  existing ruleset inspected for this issue. A stricter matching rule would
  still apply. The rule does not exempt branch creation from check enforcement.
- The optional integration identifier is omitted, so the context accepts any
  source. A maintainer can restrict it to the observed GitHub Actions app
  during import. No integration identifier is guessed. See
  [Required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging).

## Activation by a maintainer

Use the repository's **Settings**, **Rules**, **Rulesets**, **New ruleset**,
**Import a ruleset** option, select `required-pack-lint.json`, review the
default-branch target and required context, and select **Create**. This is the
[documented JSON import procedure](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository#importing-a-ruleset).
Keep the existing ruleset in place. Confirm the imported rule is active and
that its required check appears in the effective default-branch rules.

Check hosted acceptance on a disposable pull request before treating issue
#1353 as resolved:

- Add a knowledge pack with a missing sweep declaration. Confirm the lint
  check reports `SWEEP` and the merge is blocked by that required check.
- Correct the sweep declaration and introduce an account URL finding. Confirm
  `URL` fails and the required check blocks the merge again.
- Correct the pack and confirm the check succeeds. A pull request that changes
  no pack must also produce a successful check. Other required checks can
  independently block merging.

Record the check result and the merge restriction together. A failing lint
job alone does not demonstrate branch-rule enforcement. Creating these
acceptance pull requests is outside the offline configuration slice.

## Local verification

Run the ruleset contract tests together with the existing pack lint tests:

```sh
uv run --no-project --with pytest --with pyyaml python -m pytest \
  tests/unit/hygiene/test_pack_lint_ruleset.py \
  tests/unit/hygiene/test_pack_lint.py \
  tests/unit/hygiene/test_pack_lint_workflow.py \
  --noconftest -o addopts='' -q -p no:cacheprovider
```

The contract tests check activation, scope, bypasses, the exact workflow
context and unconditional execution. Existing workflow tests execute the
production shell with clean, `SWEEP`, `URL` and no-pack inputs. These are local
regressions; they do not establish that a GitHub ruleset has been imported.
