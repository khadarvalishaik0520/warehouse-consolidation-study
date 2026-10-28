"""Exploratory figure: an idle pair that takes turns (overlap 0) -- tuning auto-suspend removes its tails; merging saves nothing."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import duckdb, json, sys
sys.path.insert(0, ROOT); from common.billing import periods
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
D = ROOT + "/"; DB = sys.argv[1] if len(sys.argv) > 1 else "8858239961191194931"
con = duckdb.connect()
X = D + "data/extracts/group_%s.parquet" % DB                 # small extract shipped with the repo (same rows as Snowset)
whs = [w for (w,) in con.execute(f"select distinct wh from read_parquet('{X}') order by wh").fetchall()]
iv = {w: con.execute(f"select s, e from read_parquet('{X}') where wh = ? order by s", [w]).fetchall() for w in whs}
print({w: len(v) for w, v in iv.items()})
t0 = min(v[0][0] for v in iv.values())
# choose the busiest 12-hour window
allq = sorted(s for v in iv.values() for s, _ in v); best = max(range(len(allq)), key=lambda i: sum(1 for x in allq[i:i + 400] if x - allq[i] < 43200))
W0 = allq[best]; W1 = W0 + 12 * 3600
C = ["#2f6db3", "#d9822b"]
fig, ax = plt.subplots(figsize=(3.4, 1.55)); y = 0; labels = []
for a, tag in ((600, "600 s"), (60, "60 s")):
    for i, w in enumerate(whs):
        for p, q in periods(iv[w], a):
            if q > W0 and p < W1: ax.barh(y, (min(q, W1) - max(p, W0)) / 3600, left=(max(p, W0) - W0) / 3600, height=0.7, color=C[i], alpha=0.75, edgecolor="none")
        labels.append((y, "WH %s, %s" % ("AB"[i], tag))); y += 1
    y += 0.5
for yy, l in labels: ax.text(-0.15, yy, l, ha="right", va="center", fontsize=6.5)
ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.set_xlim(0, 12); ax.set_xlabel("Hours within one 12-hour window"); ax.invert_yaxis()
fig.savefig(ROOT + "/paper/figs/turns.pdf")
for a in (600, 60):
    P = {w: periods(iv[w], a) for w in whs}; sep = sum(q - p for w in whs for p, q in P[w]); un = sum(q - p for p, q in periods(sorted(x for v in iv.values() for x in v), a))
    print("auto %d: separate running %.1f h, merged %.1f h, overlap %.2f h" % (a, sep / 3600, un / 3600, (sep - un) / 3600))
