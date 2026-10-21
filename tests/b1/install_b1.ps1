<#
  Project Zero Hour - B1.1 test kit installer (private prototype).
  Touches ONLY:
    1) <TestCopy>\PZ\PZDev_B1.big                     (new folder inside your isolated test copy)
    2) <Documents>\Command and Conquer Generals Zero Hour Data\Maps\PZ_TestRange\   (new map folder)
  It never writes to the Steam install. Run from the unzipped kit folder:
    powershell -ExecutionPolicy Bypass -File .\install_b1.ps1 -TestCopy "D:\ZH_TestCopy"
  Then launch:  & "<TestCopy>\generalszh.exe" -win -mod "<TestCopy>\PZ\PZDev_B1.big"
#>
param(
  [Parameter(Mandatory=$true)][string]$TestCopy,
  [string]$SteamDir = "C:\Program Files (x86)\Steam\steamapps\common\Command & Conquer Generals - Zero Hour"
)
$ErrorActionPreference = "Stop"
$kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$tc  = (Resolve-Path $TestCopy).Path
if ($tc.TrimEnd('\') -ieq $SteamDir.TrimEnd('\')) { throw "Refusing: -TestCopy points at the Steam install. Use your isolated copy." }
$exe = Get-ChildItem -Path $tc -Filter "generalszh*.exe" -File | Select-Object -First 1
if (-not $exe) { Write-Warning "No generalszh*.exe found in $tc - is this the fork's test copy?" }

# verify kit integrity
Get-Content (Join-Path $kit "SHA256SUMS.txt") | ForEach-Object {
  $h, $f = $_ -split '\s+', 2
  if ($f -and $f -ne "SHA256SUMS.txt") {
    $p = Join-Path $kit $f
    $actual = (Get-FileHash -Algorithm SHA256 $p).Hash.ToLower()
    if ($actual -ne $h) { throw "Checksum mismatch: $f" }
  }
}
Write-Host "Kit checksums OK"

$pzDir = Join-Path $tc "PZ"
New-Item -ItemType Directory -Force -Path $pzDir | Out-Null
Copy-Item (Join-Path $kit "PZDev_B1.big") $pzDir -Force

$docs = [Environment]::GetFolderPath("MyDocuments")
$maps = Join-Path $docs "Command and Conquer Generals Zero Hour Data\Maps"
New-Item -ItemType Directory -Force -Path $maps | Out-Null
$dst = Join-Path $maps "PZ_TestRange"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Copy-Item -Recurse (Join-Path $kit "Maps\PZ_TestRange") $dst

$big = Join-Path $pzDir "PZDev_B1.big"
Write-Host ""
Write-Host "Installed:"
Write-Host "  $big"
Write-Host "  $dst"
Write-Host ""
Write-Host "Launch (windowed, mod archive loaded with override priority):"
if ($exe) { Write-Host "  & `"$($exe.FullName)`" -win -mod `"$big`"" } else { Write-Host "  <TestCopy>\generalszh.exe -win -mod `"$big`"" }
Write-Host ""
Write-Host "Uninstall: delete $pzDir and $dst"
