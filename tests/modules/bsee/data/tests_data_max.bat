@echo off
CALL activate worldenergydata
python -m worldenergydata .\query_blk_julia_API.yml
