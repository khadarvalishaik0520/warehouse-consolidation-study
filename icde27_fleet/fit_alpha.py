"""Fits alpha(c) exactly as frozen (PLAN.md Addendum 2 + 3). Exec time = Snowflake QUERY_HISTORY execution_time
(INFORMATION_SCHEMA, available right away), joined to the run files by query id. Writes icde27_fleet/alpha.json and
icde27_fleet/alpha_fit.json. Usage (Mac): python fit_alpha.py"""
import os, sys, json, glob, math, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "sf"))
from sf_wcp import connect
runs = []
for f in glob.glob(os.path.join(HERE, "..", "sf", "runs", "f2_*.jsonl")) + glob.glob(os.path.join(HERE, "..", "sf", "runs", "f2b_*.jsonl")):
    src = "f2b" if os.path.basename(f).startswith("f2b") else "f2"
    for l in open(f):
        r = json.loads(l); r["src"] = src; runs.append(r)
con = connect("ICDE_SZ", "wcp_fit", schema="TPCH"); cur = con.cursor()
cur.execute("""select query_id, execution_time, warehouse_size from table(information_schema.query_history_by_warehouse(
               warehouse_name=>'ICDE_SZ', end_time_range_start=>dateadd('day',-6,current_timestamp()), result_limit=>10000))""")
ex = {q: (t / 1000.0, sz) for q, t, sz in cur.fetchall()}; con.close()
SZ = {"XSMALL": 1, "SMALL": 2, "MEDIUM": 4}
T = {}                                                   # (src,name,size) -> exec times, reps 1-2 only
missing = 0
for r in runs:
    if not r["ok"] or r["rep"] == 0: continue
    if r["qid"] not in ex: missing += 1; continue
    T.setdefault((r["src"], r["name"], r["size"]), []).append(ex[r["qid"]][0])
cls = lambda x: 0 if x < 1 else 1 if x < 10 else 2 if x < 60 else 3
per = {}; rows = []
for (src, name, size), v in T.items():
    if size != "XSMALL": continue
    txs = st.median(v); c = cls(txs)
    for s in ("SMALL", "MEDIUM"):
        if (src, name, s) not in T: continue
        ts = st.median(T[(src, name, s)])
        a = math.log(txs / ts) / math.log(SZ[s]) if ts > 0 and txs > 0 else float("nan")
        per.setdefault(c, []).append(a); rows.append({"src": src, "name": name, "xs_s": round(txs, 3), "size": s, "t_s": round(ts, 3), "alpha": round(a, 3), "class": c})
alpha, note = {}, {}
for c in range(4):
    stmts = {(r["src"], r["name"]) for r in rows if r["class"] == c}
    if len(stmts) >= 2: alpha[c] = st.median(per[c]); note[c] = "fitted (%d statements, %d values)" % (len(stmts), len(per[c]))
for c in range(4):
    if c not in alpha:
        near = min(alpha, key=lambda k: abs(k - c)); alpha[c] = alpha[near]; note[c] = "no data (< 2 statements) -> nearest class %d" % near
json.dump({"placeholder": False, "alpha": {str(k): round(v, 4) for k, v in sorted(alpha.items())}, "note": note,
           "missing_qids": missing}, open(os.path.join(HERE, "alpha.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(HERE, "alpha_fit.json"), "w"), indent=1)
for r in sorted(rows, key=lambda r: (r["class"], r["name"], r["size"])): print(r)
print("ALPHA", json.load(open(os.path.join(HERE, "alpha.json"))))
