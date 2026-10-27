"""Exploratory test of Proposition 1: for every merged warehouse in the joint plans, compare the saving predicted from
coverage overlap alone (same timing, merged rate) with the saving the replay realises (queueing, size scaling, resume)."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import sys, json, duckdb, statistics as st
sys.path[:0] = [ROOT + "/icde27_fleet", ROOT]
import advisor as A
from common.billing import billed_seconds
D = ROOT + "/"
alpha = {int(k): float(v) for k, v in json.load(open(D + "icde27_fleet/alpha.json"))["alpha"].items()}
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
F3 = {r["db"]: r for r in map(json.loads, open(D + "icde27_fleet/results/f3.jsonl")) if r["db"] in fz}
con = duckdb.connect()
con.execute(f"create table q as select wh, s, e - s x from read_parquet('{D}data/snowset_iv/intervals/*/*.parquet', hive_partitioning=true)")
SZ = dict(con.execute(f"select wh, size_min from read_parquet('{D}data/snowset_iv/warehouses.parquet')").fetchall())
kw = {"alpha": alpha, "slots": 8, "resume": 1.0}; out = open(ROOT + "/icde27_fleet/results/mechanism.jsonl", "w")
for db, r in F3.items():
    blocks = [(m, s, a) for m, s, a in r["advisor_plan"] if len(m) > 1]
    if not blocks: continue
    whs = [w for m, _, _ in r["advisor_plan"] for w in m]; W = {}
    for w in whs:
        W[w] = [(s, x, SZ[w], w) for s, x in con.execute("select s, x from q where wh = ? order by s", [w]).fetchall()]
    sizes0 = {w: SZ[w] for w in whs}
    base = A.as_is(W, sizes0, 600, **kw); targets = {w: 1.2 * base[w][1] for w in W}
    for m, S, a in blocks:
        sep = sum(A.evaluate_block(W, [w], sizes0[w], a, targets, **kw)[0] for w in m)        # members separate, own size, same timeout
        real = A.evaluate_block(W, list(m), S, a, targets, **kw)[0]                             # merged, replayed
        cov = {w: billed_seconds([(s, s + x) for s, x, _, _ in W[w]], a) for w in m}
        union = billed_seconds([(s, s + x) for w in m for s, x, _, _ in W[w]], a)
        pred_same_rate = (sum(cov.values()) - union) / 3600 * S                                 # overlap term at the merged rate
        ideal = (sum(sizes0[w] * cov[w] for w in m) - S * union) / 3600                        # same timing, merged rate S
        rec = {"db": db, "k": len(m), "S": S, "sizes": [sizes0[w] for w in m], "sep": sep, "real": real, "ideal": ideal,
               "overlap_term": pred_same_rate, "equal_size": len({sizes0[w] for w in m}) == 1 and S == sizes0[m[0]]}
        out.write(json.dumps(rec) + "\n"); out.flush()
    print(db, len(blocks), flush=True)
print("MECHANISM DONE")
