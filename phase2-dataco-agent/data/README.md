# Dataset: DataCo Smart Supply Chain

## Source

**Kaggle: DataCo Smart Supply Chain For Big Data Analysis**
https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis

## Details

| Property | Value |
|---|---|
| File | `DataCoSupplyChainDataset.csv` |
| Rows | 180,519 |
| Size | ~92 MB |
| Encoding | `latin-1` (load with `encoding='latin-1'`) |

The CSV is gitignored due to its size. Download it from Kaggle and place it in this directory before running the agent.

## Key Columns Used by the Agent

| Column | Description |
|---|---|
| `Order Id` | Unique order identifier |
| `order date (DateOrders)` | Order timestamp |
| `Delivery Status` | One of: Late delivery, Advance shipping, Shipping on time, Shipping canceled |
| `Late_delivery_risk` | Binary flag (1 = at risk of late delivery) |
| `Days for shipping (real)` | Actual shipping duration in days |
| `Days for shipment (scheduled)` | Promised shipping duration in days |
| `Category Name` | Fine-grained product category (e.g. Cleats, Cardio Equipment) |
| `Department Name` | Higher-level product grouping (e.g. Fitness, Apparel) |
| `Product Name` | Product description |
| `Order Region` | Geographic region (e.g. Central America, Western Europe) |
| `Customer Segment` | Customer type (Consumer, Corporate, Home Office) |
| `Shipping Mode` | Shipping tier (Standard Class, Second Class, First Class, Same Day) |
| `Order Item Quantity` | Units ordered |
