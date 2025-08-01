# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-25-trunk-based-development-workflow/spec.md

> Created: 2025-07-25
> Version: 1.0.0

## Test Coverage

### Unit Tests

**TrunkBasedWorkflow Class**
- Test branch name extraction from spec folder paths
- Test repository root detection in various directory structures
- Test workflow status determination with different git states
- Test error handling for invalid spec folders
- Test configuration loading and validation

**GitOperations Module**
- Test git command execution with various scenarios
- Test git status parsing and interpretation
- Test branch existence checking (local and remote)
- Test commit counting and sync status detection
- Test error handling for git command failures

**PRManager Module**
- Test GitHub CLI availability detection
- Test PR creation with various title/body combinations
- Test PR status checking and URL extraction
- Test PR completion and merge operations
- Test branch cleanup after PR completion

### Integration Tests

**Complete Workflow Integration**
- Test full workflow from spec initialization to cleanup
- Test workflow resumption after interruption
- Test workflow with existing branches and PRs
- Test workflow with merge conflicts
- Test workflow with network connectivity issues

**GitHub Integration**
- Test PR creation and management with real GitHub repository
- Test authentication handling and error recovery
- Test branch protection rule compliance
- Test PR review workflow integration

**Git Repository Integration**
- Test workflow in repositories with various configurations
- Test workflow with uncommitted changes
- Test workflow with detached HEAD state
- Test workflow in repositories with multiple remotes

### Feature Tests

**Branch Management Workflow**
- User creates branch from spec folder successfully
- User switches between workflow branches
- User handles branch naming conflicts
- System prevents work on wrong branch

**Pull Request Workflow**
- User creates PR with spec-based information
- User completes PR review process
- System handles PR merge and cleanup
- System updates documentation with PR links

**Error Recovery Scenarios**
- User recovers from failed push operations
- User resolves merge conflicts during sync
- User handles authentication failures
- System recovers from partial workflow completion

### Mocking Requirements

**Git Commands**
- Mock `subprocess.run` calls for all git operations
- Mock git command responses for various repository states
- Mock network failures for git push/pull operations
- Mock authentication failures and recovery

**GitHub CLI Operations**
- Mock `gh pr create` command responses
- Mock `gh pr status` command outputs
- Mock `gh pr merge` operation results
- Mock GitHub API rate limiting scenarios

**File System Operations**
- Mock spec folder detection and validation
- Mock configuration file reading and parsing
- Mock repository root detection in test environments

## Test Data Setup

### Repository States for Testing

```python
# Test repository configurations
TEST_REPO_STATES = {
    "clean_master": {
        "current_branch": "master",
        "uncommitted_changes": False,
        "ahead_of_origin": 0,
        "behind_origin": 0
    },
    "feature_branch_ready": {
        "current_branch": "feature-test",
        "uncommitted_changes": False,
        "ahead_of_origin": 3,
        "behind_origin": 0
    },
    "dirty_working_tree": {
        "current_branch": "feature-test",
        "uncommitted_changes": True,
        "ahead_of_origin": 0,
        "behind_origin": 0
    },
    "out_of_sync": {
        "current_branch": "master",
        "uncommitted_changes": False,
        "ahead_of_origin": 0,
        "behind_origin": 5
    }
}
```

### Spec Folder Test Fixtures

```python
# Test spec folder structures
TEST_SPEC_FOLDERS = {
    "valid_spec": ".agent-os/specs/2025-07-25-test-feature",
    "no_date_prefix": ".agent-os/specs/test-feature",
    "invalid_path": ".agent-os/specs/nonexistent",
    "malformed_date": ".agent-os/specs/25-07-2025-test-feature"
}
```

### GitHub PR Test Responses

```python
# Mock GitHub CLI responses
MOCK_PR_RESPONSES = {
    "create_success": {
        "stdout": "https://github.com/user/repo/pull/123",
        "stderr": "",
        "returncode": 0
    },
    "create_failure": {
        "stdout": "",
        "stderr": "authentication required",
        "returncode": 1
    },
    "pr_exists": {
        "stdout": "",
        "stderr": "pull request already exists",
        "returncode": 1
    }
}
```

## Test Execution Strategy

### Test Environment Setup
1. Create temporary git repositories for each test
2. Mock external dependencies (GitHub CLI, network calls)
3. Set up spec folder structures in temporary directories
4. Configure test-specific git user settings

### Continuous Integration
- Run full test suite on every commit
- Include integration tests with real git operations
- Test on multiple Python versions (3.9+)
- Test on multiple operating systems (Windows, macOS, Linux)

### Performance Testing
- Test workflow performance with large repositories
- Test memory usage during extensive git operations
- Test timeout handling for slow network operations