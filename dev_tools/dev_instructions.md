### Introduction

To setup environment for the development of the library

### Summary

Follow the steps given in this document.

For more information on library development, see latest in [py_project library](https://github.com/vamseeachanta/py_package/blob/master/README.md)

### Steps

- Clone repository
- Change to relevant branch
- Pull latest code in relevant branch
- Go to <repository>/dev_tools directory latest environment.yml
  - If no virtual environment, create new using below:
    <code>
    conda env create -f environment.yml
    </code>
  - If virtual environment already exists, create new using below:
    <code>
    conda env update -f environment.yml
    </code>

- Activate the environment
    <code>
    conda activate <virtualenviornment>
    </code>
- Using the pyproject.toml file, self-install the library into the environment for development
    <code>
    cd github\<repository> # Change directory to energy repository
    python -m pip install -e .
    </code>

- use a test file to verify the process
