$ErrorActionPreference = 'Stop'
$notesRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$notesPython = Join-Path $notesRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $notesPython)) {
    throw '请先按 README.md 创建虚拟环境并安装依赖。'
}
& $notesPython (Join-Path $PSScriptRoot 'open.py') @args
