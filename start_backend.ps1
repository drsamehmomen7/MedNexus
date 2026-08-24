$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$workspaceRoot = Split-Path -Parent $repositoryRoot
$pythonExe = Join-Path $workspaceRoot "Runtime\Python310\python.exe"
$sitePackages = Join-Path $repositoryRoot ".venv\Lib\site-packages"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "MedNexus Python runtime was not found at: $pythonExe"
}

if (-not (Test-Path -LiteralPath $sitePackages -PathType Container)) {
    throw "MedNexus retained site-packages were not found at: $sitePackages"
}

$pythonVersion = & $pythonExe -c "import platform; print(platform.python_version())"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to launch the MedNexus Python runtime at: $pythonExe"
}

$pythonVersion = $pythonVersion.Trim()
if ($pythonVersion -ne "3.10.11") {
    throw "MedNexus requires Python 3.10.11, but $pythonExe reported $pythonVersion."
}

$bootstrap = @"
import sys
sys.path[:0] = [r'$sitePackages', r'$repositoryRoot']
import uvicorn
uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8001)
"@

Write-Host "Starting MedNexus Main"
Write-Host "Python: $pythonExe ($pythonVersion)"
Write-Host "Site-packages: $sitePackages"
Write-Host "Application: http://127.0.0.1:8001"

$previousUserSite = $env:PYTHONNOUSERSITE
$env:PYTHONNOUSERSITE = "1"
Push-Location $repositoryRoot
try {
    & $pythonExe -c $bootstrap
    if ($LASTEXITCODE -ne 0) {
        throw "MedNexus backend exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
    if ($null -eq $previousUserSite) {
        Remove-Item Env:PYTHONNOUSERSITE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONNOUSERSITE = $previousUserSite
    }
}
