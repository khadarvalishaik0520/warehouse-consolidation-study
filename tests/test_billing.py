import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.billing import periods, billed_seconds, busy_seconds
assert billed_seconds([(0, 10)], 60) == 70
assert billed_seconds([(0, 1)], 0) == 60                 # the 60 s minimum binds
assert billed_seconds([(0, 10), (50, 60)], 60) == 120    # second query arrives before suspend: one period 0..120
assert billed_seconds([(0, 10), (200, 210)], 60) == 140  # two periods of 70
assert periods([(0, 10), (200, 210)], 60) == [(0, 70), (200, 270)]
assert busy_seconds([(0, 10), (5, 12), (20, 21)]) == 13
print("BILLING TESTS PASSED")
