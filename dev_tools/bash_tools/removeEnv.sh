# setup the env for the project
# uses gitbash 

# assumes/needs 
# 1. gitbash
# 2. python 
# 3. miniconda 

# hardcoded. fix this soon. 
proj_home="/c/Users/sivak/Desktop/siva/personal/2024-odd-projects/assetutilities"
env_file_path="${proj_home}/dev_tools"
env_file=${env_file_path}"/environment.yml"

# locate the env name for this env 
env_name=$(grep 'name:' "$env_file" | awk '{print $2}')

# conda remove and deactivate env
if conda info --envs | grep -q "$env_name"; then
    conda deactivate
    conda env remove -n "$env_name"
    conda clean --all
    echo "Siva - Environment '$env_name' has been removed."
else
    echo "Siva - Environment '$env_name' does not exist."
fi