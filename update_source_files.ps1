# PowerShell script to update source files with new includes and namespaces
# Usage: .\update_source_files.ps1 -ProjectPath "C:\Users\dreec\Geant4Projects\EBeamSim"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectPath
)

Write-Host "Updating source files at: $ProjectPath" -ForegroundColor Green

# Function to update file content
function Update-SourceFile {
    param(
        [string]$FilePath,
        [hashtable]$Replacements
    )
    
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath -Raw
        
        foreach ($replacement in $Replacements.GetEnumerator()) {
            $content = $content -replace $replacement.Key, $replacement.Value
        }
        
        Set-Content -Path $FilePath -Value $content -Encoding UTF8
        Write-Host "Updated: $(Split-Path $FilePath -Leaf)" -ForegroundColor Gray
    } else {
        Write-Host "File not found: $FilePath" -ForegroundColor Yellow
    }
}

# Define replacements
$commonReplacements = @{
    '#include "AluconeTest.h"' = '#include "EBLConstants.hh"'
    'AluconeTest::' = 'EBL::'
}

# Update each source file
Write-Host "`nUpdating detector construction files..." -ForegroundColor Cyan
Update-SourceFile -FilePath "$ProjectPath\src\geometry\src\DetectorConstruction.cc" -Replacements @{
    '#include "AluconeTest.h"' = '#include "EBLConstants.hh"'
    'AluconeTest::DEFAULT_RESIST_THICKNESS' = 'EBL::Resist::DEFAULT_THICKNESS'
    'AluconeTest::DEFAULT_RESIST_DENSITY' = 'EBL::Resist::DEFAULT_DENSITY'
    'AluconeTest::ALUCONE_COMPOSITION' = 'EBL::Resist::ALUCONE_COMPOSITION'
    'AluconeTest::WORLD_SIZE' = 'EBL::Geometry::WORLD_SIZE'
}

Write-Host "`nUpdating primary generator files..." -ForegroundColor Cyan
Update-SourceFile -FilePath "$ProjectPath\src\beam\src\PrimaryGeneratorAction.cc" -Replacements @{
    '#include "AluconeTest.h"' = '#include "EBLConstants.hh"'
    'AluconeTest::DEFAULT_BEAM_ENERGY' = 'EBL::Beam::DEFAULT_ENERGY'
    'AluconeTest::DEFAULT_BEAM_SIZE' = 'EBL::Beam::DEFAULT_SPOT_SIZE'
    'AluconeTest::DEFAULT_BEAM_Z' = 'EBL::Beam::DEFAULT_POSITION_Z'
}

Write-Host "`nUpdating event action files..." -ForegroundColor Cyan
Update-SourceFile -FilePath "$ProjectPath\src\actions\src\EventAction.cc" -Replacements @{
    '#include "AluconeTest.h"' = '#include "EBLConstants.hh"'
    'AluconeTest::NUM_RADIAL_BINS' = 'EBL::PSF::NUM_RADIAL_BINS'
    'AluconeTest::USE_LOG_BINNING' = 'EBL::PSF::USE_LOG_BINNING'
    'AluconeTest::MIN_RADIUS' = 'EBL::PSF::MIN_RADIUS'
    'AluconeTest::MAX_RADIUS' = 'EBL::PSF::MAX_RADIUS'
}

Write-Host "`nUpdating run action files..." -ForegroundColor Cyan
Update-SourceFile -FilePath "$ProjectPath\src\actions\src\RunAction.cc" -Replacements @{
    '#include "AluconeTest.h"' = '#include "EBLConstants.hh"'
    'AluconeTest::NUM_RADIAL_BINS' = 'EBL::PSF::NUM_RADIAL_BINS'
    'AluconeTest::USE_LOG_BINNING' = 'EBL::PSF::USE_LOG_BINNING'
    'AluconeTest::MIN_RADIUS' = 'EBL::PSF::MIN_RADIUS'
    'AluconeTest::MAX_RADIUS' = 'EBL::PSF::MAX_RADIUS'
    'AluconeTest::OUTPUT_FILENAME' = 'EBL::Output::DEFAULT_FILENAME'
    'AluconeTest::BEAMER_OUTPUT_FILENAME' = 'EBL::Output::BEAMER_FILENAME'
    'AluconeTest::OUTPUT_DIRECTORY' = 'EBL::Output::DEFAULT_DIRECTORY'
}

Write-Host "`nCreating header update script..." -ForegroundColor Cyan

# Create a script to update include paths in all files
$updateIncludesScript = @'
# Update include paths in all source files
$files = Get-ChildItem -Path . -Include *.cc,*.hh -Recurse

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    
    # Update local includes to use module paths
    $content = $content -replace '#include "DetectorConstruction.hh"', '#include "geometry/DetectorConstruction.hh"'
    $content = $content -replace '#include "PhysicsList.hh"', '#include "physics/PhysicsList.hh"'
    $content = $content -replace '#include "PrimaryGeneratorAction.hh"', '#include "beam/PrimaryGeneratorAction.hh"'
    $content = $content -replace '#include "ActionInitialization.hh"', '#include "actions/ActionInitialization.hh"'
    
    Set-Content -Path $file.FullName -Value $content -Encoding UTF8
}
'@

Set-Content -Path "$ProjectPath\update_includes.ps1" -Value $updateIncludesScript

Write-Host "`nUpdate complete!" -ForegroundColor Green
Write-Host "`nManual steps required:" -ForegroundColor Yellow
Write-Host "1. Review the updated files for any compilation errors"
Write-Host "2. Update CMakeLists.txt files in each module to list source files"
Write-Host "3. Build the project to verify everything compiles"