"""F6 window scan: find 90-minute windows of same-size warehouse pairs suitable for a real merge on Snowflake.
Durations are rounded to whole seconds (min 1 s) because the run uses GENERATOR(TIMELIMIT => n)."""
import sys, json, duckdb, numpy as np
from itertools import combinations
sys.path[:0] = ["/home/claude/wcp"]
from common.billing import billed_seconds
D = "/mnt/user-data/uploads/Downloads/warehouse-cost-papers/"
W, STEP, A = 5400, 1800, 60
fz = set(open("/home/claude/wcp/icde27_fleet/frozen_groups.txt").read().split())
con = duckdb.connect()
G = {str(db): (whs, sz) for db, whs, sz in con.execute(f"""select db, list(wh order by wh), list(size_min order by wh)
     from read_parquet('{D}data/snowset_iv/warehouses.parquet') where n_db = 1 and n_sizes = 1 group by db having count(*) >= 2""").fetchall() if str(db) in fz}
allw = [w for whs, _ in G.values() for w in whs]
con.execute(f"create table q as select wh, s, e - s x from read_parquet('{D}data/snowset_iv/intervals/*/*.parquet', hive_partitioning=true) where wh in ({','.join(map(str, allw))})")
def conc(iv):
    ev = sorted([(s, 1) for s, e in iv] + [(e, -1) for s, e in iv]); c = m = 0
    for _, d in ev: c += d; m = max(m, c)
    return m
DONE = set(open("/home/claude/wcp/icde27_fleet/f6/scan1.log").read().split()[0::2])   # groups finished before the restart
out = open("/home/claude/wcp/icde27_fleet/f6/windows.jsonl", "a")
for db, (whs, sz) in G.items():
    if db in DONE: continue
    Q = {}
    for w in whs:
        r = np.array(con.execute("select s, x from q where wh = ? order by s", [w]).fetchall() or np.zeros((0, 2)))
        Q[w] = r
    sizes = dict(zip(whs, sz))
    for a, b in combinations(whs, 2):
        if sizes[a] != sizes[b] or len(Q[a]) < 15 or len(Q[b]) < 15: continue
        t0 = min(Q[a][0, 0], Q[b][0, 0]); t1 = max(Q[a][-1, 0], Q[b][-1, 0])
        for ws in np.arange(t0, t1 - W, STEP):
            lo = {w: np.searchsorted(Q[w][:, 0], ws) for w in (a, b)}; hi = {w: np.searchsorted(Q[w][:, 0], ws + W) for w in (a, b)}
            na, nb = int(hi[a] - lo[a]), int(hi[b] - lo[b])
            if not (15 <= na <= 400 and 15 <= nb <= 400): continue
            iv = {w: [(s, s + max(1.0, round(x))) for s, x in Q[w][lo[w]:hi[w]]] for w in (a, b)}
            if max(e - s for s, e in iv[a] + iv[b]) > 600: continue
            if conc(iv[a] + iv[b]) > 8: continue
            ba, bb = billed_seconds(iv[a], A), billed_seconds(iv[b], A); bm = billed_seconds(iv[a] + iv[b], A)
            if min(ba, bb) < 600: continue
            out.write(json.dumps({"db": db, "a": a, "b": b, "size": sizes[a], "ws": float(ws), "na": na, "nb": nb, "ba": ba, "bb": bb, "bm": bm,
                                  "save": 1 - bm / (ba + bb)}) + "\n")
    print(db, len(whs), flush=True)
print("SCAN DONE")
