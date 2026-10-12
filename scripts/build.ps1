param(
    [string]$Python = "python"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $repoRoot 'build'
$distDir = Join-Path $repoRoot 'dist'

# Resolve a relative interpreter before changing the working directory.
if (Test-Path -LiteralPath $Python -PathType Leaf) {
    $Python = (Resolve-Path -LiteralPath $Python).Path
}

Push-Location -LiteralPath $repoRoot
try {
    & $Python -m unittest discover -s tests -p test_engine.py
    if ($LASTEXITCODE -ne 0) { throw 'Rule tests failed.' }

    & $Python scripts/verify_ui.py
    if ($LASTEXITCODE -ne 0) { throw 'UI checks failed.' }

    New-Item -ItemType Directory -Force -Path $buildDir, $distDir | Out-Null
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name TaixuAscension `
        --icon (Join-Path $repoRoot 'app.ico') `
        --add-data "$repoRoot/content.json;." `
        --distpath $distDir `
        --workpath (Join-Path $buildDir 'cache') `
        --specpath $buildDir `
        (Join-Path $repoRoot 'main.py')
    if ($LASTEXITCODE -ne 0) { throw 'Native Windows build failed.' }

    & $Python scripts/package_windows.py
    if ($LASTEXITCODE -ne 0) { throw 'Distribution packaging failed.' }
    Write-Output "Ready: $distDir/TaixuAscension-Windows.zip"
}
finally {
    Pop-Location
}
