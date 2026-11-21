$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$remote='assembly-sim-a'
$dir='assembly-jobs/assembly-strong-round4-20261120b'
$opts=@('-o','BatchMode=yes','-o','ConnectTimeout=10')
$envCmd='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl python3 -u'
function Check { if ($LASTEXITCODE -ne 0) { throw "Previous command failed with $LASTEXITCODE" } }
python rules4.py decide
Check
scp @opts actions.json before-replay.json decisions.json "${remote}:${dir}/"
Check
ssh @opts $remote "cd $dir && $envCmd server.py score > score.log 2>&1"
Check
scp @opts "${remote}:${dir}/scores.json" .
Check
python evaluate.py
Check
scp @opts to_capture.json "${remote}:${dir}/"
Check
ssh @opts $remote "cd $dir && $envCmd capture.py failures > capture.log 2>&1"
Check
scp @opts -r "${remote}:${dir}/failure_views" .
Check
scp @opts "${remote}:${dir}/failure_views.json" .
Check
python report4.py
Check
