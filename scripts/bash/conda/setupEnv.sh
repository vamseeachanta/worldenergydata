# setup the env for the project
# uses gitbash 

# assumes/needs 
# 1. gitbash
# 2. python 
# 3. miniconda 

conda_home="/c/Users/sivak/miniconda3/"
#conda_home="/c/Users/sivakumarp/AppData/Local/anaconda3"
#conda_home="/c/ProgramData/miniconda3"

# shell script to perform daily git operations
repo_root=$(git rev-parse --show-toplevel)
# get to repo root
cd "$repo_root"

repo_name=$(basename $(git rev-parse --show-toplevel))
bash_tools_home="dev_tools/bash_tools"
today=$(date '+%Y%m%d')

# source common utilities
source ${bash_tools_home}/common.sh

# Get the absolute path to this script
# script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# echo "script_dir = $script_dir"
# cd "$script_dir/.."
# echo "project home = $(pwd)"
# return 1 

env_file="${repo_root}/dev_tools/environment.yml"

# locate the env name for this env 
env_name=$(grep 'name:' "$env_file" | awk '{print $2}')

# conda init 
source $conda_home"/etc/profile.d/conda.sh"
conda init 

# List conda environments and check if env_name exists
if conda env list | grep -q "$env_name"; then
    echo "Siva - Environment $env_name found. Updating environment."
    conda env update --file "$env_file" --prune 
else
    echo "Siva - Environment $env_name not found. Creating environment."
    echo "Siva - Creating environment $env_name."
    conda env create --file "$env_file"
fi

conda activate $env_name

# return back to where you started. 
cd - 