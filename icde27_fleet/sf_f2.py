"""ICDE F2: runtime vs warehouse size on ICDE_SZ. Sizes in ABBA order XS,S,M,M,S,XS; per size block every statement
(7 batch + 6 ladder, TPCH10) x 3 reps round-robin. Rep 1 after a resize is warm-up; alpha is fitted on reps 2-3
(pre-registered). Exec times come later from QUERY_HISTORY (pull). Writes sf/runs/f2_<ts>.jsonl."""
import sys, os, json, time; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf"))
from sf_wcp import connect, run, batch_queries, LADDER
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf", "runs"); os.makedirs(OUT, exist_ok=True)
f = open(os.path.join(OUT, "f2_%d.jsonl" % time.time()), "a")
con = connect("ICDE_SZ", "wcp_f2"); cur = con.cursor()
cur.execute("alter warehouse ICDE_SZ set auto_suspend = 60")
stmts = batch_queries() + LADDER
for block, size in enumerate(["XSMALL", "SMALL", "MEDIUM", "MEDIUM", "SMALL", "XSMALL"]):
    cur.execute("alter warehouse ICDE_SZ set warehouse_size = %s wait_for_completion = true" % size)
    cur.execute("alter session set query_tag = 'wcp_f2_b%d_%s'" % (block, size))
    for rep in range(3):
        for name, sql in stmts:
            r = run(con, sql); r.update({"block": block, "size": size, "rep": rep, "name": name})
            f.write(json.dumps(r) + "\n"); f.flush()
            print(block, size, rep, name, "ok" if r["ok"] else "FAIL " + r.get("err", ""), "%.1fs" % r["client_s"], flush=True)
cur.execute("alter warehouse ICDE_SZ set warehouse_size = XSMALL")
try: cur.execute("alter warehouse ICDE_SZ suspend")
except Exception: pass
con.close(); print("F2 DONE")
