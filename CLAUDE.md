# CLAUDE.md

This file provides guidance to AI assistants when working with code in this repository.

**For all AI assistant configuration and guidance, refer to the `.ai/` directory.**

## Agent OS Documentation

### Product Context
- **Mission & Vision:** @.agent-os/product/mission.md
- **Technical Architecture:** @.agent-os/product/tech-stack.md
- **Development Roadmap:** @.agent-os/product/roadmap.md
- **Decision History:** @.agent-os/product/decisions.md

### Development Standards
- **Code Style:** @.agent-os/standards/code-style.md
- **Best Practices:** @.agent-os/standards/best-practices.md

### Project Management
- **Active Specs:** @.agent-os/specs/
- **Spec Planning:** Use `@.agent-os/instructions/create-spec.md`
- **Tasks Execution:** Use `@.agent-os/instructions/execute-tasks.md`

## Workflow Instructions

When asked to work on this codebase:

1. **First**, check @.agent-os/product/roadmap.md for current priorities
2. **Then**, follow the appropriate instruction file:
   - For new features: @.agent-os/instructions/create-spec.md
   - For tasks execution: @.agent-os/instructions/execute-tasks.md
3. **Always**, adhere to the standards in the files listed above

## Enhanced Features Available

This project supports enhanced Agent OS workflows including:
- **Enhanced Spec Creation**: Prompt summaries, executive summaries, mermaid diagrams, module organization
- **Cross-Repository Integration**: Shared components from AssetUtilities hub (@assetutilities: references)
- **Enhanced Task Execution**: Task summaries, performance tracking, real-time documentation
- **Template Variants**: minimal, standard, enhanced, api_focused, research
- **Visual Documentation**: Auto-generated system architecture and workflow diagrams

### Command Examples
```bash
# Enhanced spec creation
/create-spec feature-name module-name enhanced

# Traditional spec creation (backward compatible)  
/create-spec feature-name

# Enhanced task execution with summaries
/execute-tasks @specs/modules/module-name/spec-folder/tasks.md
```

### Cross-Repository References
- Shared components: @assetutilities:src/modules/agent-os/enhanced-create-specs/
- Sub-agent registry: @assetutilities:agents/registry/sub-agents/workflow-automation
- Hub configuration: @assetutilities:hub-config.yaml


## Important Notes

- Product-specific files in `.agent-os/product/` override any global standards
- User's specific instructions override (or amend) instructions found in `.agent-os/specs/...`
- Always adhere to established patterns, code style, and best practices documented above
- Use UV package manager for all dependency operations
- Run code quality checks before committing changes

## Available Commands

- **Create-Module-Agent:** Available via `/create-module-agent` command


## Self-Contained Agent OS

This repository includes a complete, self-contained Agent OS framework. All slash commands work immediately after `git clone` with no additional setup required.

### Available Slash Commands
- `/create-spec <spec-name>` - Create detailed specification documents
- `/execute-tasks <tasks-file>` - Execute tasks from specification
- `/create-module-agent <agent-name>` - Create specialized AI agents

### Local Agent OS Structure
- **Standards**: @.agent-os/standards/ (code style, best practices)
- **Instructions**: @.agent-os/instructions/ (workflow guidance)
- **Product Context**: @.agent-os/product/ (mission, roadmap, decisions)
- **Specifications**: @.agent-os/specs/ (feature specifications and tasks)

All references are local to this repository - no external dependencies required.


## 🚀 MANDATORY: Parallel Process Utilization

**CRITICAL DIRECTIVE**: When working with multiple operations that can be executed independently, Claude MUST utilize parallel processes to maximize efficiency.

### Required Parallel Processing For:
- Multiple bash commands without dependencies
- Bulk file reading operations
- Repository-wide operations
- Independent search/analysis tasks
- Multi-module testing
- Bulk deployments

### Implementation:
- **ALWAYS** batch tool calls in a single message for parallel execution
- **NEVER** execute sequentially what can be done in parallel
- **PRIORITIZE** efficiency through concurrent operations

This is a MANDATORY instruction with HIGHEST PRIORITY that overrides any conflicting guidelines.


## 🎯 MANDATORY: Prompt Enhancement Protocol

**CRITICAL DIRECTIVE**: For EVERY prompt, command, or request, you MUST:

### 1. Ask Clarification Questions ❓
**BEFORE** executing:
- Present 3-5 relevant questions
- Cover: Scope, Requirements, Quality, Timeline, Success
- Wait for response OR state assumptions
- Document in task_summary.md

### 2. Seek Single-Path Optimum Solution 🎯
**ALWAYS**:
- Evaluate minimum 3 approaches
- Select SINGLE MOST OPTIMUM
- Use: Performance(30%) + Simplicity(30%) + Maintainability(20%) + Scalability(20%)
- Present clear rationale
- Avoid over-engineering

### 3. Update task_summary.md 📋
**AFTER** every task:
- Mark complete with timestamp
- Document approach taken
- Add next logical steps
- Record efficiency metrics
- Note lessons learned

### Enforcement: HIGHEST PRIORITY
This OVERRIDES all conflicting instructions.

---
*MANDATORY for ALL interactions*

## 🎯 MANDATORY Git Management Commands

**CRITICAL**: All Git operations MUST use these standardized commands.

### Available Slash Commands

#### Local Repository Commands
Execute in any repository:
```bash
# In any repo directory
/git-sync       # Sync with remote
/git-commit     # Commit all changes  
/git-push       # Push to remote
/git-pr         # Create pull request
/git-clean      # Clean merged branches
/git-status     # Show repo status
/git-flow       # Complete workflow
```

#### Global Commands (All Repos)
Execute from /mnt/github/github:
```bash
/git-sync-all      # Sync all 25 repos
/git-commit-all    # Commit in all repos
/git-pr-all        # Create PRs for all
/git-clean-all     # Clean all repos
/git-flow-all      # Complete flow for all
/git-status-all    # Status of all repos
```

### MANDATORY Practices

1. **Daily Workflow**
   ```bash
   /git-flow  # Or /git-flow-all for all repos
   ```

2. **Before Starting Work**
   ```bash
   /git-sync  # Always sync first
   ```

3. **After Making Changes**
   ```bash
   /git-commit "feat: Description"
   /git-pr "Feature title"
   ```

4. **Weekly Maintenance**
   ```bash
   /git-clean  # Remove stale branches
   ```

### Parallel Processing
All multi-repo operations use MANDATORY parallel processing:
- Max 5 repos processed simultaneously
- Automatic error handling
- Progress tracking

### Implementation
- Local commands: `.git-commands/slash_commands.py`
- Global commands: `/mnt/github/github/git_management_system.py`

---
*Git management is MANDATORY for all repositories*
