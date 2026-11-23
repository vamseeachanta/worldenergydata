#!/bin/bash

echo "Checking branch status for all repositories..."
echo "==========================================="

cd /mnt/github/github

for dir in */; do
    if [ -d "$dir/.git" ]; then
        cd "$dir"
        repo_name="${dir%/}"
        current_branch=$(git branch --show-current 2>/dev/null)
        
        # Check if master exists locally
        master_exists=$(git branch -l | grep -c "master")
        # Check if main exists locally  
        main_exists=$(git branch -l | grep -c "main")
        
        # Check remote branches
        remote_branches=$(git branch -r 2>/dev/null | head -5)
        
        echo "📁 $repo_name:"
        echo "   Current: $current_branch"
        echo "   Has master: $([ $master_exists -gt 0 ] && echo "Yes" || echo "No")"
        echo "   Has main: $([ $main_exists -gt 0 ] && echo "Yes" || echo "No")"
        echo ""
        
        cd ..
    fi
done