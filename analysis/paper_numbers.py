"""Remaining numbers quoted in the paper (exploratory analyses): as-is timeout comparison, size-model accuracy,
top-8 groups table, overlap-rule errors, and joint-plan composition. Usage: python3 analysis/paper_numbers.py"""
import os, json, math, statistics as st, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
D = ROOT + "/icde27_fleet/results/"
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
A = [r for r in map(json.loads, open(D + "f3.jsonl")) if r["db"] in fz]
S4 = {r["db"]: r for r in map(json.loads, open(D + "f5_s4.jsonl")) if r["db"] in fz}
FE = {r["db"]: r for r in map(json.loads, open(D + "f4_features.jsonl"))}
best = lambda r: min(r["size_tuned"], r["suspend_tuned"])
print("== As-is timeout assumption (all 134 groups)")
for base in ("asis_600", "asis_300", "asis_60"):
    t = sum(r[base] for r in A)
    print("  vs %s: total %.0f credits; joint saves %.1f%% (per-group median %.1f%%)" % (base, t, 100 * (1 - sum(r["advisor"] for r in A) / t),
          100 * st.median([1 - r["advisor"] / r[base] for r in A])))
print("== Joint plans")
blocks = [(m, s, a) for r in A for m, s, a in r["advisor_plan"]]
print("  blocks %d, timeouts chosen %s, merged %d (pairs %d)" % (len(blocks), sorted({a for _, _, a in blocks}), sum(len(m) > 1 for m, _, _ in blocks), sum(len(m) == 2 for m, _, _ in blocks)))
C = [r for r in A if r["consolidate_all"] is not None]
print("  consolidate-all costlier than suspend-only in %d of %d groups; than default in %d" % (sum(r["consolidate_all"] > r["suspend_tuned"] * 1.0001 for r in C), len(C), sum(r["consolidate_all"] > r["asis_600"] for r in C)))
print("== Size model (alpha_fit.json)")
rows = json.load(open(ROOT + "/icde27_fleet/alpha_fit.json")); al = json.load(open(ROOT + "/icde27_fleet/alpha.json"))["alpha"]; SZ = {"SMALL": 2, "MEDIUM": 4}
err = sorted(abs(r["xs_s"] * SZ[r["size"]] ** -al[str(r["class"])] - r["t_s"]) / r["t_s"] for r in rows)
print("  %d observations from %d statements; in-sample median error %.1f%%, p90 %.1f%%" % (len(rows), len({(r["src"], r["name"]) for r in rows}), 100 * st.median(err), 100 * err[int(.9 * len(err))]))
for fit, pred in (("SMALL", "MEDIUM"), ("MEDIUM", "SMALL")):
    a2 = {c: st.median([r["alpha"] for r in rows if r["class"] == c and r["size"] == fit]) for c in range(3)}
    e = [abs(r["xs_s"] * SZ[pred] ** -a2[r["class"]] - r["t_s"]) / r["t_s"] for r in rows if r["size"] == pred]
    print("  fit on %s, predict %s: median error %.1f%%" % (fit, pred, 100 * st.median(e)))
for a in (0, 1):
    print("  alpha=%d for all: median error %.1f%%" % (a, 100 * st.median(abs(r["xs_s"] * SZ[r["size"]] ** -a - r["t_s"]) / r["t_s"] for r in rows)))
print("== Top-8 groups by consolidation saving")
g = {r["db"]: best(r) - r["advisor"] for r in A}; G = sum(g.values()); ex = {r["db"]: 1 - r["advisor"] / best(r) for r in A}
top = sorted(A, key=lambda r: -g[r["db"]])[:8]
for r in top:
    s = S4[r["db"]]; e4 = 1 - s["advisor"] / min(s["size_tuned"], s["suspend_tuned"])
    print("  k=%2d sizes=%-22s best %6.0f joint %6.0f extra %5.1f%% share %5.1f%% overlap %.2f 4-slot extra %5.1f%%" % (r["warehouses"], sorted(r["sizes"]), best(r), r["advisor"], 100 * ex[r["db"]], 100 * g[r["db"]] / G, FE[r["db"]]["overlap_mean"], 100 * e4))
print("  top-8 share %.1f%%" % (100 * sum(g[r["db"]] for r in top) / G))
print("== Overlap rule (mean overlap > 0.547) vs pays (> 5%)")
pays = {d for d in ex if ex[d] > .05}; flag = {d for d in ex if FE[d]["overlap_mean"] > 0.547}
for name, grp in (("TP", pays & flag), ("FN", pays - flag), ("FP", flag - pays)):
    print("  %s %2d: median extra %.1f%%, median overlap %.2f, median size spread %.1f, share of saving %.1f%%" % (name, len(grp), 100 * st.median(ex[d] for d in grp), st.median(FE[d]["overlap_mean"] for d in grp), st.median(FE[d]["size_spread"] for d in grp), 100 * sum(g[d] for d in grp) / G))
