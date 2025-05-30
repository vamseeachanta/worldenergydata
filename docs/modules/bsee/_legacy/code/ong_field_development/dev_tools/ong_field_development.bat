REM https://stackoverflow.com/questions/8797983/can-a-windows-batch-file-determine-its-own-file-name
SET environment_label=%~n0

call conda env create -f %environment_label%.yaml
call activate %environment_label%
CALL pip install python-dateutil pytz --force-reinstall --upgrade
