"""Snowset -> per-warehouse execution intervals for the fleet-advisor study (data preparation only, no results).
Interval = [endTime - durationExec, endTime] (worker processes running; compile/scheduling excluded).
Writes 64 hash buckets by warehouseId, each sorted by (warehouseId, start), plus a per-warehouse inventory.
Usage: python3 snowset_load.py <snowset-main.parquet dir> <out_dir>"""
import sys, os, json, duckdb
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
con = duckdb.connect(os.path.join(out, "tmp.duckdb")); con.execute("SET threads TO 4"); con.execute("SET preserve_insertion_order=false")
con.execute(f"""create or replace table q as
  select warehouseId as wh, databaseId as db, warehouseSize as size, serverCount as servers,
         epoch(endTime) - durationExec/1000.0 as s, epoch(endTime) as e, durationTotal/1000.0 as total_s
  from read_parquet('{src}/part.*.parquet') where durationExec is not null and durationExec >= 0""")
print("rows", con.execute("select count(*) from q").fetchone()[0], flush=True)
con.execute(f"""copy (select *, abs(hash(wh)) % 64 as bucket from q order by wh, s)
              to '{out}/intervals' (format parquet, partition_by (bucket), overwrite_or_ignore)""")
con.execute(f"""copy (select wh, count(*) n, count(distinct db) n_db, any_value(db) db, min(size) size_min, max(size) size_max,
                     count(distinct size) n_sizes, min(s) t0, max(e) t1, sum(e-s)/3600.0 exec_h
              from q group by wh) to '{out}/warehouses.parquet' (format parquet)""")
r = con.execute(f"""select count(*), sum(n), count(*) filter (where n_db = 1),
       (select count(*) from (select db from read_parquet('{out}/warehouses.parquet') where n_db=1 group by db having count(*)>=2))
     from read_parquet('{out}/warehouses.parquet')""").fetchone()
json.dump({"warehouses": r[0], "queries": r[1], "warehouses_single_db": r[2], "dbs_with_2plus_single_db_warehouses": r[3]},
          open(os.path.join(out, "inventory.json"), "w"), indent=1)
print(open(os.path.join(out, "inventory.json")).read()); con.close(); os.remove(os.path.join(out, "tmp.duckdb"))
print("SNOWSET LOAD DONE")
