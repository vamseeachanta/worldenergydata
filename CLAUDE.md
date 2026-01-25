<<<<<<< HEAD
# World Energy Data

> Inherits: workspace-hub | Target: <18% (1.4KB)

## Project Focus

Global energy market data aggregation, analysis, and visualization platform.

## Tech Stack

- Python 3.11+ with uv
- Data: pandas, numpy
- Viz: Plotly (interactive HTML)
- Testing: pytest

## Project Rules

1. Data sources must include attribution and timestamp
2. Energy units standardized (BTU, MWh, barrels)
3. All visualizations interactive HTML
4. Validate against EIA/IEA formats

## Key Directories

- `src/` - Analysis modules
- `data/` - Datasets (raw/, processed/)
- `reports/` - HTML reports
- `tests/` - Test files

## Commands

```bash
uv run pytest              # Tests
uv run python -m src.main  # Run analysis
```

## Reference

- Agents: `.claude/docs/agents.md`
- Full rules: Inherited from workspace-hub/CLAUDE.md

---

*Verbose docs in `.claude/docs/`*
=======
# Claude Code Configuration

> **Context Budget**: 8KB max | **Reference Docs**: `.claude/docs/`

## Core Rules

1. **TDD mandatory** - Write tests before implementation
2. **Batch operations** - All related ops in single messages
3. **YAGNI** - Only what's needed, no over-engineering
4. **No sycophancy** - Ask clarifying questions when unclear

## Plan Mode Convention

Save plans to: `specs/modules/<module>/`
- Templates: `specs/templates/plan-template.md` or `plan-template-minimal.md`
- Required metadata: `title`, `description`, `version`, `module`, `session.id`, `session.agent`, `review`

**Cross-Review (MANDATORY)**: Min 3 iterations with OpenAI Codex + Google Gemini before implementation.

## Interactive Engagement

**ASK QUESTIONS BEFORE implementing:**
1. Understand requirements - goals, constraints, context
2. Clarify ambiguities - unclear aspects
3. Propose approach - planned strategy
4. Wait for confirmation - explicit approval
5. Ask follow-ups - as implementation reveals questions

**Never assume. Never implement without approval.**

## Concurrent Execution

**GOLDEN RULE**: 1 message = ALL related operations

```javascript
// CORRECT: All in ONE message
Task("Research", "...", "researcher")
Task("Coder", "...", "coder")
Task("Tester", "...", "tester")
TodoWrite { todos: [...8-10 items...] }
```

**Task tool executes. MCP tools coordinate (optional).**

## File Organization

**NEVER save to root folder:**
- `/src` - Source code
- `/tests` - Test files
- `/docs` - Documentation
- `/config` - Configuration
- `/scripts` - Utilities
- `/specs` - Plans and specifications

## Delegation Pattern

Use Task tool for:
- **Explore**: codebase search, understanding code
- **Plan**: architecture decisions, implementation strategy
- **Bash**: git operations, builds, tests
- **general-purpose**: multi-step implementations

Agents on-demand: `.claude/agent-library/` | Reference: `.claude/docs/agents.md`

## Key Constraints

- Files under 500 lines (modular design)
- Never hardcode secrets
- 80% test coverage minimum

## Reference Documentation

| Doc | When to Load |
|-----|--------------|
| `.claude/docs/agents.md` | Spawning agents |
| `.claude/docs/mcp-tools.md` | MCP coordination |
| `.claude/docs/execution-patterns.md` | Complex workflows |
| `.claude/docs/CONTEXT_LIMITS.md` | Context management |

## Environment

- Python: `>=3.10` with uv environment
- Run tests: `uv run pytest`
- Always use repo's uv environment

---

*Context limit: 8KB. Verbose docs in `.claude/docs/`*
>>>>>>> origin/main
