"""F7 reference: how many groups miss a week-1 latency target in week 2 with no change at all (original size, 600 s).
Week-to-week drift in p95 alone; puts the act-on-history miss counts in context. Usage: python3 asis_miss.py <snowset_iv> <alpha.json> <split.jsonl>"""
import sys, os, json, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import advisor as A
d, al, sp = sys.argv[1:4]
kw = {"alpha": {int(k): float(v) for k, v in json.load(open(al))["alpha"].items()}, "slots": 8, "resume": 1.0}
R = [json.loads(l) for l in open(sp)]; R = [r for r in R if "skip" not in r]
con = duckdb.connect()
t_lo = con.execute(f"select min(s) from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true)").fetchone()[0]; cut = t_lo + 7 * 86400
G = {db: (whs, sz) for db, whs, sz in con.execute(f"""select db, list(wh order by wh), list(size_min order by wh) from read_parquet('{d}/warehouses.parquet')
     where n_db = 1 and n_sizes = 1 group by db having count(*) >= 2""").fetchall()}
miss = 0
for r in R:
    whs, sz = G[r["db"]]; sizes0 = dict(zip(whs, sz)); W1, W2 = {}, {}
    for w in whs:
        rows = con.execute(f"select s, e - s from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true) where wh = ? order by s", [w]).fetchall()
        W1[w] = [(s, x, sizes0[w], w) for s, x in rows if s < cut]; W2[w] = [(s, x, sizes0[w], w) for s, x in rows if s >= cut]
    t1 = {w: 1.2 * v[1] for w, v in A.as_is(W1, sizes0, 600, **kw).items()}
    p2 = {w: v[1] for w, v in A.as_is(W2, sizes0, 600, **kw).items()}
    miss += any(p2[w] > t1[w] for w in whs)
print("groups %d; with no change, %d miss a week-1 latency target in week 2" % (len(R), miss))
