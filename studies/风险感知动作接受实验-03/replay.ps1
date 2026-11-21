$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$remoteUser = 'assembly-sim-a'
$remoteDir = 'assembly-jobs/assembly-acceptance-round3-1795145881212'
$sshArgs = @('-o','BatchMode=yes','-o','ConnectTimeout=8')
$remotePython = 'python3'
function RequireSuccess {
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" }
}
scp @sshArgs actions.json capture.py "${remoteUser}:${remoteDir}/"
RequireSuccess
ssh @sshArgs $remoteUser "cd $remoteDir && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl $remotePython -u server.py score > score.log 2>&1"
RequireSuccess
scp @sshArgs "${remoteUser}:${remoteDir}/scores.json" .
RequireSuccess
python analyze_acceptance.py
RequireSuccess
scp @sshArgs to_capture.json "${remoteUser}:${remoteDir}/"
RequireSuccess
ssh @sshArgs $remoteUser "cd $remoteDir && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl $remotePython -u capture.py failures > capture.log 2>&1"
RequireSuccess
scp @sshArgs -r "${remoteUser}:${remoteDir}/failure_views" .
RequireSuccess
scp @sshArgs "${remoteUser}:${remoteDir}/failure_views.json" .
RequireSuccess
python render_report.py
RequireSuccess
