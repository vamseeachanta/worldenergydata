### Introduction

To setup environment for the development of the library

### Summary

Follow the steps given in this document.

For more information on library development, see latest in [py_project library](https://github.com/vamseeachanta/py_package/blob/master/README.md)

### Steps

- Pull latest repository in relevant branch
- Install the latest environment.yml

- Using the pyproject.toml file, self-install the library into the environment for development
    <code>
    cd github\energydata # Change directory to energy repository
    python -m pip install -e .
    </code>

- use a test file to verify the process
