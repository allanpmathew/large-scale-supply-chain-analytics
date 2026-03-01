# Dataset: LaDe-D (delivery_cq.csv)

## Source

**Cainiao-AI/LaDe-D** on Hugging Face
https://huggingface.co/datasets/Cainiao-AI/LaDe-D

## Download Instructions

### Option 1 — Hugging Face CLI

```bash
pip install huggingface_hub
huggingface-cli download Cainiao-AI/LaDe-D --repo-type dataset --local-dir .
```

### Option 2 — Python

```python
from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="Cainiao-AI/LaDe-D",
    filename="delivery_cq.csv",
    repo_type="dataset",
    local_dir="phase1-lastmile-analysis/data",
)
```

### Option 3 — Manual Download

1. Go to https://huggingface.co/datasets/Cainiao-AI/LaDe-D
2. Download `delivery_cq.csv`
3. Place it in this folder (`phase1-lastmile-analysis/data/`)

## File Details

| Property | Value |
|---|---|
| File | `delivery_cq.csv` |
| City | Chongqing |
| Rows | ~931,000 |
| License | CC BY-NC 4.0 |

## Columns

| Column | Description |
|---|---|
| `order_id` | Unique order identifier |
| `lng`, `lat` | Delivery stop coordinates |
| `city` | City name |
| `region_id` | Region identifier |
| `aoi_id` | Area of Interest identifier |
| `aoi_type` | Area of Interest type (categorical) |
| `courier_id` | Courier identifier |
| `accept_time` | Timestamp when courier accepted the order |
| `accept_gps_time` | GPS timestamp closest to accept time |
| `accept_gps_lng`, `accept_gps_lat` | Courier coordinates at acceptance |
| `delivery_time` | Timestamp when delivery was completed |
| `delivery_gps_time` | GPS timestamp closest to delivery time |
| `delivery_gps_lng`, `delivery_gps_lat` | Courier coordinates at delivery |
| `ds` | Date stamp |

## Citation

Wu, L., Wen, H., et al. (2023). *LaDe: The First Comprehensive Last-mile Delivery Dataset from Industry.* arXiv:2306.10675
