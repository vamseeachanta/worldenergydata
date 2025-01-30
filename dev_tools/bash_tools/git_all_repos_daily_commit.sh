# shell script to perform daily git operations
repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

repo_name=$(basename $(git rev-parse --show-toplevel))
bash_tools_home="dev_tools/bash_tools"

# source common utilities
source ${bash_tools_home}/common.sh

# Directory containing GitHub repositories
current_dir=$(pwd)
github_dir=$(dirname "$current_dir")
assetutilities_dir="${github_dir}/assetutilities"

# rel path top bash_tools dir, daily_commit_script
bash_tools_home="dev_tools/bash_tools"
daily_commit_script_rel_path="${bash_tools_home}/git_daily_commit.sh"
clean_stale_branches_rel_path="${bash_tools_home}/git_clean_stale_local_branches.sh"
select_year_month_branch_rel_path="${bash_tools_home}/git_select_year_month_branch.sh"

cd ${github_dir}
log_message "normal" "Starting repository check-in routine process in $(pwd)..."

# Iterate through all directories in the GitHub folder
for dir in "$github_dir"/*/ ; do
    if [ -d "$dir" ]; then

        log_message "normal" "Processing repo: $(basename "$dir")"
        cd "$dir"

        # Check if there are any changes
        if [ -n "$(git status --porcelain)" ]; then
            log_message "yellow" "Changes detected in repo: $(basename "$dir")"

            # commit changes
            daily_commit_script="${dir}/${daily_commit_script_rel_path}"
            log_message "green" "Daily routine ... START"
            if [ ! -f "$daily_commit_script" ]; then
                daily_commit_script="${assetutilities_dir}/${daily_commit_script_rel_path}"
            fi
            bash "$daily_commit_script"
            log_message "green" "Daily routine in $(basename "$dir") ... FINISH"

            # loop through stale branches and create PR and delete branch
            clean_stale_branches_script="${dir}/${clean_stale_branches_rel_path}"
            if [ ! -f "$clean_stale_branches_script" ]; then
                clean_stale_branches_script="${assetutilities_dir}/${clean_stale_branches_rel_path}"
            fi
            bash "$clean_stale_branches_script"
            log_message "green" "Clean stale branches completed in $(basename "$dir") ..."

        else
            log_message "green" "No changes detected in $(basename "$dir") ..."
        fi

        # select_year_month_branch
        select_year_month_branch_script="${dir}/${select_year_month_branch_rel_path}"
        if [ ! -f "$select_year_month_branch_script" ]; then
            select_year_month_branch_script="${assetutilities_dir}/${select_year_month_branch_rel_path}"
        fi
        bash "$select_year_month_branch_script"
        log_message "green" "Select year_month branch completed in $(basename "$dir") ..."

    fi
done

# Return to original directory
cd "$github_dir"
log_message "green" "Completed daily_routine for all repositories"
