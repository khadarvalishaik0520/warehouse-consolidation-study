"""Pre-registered F3 analysis (PLAN.md F3 + Addendum 1). Written before any F3 row was read.
Primary comparison: as-is at AUTO_SUSPEND 600 (Snowflake default) vs each baseline and the advisor; totals and
per-group savings. Usage: python3 analyze_f3.py <f3.jsonl>"""
import sys, json
R = [json.loads(l) for l in open(sys.argv[1])]
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else float("nan")
print("groups", len(R), " warehouses", sum(r["warehouses"] for r in R), " queries", sum(r["queries"] for r in R))
B = ("size_tuned", "suspend_tuned", "consolidate_all", "advisor")
for k in B: print("%-16s infeasible in %d groups" % (k, sum(1 for r in R if r[k] is None)))
ok = [r for r in R if all(r[k] is not None for k in B)]
print("groups where every option is feasible:", len(ok))
for base in ("asis_600", "asis_300", "asis_60"):
    tot = sum(r[base] for r in ok)
    print("\n== vs %s (total %.1f credits over two weeks)" % (base, tot))
    for k in B:
        t = sum(r[k] for r in ok); per = [1 - r[k] / r[base] for r in ok if r[base] > 0]
        print("  %-16s total %.1f  saving %.1f%%  per-group median %.1f%% (IQR %.1f–%.1f%%)"
              % (k, t, 100 * (1 - t / tot), 100 * q(per, .5), 100 * q(per, .25), 100 * q(per, .75)))
# what the advisor adds beyond the best single-knob baseline (separates consolidation from suspend/size tuning)
extra = [1 - r["advisor"] / min(r["size_tuned"], r["suspend_tuned"]) for r in ok]
merged = sum(1 for r in ok if any(len(m) > 1 for m, s, a in r["advisor_plan"]))
print("\nadvisor vs best single-knob baseline: per-group median extra saving %.1f%% (IQR %.1f–%.1f%%); "
      "groups where the advisor merges warehouses: %d/%d" % (100 * q(extra, .5), 100 * q(extra, .25), 100 * q(extra, .75), merged, len(ok)))
print("advisor method:", {m: sum(1 for r in ok if r["advisor_method"] == m) for m in ("exhaustive", "greedy")})
