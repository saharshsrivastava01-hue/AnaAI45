"""NEXUS Virtual Cinema Chip core: sparse logical scheduler + Blender adapter.
Logical slots are identifiers, not GPUs or concurrency. Local execution is bounded.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, subprocess, shutil, time, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get("NEXUS_CORE_DB",ROOT/"nexus_core.sqlite3"))
LOGICAL_SLOTS=1_000_000_000_000
MAX_LOCAL_WORKERS=max(1,min(4,int(os.environ.get("NEXUS_WORKERS","1"))))

def connect():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript("""
    CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, project TEXT, scene INTEGER,
      kind TEXT, status TEXT, payload TEXT, created REAL, started REAL, finished REAL, result TEXT);
    CREATE TABLE IF NOT EXISTS workers(id TEXT PRIMARY KEY, name TEXT, kind TEXT, status TEXT, last_seen REAL);
    """); return con

def status():
    con=connect()
    rows=con.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status").fetchall()
    workers=con.execute("SELECT * FROM workers").fetchall()
    con.close()
    return {"name":"NEXUS Virtual Cinema Chip Core","logical_scheduler_slots":LOGICAL_SLOTS,
      "logical_slots_notice":"Sparse logical slot namespace; not physical GPUs or active concurrency.",
      "local_worker_limit":MAX_LOCAL_WORKERS,"blender_available":bool(shutil.which("blender")),
      "worker_registry":[dict(w) for w in workers],"task_counts":{r["status"]:r["n"] for r in rows}}

def submit(scene_spec,kind="blender_scene"):
    tid=str(uuid.uuid4()); con=connect()
    con.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
      (tid,"NEXUS_2090",int(scene_spec.get("scene_number",1)),kind,"queued",
       json.dumps(scene_spec),time.time(),None,None,None))
    con.commit();con.close();return tid

def claim():
    con=connect(); row=con.execute("SELECT * FROM tasks WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
    if not row: con.close(); return None
    con.execute("UPDATE tasks SET status='running',started=? WHERE id=? AND status='queued'",(time.time(),row["id"]))
    con.commit();con.close();return dict(row)

def finish(tid,status_value,result):
    con=connect();con.execute("UPDATE tasks SET status=?,finished=?,result=? WHERE id=?",
      (status_value,time.time(),json.dumps(result),tid));con.commit();con.close()

def render_task(task,blender_script=None):
    if not shutil.which("blender"):
        finish(task["id"],"blocked_no_renderer",{"error":"Blender executable not found. Install Blender and ensure it is on PATH."})
        return {"status":"blocked_no_renderer"}
    spec=json.loads(task["payload"]); out=ROOT/"renders"/task["id"]
    out.mkdir(parents=True,exist_ok=True)
    spec["output_dir"]=str(out)
    specfile=out/"scene_spec.json";specfile.write_text(json.dumps(spec,indent=2),encoding="utf-8")
    script=blender_script or ROOT/"nexus_scene_builder.py"
    cmd=["blender","-b","--python",str(script),"--","--spec",str(specfile)]
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
        result={"returncode":proc.returncode,"stdout":proc.stdout[-5000:],"stderr":proc.stderr[-5000:],"output_dir":str(out)}
        finish(task["id"],"completed" if proc.returncode==0 else "failed",result)
        return result
    except subprocess.TimeoutExpired:
        finish(task["id"],"timeout",{"error":"Local render exceeded 30-minute limit"})
        return {"status":"timeout"}

def run_once():
    t=claim()
    if not t:return {"status":"idle"}
    return render_task(t)

def make_demo():
    spec={"scene_number":1,"title":"Black Geometry — orbital establishing shot",
      "duration_seconds":5,"resolution":[1280,720],"fps":24,"quality":"preview",
      "camera_move":"slow dolly","objects":["Earth","Witness","satellite","starfield"]}
    task=submit(spec);return {"queued_task_id":task,"next":"Run python nexus_chip_core.py render-once"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("command",choices=["status","demo","render-once"]);a=p.parse_args()
    if a.command=="status":print(json.dumps(status(),indent=2))
    elif a.command=="demo":print(json.dumps(make_demo(),indent=2))
    else:print(json.dumps(run_once(),indent=2))
