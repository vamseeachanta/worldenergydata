#!/usr/bin/env python3
"""
Improved Git operations for all repositories - handles both main and master branches
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, List
import json

def get_default_branch(repo_path: Path) -> str:
    """Get the default branch name (main or master)"""
    try:
        # Try to get the default branch from remote
        cmd = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if cmd.returncode == 0:
            # Extract branch name from refs/remotes/origin/main or refs/remotes/origin/master
            return cmd.stdout.strip().split('/')[-1]
        
        # Fallback: check if main or master exists locally
        branches = subprocess.run(
            ["git", "branch", "-a"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if "main" in branches.stdout:
            return "main"
        elif "master" in branches.stdout:
            return "master"
        else:
            # Default to current branch
            current = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return current.stdout.strip()
            
    except Exception:
        return "main"  # Default fallback

def commit_and_push_improved(repo_path: Path) -> Tuple[str, dict]:
    """Commit all changes and push to default branch (main or master)"""
    repo_name = repo_path.name
    result = {"repo": repo_name, "status": "unknown", "operations": []}
    
    try:
        # Get current branch and default branch
        current_branch_cmd = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        current_branch = current_branch_cmd.stdout.strip()
        default_branch = get_default_branch(repo_path)
        
        result["current_branch"] = current_branch
        result["default_branch"] = default_branch
        
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
            result["operations"].append(f"Committed on {current_branch}")
        else:
            # Check if it's just "nothing to commit"
            if "nothing to commit" in commit_cmd.stdout:
                result["status"] = "no_changes"
                result["operations"].append("Nothing to commit")
                return repo_name, result
            else:
                result["status"] = "commit_failed"
                result["error"] = commit_cmd.stderr or commit_cmd.stdout
                return repo_name, result
        
        # If not on default branch, switch to it
        if current_branch != default_branch:
            # First, ensure the default branch exists locally
            fetch_cmd = subprocess.run(
                ["git", "fetch", "origin", default_branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            # Check if default branch exists locally
            branch_exists = subprocess.run(
                ["git", "rev-parse", "--verify", default_branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if branch_exists.returncode != 0:
                # Create default branch from origin
                create_branch = subprocess.run(
                    ["git", "checkout", "-b", default_branch, f"origin/{default_branch}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if create_branch.returncode != 0:
                    # If that fails, just push current branch
                    result["operations"].append(f"Staying on {current_branch}")
                else:
                    result["operations"].append(f"Created and switched to {default_branch}")
                    # Merge the original branch
                    merge_cmd = subprocess.run(
                        ["git", "merge", current_branch, "--no-ff", "-m", f"Merge branch '{current_branch}'"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                    if merge_cmd.returncode == 0:
                        result["operations"].append(f"Merged {current_branch} into {default_branch}")
            else:
                # Checkout existing default branch
                checkout_cmd = subprocess.run(
                    ["git", "checkout", default_branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if checkout_cmd.returncode == 0:
                    result["operations"].append(f"Switched to {default_branch}")
                    
                    # Merge current branch
                    merge_cmd = subprocess.run(
                        ["git", "merge", current_branch, "--no-ff", "-m", f"Merge branch '{current_branch}'"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if merge_cmd.returncode == 0:
                        result["operations"].append(f"Merged {current_branch} into {default_branch}")
                    else:
                        # Try fast-forward or rebase
                        result["operations"].append(f"Merge conflict - staying on {default_branch}")
        
        # Determine which branch to push
        push_branch = default_branch if current_branch != default_branch else current_branch
        
        # Push to remote
        push_cmd = subprocess.run(
            ["git", "push", "origin", push_branch],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if push_cmd.returncode == 0:
            result["operations"].append(f"Pushed to origin/{push_branch}")
            result["status"] = "success"
        else:
            # Try to pull and push again
            pull_cmd = subprocess.run(
                ["git", "pull", "origin", push_branch, "--rebase"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            push_retry = subprocess.run(
                ["git", "push", "origin", push_branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if push_retry.returncode == 0:
                result["operations"].append(f"Pulled and pushed to origin/{push_branch}")
                result["status"] = "success"
            else:
                result["status"] = "push_failed"
                result["error"] = push_retry.stderr or push_retry.stdout
                
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        
    return repo_name, result

def main():
    """Main execution"""
    base_dir = Path("/mnt/github/github")
    
    # Get all repository directories
    repos = [d for d in base_dir.iterdir() 
             if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('_')]
    
    print(f"🔍 Found {len(repos)} repositories")
    print("=" * 60)
    
    # Process all repos for commit and push
    print("\n📝 Processing all repositories...")
    print("=" * 60)
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(commit_and_push_improved, repo): repo 
            for repo in repos
        }
        
        for future in as_completed(future_to_repo):
            repo_name, result = future.result()
            results[repo_name] = result
            
            if result["status"] == "success":
                print(f"\n✅ {repo_name} [{result.get('default_branch', 'unknown')}]:")
                for op in result["operations"]:
                    print(f"   - {op}")
            elif result["status"] == "no_changes":
                print(f"\n⏭️  {repo_name}: No changes to commit")
            else:
                print(f"\n❌ {repo_name}: {result['status']}")
                if "error" in result:
                    print(f"   Error: {result['error'][:200]}")  # Truncate long errors
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    no_changes = sum(1 for r in results.values() if r["status"] == "no_changes")
    failed = [r["repo"] for r in results.values() if r["status"] not in ["success", "no_changes"]]
    
    print(f"  ✅ Successfully processed: {success_count} repositories")
    print(f"  ⏭️  No changes: {no_changes} repositories")
    
    if failed:
        print(f"  ❌ Failed: {len(failed)} repositories")
        for repo in failed:
            print(f"     - {repo} ({results[repo].get('status', 'unknown')})")
    
    print("\n✨ Git operations completed for all repositories!")

if __name__ == "__main__":
    main()