"""Phase 1 — Last-mile delivery performance analysis.

Loads delivery_cq.csv, computes transit times, classifies peak vs non-peak
hours, aggregates per city/courier/time-bucket, flags the slowest couriers,
and exports row-level and summary CSVs to the outputs/ folder.
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "delivery_cq.csv"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Load & parse
# ---------------------------------------------------------------------------
print(f"Loading {DATA_PATH} …")
df = pd.read_csv(DATA_PATH)
df["accept_time"] = pd.to_datetime(df["accept_time"])
df["delivery_time"] = pd.to_datetime(df["delivery_time"])

# ---------------------------------------------------------------------------
# Transit time
# ---------------------------------------------------------------------------
df["transit_time_hours"] = (
    (df["delivery_time"] - df["accept_time"]).dt.total_seconds() / 3600
)

# ---------------------------------------------------------------------------
# Peak / Non-Peak classification
# Peak hours: 07-10 and 16-19 (based on accept_time hour)
# ---------------------------------------------------------------------------
hour = df["accept_time"].dt.hour
df["time_bucket"] = "Non-Peak"
df.loc[((hour >= 7) & (hour < 10)) | ((hour >= 16) & (hour < 19)), "time_bucket"] = (
    "Peak"
)

# ---------------------------------------------------------------------------
# Aggregate: average transit time per city × courier × time_bucket
# ---------------------------------------------------------------------------
agg = (
    df.groupby(["city", "courier_id", "time_bucket"], as_index=False)
    .agg(
        avg_transit_time_hours=("transit_time_hours", "mean"),
        delivery_count=("transit_time_hours", "count"),
    )
)

# ---------------------------------------------------------------------------
# Flag bottom-10 % slowest couriers per city × time_bucket
# (highest avg transit time → slowest)
# ---------------------------------------------------------------------------
def flag_slow(group: pd.DataFrame) -> pd.DataFrame:
    threshold = group["avg_transit_time_hours"].quantile(0.90)
    group["is_bottom_10pct"] = group["avg_transit_time_hours"] >= threshold
    return group


agg = agg.groupby(["city", "time_bucket"], group_keys=False).apply(flag_slow)

# Propagate flag back to row-level data
slow_keys = agg.loc[agg["is_bottom_10pct"], ["city", "courier_id", "time_bucket"]]
df = df.merge(
    slow_keys.assign(is_bottom_10pct=True),
    on=["city", "courier_id", "time_bucket"],
    how="left",
)
df["is_bottom_10pct"] = df["is_bottom_10pct"].fillna(False)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
row_level_path = OUTPUT_DIR / "delivery_row_level.csv"
summary_path = OUTPUT_DIR / "delivery_summary.csv"

df.to_csv(row_level_path, index=False)
agg.to_csv(summary_path, index=False)

print(f"Row-level  → {row_level_path}  ({len(df):,} rows)")
print(f"Summary    → {summary_path}  ({len(agg):,} rows)")
print("Done.")
