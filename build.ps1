param([switch]$Portable)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Run-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program (exit $LASTEXITCODE)" }
}

if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
if ($env:OS -ne 'Windows_NT') { throw 'Build Windows releases on Windows 10/11 or a Windows CI runner.' }
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Run-Checked 'py' @('-3.12', '-m', 'venv', '.venv')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        Run-Checked 'python' @('-m', 'venv', '.venv')
    } else { throw 'Install Python 3.12 x64 on the BUILD machine, or use the included Windows GitHub Actions workflow.' }
}
$arenaPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Run-Checked $arenaPython @('-c', 'import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize(''P'')==8, ''Python 3.12 x64 is required''')
Run-Checked $arenaPython @('-B', 'scripts/release_privacy.py')
Run-Checked $arenaPython @('-m', 'pip', 'install', '-r', 'requirements-build.txt')

$previousQtPlatform = $env:QT_QPA_PLATFORM
$previousQtBackend = $env:QT_QUICK_BACKEND
$previousLayout = $env:ARENA_BUILD_LAYOUT
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    $env:QT_QUICK_BACKEND = 'software'
    # Local development tests are not distributed with the public source.
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'tests')) {
        Run-Checked $arenaPython @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
    }
    Run-Checked $arenaPython @('main.py', '--smoke-test', '--data-dir', 'build\source-smoke-data')
    Run-Checked $arenaPython @('main.py', '--smoke-test', '--preview', 'settings', '--dialog', 'directory', '--data-dir', 'build\source-settings-data')
    $env:ARENA_BUILD_LAYOUT = if ($Portable) { 'onedir' } else { 'onefile' }
    Run-Checked $arenaPython @('-m', 'PyInstaller', '--noconfirm', '--clean', 'TranslateArena.spec')
    $arenaExe = if ($Portable) { Join-Path $PSScriptRoot 'dist\TranslateArena\TranslateArena.exe' } else { Join-Path $PSScriptRoot 'dist\TranslateArena.exe' }
    $arenaSmokeData = Join-Path $PSScriptRoot 'build\frozen-smoke-data'
    # Windowed executables must be awaited explicitly to obtain their process exit code.
    $arenaProcess = Start-Process -FilePath $arenaExe -ArgumentList @('--smoke-test', '--data-dir', ('"' + $arenaSmokeData + '"')) -WindowStyle Hidden -Wait -PassThru
    if ($arenaProcess.ExitCode -ne 0) { throw "Packaged QML smoke test failed (exit $($arenaProcess.ExitCode))." }
    $arenaProcess = Start-Process -FilePath $arenaExe -ArgumentList @('--smoke-test', '--preview', 'settings', '--dialog', 'directory', '--data-dir', ('"' + $arenaSmokeData + '"')) -WindowStyle Hidden -Wait -PassThru
    if ($arenaProcess.ExitCode -ne 0) { throw "Packaged folder dialog smoke test failed (exit $($arenaProcess.ExitCode))." }
    Write-Host "Build complete: $arenaExe"
} finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
    $env:QT_QUICK_BACKEND = $previousQtBackend
    $env:ARENA_BUILD_LAYOUT = $previousLayout
}
