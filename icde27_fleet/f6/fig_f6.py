"""Figure for F6: metered credits of the two members run separately vs merged, per scenario, with the saving predicted
before the run and the saving Snowflake metered. Reads f6/schedule.json, sf/truth/f6_metering.csv. Writes paper/figs/merge_sf.pdf"""
import csv, json, os, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path[:0] = [ROOT, os.path.join(HERE, "..")]
import advisor as A
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
C = ["#2f6db3", "#d9822b"]
S = json.load(open(os.path.join(HERE, "schedule.json")))
ME = list(csv.DictReader(open(os.path.join(ROOT, "sf", "truth", "f6_metering.csv"))))
met = lambda w: sum(float(r["CREDITS_USED_COMPUTE"]) for r in ME if r["WAREHOUSE_NAME"] == w)
labels, sep, mer, pred = [], [], [], []
for s, sc in S["scenarios"].items():
    q = {w: [(o, d, 1, w) for o, d, who in sc["statements"] if who == w] for w in "AB"}
    pa, pb, pm = A.replay(q["A"], 1, 60)[0], A.replay(q["B"], 1, 60)[0], A.replay(q["A"] + q["B"], 1, 60)[0]
    pred.append(100 * (1 - pm / (pa + pb)))
    sep.append(met("ICDE_%s_A" % s) + met("ICDE_%s_B" % s)); mer.append(met("ICDE_%s_M" % s)); labels.append(sc["label"])
fig, ax = plt.subplots(figsize=(3.3, 1.65)); x = range(len(labels)); w = 0.36
ax.bar([i - w / 2 for i in x], sep, w, color=C[0], label="Two warehouses")
ax.bar([i + w / 2 for i in x], mer, w, color=C[1], label="Merged")
for i in x:
    ax.text(i, max(sep[i], mer[i]) + 0.08, "saved %.1f%%\n(predicted %.1f%%)" % (100 * (1 - mer[i] / sep[i]), pred[i]),
            ha="center", va="bottom", fontsize=6.5)
ax.set_xticks(list(x), [l.capitalize() for l in labels]); ax.set_ylabel("Metered credits"); ax.set_ylim(0, 2.5)
ax.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
fig.savefig(os.path.join(ROOT, "paper", "figs", "merge_sf.pdf"))
print("sep", [round(v, 3) for v in sep], "merged", [round(v, 3) for v in mer], "pred", [round(v, 1) for v in pred])
