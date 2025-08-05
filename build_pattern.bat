@echo off
echo Building EBeamSim with Pattern Exposure support...
cd /d C:\Users\bergsman_lab_user\CLionProjects\EBeamSim
C:\Users\bergsman_lab_user\AppData\Local\Programs\CLion\bin\cmake\win\x64\bin\cmake.exe --build cmake-build-release --target ebl_sim -j 10
echo Build complete.
pause