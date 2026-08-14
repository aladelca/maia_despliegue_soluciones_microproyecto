import json
from pathlib import Path

import pandas as pd

from online_shoppers.reporting import build_eda_summary, write_json


def test_build_eda_summary_contains_business_aggregates() -> None:
    frame = pd.DataFrame(
        {
            "Month": ["Nov", "Nov", "Feb"],
            "VisitorType": ["Returning_Visitor", "New_Visitor", "Returning_Visitor"],
            "Weekend": [False, True, False],
            "TrafficType": [1, 1, 2],
            "Revenue": [True, False, False],
        }
    )

    summary = build_eda_summary(frame)

    assert summary["rows"] == 3
    assert summary["positive_count"] == 1
    assert summary["positive_rate"] == 1 / 3
    assert summary["conversion_by_month"]["Nov"] == 0.5
    assert summary["conversion_by_visitor_type"]["New_Visitor"] == 0.0
    assert summary["conversion_by_weekend"]["false"] == 0.5


def test_build_eda_summary_reports_quality_distributions_and_target_relationships() -> None:
    frame = pd.DataFrame(
        {
            "Month": ["Nov", "Nov", "Nov"],
            "VisitorType": ["Returning_Visitor", "New_Visitor", "Returning_Visitor"],
            "Weekend": [False, True, False],
            "TrafficType": [1, 1, 1],
            "BounceRates": [0.10, 0.0, 0.10],
            "ExitRates": [0.20, 0.02, 0.20],
            "PageValues": [0.0, 20.0, 0.0],
            "Revenue": [False, True, False],
        }
    )

    summary = build_eda_summary(frame)

    assert summary["columns"] == 8
    assert summary["duplicate_rows"] == 1
    assert summary["missing_values"]["PageValues"] == 0
    assert summary["dtypes"]["Weekend"] == "bool"
    assert summary["numeric_distributions"]["PageValues"]["max"] == 20.0
    assert summary["relationship_by_revenue"]["PageValues"]["true"] == 20.0
    assert summary["relationship_by_revenue"]["BounceRates"]["false"] == 0.10


def test_write_json_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"

    write_json(path, {"z": 1, "a": 2})

    assert path.read_text() == '{\n  "a": 2,\n  "z": 1\n}\n'
    assert json.loads(path.read_text()) == {"a": 2, "z": 1}
