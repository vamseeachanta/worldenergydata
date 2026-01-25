# Memory Policies Reference

> Load on-demand for cross-session work and persistent state management

## Overview

Memory policies define how data persists across agent sessions, conversations, and workflows. Proper memory management enables knowledge retention, context sharing between agents, and workflow continuity.

## Memory Types

| Type | Duration | Use Case | Namespace Pattern |
|------|----------|----------|-------------------|
| **Short-term** | Current session | Agent working state | `swarm/session/[session-id]` |
| **Medium-term** | 24-72 hours | Cross-session handoffs | `swarm/shared/[task-name]` |
| **Long-term** | Indefinite | Knowledge base, patterns | `swarm/knowledge/[domain]` |

## Namespace Conventions

### Session Memory
```
swarm/session/[session-id]/[agent-type]/[key]
```
**Examples:**
- `swarm/session/abc123/coder/current-file`
- `swarm/session/abc123/tester/test-results`

### Shared Memory
```
swarm/shared/[workflow-name]/[key]
```
**Examples:**
- `swarm/shared/api-refactor/endpoints-list`
- `swarm/shared/auth-feature/design-decisions`

### Knowledge Memory
```
swarm/knowledge/[domain]/[topic]/[key]
```
**Examples:**
- `swarm/knowledge/bsee/api-patterns/field-extraction`
- `swarm/knowledge/testing/coverage-strategies/tdd`

## MCP Memory Operations

### Store Value
```javascript
mcp__claude-flow__memory_store({
  key: "swarm/shared/feature-x/requirements",
  value: { items: [...] },
  metadata: { author: "researcher", timestamp: Date.now() }
})
```

### Retrieve Value
```javascript
mcp__claude-flow__memory_retrieve({
  key: "swarm/shared/feature-x/requirements"
})
```

### Search Memory
```javascript
mcp__claude-flow__memory_search({
  query: "api endpoints",
  limit: 10
})
```

### List All Entries
```javascript
mcp__claude-flow__memory_list({
  limit: 50,
  offset: 0
})
```

## Hook-Based Memory

### Pre-Task: Load Context
```bash
npx claude-flow@alpha hooks pre-task \
  --task-id "implement-auth" \
  --description "Implement user authentication"
```
Automatically loads relevant memory based on task description.

### Post-Task: Persist Results
```bash
npx claude-flow@alpha hooks post-task \
  --task-id "implement-auth" \
  --success true
```
Automatically persists task outcomes and learnings.

### Session Restore
```bash
npx claude-flow@alpha hooks session-restore \
  --session-id "latest"
```
Restores previous session state for continuity.

## Agent Coordination Patterns

### Producer-Consumer
```
Agent A (Producer):
  → Stores results in swarm/shared/[task]/output

Agent B (Consumer):
  → Reads from swarm/shared/[task]/output
  → Processes and stores to swarm/shared/[task]/processed
```

### Knowledge Accumulation
```
Research Agent:
  → Findings → swarm/knowledge/[domain]/findings

Implementation Agent:
  → Reads swarm/knowledge/[domain]/findings
  → Applies patterns
```

### Handoff Protocol
```
1. Agent A completes work
2. Stores state: swarm/shared/handoff/[task-id]
3. Notifies via hooks
4. Agent B retrieves handoff state
5. Continues from checkpoint
```

## Retention Policies

| Memory Type | Auto-Cleanup | Manual Cleanup |
|-------------|--------------|----------------|
| Session | End of session | `memory_delete` |
| Shared | 72 hours | `memory_delete` |
| Knowledge | Never | Explicit request |

### Cleanup Commands
```javascript
// Delete specific key
mcp__claude-flow__memory_delete({ key: "swarm/session/old-id/..." })

// Check storage stats
mcp__claude-flow__memory_stats({})
```

## Best Practices

### DO
- Use descriptive namespace paths
- Include metadata (author, timestamp, purpose)
- Clean up session memory after completion
- Use knowledge memory for reusable patterns
- Batch memory operations in single messages

### DON'T
- Store sensitive credentials in memory
- Use memory for large binary data
- Create deeply nested namespaces (max 4 levels)
- Rely on memory for critical state (use git)
- Forget to handle missing keys gracefully

## Memory Size Guidelines

| Content Type | Max Size | Recommendation |
|--------------|----------|----------------|
| Simple values | 1KB | Keys, flags, IDs |
| Structured data | 10KB | JSON objects, lists |
| Documents | 50KB | Summaries, not full content |
| Large data | N/A | Use file system instead |

## Integration with Workflows

### SPARC Workflow Memory
```
swarm/workflow/sparc/[spec-name]/
  ├── specification/    # Requirements
  ├── pseudocode/       # Algorithm designs
  ├── architecture/     # System decisions
  ├── refinement/       # Iteration notes
  └── completion/       # Final state
```

### Cross-Review Memory
```
swarm/review/[commit-hash]/
  ├── codex-feedback/
  ├── gemini-feedback/
  └── final-status/
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Key not found | Expired or wrong namespace | Check namespace pattern |
| Stale data | No cleanup after task | Use post-task hooks |
| Memory full | Too many session entries | Run cleanup, check stats |
| Cross-agent conflict | Same key, different values | Use agent-specific namespaces |

## Related Documents

- [Execution Patterns](./execution-patterns.md) - Workflow patterns
- [CONTEXT_LIMITS](./CONTEXT_LIMITS.md) - Context budget management
- [agents.md](./agents.md) - Agent capabilities including memory-coordinator
