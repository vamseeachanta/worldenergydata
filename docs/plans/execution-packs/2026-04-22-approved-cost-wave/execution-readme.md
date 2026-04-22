# Execution Readme — Approved Cost Wave

## Dispatch order

1. Launch Stream A (#335) and Stream B (#338) in parallel.
2. Wait for both to finish and pass their targeted validation.
3. Verify Stream A has committed/pushed before launching Stream C (#337).
4. Launch Stream C (#337).

## Suggested terminal allocation

- Terminal 1 -> stream-335.md
- Terminal 2 -> stream-338.md
- Terminal 3 -> stream-337.md (launch only after Terminal 1 completes)

## Pre-launch checks for every stream

- `gh issue view <issue> --json labels,state` confirms `status:plan-approved`
- `git status --short` is clean
- `git pull --rebase origin main`
- ensure the local plan-approved marker exists if repo hooks require it

## Common validation posture

- Start with the exact new test file(s)
- Then run the closest regression boundary named in the stream prompt
- Avoid broad repo-wide runs unless the stream prompt explicitly requires it

## Stop conditions

Stop the stream and do not improvise if:
- a required file outside Owned paths must change
- the issue is already satisfied on current main
- the implementation would require #336 behavior or policy
- a sibling stream has modified a supposedly forbidden file

## Closeout requirement

Each stream must return:
- files changed
- tests run and results
- adversarial self-review summary
- whether a future issue candidate was discovered
