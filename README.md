# Large-Scale Supply Chain Analytics

Supply chain operations generate large volumes of data across planning, sourcing,
manufacturing, transportation, and fulfilment. This project designs a scalable
analytics platform that transforms operational data into actionable KPIs, enabling
performance monitoring, bottleneck detection, and a foundation for future
automation and AI.

The work is organized into phases, each targeting a distinct segment of the supply
chain. Every phase produces reproducible scripts, summary statistics, and flagged
anomalies that can feed downstream dashboards or ML pipelines.

## Phase 1 — Last-Mile Courier Performance

Analyzes last-mile delivery data from Chongqing to measure courier transit times
across peak and non-peak hours. The script computes per-courier averages, flags
the bottom-10 % slowest couriers in each city and time bucket, and exports both
row-level and aggregated summary CSVs.

### Dataset

**Source:** [Cainiao-AI/LaDe-D](https://huggingface.co/datasets/Cainiao-AI/LaDe-D) on Hugging Face

Download the dataset before running the analysis:

```bash
pip install huggingface_hub
huggingface-cli download Cainiao-AI/LaDe-D --repo-type dataset --local-dir phase1-lastmile-analysis/data
```

Or in Python:

```python
from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="Cainiao-AI/LaDe-D",
    filename="delivery_cq.csv",
    repo_type="dataset",
    local_dir="phase1-lastmile-analysis/data",
)
```

### Running the Analysis

```bash
python phase1-lastmile-analysis/notebooks/phase1_analysis.py
```

### Outputs

Results are saved to `phase1-lastmile-analysis/outputs/`:

| File | Description |
|---|---|
| `delivery_row_level.csv` | Every delivery with transit time, time bucket, and slow-courier flag |
| `delivery_summary.csv` | Aggregated average transit time per city / courier / time bucket |
