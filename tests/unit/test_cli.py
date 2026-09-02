from __future__ import annotations

from pathlib import Path

import pytest

from online_shoppers.cli import read_dvc_data_version, validate_tracking_uri


def test_full_profile_requires_http_tracking_server() -> None:
    with pytest.raises(ValueError, match="HTTP MLflow tracking server"):
        validate_tracking_uri("sqlite:///mlflow.db", profile="full")

    validate_tracking_uri("http://127.0.0.1:5000", profile="full")


def test_read_dvc_data_version_returns_md5(tmp_path: Path) -> None:
    pointer = tmp_path / "dataset.csv.dvc"
    pointer.write_text(
        "outs:\n- md5: aabbccddeeff.dir\n  size: 123\n  hash: md5\n  path: dataset.csv\n",
        encoding="utf-8",
    )

    assert read_dvc_data_version(pointer) == "md5:aabbccddeeff.dir"
