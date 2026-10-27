"""ICDE figures from the result files only (frozen 134 groups)."""
import os as _os
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
U = ROOT + "/icde27_fleet/results/"
plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
C = ["#2f6db3", "#d9822b", "#3a9e5b", "#b0413e", "#7a5aa6"]; INK = "#222222"
fro = set(open(ROOT + "/icde27_fleet/frozen_groups.txt").read().split())
R = [json.loads(l) for l in open(U + "f3.jsonl")]; R = [r for r in R if r["db"] in fro]
B = ("size_tuned", "suspend_tuned", "consolidate_all", "advisor")
ok = [r for r in R if None not in (r["size_tuned"], r["suspend_tuned"], r["advisor"])]  # all 134 (Deviation 7)
okC = [r for r in ok if r["consolidate_all"] is not None]  # consolidate-all feasible (131)
FE = {json.loads(l)["db"]: json.loads(l) for l in open(U + "f4_features.jsonl")}
# Fig 1: total savings vs as-is at 600 s
base = sum(r["asis_600"] for r in ok)
lab = ["Resize\nonly", "Tune\nauto-suspend", "Consolidate\nall$^*$", "Joint search\n(all knobs)"]
val = [100 * (1 - sum(r[k] for r in (okC if k == "consolidate_all" else ok)) / sum(r["asis_600"] for r in (okC if k == "consolidate_all" else ok))) for k in B]
fig, ax = plt.subplots(figsize=(3.3, 1.55))
bars = ax.bar(range(4), val, color=[C[4], C[0], C[1], C[2]], width=0.6)
for i, v in enumerate(val): ax.text(i, v + 1, "%.1f%%" % v, ha="center", fontsize=7)
ax.set_xticks(range(4), lab, fontsize=7); ax.set_ylabel("Billed compute saved\nvs. default settings (%)"); ax.set_ylim(0, 45)
fig.savefig(ROOT + "/paper/figs/f3_savings.pdf")
# Fig 2: extra saving over best single knob vs overlap
x = [FE[r["db"]]["overlap_mean"] for r in ok]
y = [100 * (1 - r["advisor"] / min(r["size_tuned"], r["suspend_tuned"])) for r in ok]
fig, ax = plt.subplots(figsize=(3.3, 1.75))
ax.scatter(x, y, s=7, c=[C[3] if v > 5 else C[0] for v in y], alpha=0.8, linewidths=0)
ax.axvline(0.547, color=INK, lw=0.7, ls="--"); ax.axhline(5, color="#999999", lw=0.6, ls=":")
ax.text(0.56, max(y) * 0.92, "overlap > 0.55", fontsize=7); ax.text(0.01, 6.2, "5% threshold", fontsize=6, color="#666666")
ax.set_xlabel("Mean overlap of members' running periods"); ax.set_ylabel("Extra saving from\nconsolidation (%)")
ax.set_xlim(-0.02, 1.02); fig.savefig(ROOT + "/paper/figs/f4_overlap.pdf")
print("n", len(ok), "vals", [round(v, 1) for v in val], "pays", sum(v > 5 for v in y))
# Fig: per-group saving vs default, suspend-only vs joint search (CDF over groups)
fig, ax = plt.subplots(figsize=(3.3, 1.6))
for k, lab_, c in (("suspend_tuned", "Tune auto-suspend", C[0]), ("advisor", "Joint search", C[2])):
    v = sorted(100 * (1 - r[k] / r["asis_600"]) for r in ok)
    ax.step(v, [(i + 1) / len(v) for i in range(len(v))], where="post", color=c, label=lab_, lw=1.2)
ax.set_xlabel("Group's billed compute saved vs. default (%)"); ax.set_ylabel("Share of groups")
ax.set_xlim(0, 100); ax.set_ylim(0, 1.02); ax.legend(frameon=False, fontsize=7, loc="upper left")
fig.savefig(ROOT + "/paper/figs/f3_cdf.pdf")
