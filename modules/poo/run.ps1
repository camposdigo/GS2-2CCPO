param([switch]$Test)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $compilador = Get-Command javac -ErrorAction SilentlyContinue
    $executor = Get-Command java -ErrorAction SilentlyContinue
    if (-not $compilador -or -not $executor) {
        if ($env:JAVA_HOME) {
            $compilador = Join-Path $env:JAVA_HOME 'bin\javac.exe'
            $executor = Join-Path $env:JAVA_HOME 'bin\java.exe'
        } else { throw 'Instale JDK 17+ e configure PATH ou JAVA_HOME.' }
    }
    New-Item -ItemType Directory -Path build -Force | Out-Null
    $fontes = (Get-ChildItem src -Filter '*.java' -Recurse).FullName
    & $compilador -encoding UTF-8 -d build $fontes
    if ($LASTEXITCODE -ne 0) { throw 'Falha na compilacao Java.' }
    $classe = if ($Test) { 'territorio.Verificacoes' } else { 'territorio.Main' }
    & $executor -cp build $classe
    if ($LASTEXITCODE -ne 0) { throw 'Falha na execucao Java.' }
} finally { Pop-Location }
