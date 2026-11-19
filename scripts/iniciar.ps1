param([switch]$Demo, [switch]$SemCNN)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskClassifierProcess = $null
$taskOriginalMode = $env:DEMO_MODE
$taskOriginalMongo = $env:MONGO_URI
$taskOriginalClassifier = $env:CLASSIFIER_URL
try {
    $env:DEMO_MODE = if ($Demo) { 'true' } else { 'false' }
    if (-not $env:MONGO_URI) { $env:MONGO_URI = 'mongodb://127.0.0.1:27017/territorio_vivo' }
    if (-not $env:CLASSIFIER_URL) { $env:CLASSIFIER_URL = 'http://127.0.0.1:8001' }
    if (-not $SemCNN) {
        $taskPython = Join-Path $taskRoot 'modules\cnn\.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $taskPython) {
            New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot '.runtime') | Out-Null
            $taskClassifierProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8001') -WorkingDirectory (Join-Path $taskRoot 'modules\cnn') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRoot '.runtime\cnn-output.log') -RedirectStandardError (Join-Path $taskRoot '.runtime\cnn-error.log')
        } else { Write-Warning 'Ambiente CNN ausente. O portal indicara classificador indisponivel. Execute setup.ps1.' }
    }
    $taskPort = if ($env:PORT) { $env:PORT } else { '3000' }
    Write-Host "Portal: http://localhost:$taskPort . Ctrl+C encerra esta execucao."
    if ($Demo) { Write-Host 'DEMONSTRACAO: ocorrencias sinteticas em JSON. Para validar MongoDB, execute sem -Demo.' }
    Push-Location (Join-Path $taskRoot 'web')
    try { & npm.cmd start } finally { Pop-Location }
} finally {
    if ($taskClassifierProcess -and -not $taskClassifierProcess.HasExited) {
        Stop-Process -Id $taskClassifierProcess.Id -ErrorAction SilentlyContinue
    }
    $env:DEMO_MODE = $taskOriginalMode
    $env:MONGO_URI = $taskOriginalMongo
    $env:CLASSIFIER_URL = $taskOriginalClassifier
}
