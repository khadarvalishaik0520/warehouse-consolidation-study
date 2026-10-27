"""F4 features (Addendum 4) from Snowset query history only. Usage: python f4_features.py <snowset_iv> <out.jsonl>"""
import sys, os, json, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from common.billing import periods, billed_seconds, busy_seconds
d, outp = sys.argv[1], sys.argv[2]
con = duckdb.connect()
G = con.execute(f"""select db, list(wh order by wh), list(size_min order by wh) from read_parquet('{d}/warehouses.parquet')
                    where n_db = 1 group by db having count(*) >= 2 and bool_and(n_sizes = 1) order by db""").fetchall()
done = {json.loads(l)["db"] for l in open(outp)} if os.path.exists(outp) else set()
out = open(outp, "a")
def overlaps(P, others):
    """share of periods in P that intersect any period in others (both sorted)."""
    if not P: return 0.0
    j = 0; hit = 0
    for s, e in P:
        while j < len(others) and others[j][1] < s: j += 1
        if j < len(others) and others[j][0] <= e: hit += 1
    return hit / len(P)
for db, whs, sizes in G:
    if db in done: continue
    iv, P, feat = {}, {}, {}
    for w in whs:
        iv[w] = con.execute(f"select s, e from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true) where wh = ? order by s", [w]).fetchall()
        if not iv[w]: sys.exit("no queries for %s" % w)
        P[w] = periods(iv[w], 60)
    for w in whs:
        span = max(e for _, e in iv[w]) - min(s for s, _ in iv[w]); busy = busy_seconds(iv[w]); bill = billed_seconds(iv[w], 60)
        others = sorted(x for u in whs if u != w for x in P[u])
        feat[w] = {"util": busy / span if span > 0 else 1.0, "resumes_per_day": len(P[w]) / max(span / 86400.0, 1e-9),
                   "idle_share": 1 - busy / bill if bill > 0 else 0.0, "overlap": overlaps(P[w], others),
                   "credits60": bill / 3600.0 * dict(zip(whs, sizes))[w]}
    rec = {"db": db, "k": len(whs), "size_spread": max(sizes) / min(sizes), "credits60": sum(f["credits60"] for f in feat.values())}
    for k in ("util", "resumes_per_day", "idle_share", "overlap"):
        v = [feat[w][k] for w in whs]; rec[k + "_mean"] = sum(v) / len(v); rec[k + "_min"] = min(v)
    out.write(json.dumps(rec) + "\n"); out.flush(); print(db, len(whs), "ok", flush=True)
print("F4 FEATURES DONE")
