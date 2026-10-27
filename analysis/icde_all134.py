"""ICDE re-analysis on all frozen groups where the single-knob options and the joint search are feasible (consolidate-all
feasibility no longer filters). Tie-corrected Spearman; LOO as analyze_f4.py."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json, statistics as st, glob, os, sys
sys.path.insert(0, ROOT + "/icde27_fleet")
D = ROOT + "/icde27_fleet/results/"
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
FE = {r["db"]: r for r in map(json.loads, open(D + "f4_features.jsonl"))}
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r
def spear(x, y):
    a, b = rank(x), rank(y); ma, mb = st.mean(a), st.mean(b)
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** .5
def bal(pred, y):
    P = sum(y); N = len(y) - P; tp = sum(p and t for p, t in zip(pred, y)); tn = sum((not p) and (not t) for p, t in zip(pred, y))
    return .5 * tp / P + .5 * tn / N
import importlib.util
spec = importlib.util.spec_from_file_location("a4", ROOT + "/icde27_fleet/analyze_f4.py")
src = open(ROOT + "/icde27_fleet/analyze_f4.py").read()
ns = {}; exec(src[src.index("def bal("):src.index('print("\\nSpearman')], ns)  # reuse their stump/tree code
def run(f, label, loo=False):
    R = [r for r in map(json.loads, open(f)) if r["db"] in fz]
    A = [r for r in R if None not in (r["advisor"], r["suspend_tuned"], r["size_tuned"])]
    tot = sum(r["asis_600"] for r in A)
    ex = {r["db"]: 1 - r["advisor"] / min(r["size_tuned"], r["suspend_tuned"]) for r in A}
    pays = [d for d in ex if ex[d] > .05]
    y = [ex[d] > .05 for d in ex]; ov = [FE[d]["overlap_mean"] for d in ex]
    out = {"n": len(A), "wh": sum(r["warehouses"] for r in A), "q": sum(r["queries"] for r in A),
           "size": 100 * (1 - sum(r["size_tuned"] for r in A) / tot), "suspend": 100 * (1 - sum(r["suspend_tuned"] for r in A) / tot),
           "joint": 100 * (1 - sum(r["advisor"] for r in A) / tot), "pays": len(pays), "med_extra": 100 * st.median(ex.values()),
           "tot_extra": 100 * (1 - sum(r["advisor"] for r in A) / sum(min(r["size_tuned"], r["suspend_tuned"]) for r in A)),
           "rule_acc": bal([v > 0.547 for v in ov], y), "rho_ov": spear(ov, list(ex.values()))}
    C = [r for r in A if r["consolidate_all"] is not None]
    out["consol"] = 100 * (1 - sum(r["consolidate_all"] for r in C) / sum(r["asis_600"] for r in C)); out["nC"] = len(C)
    if label == "main":
        out["pays_range"] = (100 * min(ex[d] for d in pays), 100 * max(ex[d] for d in pays), 100 * st.median([ex[d] for d in pays]))
        gain = {r["db"]: min(r["size_tuned"], r["suspend_tuned"]) - r["advisor"] for r in A}; tg = sum(gain.values())
        top = sorted(gain, key=gain.get, reverse=True)[:3]
        out["top"] = [(next(r["warehouses"] for r in A if r["db"] == d), round(100 * gain[d] / tg, 1)) for d in top]
        out["merges"] = sum(1 for r in A if any(len(m) > 1 for m, _, _ in r["advisor_plan"]))
        out["per_group_med"] = (100 * st.median([1 - r["suspend_tuned"] / r["asis_600"] for r in A]), 100 * st.median([1 - r["advisor"] / r["asis_600"] for r in A]))
        out["joint_vs_asis60"] = 100 * (1 - sum(r["advisor"] for r in A) / sum(r["asis_60"] for r in A))
        out["blocks"] = sum(len(r["advisor_plan"]) for r in A); out["merged_blocks"] = sum(1 for r in A for m, _, _ in r["advisor_plan"] if len(m) > 1)
        out["pairs"] = sum(1 for r in A for m, _, _ in r["advisor_plan"] if len(m) == 2)
        out["autos"] = sorted({a for r in A for _, _, a in r["advisor_plan"]})
        out["consol_worse_suspend"] = sum(1 for r in C if r["consolidate_all"] > r["suspend_tuned"] * 1.0001); out["consol_worse_default"] = sum(1 for r in C if r["consolidate_all"] > r["asis_600"])
        keys = [k for k in FE[next(iter(FE))] if k != "db"]
        out["rho"] = {k: round(spear([FE[d][k] for d in ex], list(ex.values())), 2) for k in keys}
        rows = []
        for d in ex:
            x = dict(FE[d]); x["pays"] = ex[d] > .05; rows.append(x)
        for name, fit, pred in (("stump", lambda Rr: ns["best_stump"](Rr, keys), ns["stump_pred"]), ("tree", lambda Rr: ns["best_tree"](Rr, keys), ns["tree_pred"])):
            loo = [pred(fit(rows[:i] + rows[i + 1:]), rows[i]) for i in range(len(rows))]
            yy = [r["pays"] for r in rows]; tp = sum(p and t for p, t in zip(loo, yy)); fp = sum(p and not t for p, t in zip(loo, yy))
            out["loo_" + name] = (round(bal(loo, yy), 3), round(tp / max(1, tp + fp), 2), round(tp / sum(yy), 2), str(fit(rows))[:160])
    print(label, json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in out.items()}))
run(D + "f3.jsonl", "main")
for f in sorted(glob.glob(D + "f5_*.jsonl")): run(f, os.path.basename(f)[3:-6])
