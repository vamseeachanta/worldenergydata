CALL ..\SET_Directories

REM ================
REM FE Model
SET program=ong_field_development
REM CALL ACTIVATE %program%

CD %git_root%
REM CALL PYTHON %program%.py

SET file_name=XOM_Julia.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=RDS_Stones.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=PBR_Cascade_Chinook.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"


SET file_name=CVX_Anchor.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=TOT_North_Platte.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"

SET file_name=Shenandoah.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Kaskida.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Tiber.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Tigris.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Jack.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=StMalo.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Cascade.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Chinook.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Buckskin.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Guadalupe.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Moccasin.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Gila.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Coronado.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=BigFoot.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"
SET file_name=Gibson.yml
CALL PYTHON %program%.py "%working_directory%\%file_name%"


CD %working_directory%
SET working_directory%=
