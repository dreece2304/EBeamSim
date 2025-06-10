# Define paths
$guiScript = "scripts/gui/ebl_gui.py"
$buildExe  = "out/build/x64-release/bin/ebl_sim.exe"

# Check that files exist
if (!(Test-Path $guiScript)) {
    Write-Error "GUI script not found: $guiScript"
    exit 1
}

if (!(Test-Path $buildExe)) {
    Write-Error "Executable not found: $buildExe"
    exit 1
}

# Read content of GUI script
$code = Get-Content $guiScript

# Regex pattern to find the hardcoded path assignment
$pattern = 'self\.executable_path\s*=\s*r?"[^"]+"'

# Replacement: make it relative using pathlib
$replacement = 'self.executable_path = str(Path(__file__).resolve().parents[3] / "out" / "build" / "x64-release" / "bin" / "ebl_sim.exe")'

# Apply replacement
$updatedCode = $code -replace $pattern, $replacement

# Write back to file (with backup)
Copy-Item $guiScript "$guiScript.bak" -Force
Set-Content $guiScript -Value $updatedCode -Encoding UTF8

Write-Output "Updated path in $guiScript and saved backup as $guiScript.bak"
