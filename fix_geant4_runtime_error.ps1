# PowerShell script to diagnose and fix Geant4 runtime errors
param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectPath = "C:\Users\dreec\Geant4Projects\EBeamSim",
    [string]$Geant4Path = "C:\Users\dreec\Geant4Projects\program_files"
)

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Geant4 Runtime Error Diagnostic" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check 1: Verify Geant4 installation
Write-Host "`n1. Checking Geant4 installation..." -ForegroundColor Yellow
if (Test-Path $Geant4Path) {
    Write-Host "   ✓ Geant4 found at: $Geant4Path" -ForegroundColor Green
    
    # Check for data directories
    $dataPath = "$Geant4Path\share\Geant4\data"
    if (Test-Path $dataPath) {
        Write-Host "   ✓ Data directory found" -ForegroundColor Green
        Get-ChildItem $dataPath | ForEach-Object {
            Write-Host "     - $($_.Name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ✗ Data directory not found!" -ForegroundColor Red
    }
} else {
    Write-Host "   ✗ Geant4 not found at: $Geant4Path" -ForegroundColor Red
}

# Check 2: Environment variables
Write-Host "`n2. Checking environment variables..." -ForegroundColor Yellow
$g4Vars = @(
    "G4ABLADATA",
    "G4LEDATA",
    "G4LEVELGAMMADATA",
    "G4NEUTRONHPDATA",
    "G4NEUTRONXSDATA",
    "G4PIIDATA",
    "G4RADIOACTIVEDATA",
    "G4REALSURFACEDATA",
    "G4SAIDXSDATA",
    "G4PARTICLEXSDATA",
    "G4ENSDFSTATEDATA"
)

$missingVars = @()
foreach ($var in $g4Vars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        Write-Host "   ✓ $var = $value" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $var is not set" -ForegroundColor Red
        $missingVars += $var
    }
}

# Check 3: Set missing environment variables
if ($missingVars.Count -gt 0) {
    Write-Host "`n3. Setting missing environment variables..." -ForegroundColor Yellow
    
    # Create a batch file to set environment variables
    $batchContent = @"
@echo off
REM Geant4 environment setup
set G4PATH=$Geant4Path
set PATH=%G4PATH%\bin;%PATH%

REM Geant4 data directories
set G4ABLADATA=%G4PATH%\share\Geant4\data\G4ABLA3.3
set G4LEDATA=%G4PATH%\share\Geant4\data\G4EMLOW8.5
set G4LEVELGAMMADATA=%G4PATH%\share\Geant4\data\PhotonEvaporation5.7
set G4NEUTRONHPDATA=%G4PATH%\share\Geant4\data\G4NDL4.7
set G4NEUTRONXSDATA=%G4PATH%\share\Geant4\data\G4NEUTRONXS1.4
set G4PIIDATA=%G4PATH%\share\Geant4\data\G4PII1.3
set G4RADIOACTIVEDATA=%G4PATH%\share\Geant4\data\RadioactiveDecay5.6
set G4REALSURFACEDATA=%G4PATH%\share\Geant4\data\RealSurface2.2
set G4SAIDXSDATA=%G4PATH%\share\Geant4\data\G4SAIDDATA2.0
set G4PARTICLEXSDATA=%G4PATH%\share\Geant4\data\G4PARTICLEXS4.0
set G4ENSDFSTATEDATA=%G4PATH%\share\Geant4\data\G4ENSDFSTATE2.3

echo Environment variables set!
echo.
echo Starting EBL simulation...
cd /d "$ProjectPath\build\bin\Release"
ebl_sim.exe
pause
"@
    
    $batchFile = "$ProjectPath\run_with_env.bat"
    Set-Content -Path $batchFile -Value $batchContent
    Write-Host "   ✓ Created run_with_env.bat" -ForegroundColor Green
    Write-Host "   Use this batch file to run your simulation with proper environment" -ForegroundColor Yellow
}

# Check 4: Visual Studio Debug Configuration
Write-Host "`n4. Creating Visual Studio debug configuration..." -ForegroundColor Yellow

