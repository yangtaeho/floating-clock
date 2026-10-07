$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed' }
    & .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed' }
    & .\.venv\Scripts\python.exe build_app.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
} finally {
    Pop-Location
}
