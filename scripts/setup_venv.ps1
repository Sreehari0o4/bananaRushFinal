param(
    [string]$Python = "python"
)

try {
    $cmd = Get-Command $Python -ErrorAction Stop
    Write-Host "Using python: $($cmd.Source)"
} catch {
    Write-Error "$Python not found. Install Python 3.10.5 or pass the interpreter path as -Python <path>."
    exit 2
}

$venvDir = '.venv'

Start-Process -FilePath $Python -ArgumentList ('-m','venv',$venvDir) -NoNewWindow -Wait
Write-Host "Created virtualenv in $venvDir"
Write-Host "To activate (PowerShell): .\$venvDir\Scripts\Activate.ps1"
Write-Host "Then run:`n  python -m pip install --upgrade pip"
if (Test-Path requirements.txt) { Write-Host 'Installing requirements...' ; Start-Process -FilePath $Python -ArgumentList ('-m','pip','install','-r','requirements.txt') -NoNewWindow -Wait } else { Write-Host 'No requirements.txt found.' }
