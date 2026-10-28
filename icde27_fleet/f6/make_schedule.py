"""F6: pick the three windows by the rule in PLAN.md Addendum 8 and write schedule.json (offsets in s, durations in
whole seconds, member A/B). Reads windows.jsonl (scan_windows.py) and the Snowset intervals."""
import json, hashlib, duckdb
D = "/mnt/user-data/uploads/Downloads/warehouse-cost-papers/"; W = 5400
R = [json.loads(l) for l in open("windows.jsonl")]
A3 = [json.loads(l) for l in open(D + "icde27_fleet/results/f3.jsonl")]
fz = set(open("../frozen_groups.txt").read().split()); b = lambda r: min(r["size_tuned"], r["suspend_tuned"])
pays = {r["db"] for r in A3 if r["db"] in fz and any(len(m) > 1 for m, _, _ in r["advisor_plan"]) and b(r) - r["advisor"] >= 1 and 1 - r["advisor"] / b(r) > 0.05}
nd = [r for r in R if max(r["ba"], r["bb"]) <= 0.8 * W]                      # both members suspend at times
HO = max((r for r in nd if r["db"] in pays), key=lambda r: (r["save"], -r["ws"]))
PO = min((r for r in nd if r["db"] in pays and r["db"] != HO["db"]), key=lambda r: (abs(r["save"] - 0.20), r["ws"]))
TT = max((r for r in R if r["save"] <= 0.02), key=lambda r: (min(r["ba"], r["bb"]), -r["ws"]))
con = duckdb.connect(); out = {"window_s": W, "auto_suspend": 60, "scenarios": {}}
for tag, r, label in (("HO", HO, "high overlap"), ("PO", PO, "partial overlap"), ("TT", TT, "turn-taking")):
    st = []
    for who, w in (("A", r["a"]), ("B", r["b"])):
        for s, x in con.execute(f"select s, e - s from read_parquet('{D}data/snowset_iv/intervals/*/*.parquet', hive_partitioning=true) "
                                f"where wh = ? and s >= ? and s < ? order by s", [w, r["ws"], r["ws"] + W]).fetchall():
            st.append([round(s - r["ws"], 3), max(1, int(round(x))), who])
    st.sort(); out["scenarios"][tag] = {"label": label, "db": r["db"], "wh_a": r["a"], "wh_b": r["b"], "orig_size": r["size"],
                                        "window_start_epoch": r["ws"], "scan_saving": r["save"], "statements": st}
out["max_d"] = max(d for sc in out["scenarios"].values() for _, d, _ in sc["statements"])
out["sha"] = hashlib.sha256(json.dumps(out["scenarios"], sort_keys=True).encode()).hexdigest()[:16]
json.dump(out, open("schedule.json", "w"))
for k, sc in out["scenarios"].items():
    print(k, sc["label"], sc["db"], "statements", len(sc["statements"]), "scan saving %.3f" % sc["scan_saving"])
print("max duration", out["max_d"], "sha", out["sha"])