print("== Savings by group size")
for lab, f in (("2", lambda k: k == 2), ("3", lambda k: k == 3), ("4-6", lambda k: 4 <= k <= 6), ("7+", lambda k: k >= 7)):
    G_ = [r for r in A if f(r["warehouses"])]; t = sum(r["asis_600"] for r in G_)
    print("  k=%-3s groups %3d wh %3d suspend %.1f%% joint %.1f%% consol %.1f%% pays %d median util %.3f" % (lab, len(G_), sum(r["warehouses"] for r in G_),
          100 * (1 - sum(r["suspend_tuned"] for r in G_) / t), 100 * (1 - sum(r["advisor"] for r in G_) / t),
          100 * (1 - sum(r["advisor"] for r in G_) / sum(best(r) for r in G_)), sum(1 - r["advisor"] / best(r) > .05 for r in G_),
          st.median(FE[r["db"]]["util_mean"] for r in G_)))
def _rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r
def _sp(x, y):
    a, b = _rank(x), _rank(y); ma, mb = st.mean(a), st.mean(b)
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** .5
print("== What drives the auto-suspend saving (Spearman with per-group saving)")
y = [1 - r["suspend_tuned"] / r["asis_600"] for r in A]
for f in ("idle_share_mean", "credits60", "util_mean", "overlap_mean"):
    print("  %-16s %+.2f" % (f, _sp([FE[r["db"]][f] for r in A], y)))
print("== Greedy vs exhaustive (results/greedy_gap.jsonl)")
Gg = [json.loads(l) for l in open(D + "greedy_gap.jsonl")]
print("  groups %d; greedy == exhaustive in %d; exhaustive == main run in %d" % (len(Gg), sum(abs(r["greedy"] - r["exhaustive"]) < 1e-6 for r in Gg), sum(abs(r["recorded"] - r["exhaustive"]) < 1e-6 for r in Gg)))
print("== Greedy vs exhaustive, groups of 5-8 (results/greedy_gap_large.jsonl)")
Gl = [json.loads(l) for l in open(D + "greedy_gap_large.jsonl")]
print("  groups %d (k = %s); greedy == exhaustive in %d; greedy re-run == main run in %d; max gap %.3f%%" % (len(Gl), ",".join(str(r["k"]) for r in sorted(Gl, key=lambda r: r["k"])),
      sum(abs(r["greedy"] - r["exhaustive"]) < 1e-6 for r in Gl), sum(abs(r["recorded"] - r["greedy"]) < 1e-6 for r in Gl),
      100 * max((r["greedy"] - r["exhaustive"]) / r["exhaustive"] for r in Gl)))
print("== Proposition 1 test (results/mechanism.jsonl)")
Mm = [json.loads(l) for l in open(D + "mechanism.jsonl")]
E_ = [r for r in Mm if r["equal_size"]]; X_ = [r for r in Mm if not r["equal_size"]]
print("  merged warehouses %d (equal-size %d, mixed %d)" % (len(Mm), len(E_), len(X_)))
print("  equal-size: realised %.0f vs predicted %.0f; median ratio %.3f" % (sum(r["sep"] - r["real"] for r in E_), sum(r["overlap_term"] for r in E_),
      st.median((r["sep"] - r["real"]) / r["overlap_term"] for r in E_ if r["overlap_term"] > 1e-6)))
print("  mixed: realised %.0f vs predicted %.0f; rate change costs %.0f" % (sum(r["sep"] - r["real"] for r in X_), sum(r["ideal"] for r in X_), sum(r["overlap_term"] - r["ideal"] for r in X_)))

print("== Size scaling per statement (paper Table II)")
T = collections.defaultdict(dict)
for r in rows: T[(r["src"], r["name"])].update({"xs": r["xs_s"], r["size"]: r["t_s"], "a_" + r["size"]: r["alpha"], "c": r["class"]})
for (src, name), v in sorted(T.items(), key=lambda kv: kv[1]["xs"]):
    print("  class %d %-4s %-26s XS %6.2f  S %6.2f  M %6.2f  alpha_S %5.2f  alpha_M %5.2f" % (v["c"], src, name, v["xs"], v["SMALL"], v["MEDIUM"], v["a_SMALL"], v["a_MEDIUM"]))
