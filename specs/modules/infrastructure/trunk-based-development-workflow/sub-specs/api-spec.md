# API Specification

This is the API specification for the spec detailed in @specs/modules/infrastructure/trunk-based-development-workflow/spec.md

> Created: 2025-07-25
> Version: 1.0.0

## CLI Interface

### Primary Commands

#### `trunk-workflow init <spec-folder>`

**Purpose:** Initialize trunk-based workflow for a specific spec
**Parameters:** 
- `spec-folder`: Path to spec folder (e.g., `.agent-os/specs/2025-07-25-some-feature`)
**Response:** Creates branch and switches to it, confirms initialization
**Errors:** Spec folder not found, git repository not detected, uncommitted changes

#### `trunk-workflow status`

**Purpose:** Show current workflow status and next recommended actions
**Parameters:** None (uses current directory context)
**Response:** Current branch, sync status, PR status, recommended next step
**Errors:** Not in a git repository, unable to determine spec context

#### `trunk-workflow push`

**Purpose:** Push current branch to origin with upstream tracking
**Parameters:** None
**Response:** Push confirmation, upstream branch setup confirmation
**Errors:** No commits to push, network connectivity issues, authentication problems

#### `trunk-workflow create-pr [--title TITLE] [--body BODY]`

**Purpose:** Create pull request for current branch targeting master
**Parameters:** 
- `--title`: Optional PR title (defaults to spec name)
- `--body`: Optional PR body (defaults to spec summary)
**Response:** PR URL and number
**Errors:** PR already exists, not on feature branch, GitHub authentication issues

#### `trunk-workflow complete-pr <pr-number>`

**Purpose:** Complete pull request by merging and cleaning up branches
**Parameters:** 
- `pr-number`: Pull request number to complete
**Response:** Merge confirmation, cleanup confirmation
**Errors:** PR not found, PR not mergeable, insufficient permissions

#### `trunk-workflow cleanup`

**Purpose:** Clean up local and remote branches after PR completion
**Parameters:** None
**Response:** Branch deletion confirmations
**Errors:** Branch still has unmerged commits, unable to delete remote branch

#### `trunk-workflow sync`

**Purpose:** Sync local master with origin/master
**Parameters:** None
**Response:** Sync confirmation, updated commit count
**Errors:** Merge conflicts, uncommitted changes on master

### Python API Interface

#### TrunkBasedWorkflow Class

```python
from trunk_workflow import TrunkBasedWorkflow

# Initialize workflow
workflow = TrunkBasedWorkflow('.agent-os/specs/2025-07-25-some-feature')

# Check current status
status = workflow.get_status()
print(f"Current branch: {status.current_branch}")
print(f"Next action: {status.next_recommended_action}")

# Execute workflow steps
if workflow.create_branch_from_spec():
    print("Branch created successfully")

if workflow.push_branch_to_origin():
    print("Branch pushed to origin")

pr_url = workflow.create_pull_request("Feature: Add new functionality", "Description...")
print(f"PR created: {pr_url}")
```

## Configuration Interface

### Configuration File: `.trunk-workflow.yaml`

```yaml
# Trunk-based workflow configuration
workflow:
  # Branch naming settings
  branch_prefix: ""  # Optional prefix for all branches
  include_spec_date: false  # Whether to include date in branch name
  
  # PR settings
  default_base_branch: "master"  # Default target branch for PRs
  auto_delete_branch: true  # Automatically delete branch after PR merge
  squash_commits: true  # Use squash merge for PRs
  
  # GitHub settings
  github_cli_path: "gh"  # Path to GitHub CLI executable
  require_pr_review: false  # Whether to require PR review before merge
  
  # Cleanup settings
  cleanup_on_complete: true  # Clean up branches automatically
  sync_master_on_complete: true  # Sync master after cleanup
```

## Response Formats

### Status Response Format

```json
{
  "current_branch": "feature-trunk-workflow",
  "is_spec_branch": true,
  "spec_folder": ".agent-os/specs/2025-07-25-trunk-based-development-workflow",
  "has_uncommitted_changes": false,
  "commits_ahead_of_origin": 3,
  "pr_exists": false,
  "pr_url": null,
  "next_recommended_action": "push",
  "workflow_stage": "development"
}
```

### Error Response Format

```json
{
  "error": true,
  "error_type": "git_error",
  "message": "Unable to push to origin: authentication failed",
  "suggested_action": "Run 'gh auth login' to authenticate with GitHub",
  "recovery_commands": [
    "gh auth login",
    "trunk-workflow push"
  ]
}
```

## Integration Points

### Agent OS Integration

The trunk-based workflow integrates with Agent OS through:

1. **Spec Detection**: Automatically detects current spec context from folder structure
2. **Task Integration**: Links workflow status to spec task completion
3. **Documentation Updates**: Updates spec documentation with PR links

### GitHub Integration

- **Authentication**: Uses `gh auth` for secure GitHub access
- **PR Management**: Full PR lifecycle through GitHub API
- **Branch Protection**: Respects repository branch protection rules