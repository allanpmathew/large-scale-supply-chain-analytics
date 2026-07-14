"""Smoke test: call each tool against the real DataCo data and print results."""

from __future__ import annotations

import json

from tools import check_inventory, flag_late_shipment, query_orders


def _print(title: str, obj) -> None:
    print(f"\n===== {title} =====")
    print(json.dumps(obj, indent=2, default=str))


def main() -> None:
    # 1a. query_orders — 'Cleats' passed as a department. Cleats is a Category,
    #     not a Department, so this should return 0 matches WITH a hint.
    q1a = query_orders({"department": "Cleats", "limit": 2})
    _print("query_orders: department='Cleats' (wrong column — expect hint)", q1a)

    # 1b. query_orders — correct: 'Fitness' as a department. Combined with
    #     status + region + date to exercise multiple filters at once.
    q1 = query_orders(
        {
            "delivery_status": "Late delivery",
            "region": "Southeast Asia",
            "department": "Fitness",
            "start_date": "2018-01-01",
            "end_date": "2018-03-31",
            "limit": 3,
        }
    )
    _print("query_orders: late Fitness (dept) in SE Asia, Q1 2018", q1)

    # 2. query_orders — risk-flag shortcut, no other filters, just to prove
    #    late_only works and returns a meaningful sample.
    q2 = query_orders({"late_only": True, "limit": 2})
    _print("query_orders: late_delivery_risk = 1, sample of 2", q2)

    # 3. check_inventory — by product name.
    c1 = check_inventory("Smart watch")
    _print("check_inventory: 'Smart watch' (product)", c1)

    # 4. check_inventory — by category.
    c2 = check_inventory("Cleats")
    _print("check_inventory: 'Cleats' (category)", c2)

    # 5. flag_late_shipment — use a real Order Id from the first query if we
    #    got any hits, otherwise fall back to a known-good ID from the sample.
    order_id = (
        q1["sample"][0]["Order Id"]
        if q1.get("sample")
        else q2["sample"][0]["Order Id"]
    )
    f1 = flag_late_shipment(order_id, "test run: exercising flag_late_shipment")
    _print(f"flag_late_shipment: order {order_id}", f1)

    # 6. flag_late_shipment — bad ID, should return ok=False.
    f2 = flag_late_shipment(999_999_999, "should not exist")
    _print("flag_late_shipment: bogus order id", f2)


if __name__ == "__main__":
    main()
