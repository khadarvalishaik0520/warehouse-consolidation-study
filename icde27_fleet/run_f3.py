"""F3 runner (ICDE). Requires fitted alpha from F2 (alpha.json); refuses to run on the placeholder.
One row per candidate group. Usage: python3 run_f3.py <snowset_iv dir> <results dir> <alpha.json> [max_groups]"""
import sys, os, json, time, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import advisor as A

def load_groups(d):
    con = duckdb.connect()
    g = con.execute(f"""select db, list(wh order by wh), list(size_min order by wh)
                        from read_parquet('{d}/warehouses.parquet') where n_db = 1 and n_sizes = 1
                        group by db having count(*) >= 2 order by db""").fetchall()
    return con, g

def main(d, res, alpha_path, cap, target=1.2, slots=8, resume=1.0, alpha_scale=1.0, tag="f3"):
    al = json.load(open(alpha_path))
    if al.get("placeholder", True): sys.exit("alpha.json is a placeholder -> run F2 on Snowflake and fit alpha first")
    alpha = {int(k): float(v) * alpha_scale for k, v in al["alpha"].items()}
    os.makedirs(res, exist_ok=True); outp = os.path.join(res, tag + ".jsonl")
    frozen = set(open(os.path.join(HERE, "frozen_groups.txt")).read().split())
    done = {json.loads(l)["db"] for l in open(outp)} if os.path.exists(outp) else set()
    con, groups = load_groups(d); out = open(outp, "a")
    for db, whs, sizes in groups[:cap]:
        if db in done or db not in frozen: continue          # F5 variants: frozen 134 groups only
        t0 = time.time(); W = {}; sizes0 = dict(zip(whs, sizes))
        for w in whs:
            rows = con.execute(f"select s, e - s from read_parquet('{d}/intervals/*/*.parquet', hive_partitioning=true) "
                               f"where wh = ? order by s", [w]).fetchall()   # no hash pruning: hash() differs across DuckDB versions
            if not rows: sys.exit("no queries loaded for warehouse %s -> stop (data/path problem)" % w)
            W[w] = [(s, x, sizes0[w], w) for s, x in rows]
        kw = {"alpha": alpha, "slots": slots, "resume": resume}
        rec = {"db": db, "warehouses": len(whs), "queries": sum(len(v) for v in W.values()),
               "sizes": [sizes0[w] for w in whs]}
        for auto in (60, 300, 600):
            rec["asis_%d" % auto] = sum(v[0] for v in A.as_is(W, sizes0, auto, **kw).values())
        base = A.as_is(W, sizes0, 600, **kw); targets = {w: target * base[w][1] for w in W}
        # (ii) separate, size tuned at auto 600; (iii) separate, suspend tuned at original size
        ii = iii = 0.0; ok2 = ok3 = True
        for w in whs:
            c2 = [A.evaluate_block(W, [w], s, 600, targets, **kw) for s in (sizes0[w] / 2.0, sizes0[w], sizes0[w] * 2.0) if s >= 1]
            c2 = [c for c, ok, _ in c2 if ok]; ok2 &= bool(c2); ii += min(c2) if c2 else 0
            c3 = [A.evaluate_block(W, [w], sizes0[w], a, targets, **kw) for a in A.AUTOS]
            c3 = [c for c, ok, _ in c3 if ok]; ok3 &= bool(c3); iii += min(c3) if c3 else 0
        rec.update({"size_tuned": ii if ok2 else None, "suspend_tuned": iii if ok3 else None})
        iv = A.best_block(W, whs, sizes0, targets, **kw); rec["consolidate_all"] = iv[0] if iv else None
        v = A.advise(W, sizes0, targets, **kw)
        rec.update({"advisor": v[0] if v else None, "advisor_plan": [[list(m), s, a] for m, s, a in v[1]] if v else None,
                    "advisor_method": v[2] if v else None, "secs": round(time.time() - t0, 1)})
        out.write(json.dumps(rec) + "\n"); out.flush(); print(db, len(whs), "wh", rec["secs"], "s", flush=True)
    print("F3 DONE")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("snowset_iv"); ap.add_argument("results"); ap.add_argument("alpha_json")
    ap.add_argument("--max", type=int, default=10**9); ap.add_argument("--target", type=float, default=1.2)
    ap.add_argument("--slots", type=int, default=8); ap.add_argument("--resume", type=float, default=1.0)
    ap.add_argument("--alpha-scale", type=float, default=1.0); ap.add_argument("--tag", default="f3")
    a = ap.parse_args()
    main(a.snowset_iv, a.results, a.alpha_json, a.max, a.target, a.slots, a.resume, a.alpha_scale, a.tag)
