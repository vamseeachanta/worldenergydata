# Available Agents Reference

> Load on-demand when spawning agents

## Core Development (5)

| Agent | Purpose |
|-------|---------|
| `coder` | Implement features, write production code |
| `reviewer` | Review code quality, security, best practices |
| `tester` | Write tests, validate coverage, TDD |
| `planner` | Design implementation strategy, task breakdown |
| `researcher` | Research codebases, gather context, analyze patterns |

## Swarm Coordination (5)

| Agent | Purpose |
|-------|---------|
| `hierarchical-coordinator` | Queen-led tree topology with specialized workers |
| `mesh-coordinator` | Peer-to-peer distributed decision making |
| `adaptive-coordinator` | Dynamic topology switching based on task needs |
| `collective-intelligence-coordinator` | Consensus-based distributed cognition |
| `swarm-memory-manager` | Shared memory and state synchronization |

## Consensus & Distributed (7)

| Agent | Purpose |
|-------|---------|
| `byzantine-coordinator` | Fault-tolerant consensus with malicious actor detection |
| `raft-manager` | Leader election and log replication |
| `gossip-coordinator` | Eventually consistent state propagation |
| `consensus-builder` | Multi-agent agreement protocols |
| `crdt-synchronizer` | Conflict-free replicated data types |
| `quorum-manager` | Dynamic quorum and membership management |
| `security-manager` | Security protocols for distributed systems |

## Performance & Optimization (5)

| Agent | Purpose |
|-------|---------|
| `perf-analyzer` | Identify bottlenecks, optimize workflows |
| `performance-benchmarker` | Run benchmarks, regression detection |
| `task-orchestrator` | Task decomposition, execution planning |
| `memory-coordinator` | Cross-session memory, context persistence |
| `smart-agent` | Intelligent agent selection and routing |

## GitHub & Repository (9)

| Agent | Purpose |
|-------|---------|
| `github-modes` | GitHub workflow orchestration |
| `pr-manager` | Pull request lifecycle management |
| `code-review-swarm` | Multi-agent code review |
| `issue-tracker` | Issue management and triage |
| `release-manager` | Release coordination and deployment |
| `workflow-automation` | GitHub Actions CI/CD pipelines |
| `project-board-sync` | GitHub Projects integration |
| `repo-architect` | Repository structure optimization |
| `multi-repo-swarm` | Cross-repository coordination |

## SPARC Methodology (6)

| Agent | Purpose |
|-------|---------|
| `sparc-coord` | SPARC phase orchestration |
| `sparc-coder` | TDD implementation within SPARC |
| `specification` | Requirements analysis phase |
| `pseudocode` | Algorithm design phase |
| `architecture` | System design phase |
| `refinement` | Iterative improvement phase |

## Specialized Development (8)

| Agent | Purpose |
|-------|---------|
| `backend-dev` | Server-side, APIs, databases |
| `mobile-dev` | Mobile app development |
| `ml-developer` | Machine learning implementation |
| `cicd-engineer` | CI/CD pipelines, DevOps |
| `api-docs` | API documentation generation |
| `system-architect` | High-level system design |
| `code-analyzer` | Static analysis, code quality |
| `base-template-generator` | Boilerplate and starter templates |

## Testing & Validation (2)

| Agent | Purpose |
|-------|---------|
| `tdd-london-swarm` | Mock-driven TDD with swarm coordination |
| `production-validator` | Production readiness validation |

## Migration & Planning (2)

| Agent | Purpose |
|-------|---------|
| `migration-planner` | Migration strategy and execution |
| `swarm-init` | Swarm initialization and topology setup |

---
**Total: 54 agents**

## Usage

```javascript
Task("Agent name", "Instructions", "agent-type")
```

## Quick Selection Guide

| Task Type | Recommended Agent |
|-----------|-------------------|
| Write new code | `coder` |
| Review changes | `reviewer` |
| Write tests | `tester` |
| Explore codebase | `researcher` |
| Design architecture | `system-architect` |
| Multi-agent task | `hierarchical-coordinator` |
| PR management | `pr-manager` |
| Performance issues | `perf-analyzer` |
| TDD workflow | `sparc-coder` or `tdd-london-swarm` |
| Cross-repo work | `multi-repo-swarm` |
