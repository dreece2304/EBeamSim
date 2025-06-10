@echo off
REM Geant4 environment setup for EBeamSim
echo Setting up Geant4 environment...

set G4PATH=C:\Users\dreec\Geant4Projects\program_files
set PATH=%G4PATH%\bin;%PATH%

REM Geant4 data directories - Using the actual versions found
set G4ABLADATA=%G4PATH%\share\Geant4\data\G4ABLA3.3
set G4CHANNELINGDATA=%G4PATH%\share\Geant4\data\G4CHANNELING1.0
set G4LEDATA=%G4PATH%\share\Geant4\data\G4EMLOW8.6.1
set G4ENSDFSTATEDATA=%G4PATH%\share\Geant4\data\G4ENSDFSTATE3.0
set G4INCLDATA=%G4PATH%\share\Geant4\data\G4INCL1.2
set G4NEUTRONHPDATA=%G4PATH%\share\Geant4\data\G4NDL4.7.1
set G4PARTICLEXSDATA=%G4PATH%\share\Geant4\data\G4PARTICLEXS4.1
set G4PIIDATA=%G4PATH%\share\Geant4\data\G4PII1.3
set G4SAIDXSDATA=%G4PATH%\share\Geant4\data\G4SAIDDATA2.0
set G4LEVELGAMMADATA=%G4PATH%\share\Geant4\data\PhotonEvaporation6.1
set G4RADIOACTIVEDATA=%G4PATH%\share\Geant4\data\RadioactiveDecay6.1.2
set G4REALSURFACEDATA=%G4PATH%\share\Geant4\data\RealSurface2.2

echo.
echo Environment variables set successfully
echo.

REM Change to the correct directory based on build type
cd /d "C:\Users\dreec\Geant4Projects\EBeamSim"

REM Check which directory exists
if exist "out\build\x64-debug\bin\ebl_sim.exe" (
    echo Found Visual Studio x64-Debug build
    cd out\build\x64-debug\bin
    echo Starting EBL simulation...
    echo.
    ebl_sim.exe
    goto end
)

if exist "out\build\x64-debug\ebl_sim.exe" (
    echo Found Visual Studio x64-Debug build in root
    cd out\build\x64-debug
    echo Starting EBL simulation...
    echo.
    ebl_sim.exe
    goto end
)

if exist "out\build\x64-release\bin\ebl_sim.exe" (
    echo Found Visual Studio x64-Release build
    cd out\build\x64-release\bin
    echo Starting EBL simulation...
    echo.
    ebl_sim.exe
    goto end
)

if exist "build\bin\Debug\ebl_sim.exe" (
    echo Found Debug build
    cd build\bin\Debug
    echo Starting EBL simulation...
    echo.
    ebl_sim.exe
    goto end
)

if exist "build\bin\Release\ebl_sim.exe" (
    echo Found Release build
    cd build\bin\Release
    echo Starting EBL simulation...
    echo.
    ebl_sim.exe
    goto end
)

echo ERROR: Could not find ebl_sim.exe!
echo.
echo Looking in current directory...
dir /s /b ebl_sim.exe 2>nul
echo.
echo Please build the project first in Visual Studio.

:end
pause