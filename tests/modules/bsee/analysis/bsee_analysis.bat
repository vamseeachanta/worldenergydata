CALL conda activate energydata

REM Well Data Analysis
REM python -m energydata query_api_01_wells_api12.yml
REM python -m energydata query_api_03_wells_api12.yml
REM python -m energydata query_api_01_block_api12.yml
python -m energydata query_api_01_block_julia.yml
python -m energydata query_api_01_block_stmalo.yml