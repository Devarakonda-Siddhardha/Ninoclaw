$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
python "$PSScriptRoot\cli.py" @args
