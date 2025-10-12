#!/usr/bin/env python3
"""
Git operations for all repositories - commit, merge, and push to master
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, List
import json

def get_repo_status(repo_path: Path) -> Tuple[str, dict]:
    """Get git status for a repository"""
    repo_name = repo_path.name
    result = {"repo": repo_name, "status": "unknown", "changes": False, "message": ""}
    
    try:
        # Check if it's a git repository
        if not (repo_path / ".git").exists():
            result["status"] = "not_git"
            result["message"] = "Not a git repository"
            return repo_name, result
            
        # Get current branch
        branch_cmd = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        current_branch = branch_cmd.stdout.strip()
        result["branch"] = current_branch
        
        # Check for changes
        status_cmd = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if status_cmd.stdout.strip():
            result["changes"] = True
            result["status"] = "has_changes"
            result["message"] = f"Has uncommitted changes on {current_branch}"
        else:
            result["status"] = "clean"
            result["message"] = f"Clean on {current_branch}"
            
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
        
    return repo_name, result

def commit_and_push(repo_path: Path) -> Tuple[str, dict]:
    """Commit all changes and push to master"""
    repo_name = repo_path.name
    result = {"repo": repo_name, "status": "unknown", "operations": []}
    
    try:
        # Get current branch
        branch_cmd = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        current_branch = branch_cmd.stdout.strip()
        
        # Check for changes
        status_cmd = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if not status_cmd.stdout.strip():
            result["status"] = "no_changes"
            result["operations"].append("No changes to commit")
            return repo_name, result
            
        # Stage all changes
        add_cmd = subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        result["operations"].append("Staged all changes")
        
        # Commit changes
        commit_msg = f"chore: Auto-commit all changes from {repo_name}"
        commit_cmd = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if commit_cmd.returncode == 0:
            result["operations"].append(f"Committed: {commit_msg}")
        else:
            result["status"] = "commit_failed"
            result["error"] = commit_cmd.stderr
            return repo_name, result
            
        # If not on master, checkout master and merge
        if current_branch != "master":
            # Checkout master
            checkout_cmd = subprocess.run(
                ["git", "checkout", "master"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if checkout_cmd.returncode == 0:
                result["operations"].append("Switched to master branch")
                
                # Merge current branch
                merge_cmd = subprocess.run(
                    ["git", "merge", current_branch, "--no-ff", "-m", f"Merge branch '{current_branch}' into master"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if merge_cmd.returncode == 0:
                    result["operations"].append(f"Merged {current_branch} into master")
                else:
                    result["status"] = "merge_failed"
                    result["error"] = merge_cmd.stderr
                    return repo_name, result
        
        # Push to remote
        push_cmd = subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if push_cmd.returncode == 0:
            result["operations"].append("Pushed to origin/master")
            result["status"] = "success"
        else:
            # Try to pull and push again
            pull_cmd = subprocess.run(
                ["git", "pull", "origin", "master", "--rebase"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            push_retry = subprocess.run(
                ["git", "push", "origin", "master"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if push_retry.returncode == 0:
                result["operations"].append("Pulled and pushed to origin/master")
                result["status"] = "success"
            else:
                result["status"] = "push_failed"
                result["error"] = push_retry.stderr
                
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        
    return repo_name, result

def main():
    """Main execution"""
    base_dir = Path("/mnt/github/github")
    
    # Get all repository directories
    repos = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    print(f"🔍 Found {len(repos)} repositories")
    print("=" * 60)
    
    # Phase 1: Check status of all repos
    print("\n📊 Phase 1: Checking repository status...")
    status_results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {executor.submit(get_repo_status, repo): repo for repo in repos}
        
        for future in as_completed(future_to_repo):
            repo_name, result = future.result()
            status_results[repo_name] = result
            
            if result["changes"]:
                print(f"  ✓ {repo_name}: {result['message']}")
            elif result["status"] == "clean":
                print(f"  - {repo_name}: {result['message']}")
            else:
                print(f"  ⚠ {repo_name}: {result['message']}")
    
    # Filter repos with changes
    repos_with_changes = [
        repo for repo in repos 
        if status_results.get(repo.name, {}).get("changes", False)
    ]
    
    if not repos_with_changes:
        print("\n✅ All repositories are clean - no changes to commit")
        return
        
    print(f"\n📝 Phase 2: Processing {len(repos_with_changes)} repositories with changes...")
    print("=" * 60)
    
    # Phase 2: Commit and push changes
    commit_results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(commit_and_push, repo): repo 
            for repo in repos_with_changes
        }
        
        for future in as_completed(future_to_repo):
            repo_name, result = future.result()
            commit_results[repo_name] = result
            
            if result["status"] == "success":
                print(f"\n✅ {repo_name}:")
                for op in result["operations"]:
                    print(f"   - {op}")
            elif result["status"] == "no_changes":
                print(f"\n⏭️  {repo_name}: {result['operations'][0]}")
            else:
                print(f"\n❌ {repo_name}: {result['status']}")
                if "error" in result:
                    print(f"   Error: {result['error']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    
    success_count = sum(1 for r in commit_results.values() if r["status"] == "success")
    no_changes = sum(1 for r in commit_results.values() if r["status"] == "no_changes")
    failed = [r["repo"] for r in commit_results.values() if r["status"] not in ["success", "no_changes"]]
    
    print(f"  ✅ Successfully processed: {success_count} repositories")
    print(f"  ⏭️  No changes: {no_changes} repositories")
    
    if failed:
        print(f"  ❌ Failed: {len(failed)} repositories")
        for repo in failed:
            print(f"     - {repo}")
    
    print("\n✨ Git operations completed for all repositories!")

if __name__ == "__main__":
    main()