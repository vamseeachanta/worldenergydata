CALL ..\SET_Directories

REM ================
REM FE Model
SET program=front_end
REM CALL ACTIVATE %program%

CD %git_root%
REM CALL PYTHON %program%.py

SET file_name=XOM_Julia_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=RDS_Stones_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=PBR_Cascade_Chinook_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"

SET file_name=CVX_Anchor_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=TOT_North_Platte_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"

SET file_name=Shenandoah_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Kaskida_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Tiber_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Tigris_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Jack_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=StMalo_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Cascade_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Chinook_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Buckskin_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Guadalupe_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Moccasin_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Gila_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Coronado_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=BigFoot_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Gibson_Rep.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"

CD %working_directory%
SET working_directory%=
