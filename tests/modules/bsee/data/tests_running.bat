@echo off
CALL activate worldenergydata

python -m worldenergydata data_refresh.yml
python -m worldenergydata query_api_01_well_scrapy.yml
python -m worldenergydata query_api_04_wells_scrapy.yml
python -m worldenergydata query_api_production_from_zip_01_well.yml
python -m worldenergydata query_api_production_from_zip_04_wells.yml
