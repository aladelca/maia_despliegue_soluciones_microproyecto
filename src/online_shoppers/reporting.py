"""Small, JSON-safe summaries used in reports and evidence."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from online_shoppers.data import TARGET_COLUMN


def _conversion_rates(frame: pd.DataFrame, column: str) -> dict[str, float]:
    rates = frame.groupby(column, observed=True)[TARGET_COLUMN].mean().sort_index()
    return {
        str(key).lower() if isinstance(key, bool) else str(key): float(value)
        for key, value in rates.items()
    }


def build_eda_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Build compact descriptive data for the report, not for model training."""

    positive_count = int(frame[TARGET_COLUMN].sum())
    numeric_columns = [
        column
        for column in frame.select_dtypes(include="number").columns
        if column != TARGET_COLUMN
    ]
    numeric_distributions = {
        column: {statistic: float(value) for statistic, value in frame[column].describe().items()}
        for column in numeric_columns
    }
    relationship_columns = [
        column for column in ("BounceRates", "ExitRates", "PageValues") if column in frame
    ]
    relationship_by_revenue = {
        column: {
            str(revenue).lower(): float(value)
            for revenue, value in frame.groupby(TARGET_COLUMN, observed=True)[column].mean().items()
        }
        for column in relationship_columns
    }
    return {
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_values": {column: int(value) for column, value in frame.isna().sum().items()},
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "positive_count": positive_count,
        "positive_rate": positive_count / int(frame.shape[0]),
        "numeric_distributions": numeric_distributions,
        "relationship_by_revenue": relationship_by_revenue,
        "conversion_by_month": _conversion_rates(frame, "Month"),
        "conversion_by_visitor_type": _conversion_rates(frame, "VisitorType"),
        "conversion_by_weekend": _conversion_rates(frame, "Weekend"),
        "conversion_by_traffic_type": _conversion_rates(frame, "TrafficType"),
    }


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Atomically write deterministic JSON for Git-friendly diffs."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
