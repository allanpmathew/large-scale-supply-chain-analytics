# Phase 1 — Last-Mile Delivery Analysis

## Overview

Phase 1 focuses on last-mile delivery performance within the broader supply chain analytics platform. Last-mile delivery is typically the most expensive and operationally complex segment of the fulfilment process. This phase establishes the analytical foundation by ingesting delivery data, computing key performance indicators, and surfacing insights that drive operational improvements.

## Objectives

- Analyse last-mile delivery datasets to identify patterns in delivery time, cost, and failure rates.
- Compute KPIs such as on-time delivery rate, average delivery duration, cost per delivery, and failed-delivery percentage.
- Detect bottlenecks and regional performance variations across delivery routes and carriers.
- Produce visualisations and summary reports that inform logistics decision-making.
- Lay the groundwork for predictive modelling and route optimisation in later phases.

## Project Structure

```
phase1-lastmile-analysis/
├── README.md          # This file
├── notebooks/         # Jupyter notebooks for exploration and analysis
├── data/              # Raw and processed delivery datasets
└── outputs/           # Generated reports, charts, and exported KPIs
```

## Key Metrics

| Metric | Description |
|---|---|
| On-Time Delivery Rate | Percentage of deliveries completed within the promised window |
| Average Delivery Duration | Mean time from dispatch to delivery confirmation |
| Cost per Delivery | Total last-mile cost divided by number of deliveries |
| Failed Delivery Rate | Percentage of delivery attempts that were unsuccessful |
| First-Attempt Success Rate | Deliveries completed on the first attempt without rescheduling |

## Getting Started

1. Place raw delivery data files in the `data/` directory.
2. Open the notebooks in `notebooks/` to run exploratory and KPI analyses.
3. Generated outputs (charts, CSV summaries, reports) will be saved to `outputs/`.

## Relationship to Overall Project

This phase is part of the **Large-Scale Supply Chain Analytics** platform. Insights produced here feed into downstream phases covering warehouse operations, transportation network optimisation, and end-to-end supply chain visibility.
