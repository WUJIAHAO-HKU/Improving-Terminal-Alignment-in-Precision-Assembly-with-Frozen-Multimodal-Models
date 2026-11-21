$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$target='assembly-sim-a'
$opts=@('-o','BatchMode=yes','-o','ConnectTimeout=8')
$dir='assembly-jobs/assembly-transfer06'
$old='assembly-jobs/assembly-workstation-05-20261120a'
function Check { if($LASTEXITCODE -ne 0){throw "step exited $LASTEXITCODE"} }
python experiment.py decide
Check
ssh @opts $target "mkdir -p $dir && cp $old/server.py $old/rig_base.py $dir/"
Check
scp @opts actions.json gates.json masks.json locked-before-replay.json protocol.txt lock.json "${target}:${dir}/"
Check
ssh @opts $target "cd $dir && MUJOCO_GL=egl PYOPENGL_PLATFORM=egl python3 -u server.py score > score.log 2>&1"
Check
scp @opts "${target}:${dir}/scores.json" .
Check
python analyze.py
Check
python make_pdf.py
Check
