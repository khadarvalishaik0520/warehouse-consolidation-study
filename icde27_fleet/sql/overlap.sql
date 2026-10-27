-- Mean overlap of a candidate group's running periods at 60 s auto-suspend (identical to the paper's listing).
-- Input: q(wh, s, e) execution intervals, epoch seconds.
WITH tail AS (SELECT wh, s, e + 60 AS e FROM q),
reach AS (SELECT wh, s, e, MAX(e) OVER
    (PARTITION BY wh ORDER BY s, e ROWS BETWEEN
     UNBOUNDED PRECEDING AND CURRENT ROW) AS hi FROM tail),
gap AS (SELECT wh, s, e, CASE WHEN s > LAG(hi) OVER
    (PARTITION BY wh ORDER BY s, e) THEN 1 ELSE 0
    END AS brk FROM reach),
run_id AS (SELECT wh, s, e, SUM(brk) OVER (PARTITION
    BY wh ORDER BY s, e ROWS UNBOUNDED PRECEDING) AS r
    FROM gap),
period AS (SELECT wh, r, MIN(s) AS a, MAX(e) AS b
    FROM run_id GROUP BY wh, r),
shared AS (SELECT p.wh, p.r, MAX(CASE WHEN o.wh IS NULL
    THEN 0 ELSE 1 END) AS h FROM period p LEFT JOIN
    period o ON o.wh <> p.wh AND o.a <= p.b AND o.b >= p.a
    GROUP BY p.wh, p.r)
SELECT AVG(ov) AS mean_overlap FROM
  (SELECT wh, AVG(h) AS ov FROM shared GROUP BY wh) per_wh;
