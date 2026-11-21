from execute import *
import time
model='gpt-6.1-terra'
collect(model,['grip']);prepare(model,'grip');push(model+'-grip.json')
py='WORKERS=2 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl OPENBLAS_NUM_THREADS=1 python3'
ssh(py+' server.py grip '+model+' && tar czf '+model+'-grips.tar.gz sim/'+model+'/*/01-eye.png sim/'+model+'/*/grip.json')
pull(model+'-grips.tar.gz');untar(model+'-grips.tar.gz');(D/('ready-grip-'+model)).touch()
collect(model,['first','repeat','depth','overhead'])
print('all model replies ready',flush=True)
