"""ICDE F2b: size scaling for long statements on SNOWFLAKE_SAMPLE_DATA.TPCH_SF100 (ICDE_SZ). Same protocol as F2:
ABBA sizes XS,S,M,M,S,XS; statements x 3 reps round-robin; rep 0 after resize = warm-up. Writes sf/runs/f2b_<ts>.jsonl."""
import sys, os, json, time; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf"))
import snowflake.connector
from sf_wcp import run
LONG = [  # standard TPC-H shapes on SF100 (no result cache)
 ("q1_pricing", "select l_returnflag, l_linestatus, sum(l_quantity), sum(l_extendedprice*(1-l_discount)), avg(l_discount), count(*) from lineitem where l_shipdate <= date '1998-09-02' group by 1,2 order by 1,2"),
 ("q6_forecast", "select sum(l_extendedprice*l_discount) from lineitem where l_shipdate >= date '1994-01-01' and l_shipdate < date '1995-01-01' and l_discount between 0.05 and 0.07 and l_quantity < 24"),
 ("q3_shipping", "select l_orderkey, sum(l_extendedprice*(1-l_discount)) r, o_orderdate from customer join orders on c_custkey=o_custkey join lineitem on l_orderkey=o_orderkey where c_mktsegment='BUILDING' and o_orderdate < date '1995-03-15' and l_shipdate > date '1995-03-15' group by l_orderkey, o_orderdate order by r desc limit 10"),
 ("q18_large", "select c_name, o_orderkey, sum(l_quantity) from customer join orders on c_custkey=o_custkey join lineitem on o_orderkey=l_orderkey where o_orderkey in (select l_orderkey from lineitem group by l_orderkey having sum(l_quantity) > 300) group by 1,2 order by 3 desc limit 100"),
 ("cd_supp_part", "select count(distinct l_suppkey, l_partkey) from lineitem"),
 ("top_cust_100", "select o_custkey, sum(l_extendedprice*(1-l_discount)) r from lineitem join orders on l_orderkey=o_orderkey group by 1 order by 2 desc limit 10"),
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf", "runs"); os.makedirs(OUT, exist_ok=True)
f = open(os.path.join(OUT, "f2b_%d.jsonl" % time.time()), "a")
con = snowflake.connector.connect(connection_name="cdexp", warehouse="ICDE_SZ", database="SNOWFLAKE_SAMPLE_DATA", schema="TPCH_SF100",
      session_parameters={"USE_CACHED_RESULT": False, "QUERY_TAG": "wcp_f2b", "STATEMENT_TIMEOUT_IN_SECONDS": 600})
cur = con.cursor(); cur.execute("alter warehouse ICDE_SZ set auto_suspend = 60")
for block, size in enumerate(["XSMALL", "SMALL", "MEDIUM", "MEDIUM", "SMALL", "XSMALL"]):
    cur.execute("alter warehouse ICDE_SZ set warehouse_size = %s wait_for_completion = true" % size)
    cur.execute("alter session set query_tag = 'wcp_f2b_b%d_%s'" % (block, size))
    for rep in range(3):
        for name, sql in LONG:
            r = run(con, sql); r.update({"block": block, "size": size, "rep": rep, "name": name})
            f.write(json.dumps(r) + "\n"); f.flush()
            print(block, size, rep, name, "ok" if r["ok"] else "FAIL " + r.get("err", ""), "%.1fs" % r["client_s"], flush=True)
cur.execute("alter warehouse ICDE_SZ set warehouse_size = XSMALL")
try: cur.execute("alter warehouse ICDE_SZ suspend")
except Exception: pass
con.close(); print("F2B DONE")
