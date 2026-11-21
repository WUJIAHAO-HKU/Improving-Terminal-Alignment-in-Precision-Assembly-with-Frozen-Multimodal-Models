"""Query two model IDs in fresh, image-only benchmark sessions. Run beside the three case sheets."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
VIEW = os.getenv("ASSEMBLY_VIEW","overhead")
PREFIX = "" if VIEW=="overhead" else VIEW+"-"
IMAGE_PREFIX = "" if VIEW=="overhead" else ("tight-" if VIEW.startswith("tight") else "oblique-")
COMMON = """These are four independent simulated precision-assembly scenes. Each 336x336 image excludes its white Case title strip. A brown movable nut has a square central hole and a handle to the right. The square peg underneath is stationary, visible through the aperture and sometimes partially occluded. Move the nut horizontally to center the hole over the peg before lowering. Use only the attached pixels. Do not use tools or read files. Orthogonal camera axes: robot +X is image right, robot +Y is image up. Approximate scale at the nut: 0.558 millimeters per pixel. Square peg side 32 mm, hole side 45.5 mm. Return one JSON array, one row per labeled case. Read each independently. No commentary."""
PROMPTS = {
    "direct": COMMON + """ For each case directly output your estimated ideal world-frame motion of the nut in integer millimeters as {"id":number,"dx":number,"dy":number}. Center it even if it already fits.""",
    "landmarks": COMMON + """ For each case return your estimated centers of the hole and peg (infer the center of the full peg even when partly hidden) as {"id":number,"hole":[u,v],"peg":[u,v]}. Pixel origin is the top-left of each 336x336 scene, right is positive u and down is positive v. A fixed arithmetic decoder will convert your two positions into a motion."""
}
if VIEW.startswith("oblique"):
    for key,prompt in list(PROMPTS.items()):
        start=prompt.index("Orthogonal camera axes:")
        end=prompt.index("Square peg side")
        PROMPTS[key]=prompt[:start]+"""Camera is pitched 38 degrees from vertical, looking toward world +Y and down. Image right is world +X. Up the image points away along the table. Perspective camera: vertical field of view 30 degrees, principal point (167.5,167.5), distance from camera to its optical-axis intersection with the peg-top plane 350 mm. Upper face of nut is 34 mm above peg top. Use any of these calibration parameters as appropriate. """+prompt[end:]
    if VIEW == "oblique-noheight":
        PROMPTS = {"direct":PROMPTS["direct"].replace("Upper face of nut is 34 mm above peg top. ","")}
if VIEW.startswith("tight"):
    for key in PROMPTS:
        PROMPTS[key]=PROMPTS[key].replace("peg side 32 mm","peg side 43.5 mm")
    PROMPTS["direct"]=PROMPTS["direct"].replace("integer millimeters","millimeters to one decimal place")
    if VIEW=="tight-calibrated":
        PROMPTS={"direct":PROMPTS["direct"]+" Additional calibration: pinhole camera, principal point (167.5,167.5), vertical field of view 30 degrees, image 336 pixels high. Optical depths for nut top and peg top are 340 and 374 mm respectively."}
def run(spec):
    model,mode,sheet = spec
    with tempfile.TemporaryDirectory() as work:
        reply = Path(work)/"answer.txt"
        cmd = [shutil.which("codex"),"exec","--ephemeral","--skip-git-repo-check","--color","never",
               "-s","read-only","-m",model,"-c",'model_reasoning_effort="medium"',
               "-i",str(ROOT/f"{IMAGE_PREFIX}cases-{sheet}.png"),"-o",str(reply),PROMPTS[mode]]
        proc = subprocess.run(cmd,cwd=work,stdin=subprocess.DEVNULL,capture_output=True,timeout=220)
        if proc.returncode or not reply.exists():
            raise RuntimeError(str(spec)+proc.stderr.decode(errors="replace")[-600:])
        answer=reply.read_text(encoding="utf-8").strip()
        rows=json.loads(answer[answer.index("["):answer.rindex("]")+1])
        assert sorted(row["id"] for row in rows)==list(range(4*sheet-3,4*sheet+1))
        print(model,mode,sheet,rows,flush=True)
        return model,mode,rows
if __name__=="__main__":
    import sys
    models=sys.argv[1:] or ["gpt-6.2-sol","gpt-6.1-terra"]
    specs=[(model,mode,sheet) for sheet in range(1,4) for mode in PROMPTS for model in models]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        for model, mode, rows in ex.map(run,specs):
            out=ROOT/f"{PREFIX}{model}-{mode}-{(rows[0]['id']-1)//4+1}.json"
            out.write_text(json.dumps(rows,indent=2),encoding="utf-8")

