# Technical Specification

This is the technical specification for the spec detailed in @specs/modules/infrastructure/trunk-based-development-workflow/spec.md

> Created: 2025-07-25
> Version: 1.0.0

## Technical Requirements

- **Git Integration**: Use Python's `subprocess` or `GitPython` library for all git operations
- **Error Handling**: Comprehensive error handling for git failures, network issues, and user conflicts
- **Branch Naming**: Extract branch names from spec folder names, removing date prefixes (YYYY-MM-DD-)
- **PR Integration**: Use GitHub CLI (`gh`) or GitHub API for pull request creation and management
- **Status Tracking**: Provide clear feedback on workflow progress and current state
- **Atomic Operations**: Ensure each step can be safely retried if interrupted
- **Cross-Platform**: Support Windows, macOS, and Linux environments

## Approach Options

**Option A: Python CLI Tool with GitPython**
- Pros: Native Python integration, rich git operations, easy error handling
- Cons: Additional dependency, learning curve for GitPython API

**Option B: Python Wrapper for Git CLI Commands** (Selected)
- Pros: Direct git command usage, familiar to developers, no additional dependencies
- Cons: Platform-specific command handling, string parsing for git output

**Option C: Shell Script Automation**
- Pros: Direct git access, simple implementation
- Cons: Platform limitations, limited error handling, no Python integration

**Rationale:** Option B provides the best balance of functionality and simplicity, leveraging existing git CLI tools while maintaining Python integration for the broader Agent OS ecosystem.

## Core Functions Architecture

### GitWorkflow Class Structure

```python
class TrunkBasedWorkflow:
    def __init__(self, spec_folder_path: str):
        self.spec_folder = spec_folder_path
        self.branch_name = self._extract_branch_name()
        self.repo_root = self._find_repo_root()
    
    def create_branch_from_spec(self) -> bool
    def get_current_status(self) -> WorkflowStatus
    def push_branch_to_origin(self) -> bool
    def create_pull_request(self, title: str, body: str) -> str
    def complete_pull_request(self, pr_number: int) -> bool
    def cleanup_branches(self) -> bool
    def sync_with_master(self) -> bool
```

### Workflow State Management

```python
@dataclass
class WorkflowStatus:
    current_branch: str
    is_spec_branch: bool
    has_uncommitted_changes: bool
    is_ahead_of_origin: bool
    pr_exists: bool
    pr_url: Optional[str]
    next_recommended_action: str
```

## Git Command Implementations

### Branch Operations
- `git checkout -b {branch_name}` for branch creation
- `git push -u origin {branch_name}` for initial push
- `git branch -d {branch_name}` for local cleanup
- `git push origin --delete {branch_name}` for remote cleanup

### Status Checking
- `git status --porcelain` for uncommitted changes
- `git rev-list --count HEAD..origin/master` for sync status
- `git branch --show-current` for current branch

### PR Operations
- `gh pr create --title "{title}" --body "{body}" --base master`
- `gh pr merge {pr_number} --squash --delete-branch`

## Error Handling Strategy

### Common Error Scenarios
1. **Uncommitted Changes**: Prompt user to commit or stash changes
2. **Network Connectivity**: Retry with exponential backoff
3. **Merge Conflicts**: Provide clear instructions for manual resolution
4. **Permission Issues**: Check GitHub authentication and permissions
5. **Branch Already Exists**: Offer to switch to existing branch or create with suffix

### Recovery Mechanisms
- **State Persistence**: Save workflow state to allow resumption after interruption
- **Rollback Capability**: Ability to undo partially completed operations
- **Safe Mode**: Read-only mode to check status without making changes

## External Dependencies

- **GitHub CLI (gh)** - For pull request creation and management
- **Justification:** Provides official GitHub integration with authentication handling

The system will check for `gh` availability and provide installation instructions if missing. Fallback to GitHub API via HTTP requests is possible but `gh` CLI provides better user experience with existing authentication.