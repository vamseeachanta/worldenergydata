# Claude Code Configuration

> Inherits: workspace-hub | Target: <8KB

## Core Rules (MANDATORY)

1. **TDD**: Write failing test → implement → refactor
2. **YAGNI**: Simplest solution, no over-engineering
3. **Batch operations**: Single message = all related operations
4. **No sycophancy**: Push back on bad ideas, never "You're absolutely right!"
5. **Ask first**: Stop and clarify rather than assume

## Execution Patterns

### Task Tool for Agents
```javascript
// Single message - all agents in parallel
Task("Researcher", "Analyze...", "researcher")
Task("Coder", "Implement...", "coder")
Task("Tester", "Test...", "tester")
```

### File Organization
- `/src` - Source code
- `/tests` - Test files
- `/docs` - Documentation
- `/data` - CSV files (raw/, processed/, results/)
- `/reports` - HTML reports

### HTML Reporting
- Interactive plots only (Plotly, Bokeh, Altair)
- No static matplotlib exports
- CSV with relative paths

## Code Standards

### Naming
Names tell what code does, not how:
- `Tool` not `AbstractToolInterface`
- Never: NewAPI, LegacyHandler, MCPWrapper

### Comments
- Start files: `ABOUTME: ` (2 lines)
- Explain WHAT/WHY, never "improved" or "new"

### Git
- Never skip pre-commit hooks
- Never `git add -A` without `git status`
- Commit frequently

## Agent Coordination

### Before/During/After Work
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks post-edit --file "[file]"
npx claude-flow@alpha hooks post-task --task-id "[task]"
```

### MCP vs Claude Code
- **MCP**: Coordination setup (swarm_init, topology)
- **Claude Code Task tool**: Actual agent execution

## SPARC Workflow
1. Specification → Requirements
2. Pseudocode → Algorithm design
3. Architecture → System design
4. Refinement → TDD implementation
5. Completion → Integration

## Reference Docs (Load on-demand)
- `.claude/docs/ai-orchestration-reference.md` - Agents, MCP tools, examples
- `.claude/docs/engineering-principles.md` - Full engineering principles
- `~/.agent-os/instructions/create-spec.md` - Spec creation
- `~/.agent-os/instructions/execute-tasks.md` - Task execution

## Rule Precedence
1. Security/Safety
2. TDD (mandatory)
3. Code quality
4. Orchestration patterns
5. Project-specific overrides
