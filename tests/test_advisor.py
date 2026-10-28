import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "icde27_fleet"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from advisor import replay, as_is, advise, set_partitions, p95
from common.billing import billed_seconds
# 1) single query, no contention: billed = exec + auto (>= 60), latency = exec + resume delay
b, lat, iv = replay([(0.0, 10.0, 1, "a")], 1, 60)
assert abs(b - 71.0) < 1e-9 and abs(lat[0] - 11.0) < 1e-9, (b, lat)
# 2) more than 8 concurrent queries queue
q = [(0.0, 10.0, 1, "a")] * 9
b, lat, _ = replay(q, 1, 60); assert max(lat) > 20 and min(lat) < 12
# 3) Bell numbers
assert [sum(1 for _ in set_partitions(list(range(n)))) for n in range(1, 6)] == [1, 2, 5, 15, 52]
# 4) two sparse warehouses on opposite schedules: merging should save (idle tails shared) while meeting targets
rng = random.Random(5); W = {}
for w, off in (("a", 0), ("b", 30)):
    W[w] = [(h * 3600 + off + rng.uniform(0, 5), rng.uniform(1, 5), 1, w) for h in range(48)]
sizes0 = {"a": 1, "b": 1}
base = as_is(W, sizes0, 600); targets = {w: 1.2 * base[w][1] for w in W}
res = advise(W, sizes0, targets)
print("as-is credits:", round(sum(v[0] for v in base.values()), 3), " advisor:", round(res[0], 3), res[1], res[2])
assert res[0] <= sum(v[0] for v in base.values()) + 1e-9
# 5) greedy path runs on 5 warehouses
W5 = {w: [(h * 3600 + i * 10 + rng.uniform(0, 3), 2.0, 1, w) for h in range(10)] for i, w in enumerate("abcde")}
b5 = as_is(W5, {w: 1 for w in W5}, 600); r5 = advise(W5, {w: 1 for w in W5}, {w: 1.2 * b5[w][1] for w in W5})
print("greedy 5:", round(sum(v[0] for v in b5.values()), 3), "->", round(r5[0], 3), r5[2], len(r5[1]), "blocks")
# 6) the 60 s minimum in the replay: binds when auto < 60, never when auto >= 60 (every option the paper evaluates)
from common.billing import periods, MIN_BILL
from advisor import AUTOS
rng6 = random.Random(6)
for trial in range(200):
    q = sorted((rng6.uniform(0, 7200), rng6.choice([0.2, 1, 5, 30, 120]), 1, "x") for _ in range(rng6.randint(1, 60)))
    for auto in (0, 10, 30) + AUTOS:
        b, _, iv = replay(q, 1, auto)
        P = periods(iv, auto)
        assert abs(b - sum(max(MIN_BILL, e - s) for s, e in P)) < 1e-6          # replay bills each period with the minimum
        if auto >= 60:
            assert min(e - s for s, e in P) >= 60 - 1e-9 and abs(b - sum(e - s for s, e in P)) < 1e-6   # minimum never binds
b0, _, _ = replay([(0, 1.0, 1, "x")], 1, 0)
assert abs(b0 - 60) < 1e-9                                                     # a 1 s query at auto 0 is billed 60 s
print("60 s minimum: binds only below 60 s auto-suspend; checked on 200 random workloads x 6 timeouts")
print("ADVISOR TESTS PASSED")
