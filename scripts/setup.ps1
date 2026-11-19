param([switch]$OnlyWeb)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Push-Location $taskRoot
try {
    Push-Location web
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias web.' }
    } finally { Pop-Location }
    if (-not $OnlyWeb) {
        $taskPython = Join-Path $taskRoot '.tools\python312\python.exe'
        if (-not (Test-Path -LiteralPath $taskPython)) {
            throw 'Python 3.12 local ausente. Execute: py install --target=.\.tools\python312 3.12 ; ou crie os ambientes com sua instalacao Python 3.12 conforme README.'
        }
        foreach ($taskModule in @('water', 'cnn')) {
            $taskVenv = Join-Path $taskRoot "modules\$taskModule\.venv"
            if (-not (Test-Path -LiteralPath (Join-Path $taskVenv 'Scripts\python.exe'))) {
                & $taskPython -m venv $taskVenv
                if ($LASTEXITCODE -ne 0) { throw "Falha ao criar ambiente $taskModule." }
            }
            & (Join-Path $taskVenv 'Scripts\python.exe') -m pip install -r (Join-Path $taskRoot "modules\$taskModule\requirements.txt")
            if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias $taskModule." }
        }
    }
    Write-Host 'Dependencias prontas. Leia README.md para iniciar MongoDB e o portal.'
} finally { Pop-Location }
