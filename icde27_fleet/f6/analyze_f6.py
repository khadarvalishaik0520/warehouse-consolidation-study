"""F6 analysis (PLAN.md Addendum 8). Per scenario: the saving from merging two warehouses, as predicted by the replay
before the run, by the billing model on the statements Snowflake actually executed, by Snowflake's resume/suspend
events, and by Snowflake's metered compute credits. Usage: python3 icde27_fleet/f6/analyze_f6.py [--predict-only]"""
import csv, glob, json, os, sys
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", ".."); sys.path[:0] = [ROOT, os.path.join(HERE, "..")]
from common.billing import billed_seconds
import advisor as A
S = json.load(open(os.path.join(HERE, "schedule.json"))); AUTO = 60
P = lambda x: datetime.fromisoformat(x).timestamp()

def predicted(sc):
    """Replay of the schedule at X-Small (8 slots, 1 s billed resume delay), billed seconds per warehouse."""
    q = {w: [(o, d, 1, w) for o, d, who in sc["statements"] if who == w] for w in ("A", "B")}
    out = {w: A.replay(q[w], 1, AUTO)[0] for w in ("A", "B")}; out["M"] = A.replay(q["A"] + q["B"], 1, AUTO)[0]
    return out

def line(label, v):
    sep = v["A"] + v["B"]; f = "%7.4f" if "credits" in label else "%7.1f"
    return ("  %-34s A " + f + "  B " + f + "  A+B " + f + "  merged " + f + "  saving " + f + " (%5.1f%%)") % (
        label, v["A"], v["B"], sep, v["M"], sep - v["M"], 100 * (sep - v["M"]) / sep)

pred = {s: predicted(sc) for s, sc in S["scenarios"].items()}
if "--predict-only" in sys.argv:
    for s in S["scenarios"]: print(s, S["scenarios"][s]["label"]); print(line("predicted billed minutes", {k: v / 60 for k, v in pred[s].items()}))
    sys.exit()
T = os.path.join(ROOT, "sf", "truth")
QH = list(csv.DictReader(open(os.path.join(T, "f6_query_history.csv"))))
EV = sorted(csv.DictReader(open(os.path.join(T, "f6_events.csv"))), key=lambda r: P(r["TIMESTAMP"]))
ME = list(csv.DictReader(open(os.path.join(T, "f6_metering.csv"))))
runs = [json.loads(l) for f in glob.glob(os.path.join(ROOT, "sf", "runs", "f6_*.jsonl")) for l in open(f)]
sent = [r for r in runs if "qid" in r and r.get("ok")]; ids = {r["qid"] for r in sent}
print("statements sent %d, failed to send %d, median lateness %.2f s, max %.2f s" % (len(sent), sum(1 for r in runs if r.get("ok") is False),
      sorted(r["late"] for r in sent)[len(sent) // 2], max(r["late"] for r in sent)))
for s, sc in S["scenarios"].items():
    print("\n%s - %s" % (s, sc["label"]))
    real, evs, met, queued, fails = {}, {}, {}, 0.0, 0
    for x in ("A", "B", "M"):
        w = "ICDE_%s_%s" % (s, x)
        q = [r for r in QH if r["WAREHOUSE_NAME"] == w and r["QUERY_ID"] in ids]
        fails += sum(r["EXECUTION_STATUS"] != "SUCCESS" for r in q)
        queued += sum(float(r["QUEUED_OVERLOAD_TIME"] or 0) for r in q) / 1000
        real[x] = billed_seconds([(P(r["END_TIME"]) - float(r["EXECUTION_TIME"]) / 1000, P(r["END_TIME"])) for r in q], AUTO)
        cur, tot = None, 0.0
        for r in EV:
            if r["WAREHOUSE_NAME"] != w: continue
            # Snowflake logs these two events with state STARTED (as in F1's validate_f1.py); the first version of this
            # script filtered on COMPLETED and found none -- fixed before any metered number was read
            if r["EVENT_NAME"] == "RESUME_WAREHOUSE": cur = P(r["TIMESTAMP"])
            elif r["EVENT_NAME"] == "SUSPEND_WAREHOUSE" and cur is not None:
                tot += max(60.0, P(r["TIMESTAMP"]) - cur); cur = None
        evs[x] = tot; met[x] = sum(float(r["CREDITS_USED_COMPUTE"]) for r in ME if r["WAREHOUSE_NAME"] == w)
    print("  statements failed %d, total queued for overload %.1f s" % (fails, queued))
    print(line("predicted before the run (min)", {k: v / 60 for k, v in pred[s].items()}))
    print(line("model on executed statements (min)", {k: v / 60 for k, v in real.items()}))
    print(line("Snowflake resume/suspend events (min)", {k: v / 60 for k, v in evs.items()}))
    print(line("Snowflake metered credits", met))
    print("  implied credits per running hour: " + "  ".join("%s %.3f" % (x, met[x] / (evs[x] / 3600)) for x in ("A", "B", "M") if evs[x]))
