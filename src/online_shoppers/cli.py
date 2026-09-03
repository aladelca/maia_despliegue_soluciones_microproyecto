"""Command-line entry points for reproducible training and experiment verification."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

import yaml

from online_shoppers.data import load_dataset
from online_shoppers.experimentation import CampaignPaths, run_experiment_campaign


def validate_tracking_uri(tracking_uri: str, *, profile: str) -> None:
    """Require the full campaign to write to an HTTP MLflow server."""

    if profile == "full" and not tracking_uri.startswith(("http://", "https://")):
        raise ValueError("the full profile requires an HTTP MLflow tracking server")


def read_dvc_data_version(pointer_path: Path) -> str:
    """Read the content hash from a single-output DVC pointer."""

    payload = yaml.safe_load(pointer_path.read_text(encoding="utf-8"))
    outputs = payload.get("outs", []) if isinstance(payload, dict) else []
    if len(outputs) != 1 or not isinstance(outputs[0], dict) or "md5" not in outputs[0]:
        raise ValueError(f"invalid single-output DVC pointer: {pointer_path}")
    return f"md5:{outputs[0]['md5']}"


def _git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "local"


def _campaign_paths(root: Path) -> CampaignPaths:
    return CampaignPaths(
        artifact_path=root / "models/champion.joblib",
        metadata_path=root / "models/model_metadata.json",
        metrics_path=root / "reports/model_metrics.json",
        comparison_path=root / "reports/experiments/final_model_comparison.json",
        protocol_path=root / "reports/experiments/protocol_manifest.json",
        tracking_artifacts_dir=root / ".mlflow-artifacts",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m online_shoppers")
    subcommands = parser.add_subparsers(dest="command", required=True)
    experiment = subcommands.add_parser("experiment", help="run a tracked model campaign")
    experiment.add_argument("--profile", choices=("smoke", "full"), required=True)
    experiment.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI"),
        required=os.getenv("MLFLOW_TRACKING_URI") is None,
    )
    experiment.add_argument(
        "--data-path", type=Path, default=Path("data/raw/online_shoppers_intention.csv")
    )
    experiment.add_argument(
        "--dvc-pointer",
        type=Path,
        default=Path("data/raw/online_shoppers_intention.csv.dvc"),
    )
    experiment.add_argument("--output-root", type=Path, default=Path.cwd())
    experiment.add_argument("--experiment-name", default="online-shoppers-ec2-large-experiment")
    experiment.add_argument("--registered-model-name", default="online-shoppers-purchase-intention")
    experiment.add_argument("--git-revision", default=None)
    experiment.add_argument("--data-version", default=None)
    experiment.add_argument("--random-seed", type=int, default=42)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command != "experiment":  # pragma: no cover - argparse enforces the command
        raise ValueError(f"unknown command: {args.command}")
    validate_tracking_uri(args.tracking_uri, profile=args.profile)
    data_version = args.data_version or read_dvc_data_version(args.dvc_pointer)
    git_revision = args.git_revision or _git_revision()
    outcome = run_experiment_campaign(
        load_dataset(args.data_path),
        tracking_uri=args.tracking_uri,
        paths=_campaign_paths(args.output_root),
        profile=args.profile,
        experiment_name=args.experiment_name,
        registered_model_name=args.registered_model_name or None,
        git_revision=git_revision,
        data_version=data_version,
        random_seed=args.random_seed,
    )
    print(
        json.dumps(
            {
                "champion": outcome.champion_name,
                "champion_run_id": outcome.champion_run_id,
                "threshold": outcome.threshold,
                "validation_metrics": outcome.validation_metrics,
                "test_metrics": outcome.test_metrics,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0
