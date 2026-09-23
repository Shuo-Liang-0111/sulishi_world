param([string]$NativePath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$blenderExe = 'F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe'
$runtimeDir = Join-Path $projectRoot 'runtime'
$logDir = Join-Path $runtimeDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$listener = Get-NetTCPConnection -State Listen -LocalPort 19876 -ErrorAction SilentlyContinue
if ($listener) {
    $owner = Get-Process -Id $listener[0].OwningProcess
    if ($owner.Path -ne $blenderExe.Replace('/', '\')) { throw 'Port 19876 belongs to another program.' }
    [pscustomobject]@{status='already_running';pid=$owner.Id;port=19876} | ConvertTo-Json
    exit 0
}
$env:BLENDER_USER_CONFIG = Join-Path $runtimeDir 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS = Join-Path $runtimeDir 'blender_profile/scripts'
$env:TMP = Join-Path $runtimeDir 'tmp'
$env:TEMP = $env:TMP
$env:DISABLE_TELEMETRY = 'true'
if ($NativePath) {
    $requestedNative = (Resolve-Path -LiteralPath $NativePath).Path
    $nativeRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'native')) + [IO.Path]::DirectorySeparatorChar
    if (-not $requestedNative.StartsWith($nativeRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($requestedNative) -ne '.blend') { throw 'Requested native must be a Blender file inside this project native directory.' }
    $env:ZURICH_NATIVE_FILE = $requestedNative
} else { $env:ZURICH_NATIVE_FILE = '' }
New-Item -ItemType Directory -Force -Path $env:BLENDER_USER_CONFIG,$env:BLENDER_USER_SCRIPTS,$env:TMP | Out-Null
$addonDir = Join-Path $env:BLENDER_USER_SCRIPTS 'addons'
New-Item -ItemType Directory -Force -Path $addonDir | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'vendor/mcp-for-blender/addon.py') -Destination (Join-Path $addonDir 'blender_mcp.py')
$bootstrap = Join-Path $PSScriptRoot 'blender_bootstrap.py'
$proc = Start-Process -FilePath $blenderExe -ArgumentList @('--factory-startup','--python', $bootstrap) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'blender-stdout.log') -RedirectStandardError (Join-Path $logDir 'blender-stderr.log')
[pscustomobject]@{status='starting';pid=$proc.Id;port=19876;project=$projectRoot} | ConvertTo-Json | Tee-Object -FilePath (Join-Path $runtimeDir 'blender_process.json')
