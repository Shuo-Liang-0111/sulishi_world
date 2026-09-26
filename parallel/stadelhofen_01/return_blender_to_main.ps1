$ErrorActionPreference='Stop'
$sfRoot='H:/MyWorld/ZurichWorld/parallel/stadelhofen_01'
$sfLeasePath='H:/MyWorld/ZurichWorld/runtime/coordination/blender_lease.json'
$sfSpec=Get-Content -LiteralPath (Join-Path $sfRoot 'derived/build_input.json') -Raw | ConvertFrom-Json
$sfTag=$sfSpec.version.Split('_')[-1]
$sfReview=Get-Content -LiteralPath (Join-Path $sfRoot ('evidence/'+$sfTag+'/visual_review.json')) -Raw | ConvertFrom-Json
$sfReplay=Get-Content -LiteralPath (Join-Path $sfRoot ('evidence/'+$sfTag+'/integration_replay.json')) -Raw | ConvertFrom-Json
if (-not $sfReview.local_visual_passed -or -not $sfReplay.passed) { throw 'Local review or independent replay is incomplete.' }
if (@($sfReview.views | Where-Object { -not $_.actually_viewed -or -not $_.fully_decoded }).Count -ne 0 -or $sfReview.views.Count -ne 6) { throw 'Six actual image reviews are required.' }
$sfReceipts=@()
foreach ($sfFile in $sfReview.process_receipts) {
    $sfResolved=[IO.Path]::GetFullPath((Join-Path $sfRoot $sfFile))
    if (-not $sfResolved.StartsWith(($sfRoot.Replace('/','\')+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Receipt outside package.' }
    $sfRecord=Get-Content -LiteralPath $sfResolved -Raw | ConvertFrom-Json
    if (-not $sfRecord.finished -or $sfRecord.exit_code -ne 0) { throw ('Incomplete process receipt: '+$sfFile) }
    $sfReceipts+=@{path=$sfResolved;process_id=$sfRecord.process_id;exit_code=$sfRecord.exit_code;finished_utc=$sfRecord.finished_utc}
}
if (Get-Process -Name blender -ErrorAction SilentlyContinue) { throw 'Blender is still active; resource cannot be returned.' }
$sfBefore=Get-Content -LiteralPath $sfLeasePath -Raw | ConvertFrom-Json
if ($sfBefore.owner_thread -ne '01a0dd2f-d4ef-7ef0-a269-3bbfc3ce4d30' -or -not $sfBefore.secondary_may_launch) { throw 'Lease no longer belongs to this secondary thread.' }
$sfAfter=$sfBefore | ConvertTo-Json -Depth 8 | ConvertFrom-Json
$sfAfter.owner_thread='01a08947-06f2-7123-b7c7-c955cfa6c809'
$sfAfter.owner_role='main'
$sfAfter.status='reserved'
$sfAfter.process_id=$null
$sfAfter.secondary_may_launch=$false
$sfAfter.main_may_launch=$true
$sfAfter.updated_utc=(Get-Date).ToUniversalTime().ToString('o')
$sfAfter.purpose=('SF1 '+$sfSpec.version+' local batch handed off for independent main acceptance. Secondary stopped; no next area assigned.')
$sfAfter | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $sfLeasePath -Encoding utf8
$sfReceipt=@{returned_utc=$sfAfter.updated_utc;version=$sfSpec.version;observed_blender_processes=@();before=$sfBefore;after=$sfAfter;process_receipts=$sfReceipts;secondary_stopped=$true;accepted_by_main=$false}
$sfReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $sfRoot ('evidence/'+$sfTag+'/resource_return.json')) -Encoding utf8
Write-Output ('BLENDER_RETURNED_TO_MAIN '+$sfAfter.updated_utc)
