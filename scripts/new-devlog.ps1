param(
  [string]$Date = (Get-Date -Format "yyyy-MM-dd")
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TemplatePath = Join-Path $ProjectRoot "devlogs/template.md"
$LogPath = Join-Path $ProjectRoot "devlogs/$Date.md"

if (-not (Test-Path $TemplatePath)) {
  throw "Missing devlog template: $TemplatePath"
}

if (Test-Path $LogPath) {
  Write-Host "Devlog already exists: $LogPath"
  exit 0
}

$content = Get-Content $TemplatePath -Raw
$content = $content.Replace("YYYY-MM-DD", $Date)
Set-Content -Path $LogPath -Value $content -Encoding UTF8
Write-Host "Created devlog: $LogPath"
