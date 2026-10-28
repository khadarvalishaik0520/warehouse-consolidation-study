"""Extension (post-review): exhaustive vs greedy on the 10 greedy groups of 5-8 warehouses. Pre-registered secondary metric (PLAN.md F3): gap between greedy and exhaustive search, on the groups small enough
for exhaustive search (3-4 warehouses; for pairs both searches are identical). Inputs rebuilt exactly as run_f3.py."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import sys, os, json, time, duckdb
sys.path[:0] = [ROOT + "/icde27_fleet", ROOT]
import advisor as A
D = ROOT + "/"
al = json.load(open(D + "icde27_fleet/alpha.json")); alpha = {int(k): float(v) for k, v in al["alpha"].items()}
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
F3 = {r["db"]: r for r in map(json.loads, open(D + "icde27_fleet/results/f3.jsonl")) if r["db"] in fz}
sel = sorted(d for d, r in F3.items() if r["advisor_method"] == "greedy" and r["warehouses"] <= 8)
con = duckdb.connect()
con.execute(f"create table q as select wh, s, e - s x from read_parquet('{D}data/snowset_iv/intervals/*/*.parquet', hive_partitioning=true)")
G = {str(db): (whs, sizes) for db, whs, sizes in con.execute(f"""select db, list(wh order by wh), list(size_min order by wh)
     from read_parquet('{D}data/snowset_iv/warehouses.parquet') where n_db = 1 and n_sizes = 1 group by db having count(*) >= 2""").fetchall()}
out = open(ROOT + "/icde27_fleet/results/greedy_gap_large.jsonl", "w"); kw = {"alpha": alpha, "slots": 8, "resume": 1.0}
for db in sel:
    t0 = time.time(); whs, sizes = G[db]; sizes0 = dict(zip(whs, sizes)); W = {}
    for w in whs:
        rows = con.execute("select s, x from q where wh = ? order by s", [w]).fetchall()
        W[w] = [(s, x, sizes0[w], w) for s, x in rows]
    base = A.as_is(W, sizes0, 600, **kw); targets = {w: 1.2 * base[w][1] for w in W}
    ex = A.advise(W, sizes0, targets, exhaustive_max=8, **kw); gr = A.advise(W, sizes0, targets, **kw)
    rec = {"db": db, "k": len(whs), "recorded": F3[db]["advisor"], "exhaustive": ex[0] if ex else None, "greedy": gr[0] if gr else None,
           "ex_plan": [[len(m), s, a] for m, s, a in ex[1]] if ex else None, "gr_plan": [[len(m), s, a] for m, s, a in gr[1]] if gr else None}
    out.write(json.dumps(rec) + "\n"); out.flush(); print(db, len(whs), "%.0fs" % (time.time() - t0), rec["recorded"], rec["exhaustive"], rec["greedy"], flush=True)
print("GREEDY GAP LARGE DONE")
