"""Fleet advisor (ICDE paper). Pure functions; design frozen in PLAN.md Addendum 1.
A query = (arrival, exec_seconds_at_original_size, original_size, origin_warehouse).
Arrival = observed execution start in Snowset (original queueing is folded into the arrival; documented limitation)."""
import heapq, os, sys
from itertools import combinations
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.billing import billed_seconds

SLOTS, RESUME_DELAY, AUTOS = 8, 1.0, (60, 300, 600)
ALPHA = {0: 0.5, 1: 0.5, 2: 0.5, 3: 0.5}          # placeholder until fitted on F2 (never reported)

def cls(x):
    return 0 if x < 1 else 1 if x < 10 else 2 if x < 60 else 3

def scaled(x, s_old, s_new, alpha=ALPHA):
    return x * (s_old / float(s_new)) ** alpha[cls(x)]

def replay(queries, size, auto, slots=SLOTS, resume=RESUME_DELAY, alpha=ALPHA):
    """FIFO multi-slot replay on one warehouse. Returns (billed_seconds, latency list per query in input order,
    exec intervals). Suspend happens auto seconds after the last running query ends."""
    order = sorted(range(len(queries)), key=lambda i: queries[i][0])
    free = [0.0] * slots; heapq.heapify(free)          # slot free times
    lat = [0.0] * len(queries); iv = []
    up_from, up_until = -1e18, -1e18                    # warehouse usable from / stays up until (end + auto)
    for i in order:
        a, x, s_old, _ = queries[i]
        d = scaled(x, s_old, size, alpha)
        start = max(a, heapq.heappop(free)); billed_from = start
        if start > up_until:                            # suspended -> resume (delay is billed)
            up_from = start + resume
        start = max(start, up_from)
        end = start + d; heapq.heappush(free, end)
        up_until = max(up_until, end + auto); lat[i] = end - a
        iv.append((min(billed_from, start), end))
    return billed_seconds(iv, auto), lat, iv

def p95(v):
    if not v: return 0.0
    v = sorted(v); return v[min(len(v) - 1, int(0.95 * (len(v) - 1) + 0.5))]

def cost_credits(billed_s, size):
    return billed_s / 3600.0 * size

def evaluate_block(W, members, size, auto, targets, **kw):
    """W: dict wh -> query list. members: warehouses sharing one new warehouse. Returns (credits, ok, worst ratio)."""
    q = [x for w in members for x in W[w]]
    b, lat, _ = replay(q, size, auto, **kw)
    ok, worst, k = True, 0.0, 0
    for w in members:
        n = len(W[w]); r = p95(lat[k:k + n]) / max(targets[w], 1e-9); k += n
        worst = max(worst, r); ok = ok and r <= 1.0
    return cost_credits(b, size), ok, worst

def best_block(W, members, sizes0, targets, **kw):
    """Cheapest feasible (size, auto) for one block. Sizes = {s/2, s, 2s} of the members' original sizes."""
    cand = sorted({c for w in members for c in (sizes0[w] / 2.0, sizes0[w], sizes0[w] * 2.0) if c >= 1})
    best = None
    for size in cand:
        for auto in AUTOS:
            c, ok, worst = evaluate_block(W, members, size, auto, targets, **kw)
            if ok and (best is None or c < best[0]): best = (c, size, auto)
    return best

def as_is(W, sizes0, auto, **kw):
    out = {}
    for w in W:
        b, lat, _ = replay(W[w], sizes0[w], auto, **kw)
        out[w] = (cost_credits(b, sizes0[w]), p95(lat))
    return out

def set_partitions(items):
    if len(items) == 1:
        yield [items]; return
    first, rest = items[0], items[1:]
    for p in set_partitions(rest):
        for i in range(len(p)):
            yield p[:i] + [[first] + p[i]] + p[i + 1:]
        yield [[first]] + p

def advise(W, sizes0, targets, exhaustive_max=4, **kw):
    """Returns (credits, partition [(members, size, auto)], method)."""
    whs = sorted(W); memo = {}
    def blk(m):
        key = tuple(sorted(m))
        if key not in memo: memo[key] = best_block(W, list(key), sizes0, targets, **kw)
        return memo[key]
    if len(whs) <= exhaustive_max:
        best = None
        for p in set_partitions(whs):
            bl = [blk(m) for m in p]
            if any(b is None for b in bl): continue
            c = sum(b[0] for b in bl)
            if best is None or c < best[0]: best = (c, [(tuple(sorted(m)), b[1], b[2]) for m, b in zip(p, bl)], "exhaustive")
        return best
    part = [[w] for w in whs]                            # greedy pairwise merging
    while True:
        cur = {tuple(sorted(m)): blk(m) for m in part}
        best_gain, best_pair = 0.0, None
        for a, b in combinations(range(len(part)), 2):
            mb = blk(part[a] + part[b])
            if mb is None: continue
            ca, cb = cur[tuple(sorted(part[a]))], cur[tuple(sorted(part[b]))]
            if ca is None or cb is None: continue
            gain = ca[0] + cb[0] - mb[0]
            if gain > best_gain: best_gain, best_pair = gain, (a, b)
        if best_pair is None: break
        a, b = best_pair; part[a] = part[a] + part[b]; del part[b]
    bl = [blk(m) for m in part]
    if any(b is None for b in bl): return None
    return (sum(b[0] for b in bl), [(tuple(sorted(m)), b[1], b[2]) for m, b in zip(part, bl)], "greedy")
