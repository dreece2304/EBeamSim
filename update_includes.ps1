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