# Create launch.vs.json for Visual Studio debugging
$launchConfig = @"
{
  "version": "0.2.1",
  "defaults": {},
  "configurations": [
    {
      "type": "default",
      "project": "CMakeLists.txt",
      "projectTarget": "ebl_sim.exe",
      "name": "ebl_sim.exe (with Geant4 env)",
      "env": {
        "PATH": "$Geant4Path\\bin;${env.PATH}",
        "G4ABLADATA": "$Geant4Path\\share\\Geant4\\data\\G4ABLA3.3",
        "G4LEDATA": "$Geant4Path\\share\\Geant4\\data\\G4EMLOW8.5",
        "G4LEVELGAMMADATA": "$Geant4Path\\share\\Geant4\\data\\PhotonEvaporation5.7",
        "G4NEUTRONHPDATA": "$Geant4Path\\share\\Geant4\\data\\G4NDL4.7",
        "G4NEUTRONXSDATA": "$Geant4Path\\share\\Geant4\\data\\G4NEUTRONXS1.4",
        "G4PIIDATA": "$Geant4Path\\share\\Geant4\\data\\G4PII1.3",
        "G4RADIOACTIVEDATA": "$Geant4Path\\share\\Geant4\\data\\RadioactiveDecay5.6",
        "G4REALSURFACEDATA": "$Geant4Path\\share\\Geant4\\data\\RealSurface2.2",
        "G4SAIDXSDATA": "$Geant4Path\\share\\Geant4\\data\\G4SAIDDATA2.0",
        "G4PARTICLEXSDATA": "$Geant4Path\\share\\Geant4\\data\\G4PARTICLEXS4.0",
        "G4ENSDFSTATEDATA": "$Geant4Path\\share\\Geant4\\data\\G4ENSDFSTATE2.3"
      }
    }
  ]
}
"@

# Create .vs directory if it doesn't exist
$vsDir = "$ProjectPath\.vs"
if (!(Test-Path $vsDir)) {
    New-Item -ItemType Directory -Path $vsDir -Force | Out-Null
}

Set-Content -Path "$vsDir\launch.vs.json" -Value $launchConfig
Write-Host "   ✓ Created launch.vs.json for Visual Studio debugging" -ForegroundColor Green

# Check 5: Test macro
Write-Host "`n5. Creating test macro..." -ForegroundColor Yellow
$testMacro = @"
# Simple test macro
/run/initialize
/run/beamOn 1
"@

Set-Content -Path "$ProjectPath\build\bin\Release\test_simple.mac" -Value $testMacro
Write-Host "   ✓ Created test_simple.mac" -ForegroundColor Green

# Summary
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Summary and Next Steps" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if ($missingVars.Count -gt 0) {
    Write-Host "`nEnvironment variables were missing. To run:" -ForegroundColor Yellow
    Write-Host "1. Use the batch file:" -ForegroundColor White
    Write-Host "   $ProjectPath\run_with_env.bat" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Or set them permanently in System Properties:" -ForegroundColor White
    Write-Host "   - Right-click 'This PC' -> Properties" -ForegroundColor Gray
    Write-Host "   - Advanced system settings -> Environment Variables" -ForegroundColor Gray
    Write-Host "   - Add each G4*DATA variable pointing to the correct path" -ForegroundColor Gray
} else {
    Write-Host "`nEnvironment looks good!" -ForegroundColor Green
}

Write-Host "`nTo debug in Visual Studio:" -ForegroundColor Yellow
Write-Host "1. Reload the project (close and reopen)" -ForegroundColor White
Write-Host "2. Select 'ebl_sim.exe (with Geant4 env)' from the startup dropdown" -ForegroundColor White
Write-Host "3. Press F5 to debug" -ForegroundColor White

Write-Host "`nIf you still get errors, check:" -ForegroundColor Yellow
Write-Host "- Geant4 version compatibility (built with same compiler?)" -ForegroundColor White
Write-Host "- Debug vs Release mode consistency" -ForegroundColor White
Write-Host "- All DLLs are accessible in PATH" -ForegroundColor White

Write-Host "`nScript completed!" -ForegroundColor Green