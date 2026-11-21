$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$target='assembly-sim-a'
$dir='assembly-jobs/assembly-workstation-05-20261120a'
$opts=@('-o','BatchMode=yes','-o','ConnectTimeout=10')
$runner='MUJOCO_GL=egl PYOPENGL_PLATFORM=egl python3 -u'
function Check {if ($LASTEXITCODE -ne 0){throw "Step failed with $LASTEXITCODE"}}
python policy5.py decide
Check
scp @opts decisions.json before-replay.json actions.json square_check.py "${target}:${dir}/"
Check
ssh @opts $target "cd $dir && $runner bench.py score >score.log 2>&1 && $runner square_check.py >square.log 2>&1"
Check
scp @opts "${target}:${dir}/scores.json" "${target}:${dir}/square-refined.json" .
Check
python evaluate5.py
Check
scp @opts to_capture.json "${target}:${dir}/"
Check
ssh @opts $target "cd $dir && $runner capture.py failures >capture.log 2>&1"
Check
scp @opts -r "${target}:${dir}/failure_views" .
Check
scp @opts "${target}:${dir}/failure_views.json" .
Check
python report5.py
Check
