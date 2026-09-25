$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$configPath = Join-Path $projectRoot 'workspace.local.json'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw 'Create workspace.local.json from workspace.example.json and verify its local paths.'
}
$workspaceConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$runtimeDir = Join-Path $projectRoot 'runtime'
$env:ZURICH_WORKSPACE = $projectRoot
$env:PYTHONPATH = Join-Path $projectRoot 'tools'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:TMP = Join-Path $runtimeDir 'tmp'
$env:TEMP = $env:TMP
$env:PIP_CACHE_DIR = Join-Path $runtimeDir 'pip-cache'
$env:UV_CACHE_DIR = Join-Path $runtimeDir 'uv-cache'
$env:DISABLE_TELEMETRY = 'true'
$env:BLENDER_MCP_DISABLE_TELEMETRY = 'true'
$env:BLENDER_USER_CONFIG = Join-Path $runtimeDir 'blender_profile/config'
$env:BLENDER_USER_SCRIPTS = Join-Path $runtimeDir 'blender_profile/scripts'
$env:APPDATA = Join-Path $runtimeDir 'mcp_profile'
New-Item -ItemType Directory -Force -Path $env:TMP,$env:APPDATA,$env:BLENDER_USER_CONFIG,$env:BLENDER_USER_SCRIPTS | Out-Null
