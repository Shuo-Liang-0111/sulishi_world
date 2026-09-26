param(
    [Parameter(Mandatory=$true)][string]$Script,
    [string]$Native = '',
    [string]$Arguments = ''
)
$ErrorActionPreference='Stop'
$sfRoot='H:/MyWorld/ZurichWorld/parallel/stadelhofen_01'
Set-Location -LiteralPath 'H:/MyWorld/ZurichWorld'
$resolvedScript=[IO.Path]::GetFullPath((Join-Path $sfRoot $Script))
if (-not $resolvedScript.StartsWith(($sfRoot.Replace('/','\')+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Script outside package.' }
$lease=Get-Content -LiteralPath 'H:/MyWorld/ZurichWorld/runtime/coordination/blender_lease.json' -Raw | ConvertFrom-Json
if ($lease.owner_thread -ne '01a0dd2f-d4ef-7ef0-a269-3bbfc3ce4d30') { throw 'Blender lease belongs to another conversation.' }
if (-not $lease.secondary_may_launch) { throw 'Main has not released Blender to secondary.' }
if (Get-Process -Name blender -ErrorAction SilentlyContinue) { throw 'A Blender process is still active; never launch a second one.' }
$sfRuntime=Join-Path $sfRoot 'runtime'
$env:TEMP=Join-Path $sfRuntime 'tmp';$env:TMP=$env:TEMP
$env:PYTHONDONTWRITEBYTECODE='1';$env:PYTHONUTF8='1'
$env:BLENDER_USER_CONFIG=Join-Path $sfRuntime 'profile/config'
$env:BLENDER_USER_SCRIPTS=Join-Path $sfRuntime 'profile/scripts'
$env:APPDATA=Join-Path $sfRuntime 'profile/appdata'
$env:BLENDER_MCP_DISABLE_TELEMETRY='true';$env:DISABLE_TELEMETRY='true'
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:BLENDER_USER_CONFIG,$env:BLENDER_USER_SCRIPTS,$env:APPDATA | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$log=Join-Path $sfRuntime ($stamp+'.stdout.log');$err=Join-Path $sfRuntime ($stamp+'.stderr.log')
$exe='F:/MyWorld/runtime/blender-4.5.13-windows-x64/blender.exe'
$sfArgs='--factory-startup --background'
if ($Native) {
    $resolvedNative=[IO.Path]::GetFullPath((Join-Path $sfRoot $Native))
    if (-not $resolvedNative.StartsWith(($sfRoot.Replace('/','\')+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Native outside package.' }
    $sfArgs+=' "'+$resolvedNative+'"'
}
$sfArgs+=' --python-exit-code 1 --python "'+$resolvedScript+'"'
if ($Arguments) { $sfArgs+=' -- '+$Arguments }
$p=Start-Process -FilePath $exe -ArgumentList $sfArgs -WorkingDirectory 'H:/MyWorld/ZurichWorld' -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $err
$record=@{process_id=$p.Id;script=$resolvedScript;native=$Native;arguments=$Arguments;log=$log;stderr=$err;started_utc=(Get-Date).ToUniversalTime().ToString('o');lease_seen=$lease;finished=$false}
$recfile=Join-Path $sfRuntime ($stamp+'.process.json')
$record|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $recfile -Encoding utf8
$lease.status='occupied';$lease.process_id=$p.Id;$lease.updated_utc=(Get-Date).ToUniversalTime().ToString('o')
$lease|ConvertTo-Json -Depth 5|Set-Content -LiteralPath 'H:/MyWorld/ZurichWorld/runtime/coordination/blender_lease.json' -Encoding utf8
Write-Output ('BLENDER_STARTED '+$p.Id+' '+$recfile)
$p.WaitForExit();$p.Refresh()
$record.finished=$true;$record.exit_code=$p.ExitCode;$record.finished_utc=(Get-Date).ToUniversalTime().ToString('o')
$record|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $recfile -Encoding utf8
$sfExitLease=Get-Content -LiteralPath 'H:/MyWorld/ZurichWorld/runtime/coordination/blender_lease.json' -Raw | ConvertFrom-Json
if ($sfExitLease.owner_thread -eq '01a0dd2f-d4ef-7ef0-a269-3bbfc3ce4d30' -and $sfExitLease.process_id -eq $p.Id) {
    $sfExitLease.status='reserved';$sfExitLease.process_id=$null;$sfExitLease.updated_utc=(Get-Date).ToUniversalTime().ToString('o')
    $sfExitLease|ConvertTo-Json -Depth 6|Set-Content -LiteralPath 'H:/MyWorld/ZurichWorld/runtime/coordination/blender_lease.json' -Encoding utf8
} else {
    Write-Output 'LEASE_CHANGED_DURING_PROCESS: no exit-time overwrite of another owner.'
}
Write-Output ('BLENDER_EXIT '+$p.ExitCode+' '+$recfile)
exit $p.ExitCode
