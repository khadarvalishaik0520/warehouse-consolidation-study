"""F7 analysis (PLAN.md Addendum 7): fit the overlap rule on week 1, test it on week 2; act on week-1 plans in week 2.
Usage: python3 icde27_fleet/f7/analyze_split.py [split.jsonl]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "split.jsonl"))]
skip = [r for r in R if "skip" in r]; R = [r for r in R if "skip" not in r]
best = lambda o: min(o["size_tuned"], o["suspend_tuned"])
def pays(o): return (any(len(m) > 1 for m, _, _ in o["plan"]) and best(o) - o["advisor"] >= 0.5
                     and 1 - o["advisor"] / best(o) > 0.05)
def score(pred, y):
    tp = sum(p and t for p, t in zip(pred, y)); fp = sum(p and not t for p, t in zip(pred, y))
    fn = sum(t and not p for p, t in zip(pred, y)); tn = len(y) - tp - fp - fn
    rec = tp / (tp + fn) if tp + fn else 0.0; spec = tn / (tn + fp) if tn + fp else 0.0
    return (rec + spec) / 2, (tp / (tp + fp) if tp + fp else float("nan")), rec, tp, fp, fn
y1 = [pays(r["w1"]) for r in R]; y2 = [pays(r["w2"]) for r in R]
x1 = [r["f1"]["overlap_mean"] for r in R]; x2 = [r["f2"]["overlap_mean"] for r in R]
print("groups %d analysed, %d excluded (a warehouse runs nothing in one week)" % (len(R), len(skip)))
print("pays: week 1 %d, week 2 %d, both %d" % (sum(y1), sum(y2), sum(a and b for a, b in zip(y1, y2))))
cands = sorted(set(x1))
th = max(cands, key=lambda t: (score([x > t for x in x1], y1)[0], -t))      # ties -> lowest threshold
print("threshold fitted on week 1: overlap > %.3f (week-1 in-sample bal.acc %.2f)" % (th, score([x > th for x in x1], y1)[0]))
for name, t in (("week-1 threshold", th), ("full-trace threshold 0.617", 0.617)):
    b, p, rc, tp, fp, fn = score([x > t for x in x1], y2)
    print("  %-28s week-1 features -> week-2 labels: bal.acc %.2f  precision %.2f  recall %.2f  (TP %d FP %d FN %d)" % (name, b, p, rc, tp, fp, fn))
b, p, rc, *_ = score([x > 0.617 for x in x2], y2)
print("  reference: week-2 features -> week-2 labels at 0.617: bal.acc %.2f precision %.2f recall %.2f" % (b, p, rc))
# act on history
flag = [x > th for x in x1]
cost = sum(r["w2_with_w1_plan"][0] if f else r["w2_with_w1_susp"][0] for r, f in zip(R, flag))
miss = sum(not (r["w2_with_w1_plan"][1] if f else r["w2_with_w1_susp"][1]) for r, f in zip(R, flag))
susp = sum(r["w2_with_w1_susp"][0] for r in R); orac = sum(r["w2"]["advisor"] for r in R)
orac_single = sum(best(r["w2"]) for r in R); asis = sum(r["w2"]["asis_600"] for r in R)
print("week 2 billed credits: as-is %.0f | week-1 timeouts everywhere %.0f | rule + week-1 plans %.0f | oracle best single knob %.0f | oracle joint %.0f"
      % (asis, susp, cost, orac_single, orac))
print("  consolidation saving captured by acting on week 1: %.0f of the oracle's %.0f credits (%.0f%%); vs week-1 timeouts %.0f credits"
      % (susp - cost, susp - orac, 100 * (susp - cost) / (susp - orac) if susp > orac else float("nan"), susp - cost))
allplan = sum(r["w2_with_w1_plan"][0] for r in R)
print("  week-1 joint plans everywhere (no rule): %.0f credits; groups missing a latency target: rule %d, all plans %d, timeouts %d"
      % (allplan, miss, sum(not r["w2_with_w1_plan"][1] for r in R), sum(not r["w2_with_w1_susp"][1] for r in R)))
# coverage: how much of the full-trace consolidation saving sits in the analysed groups
F3 = os.environ.get("F3", os.path.join(HERE, "..", "results", "f3.jsonl"))
if os.path.exists(F3):
    T = {json.loads(l)["db"]: json.loads(l) for l in open(F3)}; inc = {r["db"] for r in R}; allg = inc | {r["db"] for r in skip}
    g = {d: max(0.0, min(T[d]["size_tuned"], T[d]["suspend_tuned"]) - T[d]["advisor"]) for d in allg}
    pf = lambda t: (any(len(m) > 1 for m, _, _ in t["advisor_plan"]) and min(t["size_tuned"], t["suspend_tuned"]) - t["advisor"] >= 1
                    and 1 - t["advisor"] / min(t["size_tuned"], t["suspend_tuned"]) > 0.05)
    print("coverage: analysed groups hold %.1f%% of the full-trace consolidation saving; %d of the %d full-trace paying groups"
          % (100 * sum(g[d] for d in inc) / sum(g.values()), sum(pf(T[d]) for d in inc), sum(pf(T[d]) for d in allg)))
