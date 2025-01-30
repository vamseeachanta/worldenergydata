# shell script to perform daily git operations
repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

repo_name=$(basename $(git rev-parse --show-toplevel))
bash_tools_home="dev_tools/bash_tools"

# source common utilities
# source ${bash_tools_home}/common.sh

repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

year_month=$(date '+%Y%m')
year_month_branch_name=$year_month

# Check current branch matches year_month_branch_name
current_branch=$(git branch --show-current)
if [ "$current_branch" == "$year_month_branch_name" ]; then
  source ${bash_tools_home}/git_daily_commit.sh
else
  git fetch
  # if branch exists at origin, checkout 
  if git ls-remote --heads origin $year_month_branch_name | grep -q $year_month_branch_name; then
    echo "Branch $year_month_branch_name exists"
    git checkout -b $year_month_branch_name origin/$year_month_branch_name
    log_message "green" "Repo : ${repo_name} : Checked out branch $year_month_branch_name exists at origin"
  # create new year_month_branch_name, checkout and push to origin
  else
    echo "Creating new branch $year_month_branch_name"
    git checkout -b $year_month_branch_name
    git push -u origin $year_month_branch_name
    log_message "green" "Repo : ${repo_name} : Created new branch $year_month_branch_name and pushed to origin"
  fi
fi

exit 0
