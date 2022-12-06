CALL ..\SET_Directories

REM ================
REM FE Model
SET program=ong_field_development
REM CALL ACTIVATE %program%

CD %git_root%
REM CALL PYTHON %program%.py

SET file_name=all_well_analysis.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"

CD %working_directory%
SET working_directory%=
