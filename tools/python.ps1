# Reuse the installed interpreter as a read dependency; execute in the H checkout.
$forwardedArguments = @($args)
$hasPipelineInput = $MyInvocation.ExpectingInput
. (Join-Path $PSScriptRoot 'workspace_env.ps1')
$pythonExe = (Resolve-Path -LiteralPath $workspaceConfig.python_executable).Path
Push-Location -LiteralPath $projectRoot
try {
    if ($hasPipelineInput) { $input | & $pythonExe -B -X utf8 @forwardedArguments }
    else { & $pythonExe -B -X utf8 @forwardedArguments }
    $result = $LASTEXITCODE
} finally { Pop-Location }
exit $result
