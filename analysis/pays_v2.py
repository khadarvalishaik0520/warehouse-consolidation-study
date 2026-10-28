"""Revised 'consolidation pays' (post-review): extra saving > 5% AND the joint plan merges warehouses AND >= 1 credit saved."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json, statistics as st, glob, os, sys
src = open(ROOT + "/icde27_fleet/analyze_f4.py").read(); ns = {}
exec(src[src.index("def bal("):src.index('print("\\nSpearman')], ns)
D = ROOT + "/icde27_fleet/results/"
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
FE = {r["db"]: r for r in map(json.loads, open(D + "f4_features.jsonl"))}
best = lambda r: min(r["size_tuned"], r["suspend_tuned"])
def pays(r, th=0.05, floor=1.0):
    return (1 - r["advisor"] / best(r) > th) and any(len(m) > 1 for m, _, _ in r["advisor_plan"]) and (best(r) - r["advisor"] >= floor)
def bal(pred, y):
    P = sum(y); N = len(y) - P; tp = sum(p and t for p, t in zip(pred, y)); tn = sum((not p) and (not t) for p, t in zip(pred, y))
    return .5 * tp / P + .5 * tn / N, tp, sum(p and not t for p, t in zip(pred, y))
def summary(f, label, full=False):
    A = [r for r in map(json.loads, open(f)) if r["db"] in fz and None not in (r["advisor"], r["suspend_tuned"], r["size_tuned"])]
    y = [pays(r) for r in A]; x = [FE[r["db"]]["overlap_mean"] > 0.547 for r in A]
    acc, tp, fp = bal(x, y)
    g = {r["db"]: best(r) - r["advisor"] for r in A}; G = sum(g.values())
    out = "%-5s pays %d  rule bal.acc %.2f (prec %.2f rec %.2f)  pays-share of saving %.1f%%" % (label, sum(y), acc, tp / (tp + fp), tp / sum(y), 100 * sum(g[r["db"]] for r, t in zip(A, y) if t) / G)
    if full:
        P = [r for r, t in zip(A, y) if t]; ex = [1 - r["advisor"] / best(r) for r in P]
        out += "\n   range %.1f-%.1f%% median %.1f%%; by k: %s" % (100 * min(ex), 100 * max(ex), 100 * st.median(ex),
              {lab: sum(1 for r in P if f_(r["warehouses"])) for lab, f_ in (("2", lambda k: k == 2), ("3", lambda k: k == 3), ("4-6", lambda k: 4 <= k <= 6), ("7+", lambda k: k >= 7))})
        flag = {r["db"] for r in A if FE[r["db"]]["overlap_mean"] > 0.547}; Pd = {r["db"] for r in P}
        for name, grp in (("TP", Pd & flag), ("FN", Pd - flag), ("FP", flag - Pd)):
            out += "\n   %s %2d: median extra %.1f%%, overlap %.2f, size spread %.1f, share %.1f%%" % (name, len(grp),
                   100 * st.median([1 - r["advisor"] / best(r) for r in A if r["db"] in grp]) if grp else 0, st.median(FE[d]["overlap_mean"] for d in grp), st.median(FE[d]["size_spread"] for d in grp), 100 * sum(g[d] for d in grp) / G)
        keys = [k for k in FE[A[0]["db"]] if k != "db"]
        rows = []
        for r in A:
            z = dict(FE[r["db"]]); z["pays"] = pays(r); rows.append(z)
        yy = [z["pays"] for z in rows]
        for name, fit, pred in (("stump", lambda R_: ns["best_stump"](R_, keys), ns["stump_pred"]), ("tree", lambda R_: ns["best_tree"](R_, keys), ns["tree_pred"])):
            loo = [pred(fit(rows[:i] + rows[i + 1:]), rows[i]) for i in range(len(rows))]
            a_, tp_, fp_ = bal(loo, yy)
            out += "\n   LOO %s: bal.acc %.3f prec %.2f rec %.2f  full-data: %s" % (name, a_, tp_ / max(1, tp_ + fp_), tp_ / sum(yy), str(fit(rows))[:170])
        for th in (0.03, 0.10):
            yt = [pays(r, th) for r in A]; a_, tp_, fp_ = bal(x, yt)
            out += "\n   threshold %.0f%%: positives %d, fixed rule bal.acc %.2f prec %.2f rec %.2f" % (100 * th, sum(yt), a_, tp_ / (tp_ + fp_), tp_ / sum(yt))
        old = [1 - r["advisor"] / best(r) > .05 for r in A]
        out += "\n   old definition positives %d; removed: %s" % (sum(old), [(r["warehouses"], r["queries"], round(best(r) - r["advisor"], 2), any(len(m) > 1 for m, _, _ in r["advisor_plan"])) for r, o, n in zip(A, old, y) if o and not n])
        nm = sum(best(r) - r["advisor"] for r in A if not any(len(m) > 1 for m, _, _ in r["advisor_plan"]))
        out += "\n   saving in groups without any merge: %.2f credits of %.0f" % (nm, G)
    print(out)
summary(D + "f3.jsonl", "main", True)
for f in sorted(glob.glob(D + "f5_*.jsonl")): summary(f, os.path.basename(f)[3:-6])

print("== Table of groups where consolidation pays (paper Table V)")
A = [r for r in map(json.loads, open(D + "f3.jsonl")) if r["db"] in fz]
g = {r["db"]: best(r) - r["advisor"] for r in A}; G = sum(g.values())
for i, r in enumerate(sorted([r for r in A if pays(r)], key=lambda r: -g[r["db"]]), 1):
    print("  %2d k=%2d sizes=%-26s queries %9d best %8.1f joint %8.1f extra %5.1f%% share %5.1f%% overlap %.2f merged %s" % (i, r["warehouses"], sorted(r["sizes"]), r["queries"],
          best(r), r["advisor"], 100 * (1 - r["advisor"] / best(r)), 100 * g[r["db"]] / G, FE[r["db"]]["overlap_mean"], "+".join(str(len(m)) for m, _, _ in r["advisor_plan"] if len(m) > 1)))
