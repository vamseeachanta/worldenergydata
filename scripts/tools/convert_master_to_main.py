#!/usr/bin/env python3
"""
Convert all repository default branches from master to main
Following GitHub's modern best practices
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Dict
import time

def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name"""
    try:
        cmd = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return cmd.stdout.strip()
    except Exception:
        return "unknown"

def check_branch_exists(repo_path: Path, branch: str, remote: bool = False) -> bool:
    """Check if a branch exists locally or remotely"""
    try:
        if remote:
            cmd = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return branch in cmd.stdout
        else:
            cmd = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return cmd.returncode == 0
    except Exception:
        return False

def convert_master_to_main(repo_path: Path) -> Tuple[str, Dict]:
    """Convert master branch to main for a repository"""
    repo_name = repo_path.name
    result = {
        "repo": repo_name,
        "status": "unknown",
        "operations": [],
        "original_branch": "",
        "final_branch": ""
    }
    
    try:
        # Check if it's a git repository
        if not (repo_path / ".git").exists():
            result["status"] = "not_git"
            result["operations"].append("Not a git repository")
            return repo_name, result
        
        # Get current branch
        current_branch = get_current_branch(repo_path)
        result["original_branch"] = current_branch
        
        # Check if main already exists
        main_exists_local = check_branch_exists(repo_path, "main", remote=False)
        main_exists_remote = check_branch_exists(repo_path, "main", remote=True)
        master_exists_local = check_branch_exists(repo_path, "master", remote=False)
        master_exists_remote = check_branch_exists(repo_path, "master", remote=True)
        
        # Determine the action needed
        if main_exists_remote and not master_exists_remote:
            result["status"] = "already_main"
            result["operations"].append("Repository already uses 'main' as default")
            result["final_branch"] = "main"
            return repo_name, result
        
        if not master_exists_local and not master_exists_remote:
            # No master branch, but check if we need to create main
            if not main_exists_remote:
                # Create main from current branch
                if current_branch != "main":
                    # Create and switch to main
                    create_cmd = subprocess.run(
                        ["git", "checkout", "-b", "main"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True
                    )
                    if create_cmd.returncode == 0:
                        result["operations"].append("Created 'main' branch from current branch")
                    else:
                        result["status"] = "create_failed"
                        result["error"] = create_cmd.stderr
                        return repo_name, result
                
                # Push main to remote
                push_cmd = subprocess.run(
                    ["git", "push", "-u", "origin", "main"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if push_cmd.returncode == 0:
                    result["operations"].append("Pushed 'main' to remote")
                    result["status"] = "converted"
                    result["final_branch"] = "main"
                else:
                    result["status"] = "push_failed"
                    result["error"] = push_cmd.stderr
            else:
                result["status"] = "already_main"
                result["operations"].append("Already using 'main'")
                result["final_branch"] = "main"
            return repo_name, result
        
        # Master exists, need to rename it to main
        result["operations"].append(f"Converting 'master' to 'main' for {repo_name}")
        
        # Step 1: Fetch latest changes
        fetch_cmd = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        result["operations"].append("Fetched latest changes")
        
        # Step 2: Checkout master if not already on it
        if current_branch != "master":
            checkout_cmd = subprocess.run(
                ["git", "checkout", "master"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if checkout_cmd.returncode != 0:
                # Try to create master from origin/master
                create_master = subprocess.run(
                    ["git", "checkout", "-b", "master", "origin/master"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if create_master.returncode != 0:
                    result["status"] = "checkout_failed"
                    result["error"] = "Could not checkout master branch"
                    return repo_name, result
            result["operations"].append("Checked out master branch")
        
        # Step 3: Create main branch from master
        if main_exists_local:
            # Delete existing local main
            delete_cmd = subprocess.run(
                ["git", "branch", "-D", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            result["operations"].append("Deleted existing local 'main' branch")
        
        # Create main from master
        create_main_cmd = subprocess.run(
            ["git", "branch", "-m", "master", "main"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if create_main_cmd.returncode == 0:
            result["operations"].append("Renamed 'master' to 'main' locally")
        else:
            # Alternative approach
            create_alt = subprocess.run(
                ["git", "checkout", "-b", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if create_alt.returncode == 0:
                result["operations"].append("Created 'main' from master")
            else:
                result["status"] = "rename_failed"
                result["error"] = create_main_cmd.stderr
                return repo_name, result
        
        # Step 4: Push main to remote
        push_main_cmd = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if push_main_cmd.returncode == 0:
            result["operations"].append("Pushed 'main' to remote")
        else:
            # Force push if needed (be careful!)
            force_push = subprocess.run(
                ["git", "push", "-u", "origin", "main", "--force-with-lease"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if force_push.returncode == 0:
                result["operations"].append("Force pushed 'main' to remote (with lease)")
            else:
                result["status"] = "push_failed"
                result["error"] = push_main_cmd.stderr
                return repo_name, result
        
        # Step 5: Update default branch on GitHub (this requires gh CLI or API)
        # For now, we'll just note that this needs to be done
        result["operations"].append("⚠️ Need to update default branch on GitHub settings")
        
        # Step 6: Delete master branch remotely (optional, commented out for safety)
        # delete_remote_cmd = subprocess.run(
        #     ["git", "push", "origin", "--delete", "master"],
        #     cwd=repo_path,
        #     capture_output=True,
        #     text=True
        # )
        # if delete_remote_cmd.returncode == 0:
        #     result["operations"].append("Deleted remote 'master' branch")
        
        result["status"] = "converted"
        result["final_branch"] = "main"
        
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
    
    print("🔄 Converting Repository Default Branches: master → main")
    print("=" * 60)
    print(f"📁 Found {len(repos)} repositories to process")
    print()
    
    results = {}
    
    # Process repositories in batches to avoid overwhelming the system
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_repo = {
            executor.submit(convert_master_to_main, repo): repo 
            for repo in repos
        }
        
        for future in as_completed(future_to_repo):
            repo_name, result = future.result()
            results[repo_name] = result
            
            if result["status"] == "converted":
                print(f"✅ {repo_name}: Successfully converted to 'main'")
                for op in result["operations"]:
                    print(f"   - {op}")
            elif result["status"] == "already_main":
                print(f"✓  {repo_name}: Already using 'main' branch")
            elif result["status"] == "not_git":
                print(f"⏭️  {repo_name}: Not a git repository")
            else:
                print(f"❌ {repo_name}: {result['status']}")
                if "error" in result:
                    print(f"   Error: {result.get('error', 'Unknown error')[:150]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CONVERSION SUMMARY:")
    
    converted = sum(1 for r in results.values() if r["status"] == "converted")
    already_main = sum(1 for r in results.values() if r["status"] == "already_main")
    failed = [r["repo"] for r in results.values() if r["status"] not in ["converted", "already_main", "not_git"]]
    
    print(f"  ✅ Successfully converted: {converted} repositories")
    print(f"  ✓  Already using 'main': {already_main} repositories")
    
    if failed:
        print(f"  ❌ Failed: {len(failed)} repositories")
        for repo in failed:
            print(f"     - {repo}")
    
    if converted > 0:
        print("\n⚠️  IMPORTANT NEXT STEPS:")
        print("  1. Go to each repository's GitHub settings")
        print("  2. Change the default branch from 'master' to 'main'")
        print("  3. Update any CI/CD pipelines that reference 'master'")
        print("  4. Notify team members about the branch change")
        print("  5. Optionally delete the old 'master' branch after verification")
    
    print("\n✨ Branch conversion process completed!")

if __name__ == "__main__":
    main()