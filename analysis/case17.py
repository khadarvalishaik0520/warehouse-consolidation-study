"""Case study (exploratory): the 17-warehouse group. Running periods at 60 s per warehouse vs merged plan."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import duckdb, json, sys, collections
sys.path.insert(0, ROOT); from common.billing import periods
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
D = ROOT + "/"
r = next(r for r in map(json.loads, open(D + "icde27_fleet/results/f3.jsonl")) if r["warehouses"] == 17)
X = D + "data/extracts/group_%s.parquet" % r["db"]          # small extract shipped with the repo (same rows as Snowset)
size = dict(duckdb.connect().execute(f"select distinct wh, size_min from read_parquet('{X}')").fetchall())
iv = collections.defaultdict(list)
for w, s, e in duckdb.connect().execute(f"select wh, s, e from read_parquet('{X}') order by wh, s").fetchall(): iv[w].append((s, e))
P = {w: periods(v, 60) for w, v in iv.items()}
t0 = min(p[0][0] for p in P.values()); t1 = max(p[-1][1] for p in P.values())
# concurrency: how many member warehouses are running, time-weighted
ev = sorted([(a, 1) for p in P.values() for a, _ in p] + [(b, -1) for p in P.values() for _, b in p])
n = 0; prev = ev[0][0]; acc = collections.Counter()
for t, d in ev:
    acc[n] += t - prev; n += d; prev = t
busy = sum(v for k, v in acc.items() if k > 0)
print("span days %.1f; time any running %.1f%%; time-weighted mean warehouses running when any %.2f; share of running time with >=4 running %.1f%%"
      % ((t1 - t0) / 86400, 100 * busy / (t1 - t0), sum(k * v for k, v in acc.items()) / busy, 100 * sum(v for k, v in acc.items() if k >= 4) / busy))
sep = sum(sum(b - a for a, b in p) for p in P.values()); sep_cr = sum(sum(b - a for a, b in p) * size[w] for w, p in P.items()) / 3600
print("sum of separate running hours %.0f, credit-weighted %.0f credits (replay suspend_tuned %.0f)" % (sep / 3600, sep_cr, r["suspend_tuned"]))
for m, s, a in r["advisor_plan"]:
    u = periods(sorted(x for w in m for x in iv[w]), 60)
    print("block size %s members %d sizes %s merged running h %.0f vs separate %.0f" % (s, len(m), sorted(size[w] for w in m), sum(b - a for a, b in u) / 3600, sum(sum(b - a for a, b in P[w]) for w in m) / 3600))
# figure: one 6-hour window on a weekday with heavy activity
day = t0 + 3 * 86400; W0, W1 = day + 8 * 3600, day + 14 * 3600
order = [w for m, _, _ in r["advisor_plan"] for w in m]; col = {}
C = ["#2f6db3", "#d9822b", "#3a9e5b"]
for i, (m, _, _) in enumerate(r["advisor_plan"]):
    for w in m: col[w] = C[i]
fig, ax = plt.subplots(figsize=(3.4, 2.4)); y = 0
for i, (m, s, _) in enumerate(r["advisor_plan"]):
    u = periods(sorted(x for w in m for x in iv[w]), 60)
    for a, b in u:
        if b > W0 and a < W1: ax.barh(y, (min(b, W1) - max(a, W0)) / 3600, left=(max(a, W0) - W0) / 3600, height=0.8, color=C[i], edgecolor="none")
    ax.text(-0.08, y, "merged %s" % "ABC"[i], ha="right", va="center", fontsize=6); y += 1
y += 0.6
for w in order:
    for a, b in P[w]:
        if b > W0 and a < W1: ax.barh(y, (min(b, W1) - max(a, W0)) / 3600, left=(max(a, W0) - W0) / 3600, height=0.7, color=col[w], alpha=0.55, edgecolor="none")
    y += 1
ax.text(-0.08, (y + 3.6) / 2, "17 original\nwarehouses", ha="right", va="center", fontsize=6)
ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.set_xlim(0, 6); ax.set_ylim(-0.7, y)
ax.set_xlabel("Hours within one six-hour window")
fig.savefig(ROOT + "/paper/figs/case17.pdf"); print("window starts day 3 08:00 UTC of trace")
