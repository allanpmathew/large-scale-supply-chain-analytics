# Phase 1 — Last-Mile Execution Analysis

## Dataset Used

**LaDe delivery_CQ dataset**

| Column | Description |
|---|---|
| `order_id` | Unique order identifier |
| `region_id` | Region of delivery |
| `city` | City of delivery |
| `courier_id` | Courier handling the delivery |
| `accept_time` | Timestamp when the courier accepted the order |
| `delivery_time` | Timestamp when the delivery was completed |
| GPS coordinates | Latitude and longitude of delivery |
| `ds` | Date stamp |

**Dataset Grain:** One row represents one last-mile delivery execution event for one order handled by one courier.

## Scope

This dataset covers **only the last-mile delivery portion** of the supply chain. It does NOT include:

- Order creation
- Warehouse picking
- Sorting
- Inventory
- Product data
- Cold chain
- SLA promise times

Those will be added in later phases.

## KPI Defined

**Courier Performance** = Average last-mile transit time, calculated as:

```
delivery_time - accept_time
```

Measured in **hours**.

### Comparison Rules

- Couriers are compared **only within the same city**.
- Performance is segmented by **time-of-day** to control for traffic bias.

### Time Buckets

| Bucket | Hours |
|---|---|
| Peak | 07:00–10:00 and 16:00–19:00 |
| Non-Peak | All other hours |

### Poor Performance Definition

A courier is underperforming if their average transit time is **significantly higher** than peers in the same city and same time bucket.

## Output Built

- Transit time column
- Peak vs Non-Peak classification
- Average transit time per city and courier
- Bottom 10% slowest couriers per city
- Data exported for Power BI

## Power BI Visuals

- Average transit time by city
- Courier comparison (Peak vs Non-Peak)
- Bottom 10% highlight

## What Phase 1 Demonstrates

- Controlled KPI definition
- Bias handling (geography + congestion)
- Operational fairness logic
- Real last-mile analytics

## Project Structure

```
phase1-lastmile-analysis/
├── README.md          # This file
├── notebooks/         # Jupyter notebooks for exploration and analysis
├── data/              # Raw and processed delivery datasets
└── outputs/           # Generated reports, charts, and exported KPIs
```

## Planned Phases

| Phase | Focus |
|---|---|
| **Phase 1** | Last-Mile Execution Analysis (current) |
| **Phase 2** | Full Lifecycle Integration (DataCo dataset) |
| **Phase 3** | Robotics & Automation Simulation |
| **Phase 4** | Cold Chain Simulation |
| **Phase 5** | Architecture Thinking |
