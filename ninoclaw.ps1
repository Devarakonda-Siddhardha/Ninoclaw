$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) {
        & $VenvPython "$PSScriptRoot\cli.py" @args
        exit $LASTEXITCODE
    }
}
if (Get-Command py -ErrorAction SilentlyContinue) {
    py "$PSScriptRoot\cli.py" @args
} else {
    python "$PSScriptRoot\cli.py" @args
}
