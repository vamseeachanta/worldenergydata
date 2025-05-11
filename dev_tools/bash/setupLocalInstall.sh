# use this script to install the package locally (developer/self-use only)

# locate repo root
repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

repo_name=$(basename $(git rev-parse --show-toplevel))
today=$(date '+%Y%m%d')
bash_tools_home="dev_tools/bash_tools"

# source common utilities
source ${bash_tools_home}/common.sh

log_message "normal" "Setting up local install for ${repo_name} at ${repo_root}"
python -m pip install -e .

# return back to where you started.
cd - 