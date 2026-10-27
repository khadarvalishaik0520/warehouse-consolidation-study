"""F1 billing validation (paper Table II): model running periods from the probe statements vs Snowflake's own
resume/suspend events on ICDE_SUSP. Reads sf/runs/f1_*.jsonl and sf/truth/*.csv. Usage: python3 sf/validate_f1.py"""
import csv, glob, json, os, statistics as st, sys
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from common.billing import periods
P = lambda x: datetime.fromisoformat(x).timestamp()
runs = [json.loads(l) for f in glob.glob(os.path.join(HERE, "runs", "f1_*.jsonl")) for l in open(f)]
QH = {r["QUERY_ID"]: r for r in csv.DictReader(open(os.path.join(HERE, "truth", "query_history.csv")))}
allq = [r for r in QH.values() if r["WAREHOUSE_NAME"] == "ICDE_SUSP"]
EV = sorted((r for r in csv.DictReader(open(os.path.join(HERE, "truth", "events.csv")))
             if r["WAREHOUSE_NAME"] == "ICDE_SUSP" and r["EVENT_NAME"] in ("RESUME_WAREHOUSE", "SUSPEND_WAREHOUSE")), key=lambda r: P(r["TIMESTAMP"]))
pairs, cur = [], None
for r in EV:
    if r["EVENT_NAME"] == "RESUME_WAREHOUSE": cur = P(r["TIMESTAMP"])
    elif cur is not None: pairs.append((cur, P(r["TIMESTAMP"]))); cur = None
probe_ids = {r["qid"] for r in runs}
for auto in (300, 60):
    q = [QH[r["qid"]] for r in runs if r["auto"] == auto and r["qid"] in QH]
    iv = sorted((P(x["END_TIME"]) - int(x["EXECUTION_TIME"]) / 1000, P(x["END_TIME"])) for x in q)
    lo, hi = iv[0][0] - 5, iv[-1][1] + auto + 5
    act = [(a, b) for a, b in pairs if b > lo and a < hi]
    for label, ivs in (("probes only", iv), ("all statements logged on the warehouse", sorted(iv + [
            (P(x["END_TIME"]) - int(x["EXECUTION_TIME"]) / 1000, P(x["END_TIME"])) for x in allq
            if lo < P(x["START_TIME"]) < hi and x["QUERY_ID"] not in probe_ids]))):
        mod = periods(ivs, auto); ms = sum(max(60, b - a) for a, b in mod); asec = sum(b - a for a, b in act)
        tails = [b - max(y for x, y in iv if a - 2 <= x <= b) for a, b in act if any(a - 2 <= x <= b for x, y in iv)]
        print("auto %3d s, %-40s periods model/actual %d/%d  time ratio %.3f  median tail %.1f s"
              % (auto, label, len(mod), len(act), ms / asec, st.median(tails)))
