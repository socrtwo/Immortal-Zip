# Build a Windows executable + NSIS installer.
# Runs on the windows-latest GitHub runner.
param()
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $Root

$Version = (& python -c "import immortal_zip; print(immortal_zip.__version__)").Trim()
$Dist = Join-Path $Root "dist"
if (Test-Path $Dist) { Remove-Item $Dist -Recurse -Force }
New-Item -ItemType Directory -Path $Dist | Out-Null

Write-Host ">>> PyInstaller bundle"
pyinstaller --noconfirm --clean --distpath $Dist --workpath (Join-Path $Dist "work") build/immortal-zip.spec

# Locate NSIS (installed via chocolatey on the runner).
$MakeNsis = (Get-Command makensis -ErrorAction SilentlyContinue)
if (-not $MakeNsis) {
  $candidates = @("C:\Program Files (x86)\NSIS\makensis.exe", "C:\Program Files\NSIS\makensis.exe")
  foreach ($c in $candidates) { if (Test-Path $c) { $MakeNsis = $c; break } }
}
if (-not $MakeNsis) { throw "makensis.exe not found" }

Write-Host ">>> NSIS installer"
Push-Location build
& $MakeNsis installer.nsi
Pop-Location

$Setup = Join-Path $Root "build\Immortal-Zip-Setup.exe"
$Final = Join-Path $Dist ("Immortal-Zip-{0}-Setup.exe" -f $Version)
Move-Item $Setup $Final -Force
Write-Host (">>> Wrote {0}" -f $Final)
Get-Item $Final | Select-Object Name, Length
