# shell script to perform daily git operations
repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

repo_name=$(basename $(git rev-parse --show-toplevel))
bash_tools_home="dev_tools/bash_tools"

# source common utilities
source ${bash_tools_home}/common.sh
# source ${bash_tools_home}/git_select_year_month_branch.sh

daily_commit_message=$(date '+%Y%m%d')

cat << COM
Starting daily git routine. key details 
  - Repository name: $repo_name
  - Repository root: $repo_root
  - Daily Commit message: $daily_commit_message
Executing git operations now 
COM

if [ -n "$(git status --porcelain)" ]; then
    log_message "yellow" "Changes detected in repo: $(basename "$dir")"

    # get to repo root
    cd "$repo_root"

    # perform git operations
    git pull
    git add --all
    git commit -m "$daily_commit_message"
    git push

fi

log_message "green" "Repo : ${repo_name} : Daily git operations completed"
