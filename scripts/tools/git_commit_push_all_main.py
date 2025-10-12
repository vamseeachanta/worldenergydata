#!/usr/bin/env python3
"""
Commit and push all changes to main branch for all repositories
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Dict
import time

def commit_and_push_to_main(repo_path: Path) -> Tuple[str, Dict]:
    """Commit all changes and push to main branch"""
    repo_name = repo_path.name
    result = {
        "repo": repo_name,
        "status": "unknown",
        "operations": [],
        "branch": ""
    }
    
    try:
        # Check if it's a git repository
        if not (repo_path / ".git").exists():
            result["status"] = "not_git"
            result["operations"].append("Not a git repository")
            return repo_name, result
        
        # Get current branch
        current_branch_cmd = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        current_branch = current_branch_cmd.stdout.strip()
        result["branch"] = current_branch
        
        # Check for uncommitted changes
        status_cmd = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        has_changes = bool(status_cmd.stdout.strip())
        
        if has_changes:
            # Stage all changes
            add_cmd = subprocess.run(
                ["git", "add", "-A"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            result["operations"].append("Staged all changes")
            
            # Commit changes
            commit_msg = f"chore: Update {repo_name} - auto-commit all changes"
            commit_cmd = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if commit_cmd.returncode == 0:
                result["operations"].append(f"Committed changes")
            else:
                if "nothing to commit" in commit_cmd.stdout:
                    result["operations"].append("No changes to commit")
                else:
                    result["status"] = "commit_failed"
                    result["error"] = commit_cmd.stderr or commit_cmd.stdout
                    return repo_name, result
        else:
            result["operations"].append("No changes to commit")
        
        # Ensure we're on main branch
        if current_branch != "main":
            # Switch to main
            checkout_cmd = subprocess.run(
                ["git", "checkout", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if checkout_cmd.returncode == 0:
                result["operations"].append("Switched to main branch")
                
                # Merge the previous branch if it had changes
                if has_changes and current_branch:
                    merge_cmd = subprocess.run(
                        ["git", "merge", current_branch, "--no-ff", "-m", f"Merge branch '{current_branch}' into main"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if merge_cmd.returncode == 0:
                        result["operations"].append(f"Merged {current_branch} into main")
            else:
                # Stay on current branch if can't switch
                result["operations"].append(f"Staying on {current_branch}")
        
        # Pull latest changes first (to avoid conflicts)
        pull_cmd = subprocess.run(
            ["git", "pull", "origin", "main", "--rebase", "--allow-unrelated-histories"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if pull_cmd.returncode == 0 and "up to date" not in pull_cmd.stdout.lower():
            result["operations"].append("Pulled and rebased latest changes")
        
        # Push to remote
        push_cmd = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if push_cmd.returncode == 0:
            result["operations"].append("Pushed to origin/main")
            result["status"] = "success"
        else:
            # Check if it's just "everything up-to-date"
            if "Everything up-to-date" in push_cmd.stderr or "Everything up-to-date" in push_cmd.stdout:
                result["operations"].append("Already up-to-date")
                result["status"] = "success"
            else:
                # Try force push with lease (safer than --force)
                force_push = subprocess.run(
                    ["git", "push", "origin", "main", "--force-with-lease"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if force_push.returncode == 0:
                    result["operations"].append("Force pushed to origin/main (with lease)")
                    result["status"] = "success"
                else:
                    result["status"] = "push_failed"
                    result["error"] = push_cmd.stderr or push_cmd.stdout
        
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["error"] = "Operation timed out"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return repo_name, result

def main():
    """Main execution"""
    base_dir = Path("/mnt/github/github")
    
    # Get all repository directories (excluding hidden and system directories)
    repos = [
        d for d in base_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('_')
    ]
    
    print("🚀 Committing and Pushing All Changes to Main Branch")
    print("=" * 60)
    print(f"📁 Processing {len(repos)} repositories")
    print()
    
    results = {}
    success_count = 0
    failed_repos = []
    
    # Process repositories with limited parallelism to avoid overwhelming the system
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_repo = {
            executor.submit(commit_and_push_to_main, repo): repo 
            for repo in repos
        }
        
        for future in as_completed(future_to_repo):
            repo_name, result = future.result()
            results[repo_name] = result
            
            if result["status"] == "success":
                success_count += 1
                print(f"✅ {repo_name}")
                for op in result["operations"]:
                    print(f"   - {op}")
            elif result["status"] == "not_git":
                print(f"⏭️  {repo_name}: Not a git repository")
            else:
                failed_repos.append(repo_name)
                print(f"❌ {repo_name}: {result['status']}")
                if "error" in result:
                    error_msg = result['error'][:150] if len(result['error']) > 150 else result['error']
                    print(f"   Error: {error_msg}")
            print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY:")
    print(f"  ✅ Successfully processed: {success_count} repositories")
    print(f"  ❌ Failed: {len(failed_repos)} repositories")
    
    if failed_repos:
        print("\n  Failed repositories:")
        for repo in failed_repos:
            print(f"     - {repo}: {results[repo]['status']}")
    
    print("\n✨ Git operations completed!")
    
    return success_count, failed_repos

if __name__ == "__main__":
    success, failed = main()