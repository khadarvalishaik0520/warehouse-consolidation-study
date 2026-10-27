"""ICDE F1: suspend/resume billing on ICDE_SUSP. Short probe statements separated by pre-registered gaps around
AUTO_SUSPEND; truth = WAREHOUSE_EVENTS_HISTORY + metering (pull). Writes sf/runs/f1_<ts>.jsonl."""
import sys, os, json, time; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf"))
from sf_wcp import connect, run
GAPS = {60: [20, 45, 75, 120, 240, 20, 45, 75, 120, 240], 300: [120, 280, 330, 600, 120, 280, 330]}
PROBE = "select count(*) from lineitem where l_shipdate = date '2024-03-15'"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf", "runs"); os.makedirs(OUT, exist_ok=True)
f = open(os.path.join(OUT, "f1_%d.jsonl" % time.time()), "a")
con = connect("ICDE_SUSP", "wcp_f1", schema="TPCH"); cur = con.cursor()
for auto, gaps in GAPS.items():
    cur.execute("alter warehouse ICDE_SUSP set auto_suspend = %d" % auto)
    try: cur.execute("alter warehouse ICDE_SUSP suspend")
    except Exception: pass
    time.sleep(30); cur.execute("alter session set query_tag = 'wcp_f1_a%d'" % auto)
    for i, gap in enumerate([0] + gaps):
        time.sleep(gap); r = run(con, PROBE); r.update({"auto": auto, "i": i, "gap_before": gap})
        f.write(json.dumps(r) + "\n"); f.flush(); print("auto", auto, "probe", i, "gap", gap, "ok" if r["ok"] else "FAIL", flush=True)
    time.sleep(auto + 90)                       # let it suspend on its own
con.close(); print("F1 DONE")
