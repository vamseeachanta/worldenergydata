#!/usr/bin/env python3
"""
Script to help migrate from requirements.txt to uv project management.
This script provides commands to sync dependencies from requirements.txt to uv.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return its output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {cmd}")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Error running: {cmd}")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Exception running {cmd}: {e}")
        return False

def main():
    """Main function to handle uv migration."""
    print("🚀 uv Migration Helper for worldenergydata")
    print("=" * 50)
    
    # Check if uv is installed
    if not run_command("uv --version"):
        print("Please install uv first: pip install uv")
        sys.exit(1)
    
    # Change to project directory
    project_dir = Path(__file__).parent.parent
    print(f"📁 Working in: {project_dir}")
    
    # Initialize uv project if needed
    print("\n1. Initializing uv project...")
    run_command("uv init --no-readme")
    
    # Add dependencies from requirements.txt
    print("\n2. Adding dependencies from requirements.txt...")
    requirements_file = project_dir / "scripts" / "requirements.txt"
    if requirements_file.exists():
        run_command(f"uv add -r {requirements_file}")
    else:
        print(f"❌ Requirements file not found: {requirements_file}")
    
    # Add dev dependencies
    print("\n3. Adding dev dependencies...")
    dev_deps = ["black>=23.0", "bumpver>=2023.1129", "isort>=5.0.0", "pytest>=7.0.0"]
    for dep in dev_deps:
        run_command(f"uv add --dev {dep}")
    
    # Sync the environment
    print("\n4. Syncing environment...")
    run_command("uv sync")
    
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("- Run 'uv sync' to install dependencies")
    print("- Run 'uv run python -m worldenergydata' to run your project")
    print("- Run 'uv add <package>' to add new dependencies")
    print("- Run 'uv remove <package>' to remove dependencies")

if __name__ == "__main__":
    main()
