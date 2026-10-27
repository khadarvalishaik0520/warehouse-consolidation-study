"""F4 analysis (Addendum 4). Usage: python3 analyze_f4.py <f3.jsonl> <f4_features.jsonl> <frozen dbs file>"""
import sys, json, math
F3 = {json.loads(l)["db"]: json.loads(l) for l in open(sys.argv[1])}
FE = {json.loads(l)["db"]: json.loads(l) for l in open(sys.argv[2])}
frozen = set(open(sys.argv[3]).read().split())
B = ("size_tuned", "suspend_tuned", "consolidate_all", "advisor")
rows = []
for db in sorted(frozen):
    r = F3[db]
    if any(r[k] is None for k in B) or db not in FE: continue
    best1 = min(r["size_tuned"], r["suspend_tuned"]); extra = 1 - r["advisor"] / best1
    x = dict(FE[db]); x["extra"] = extra; x["pays"] = extra > 0.05; rows.append(x)
FEATS = [k for k in rows[0] if k not in ("db", "extra", "pays")]
print("groups", len(rows), "PAYS", sum(r["pays"] for r in rows))
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
    for p, i in enumerate(o): r[i] = p
    return r
def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma = mb = (n - 1) / 2
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0
def bal(pred, y):
    tp = sum(p and t for p, t in zip(pred, y)); tn = sum((not p) and (not t) for p, t in zip(pred, y))
    P = sum(y); N = len(y) - P
    return 0.5 * (tp / P if P else 0) + 0.5 * (tn / N if N else 0)
def best_stump(R, feats):
    best = None; y = [r["pays"] for r in R]
    for f in feats:
        vals = sorted({r[f] for r in R})
        for i in range(len(vals) - 1):
            th = (vals[i] + vals[i + 1]) / 2
            for sign in (1, -1):
                pred = [(r[f] > th) if sign == 1 else (r[f] <= th) for r in R]; b = bal(pred, y)
                if best is None or b > best[0]: best = (b, f, th, sign)
    return best
def stump_pred(st, r):
    _, f, th, sign = st; return (r[f] > th) if sign == 1 else (r[f] <= th)
def best_tree(R, feats, minleaf=5):
    root = best_stump(R, feats)
    if root is None: return None
    left = [r for r in R if not stump_pred(root, r)]; right = [r for r in R if stump_pred(root, r)]
    def leaf(S):
        if len(S) < 2 * minleaf or all(r["pays"] == S[0]["pays"] for r in S): return ("leaf", sum(r["pays"] for r in S) * 2 > len(S))
        st = best_stump(S, feats)
        if st is None: return ("leaf", sum(r["pays"] for r in S) * 2 > len(S))
        a = [r for r in S if stump_pred(st, r)]; b = [r for r in S if not stump_pred(st, r)]
        if len(a) < minleaf or len(b) < minleaf: return ("leaf", sum(r["pays"] for r in S) * 2 > len(S))
        return ("split", st, ("leaf", sum(r["pays"] for r in a) * 2 > len(a)), ("leaf", sum(r["pays"] for r in b) * 2 > len(b)))
    return ("split", root, leaf(right), leaf(left))
def tree_pred(t, r):
    if t[0] == "leaf": return t[1]
    _, st, yes, no = t; return tree_pred(yes if stump_pred(st, r) else no, r)
print("\nSpearman with extra saving (secondary outcome):")
for f in FEATS: print("  %-22s %+.2f" % (f, spearman([r[f] for r in rows], [r["extra"] for r in rows])))
y = [r["pays"] for r in rows]
for name, fit, pred in (("single feature", lambda R: best_stump(R, FEATS), stump_pred), ("depth-2 tree", lambda R: best_tree(R, FEATS), tree_pred)):
    loo = []
    for i in range(len(rows)):
        m = fit(rows[:i] + rows[i + 1:]); loo.append(pred(m, rows[i]))
    tp = sum(p and t for p, t in zip(loo, y)); fp = sum(p and not t for p, t in zip(loo, y))
    print("\n%s: LOO balanced accuracy %.3f, precision %.2f, recall %.2f (tp %d fp %d of %d PAYS)"
          % (name, bal(loo, y), tp / (tp + fp) if tp + fp else 0, tp / sum(y), tp, fp, sum(y)))
    full = fit(rows); print("   full-data rule:", full)
