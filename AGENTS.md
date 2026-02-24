# worldenergydata Agent Contract

> Inherits canonical contract from: workspace-hub/AGENTS.md
> For full contract, required gates, and workflow rules see hub AGENTS.md.

## Repo Role

Global energy market data aggregation, analysis, and visualization platform.
Owns Tier 1 Collection Data — raw data from external public sources.

## Required Gates (inherited)

1. Every non-trivial task must map to a WRK-* item in workspace-hub/.claude/work-queue/
2. Planning + explicit approval are required before implementation.
3. Route B/C work requires cross-review before completion.

## Provider Adapters

- Claude: `.claude/CLAUDE.md`
- Codex: `.codex/CODEX.md` (if present)
- Gemini: `.gemini/GEMINI.md` (if present)
- Skills: `.codex/skills` and `.gemini/skills` symlink to workspace-hub `.claude/skills/`
