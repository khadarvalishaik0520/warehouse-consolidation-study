"""Read-only: pulls Snowflake's own records for the two calibration warehouses into sf/truth/*.csv.
ACCOUNT_USAGE lags (query history ~45 min, attribution up to ~8 h): run the morning after, and before the trial ends."""
import sys, os, csv; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sf_wcp import connect
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truth"); os.makedirs(OUT, exist_ok=True)
W = "('ICDE_SZ','ICDE_SUSP')"; SINCE = "'2026-10-20'"
Q = {
 "query_history": f"""select query_id, query_tag, warehouse_name, warehouse_size, start_time, end_time, execution_status,
    total_elapsed_time, execution_time, compilation_time, queued_provisioning_time, queued_overload_time,
    credits_used_cloud_services from snowflake.account_usage.query_history
    where warehouse_name in {W} and start_time >= {SINCE}""",
 "attribution": f"""select query_id, query_tag, warehouse_name, start_time, end_time, credits_attributed_compute
    from snowflake.account_usage.query_attribution_history where warehouse_name in {W} and start_time >= {SINCE}""",
 "events": f"""select timestamp, warehouse_name, event_name, event_reason, event_state, size, cluster_number
    from snowflake.account_usage.warehouse_events_history where warehouse_name in {W} and timestamp >= {SINCE}""",
 "metering": f"""select start_time, end_time, warehouse_name, credits_used, credits_used_compute, credits_used_cloud_services
    from snowflake.account_usage.warehouse_metering_history where warehouse_name in {W} and start_time >= {SINCE}""",
}
con = connect("ICDE_SUSP", "wcp_pull", schema="TPCH"); cur = con.cursor()
for name, sql in Q.items():
    cur.execute(sql); rows = cur.fetchall(); cols = [c[0] for c in cur.description]
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(cols); w.writerows(rows)
    print(name, len(rows), "rows")
con.close(); print("PULL DONE")
