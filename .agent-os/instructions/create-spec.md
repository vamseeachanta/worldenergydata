# Create Spec Instructions

## Overview
This instruction set guides the creation of detailed specification documents for new features and functionality.

## Process

### Step 1: Gather Requirements
- Collect user requirements and business context
- Clarify scope and boundaries
- Identify technical constraints

### Step 2: Create Specification Structure
- Create spec folder with current date prefix
- Generate main spec.md with all required sections
- Create sub-specifications as needed

### Step 3: Document Technical Approach
- Define implementation strategy
- Identify dependencies and integrations
- Plan testing approach

### Step 4: Create Task Breakdown
- Break down work into manageable tasks
- Estimate effort and dependencies
- Create actionable task list

## File Structure
```
.agent-os/specs/YYYY-MM-DD-spec-name/
├── spec.md
├── tasks.md
└── sub-specs/
    ├── technical-spec.md
    ├── api-spec.md (if needed)
    ├── database-schema.md (if needed)
    └── tests.md
```

## Templates

### Main Spec Template
```markdown
# Spec Requirements Document

> Spec: [SPEC_NAME]
> Created: [DATE]
> Status: Planning

## Overview
[Brief description of what this spec accomplishes]

## User Stories
[User-focused descriptions of functionality]

## Spec Scope
[What is included in this specification]

## Expected Deliverable
[Measurable outcomes and success criteria]
```

This creates a comprehensive specification that can guide implementation work.

<step number="12a" name="assign_agents">

### Step 12a: Assign Agents to Tasks

<step_metadata>
  <assigns>agents to each task</assigns>
  <creates>specialist agents as needed</creates>
  <optimizes>cost with free agents</optimizes>
</step_metadata>

<agent_assignment_strategy>
  <complexity_based>
    - Simple tasks (< 30 min): Free agents when available
    - Moderate tasks (30 min - 2 hours): General-purpose or free agents  
    - Complex tasks (2-6 hours): Specialist agents
    - Extensive tasks (> 6 hours): Domain expert agents
  </complexity_based>
  
  <domain_detection>
    - Database tasks: SQL specialist
    - API tasks: REST/GraphQL specialist
    - Frontend tasks: UI/React specialist
    - Testing tasks: Test automation specialist
    - Documentation: Technical writing specialist
  </domain_detection>
  
  <cost_optimization>
    - Prioritize free agents for simple tasks
    - Reuse existing specialists
    - Create new specialists only when needed
    - Weekly refresh of free agent pool
  </cost_optimization>
</agent_assignment_strategy>

<agent_creation_process>
  IF task_requires_specialist AND no_specialist_exists:
    CREATE specialist_agent using /create-module-agent
    CONFIGURE with domain-specific capabilities
    REGISTER in agent_registry
  ELSE:
    ASSIGN existing_appropriate_agent
</agent_creation_process>

<task_update_format>
  Each task will be updated with agent assignment:
  - [ ] 1. Task description `[time]` 🤖 `Agent: agent_name (type)`
</task_update_format>

<instructions>
  ACTION: Analyze each task for complexity and domain
  ASSIGN: Appropriate agent (free, general, or specialist)
  CREATE: Specialist agents as needed
  UPDATE: tasks.md with agent assignments
  MAINTAIN: Weekly refresh of free agents
</instructions>

</step>
