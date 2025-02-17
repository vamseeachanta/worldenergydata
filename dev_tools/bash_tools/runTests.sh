#! /bin/bash 

# have to hard code this into each script
# assumes git was used to clone the repo
project_root=$(git rev-parse --show-toplevel)
repo_name=$(basename ${project_root})
cd "$project_root"

# load common.sh 
#source ./tools/common.sh
gitbash_tools_home="${project_root}/dev_tools/bash_tools"
source ${gitbash_tools_home}/common.sh

test_home=${project_root}"/tests"
template_module_home=${test_home}"/modules"

log_message "green" "Running tests for module = ${repo_name}, project_root = ${project_root}"

# Initialize counter
counter=0

# this is succeeding. 
config_file="${template_module_home}/file_edit/file_edit_split.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

log_message "normal" "----------------------------------------------"
log_message "normal" "press any key to exit"
pause_for_user

exit 1

# invoking custom test client
config_file="${template_module_home}/reportgen/reportgen-sympy_function_1_cfg.yml"
python_script="${template_module_home}/reportgen/test-clients/sympy_function_1.py"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python ${python_script} ${config_file}"
pause_for_user
python ${python_script} ${config_file}

# basic reportgen works
config_file="${template_module_home}/reportgen/reportgen-cfg.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

# now to setup reportgen
config_file="${template_module_home}/reportgen/reportgen-cfg-md.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

# now to setup reportgen
config_file="${template_module_home}/reportgen/reportgen-cfg-docx.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

# now to setup reportgen
config_file="${template_module_home}/reportgen/reportgen-cfg-20in-md.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

# now to setup reportgen
config_file="${template_module_home}/reportgen/reportgen-cfg-20in-docx.yml"
((counter++))
log_message "normal" "----------------------------------------------"
log_message "normal" "Test #${counter} python -m ${repo_name} ${config_file}"
pause_for_user
python -m ${repo_name} ${config_file}

log_message "normal" "----------------------------------------------"
log_message "normal" "press any key to exit"
pause_for_user

# return back to where you started.
cd - 

exit 1 


python src/assetutilities/tests/test_data/test_all_yml.py 
