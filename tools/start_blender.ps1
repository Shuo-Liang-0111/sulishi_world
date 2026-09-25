param(
    [string]$NativePath = '',
    [switch]$Background,
    [string]$Script = '',
    [string[]]$ScriptArgs = @(),
    [switch]$CheckOnly,
    [switch]$WaitForExit
)
if ($WaitForExit -and -not $Background) { throw 'WaitForExit is for finite background jobs, not the author session.' }
. (Join-Path $PSScriptRoot 'workspace_env.ps1')
$blenderExe = (Resolve-Path -LiteralPath $workspaceConfig.blender_executable).Path
$logDir = Join-Path $runtimeDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if (-not $NativePath) { $NativePath = $workspaceConfig.working_native }
$requestedNative = (Resolve-Path -LiteralPath $NativePath).Path
$allowedNative = $false
foreach ($base in @($projectRoot, $workspaceConfig.legacy_asset_root)) {
    if (-not $base) { continue }
    $nativeRoot = [IO.Path]::GetFullPath((Join-Path $base 'native')) + [IO.Path]::DirectorySeparatorChar
    if ($requestedNative.StartsWith($nativeRoot,[StringComparison]::OrdinalIgnoreCase)) { $allowedNative = $true }
}
if (-not $allowedNative -or [IO.Path]::GetExtension($requestedNative) -ne '.blend') {
    throw 'Native must be a .blend inside an explicitly configured Zurich native directory.'
}
$env:ZURICH_NATIVE_FILE = $requestedNative
$arguments = @('--factory-startup')
if ($Background) {
    if (-not $Script) { throw 'Background mode needs an explicit script.' }
    $scriptPath = (Resolve-Path -LiteralPath (Join-Path $projectRoot $Script)).Path
    $toolsRoot = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $scriptPath.StartsWith($toolsRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Use a script in the active tools directory.' }
    if ((Get-Content -LiteralPath $scriptPath -Raw).Contains("Path('F:/MyWorld/ZurichWorld')")) {
        throw 'Historical script still uses the legacy write root. Port and review it before running.'
    }
    $arguments += @('--background', ('"' + $requestedNative + '"'), '--python-exit-code', '1', '--python', ('"' + $scriptPath + '"'))
    if ($ScriptArgs.Count) { $arguments += '--'; $arguments += $ScriptArgs }
} else {
    if ($Script) { throw 'Custom scripts require Background mode.' }
    $addonDir = Join-Path $env:BLENDER_USER_SCRIPTS 'addons'
    New-Item -ItemType Directory -Force -Path $addonDir | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'vendor/mcp-for-blender/addon.py') -Destination (Join-Path $addonDir 'blender_mcp.py')
    $arguments += @('--python', ('"' + (Join-Path $PSScriptRoot 'blender_bootstrap.py') + '"'))
}
$record = [ordered]@{project=$projectRoot;native=$requestedNative;executable=$blenderExe;temporary=$env:TMP;logs=$logDir;background=[bool]$Background;arguments=$arguments}
if ($CheckOnly) { $record.status='configuration_verified'; $record | ConvertTo-Json -Depth 4; exit 0 }
$existing = @(Get-Process -Name blender -ErrorAction SilentlyContinue)
if ($existing.Count) { throw 'A Blender process already exists. Inspect it before starting another author or render process.' }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stdout = Join-Path $logDir ('blender-' + $stamp + '.stdout.log')
$stderr = Join-Path $logDir ('blender-' + $stamp + '.stderr.log')
$proc = Start-Process -FilePath $blenderExe -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$record.status='starting';$record.pid=$proc.Id;$record.port=19876;$record.stdout=$stdout;$record.stderr=$stderr
$record | ConvertTo-Json -Depth 4 | Tee-Object -FilePath (Join-Path $runtimeDir 'blender_process.json')
if ($WaitForExit) {
    # Retain the Process returned by Start-Process and its native handle.
    # Reacquiring by PID later can lose ExitCode after the process has ended.
    $taskProcessHandle = $proc.Handle
    $proc.WaitForExit()
    $taskNativeExitCode = $proc.ExitCode
    if ($null -eq $taskNativeExitCode) { throw 'Background process ended but its exit code was unavailable.' }
    [ordered]@{ pid=$proc.Id; native=$requestedNative; exit_code=$taskNativeExitCode;
        completed_utc=[DateTime]::UtcNow.ToString('o'); stdout=$stdout; stderr=$stderr } |
        ConvertTo-Json | Tee-Object -FilePath (Join-Path $logDir ('blender-' + $stamp + '.exit.json'))
    exit $taskNativeExitCode
}
