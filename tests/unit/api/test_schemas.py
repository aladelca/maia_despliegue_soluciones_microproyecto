import math

import pytest
from pydantic import ValidationError

from online_shoppers.api.schemas import SessionFeatures
from tests.factories import valid_prediction_payload


def test_session_features_accepts_the_exact_uci_contract() -> None:
    payload = valid_prediction_payload()

    session = SessionFeatures.model_validate(payload)

    assert session.model_dump(by_alias=True) == payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Administrative", -1),
        ("Administrative_Duration", -0.1),
        ("BounceRates", 1.01),
        ("ExitRates", math.nan),
        ("SpecialDay", math.inf),
        ("OperatingSystems", 0),
        ("Month", "Jan"),
        ("VisitorType", "Robot"),
    ],
)
def test_session_features_rejects_invalid_values(field: str, value: object) -> None:
    payload = valid_prediction_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        SessionFeatures.model_validate(payload)


def test_session_features_rejects_missing_and_extra_fields() -> None:
    missing = valid_prediction_payload()
    missing.pop("Month")
    extra = valid_prediction_payload() | {"SessionId": "not-allowed"}

    with pytest.raises(ValidationError):
        SessionFeatures.model_validate(missing)
    with pytest.raises(ValidationError):
        SessionFeatures.model_validate(extra)
