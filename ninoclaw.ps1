$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython "$PSScriptRoot\cli.py" @args
} else {
    py "$PSScriptRoot\cli.py" @args
}
