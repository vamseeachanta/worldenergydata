# Cross-Review Policy

> **Version**: 1.0 | **Updated**: 2026-01-20

## Core Rule

**ALL work performed by Claude Code or Google Gemini MUST be reviewed by OpenAI Codex.**

## Policy Details

### When to Trigger

- After ANY code commit by Claude or Gemini
- Before presenting work to user
- On significant implementation milestones

### Review Process

1. **Commit changes** immediately after task completion
2. **Submit for Codex review** via post-commit hook
3. **Implement feedback** from Codex (maximum 3 iterations)
4. **Present to user** only after Codex approval OR 3 iterations complete

### Iteration Limits

| Metric | Value |
|--------|-------|
| Max iterations | 3 |
| Review scope | All code commits by Claude/Gemini |
| Reviewer | OpenAI Codex |
| Timeout | None (complete all iterations) |

### Review Scope

Codex reviews for:
- Code quality and best practices
- Security vulnerabilities
- Performance concerns
- Test coverage adequacy
- Documentation completeness
- Adherence to project standards

### Exceptions

Cross-review may be skipped for:
- Documentation-only changes (no code)
- Configuration file updates
- Dependency version bumps
- Typo fixes in comments

User must explicitly approve skipping review.

## Implementation

### Post-Commit Hook

```bash
# .claude/hooks/post-commit
#!/bin/bash
# Trigger Codex review after commit
if [ "$SKIP_CROSS_REVIEW" != "true" ]; then
  echo "Submitting for Codex cross-review..."
  # Implementation depends on Codex integration
fi
```

### Review Request Format

```markdown
## Cross-Review Request

**Commit**: [hash]
**Author**: Claude Code / Google Gemini
**Files Changed**: [list]

### Changes Summary
[Brief description]

### Review Focus Areas
- [ ] Code quality
- [ ] Security
- [ ] Performance
- [ ] Tests
```

## Related Documents

- [Context Limits](./CONTEXT_LIMITS.md)
- [Execution Patterns](./execution-patterns.md)
- Full policy: workspace-hub `docs/modules/ai/CROSS_REVIEW_POLICY.md`
