"""F7 (exploratory, pre-registered in PLAN.md Addendum 7 before running): time-split test of the overlap rule.
Week 1 = first 7 days of the trace, week 2 = the rest. For each frozen group and each week: features (as f4_features.py)
and the same options as run_f3.py (as-is, size-tuned, suspend-tuned, joint search). Then the week-1 choices (joint plan,
suspend-tuned timeouts) are replayed unchanged on week-2 traffic, against week-1 latency targets.
Usage: python3 run_split.py <snowset_iv> <alpha.json> <out.jsonl> [max_groups]"""
import sys, os, json, time, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import advisor as A
from common.billing import periods, billed_seconds, busy_seconds

def overlaps(P, others):
    if not P: return 0.0
    j = hit = 0
    for s, e in P:
        while j < len(others) and others[j][1] < s: j += 1
        if j < len(others) and others[j][0] <= e: hit += 1
    return hit / len(P)

def features(iv, sizes0):
    whs = [w for w in iv if iv[w]]; P = {w: periods(iv[w], 60) for w in whs}; f = {}
    for w in whs:
        span = max(e for _, e in iv[w]) - min(s for s, _ in iv[w]); busy = busy_seconds(iv[w]); bill = billed_seconds(iv[w], 60)
        others = sorted(x for u in whs if u != w for x in P[u])
        f[w] = {"util": busy / span if span > 0 else 1.0, "idle_share": 1 - busy / bill if bill > 0 else 0.0,
                "overlap": overlaps(P[w], others), "credits60": bill / 3600.0 * sizes0[w]}
    out = {"k_active": len(whs), "credits60": sum(v["credits60"] for v in f.values())}
    for k in ("util", "idle_share", "overlap"):
        v = [f[w][k] for w in whs]; out[k + "_mean"] = sum(v) / len(v) if v else 0.0
    return out

def options(W, sizes0, kw):
    whs = sorted(W); base = A.as_is(W, sizes0, 600, **kw); targets = {w: 1.2 * base[w][1] for w in W}
    rec = {"asis_600": sum(v[0] for v in base.values())}
    ii = iii = 0.0; susp = {}
    for w in whs:
        c2 = [A.evaluate_block(W, [w], s, 600, targets, **kw)[:2] for s in (sizes0[w] / 2.0, sizes0[w], sizes0[w] * 2.0) if s >= 1]
        ii += min(c for c, ok in c2 if ok)
        c3 = [(A.evaluate_block(W, [w], sizes0[w], a, targets, **kw)[:2], a) for a in A.AUTOS]
        c, a = min(((c, a) for (c, ok), a in c3 if ok)); iii += c; susp[w] = a
    v = A.advise(W, sizes0, targets, **kw)
    rec.update({"size_tuned": ii, "suspend_tuned": iii, "advisor": v[0], "plan": [[list(m), s, a] for m, s, a in v[1]],
                "susp_choice": susp})
    return rec, targets

def apply_plan(W, plan, targets, kw):
    """Cost and latency check of a fixed plan [(members, size, auto)] on traffic W."""
    c = 0.0; ok_all = True; worst = 0.0
    for m, s, a in plan:
        m = [w for w in m if W.get(w)]
        if not m: continue
        ci, ok, wr = A.evaluate_block(W, m, s, a, targets, **kw); c += ci; ok_all &= ok; worst = max(worst, wr)
    return c, ok_all, worst

def main(d, alpha_path, outp, cap=10**9):
    al = json.load(open(alpha_path)); kw = {"alpha": {int(k): float(v) for k, v in al["alpha"].items()}, "slots": 8, "resume": 1.0}
    frozen = set(open(os.path.join(HERE, "..", "frozen_groups.txt")).read().split())
    con = duckdb.connect()
    G = con.execute(f"""select db, list(wh order by wh), list(size_min order by wh) from read_parquet('{d}/warehouses.parquet')
                        where n_db = 1 and n_sizes = 1 group by db having count(*) >= 2 order by db""").fetchall()
    G = [g for g in G if g[0] in frozen]
    t_lo = con.execute(f"select min(s) from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true)").fetchone()[0]
    cut = t_lo + 7 * 86400
    done = {json.loads(l)["db"] for l in open(outp)} if os.path.exists(outp) else set()
    out = open(outp, "a")
    for db, whs, sizes in sorted(G, key=lambda g: len(g[1]))[:cap]:
        if db in done: continue
        t0 = time.time(); sizes0 = dict(zip(whs, sizes)); W1, W2, I1, I2 = {}, {}, {}, {}
        for w in whs:
            rows = con.execute(f"select s, e from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true) where wh = ? order by s", [w]).fetchall()
            r1 = [x for x in rows if x[0] < cut]; r2 = [x for x in rows if x[0] >= cut]
            I1[w], I2[w] = r1, r2
            W1[w] = [(s, e - s, sizes0[w], w) for s, e in r1]; W2[w] = [(s, e - s, sizes0[w], w) for s, e in r2]
        rec = {"db": db, "k": len(whs), "sizes": sizes}
        if not all(W1.values()) or not all(W2.values()):
            rec["skip"] = "a warehouse is idle in one week"; out.write(json.dumps(rec) + "\n"); out.flush(); print(db, "skip", flush=True); continue
        o1, tg1 = options(W1, sizes0, kw); o2, _ = options(W2, sizes0, kw)
        rec.update({"f1": features(I1, sizes0), "f2": features(I2, sizes0), "w1": o1, "w2": o2})
        # week-1 choices replayed unchanged on week 2, against week-1 latency targets
        rec["w2_with_w1_plan"] = apply_plan(W2, o1["plan"], tg1, kw)
        rec["w2_with_w1_susp"] = apply_plan(W2, [[[w], sizes0[w], o1["susp_choice"][w]] for w in whs], tg1, kw)
        rec["secs"] = round(time.time() - t0, 1)
        out.write(json.dumps(rec) + "\n"); out.flush(); print(db, len(whs), rec["secs"], flush=True)
    print("F7 DONE")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 10**9)
