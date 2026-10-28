"""ICDE F6 (PLAN.md Addendum 8): a real merge on Snowflake. Three scenarios, each a 90-minute window of a same-size
warehouse pair from Snowset, replayed at X-Small with AUTO_SUSPEND = 60 on three warehouses at once:
the two members separately (<S>_A, <S>_B) and both together on one warehouse (<S>_M). Scenarios: HO (high overlap),
PO (partial overlap), TT (turn-taking). Each statement is GENERATOR(TIMELIMIT => d), d = the Snowset duration rounded to whole seconds.
Statements are submitted asynchronously at their scheduled offsets; nothing waits for results.

  python sf_f6.py check   three timed statements on ICDE_SUSP (1, 5, 20 s; < 0.05 credits)
  python sf_f6.py dry     prints what run would send (no connection)
  python sf_f6.py run     all three scenarios together, about 95 minutes; writes sf/runs/f6_<ts>.jsonl
Credentials only from ~/.snowflake/connections.toml [cdexp]."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "sf"))
from sf_wcp import connect
SCHED = json.load(open(os.path.join(HERE, "f6", "schedule.json")))
OUT = os.path.join(HERE, "..", "sf", "runs"); os.makedirs(OUT, exist_ok=True)
SQL = "select count(*) /* f6 {tag} {i} */ from table(generator(timelimit => {d}))"
WH = ["ICDE_%s_%s" % (s, x) for s in SCHED["scenarios"] for x in "ABM"]

def check():
    con = connect("ICDE_SUSP", "wcp_f6_check", schema="TPCH"); cur = con.cursor()
    for d in (1, 5, 20):
        t = time.time(); cur.execute(SQL.format(tag="check", i=d, d=d)); cur.fetchall(); qid = cur.sfqid
        cur.execute("select execution_time, total_elapsed_time from table(information_schema.query_history_by_session()) "
                    "where query_id = %s", (qid,)); r = cur.fetchone()
        print("timelimit %2d s: client %.2f s, execution %.2f s, elapsed %.2f s" % (d, time.time() - t, r[0] / 1000, r[1] / 1000))
    cur.execute("alter warehouse ICDE_SUSP suspend"); con.close(); print("F6 CHECK DONE")

def jobs_list():
    jobs = []
    for s, sc in SCHED["scenarios"].items():
        for i, (off, d, who) in enumerate(sc["statements"]):
            jobs.append((off, "ICDE_%s_%s" % (s, who), s, i, d)); jobs.append((off, "ICDE_%s_M" % s, s, i, d))
    return sorted(jobs)

def dry():
    j = jobs_list(); print(len(j), "statements on", sorted({w for _, w, *_ in j}), "last offset %.0f s, schedule %s" % (j[-1][0], SCHED["sha"]))

def run():
    cons = {w: connect(w, "wcp_f6_" + w, schema="TPCH") for w in WH}
    for w, c in cons.items():                      # same starting state: suspended, 60 s, X-Small
        cur = c.cursor(); cur.execute("alter warehouse %s set warehouse_size = xsmall auto_suspend = 60 auto_resume = true" % w)
        try: cur.execute("alter warehouse %s suspend" % w)
        except Exception: pass
    jobs = jobs_list(); f = open(os.path.join(OUT, "f6_%d.jsonl" % time.time()), "a")
    time.sleep(90); T0 = time.time() + 5
    f.write(json.dumps({"T0": T0, "schedule_sha": SCHED["sha"]}) + "\n"); f.flush()
    print("start at", time.strftime("%H:%M:%S", time.localtime(T0)), "-", len(jobs), "statements, ends about",
          time.strftime("%H:%M", time.localtime(T0 + SCHED["window_s"] + 120)), flush=True)
    for n, (off, w, s, i, d) in enumerate(jobs):
        dt = T0 + off - time.time()
        if dt > 0: time.sleep(dt)
        cur = cons[w].cursor(); t = time.time()
        try:
            cur.execute_async(SQL.format(tag=w, i=i, d=d)); r = {"ok": True, "qid": cur.sfqid}
        except Exception as e:
            r = {"ok": False, "err": str(e)[:200]}
        r.update({"wh": w, "scenario": s, "i": i, "off": off, "d": d, "sent": t, "late": t - (T0 + off)})
        f.write(json.dumps(r) + "\n"); f.flush()
        if n % 50 == 0: print("%5d/%d  t+%5.0f s  late %.2f s" % (n, len(jobs), t - T0, r["late"]), flush=True)
    time.sleep(SCHED["max_d"] + 150)                # last statements finish, every warehouse suspends on its own
    for w, c in cons.items():
        cur = c.cursor(); cur.execute("show warehouses like '%s'" % w); print(w, cur.fetchone()[1]); c.close()
    print("F6 DONE - run 'pull' tomorrow morning (ACCOUNT_USAGE lags up to 3 h for metering)")

if __name__ == "__main__":
    {"check": check, "run": run, "dry": dry}[sys.argv[1]]()
