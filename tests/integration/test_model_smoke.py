from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from online_shoppers.artifacts import load_artifact


def test_real_dvc_model_loads_and_produces_probabilities() -> None:
    artifact_path = Path("models/champion.joblib")
    metadata_path = Path("models/model_metadata.json")
    if not artifact_path.exists():
        pytest.skip("run dvc pull to materialize the champion model")

    bundle, _ = load_artifact(artifact_path, metadata_path)
    sample = pd.DataFrame(
        [
            {
                "Administrative": 2,
                "Administrative_Duration": 35.5,
                "Informational": 1,
                "Informational_Duration": 12.0,
                "ProductRelated": 12,
                "ProductRelated_Duration": 420.0,
                "BounceRates": 0.01,
                "ExitRates": 0.03,
                "PageValues": 18.5,
                "SpecialDay": 0.0,
                "Month": "Nov",
                "OperatingSystems": 2,
                "Browser": 2,
                "Region": 1,
                "TrafficType": 3,
                "VisitorType": "Returning_Visitor",
                "Weekend": False,
            }
        ]
    )
    probabilities = bundle.pipeline.predict_proba(sample.loc[:, bundle.feature_names])[:, 1]

    assert probabilities.shape == (1,)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
