# Introduction

Energy Data Library to get data from public sources. The energy includes the following:
- Oil and Gas facilities
- Wind
- Other Source (TBA)

## Summary



## Usage


**Using toml file, bumpver and twine**

| Step |  Description | Commands/Detailed Description | Reference |
|---|---|---|---|
| 1 | Create python project with directory structure | Follow pep8 guidelines | [https://www.freecodecamp.org/news/build-your-first-python-package/](https://www.freecodecamp.org/news/build-your-first-python-package/) |
| 2 | Package compliance | Ensure all directories are package modules using __init__.py  | [https://www.freecodecamp.org/news/build-your-first-python-package/](https://www.freecodecamp.org/news/build-your-first-python-package/) |
| 3 | Add .toml file and setup.py to build wheels | pip install bumpver <br> bumpver update --patch  <br> pip install build <br> python -m build | https://realpython.com/pypi-publish-python-package/ |
| 4 | Create account on pypi and upload using twine package | These commands will push the .whl and .tar.gz file into the pypi repository <br> conda install twine <br> twine upload dist/*  | https://realpython.com/pypi-publish-python-package/ |

To see instructions using setup.py & twine, without Version Bump, see [using setup.py](docs\using_setuppy.md)

## CI

More CI/CD streamlining for python packages:
- use cookiecutter to generate a package template
- set up travis CI for auto deployment of package to pypi

 #TODO 
- Convert library to a cookiecutter template. Helps parametrize the library name.

https://github.com/audreyfeldroy/cookiecutter-pypackage
https://cookiecutter-pypackage.readthedocs.io/en/latest/tutorial.html
https://pypi.org/project/cookiecutter/

https://github.com/boromir674/cookiecutter-python-package
https://github.com/boromir674/cookiecutter-python-package/tox.ini

https://youtu.be/ugGu8fHWFog (A data science project example folder)

### Github

Helps cover testing, test coverage, etc.
https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python
https://hynek.me/articles/python-github-actions/

### Travis CI, No Free Support?

https://jacobtomlinson.dev/posts/2021/testing-and-continuous-integration-for-python-packages-with-github-actions/

https://github.com/ksator/continuous-integration-with-python

https://medium.com/swlh/automate-python-testing-with-github-actions-7926b5d8a865


## Testing a Package Locally 

**Using .toml file (Working)**

A package can be imported locally from another code and thoroughly tested as well if required. Editable install is the best way to achieve this.
The steps to do so are:
- Change to the current working directory where the pyproject.toml file is located
- Execute the following command to install the package locally
	- python -m pip install -e .
- This installation uses the files in the current working directory

**Using conda-build (Did not work)**

Building A Package Locally
- Add following package to the base environment
    -Install conda-buiild
    -Conda install conda-build
- Utilize the below to build the package in current path. A specific path can also be specified.
    - Conda develop . 
    - https://docs.conda.io/projects/conda-build/en/latest/user-guide/tutorials/build-pkgs.html


## Writing Tests
- Write tests. Preferably utilize pytest. 
- Example test and file structure
	- https://github.com/jumptrading/luddite
	- Utilized test_package.py for all tests 
	- pytest.ini file for pytest configurations
	- Utilize github test workflows
	- https://github.com/jumptrading/luddite/blob/master/.github/workflows/tests.yml
- https://tox.wiki/en/latest/

### References

[https://www.freecodecamp.org/news/build-your-first-python-package/](https://www.freecodecamp.org/news/build-your-first-python-package/)

[https://python-packaging-tutorial.readthedocs.io/en/latest/setup_py.html](https://python-packaging-tutorial.readthedocs.io/en/latest/setup_py.html)

[https://packaging.python.org/](https://packaging.python.org/)

Guidelines to contribute to libraries:
[https://pandas.pydata.org/docs/development/contributing.html#contributing](https://pandas.pydata.org/docs/development/contributing.html#contributing)

https://realpython.com/pypi-publish-python-package/
