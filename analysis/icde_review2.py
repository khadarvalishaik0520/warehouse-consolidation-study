"""Responses to the second review (exploratory): fleet totals without the top group(s); rule accuracy at 3% / 10% thresholds."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json, statistics as st, sys
D = ROOT + "/icde27_fleet/results/"
fz = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
A = [r for r in map(json.loads, open(D + "f3.jsonl")) if r["db"] in fz]
FE = {r["db"]: r for r in map(json.loads, open(D + "f4_features.jsonl"))}
b = lambda r: min(r["size_tuned"], r["suspend_tuned"])
def tot(G):
    t = sum(r["asis_600"] for r in G)
    return (100 * (1 - sum(r["suspend_tuned"] for r in G) / t), 100 * (1 - sum(r["advisor"] for r in G) / t),
            100 * (1 - sum(r["advisor"] for r in G) / sum(b(r) for r in G)), sum(1 - r["advisor"] / b(r) > .05 for r in G))
gain = sorted(A, key=lambda r: -(b(r) - r["advisor"]))
for drop in (0, 1, 2):
    G = [r for r in A if r not in gain[:drop]]
    print("drop top %d: n=%d suspend %.1f joint %.1f consolidation adds %.1f%% pays %d" % ((drop, len(G)) + tot(G)))
for th in (0.03, 0.05, 0.10):
    y = [1 - r["advisor"] / b(r) > th for r in A]; x = [FE[r["db"]]["overlap_mean"] > 0.547 for r in A]
    P = sum(y); tp = sum(p and t for p, t in zip(x, y)); tn = sum((not p) and (not t) for p, t in zip(x, y)); fp = sum(p and not t for p, t in zip(x, y))
    print("threshold %.0f%%: positives %d, fixed rule bal.acc %.2f precision %.2f recall %.2f" % (100 * th, P, .5 * tp / P + .5 * tn / (len(y) - P), tp / (tp + fp), tp / P))
