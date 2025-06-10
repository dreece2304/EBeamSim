# Quick fix for parentheses mismatch in DetectorConstruction.cc
$file = "C:\Users\dreec\Geant4Projects\EBeamSim\src\geometry\src\DetectorConstruction.cc"

Write-Host "Checking parentheses balance..." -ForegroundColor Yellow

# Read file and count parentheses line by line
$lines = Get-Content $file
$balance = 0
$lineNum = 0

foreach ($line in $lines) {
    $lineNum++
    $open = ([regex]::Matches($line, '\(')).Count
    $close = ([regex]::Matches($line, '\)')).Count
    $balance += ($open - $close)
    
    # Show lines with imbalance
    if ($open -ne $close) {
        if (($open - $close) -gt 1 -or ($open - $close) -lt -1) {
            Write-Host "Line $lineNum has imbalance: $open open, $close close" -ForegroundColor Red
            Write-Host "  $line" -ForegroundColor Gray
        }
    }
}

Write-Host "`nTotal: $balance extra opening parentheses" -ForegroundColor $(if ($balance -eq 0) {"Green"} else {"Red"})

# Try a simple fix - add )) at the end of the file before the last }
if ($balance -eq 2) {
    Write-Host "`nAdding 2 closing parentheses before final brace..." -ForegroundColor Yellow
    $content = Get-Content $file -Raw
    
    # Find the last } in the file
    $lastBrace = $content.LastIndexOf('}')
    if ($lastBrace -gt 0) {
        $content = $content.Insert($lastBrace, "))`n")
        Set-Content $file $content -NoNewline
        Write-Host "✓ Added )) before the final }" -ForegroundColor Green
    }
}

Write-Host "`nDone! Try rebuilding now." -ForegroundColor Green