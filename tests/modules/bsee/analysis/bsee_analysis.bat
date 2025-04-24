CALL conda activate energydata

REM Well Data Analysis
REM python -m energydata query_api_01_wells_api12.yml
REM python -m energydata query_api_03_wells_api12.yml
REM python -m energydata query_api_01_block_api12.yml

python -m energydata query_field_julia.yml
python -m energydata query_field_stmalo.yml

@REM Run individual field blocks
@REM python -m energydata query_field_stmalo.yml "{'meta': {'label': 'goa_stmalo_633'}, 'data': {'groups': [{'bottom_block': [633]}]}}"
@REM python -m energydata query_field_stmalo.yml "{'meta': {'label': 'goa_stmalo_634'}, 'data': {'groups': [{'bottom_block': [634]}]}}"
@REM python -m energydata query_field_stmalo.yml "{'meta': {'label': 'goa_stmalo_677'}, 'data': {'groups': [{'bottom_block': [677]}]}}"

@REM python -m energydata query_field_julia.yml "{'meta': {'label': 'goa_julia_584'}, 'data': {'groups': [{'bottom_block': [584]}]}}"
@REM python -m energydata query_field_julia.yml "{'meta': {'label': 'goa_julia_678'}, 'data': {'groups': [{'bottom_block': [678]}]}}"
@REM python -m energydata query_field_julia.yml "{'meta': {'label': 'goa_julia_758'}, 'data': {'groups': [{'bottom_block': [758]}]}}"
@REM python -m energydata query_field_julia.yml "{'meta': {'label': 'goa_julia_759'}, 'data': {'groups': [{'bottom_block': [759]}]}}"
