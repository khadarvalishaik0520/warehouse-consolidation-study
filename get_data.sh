#!/bin/bash
# Downloads Snowset (Vuppalapati et al., NSDI 2020; public) and prepares per-warehouse execution intervals.
#   ./get_data.sh            -> data/snowset/ (about 8 GB compressed) and data/snowset_iv/ (intervals, 64 buckets)
set -eu
cd "$(dirname "$0")"; mkdir -p data/snowset
( cd data/snowset && curl -C - -O "http://www.cs.cornell.edu/~midhul/snowset/snowset-main.parquet.tar.gz" && tar -xzf snowset-main.parquet.tar.gz )
python3 icde27_fleet/snowset_load.py "$(find data/snowset -name 'part.*.parquet' -printf '%h\n' | head -1)" data/snowset_iv
