"""Public API request and response schemas."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
NonNegativeFloat = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Rate = Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
PositiveCategory = Annotated[int, Field(strict=True, ge=1)]


class SessionFeatures(BaseModel):
    """The 17 UCI features accepted by the inference endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    administrative: NonNegativeInt = Field(alias="Administrative")
    administrative_duration: NonNegativeFloat = Field(alias="Administrative_Duration")
    informational: NonNegativeInt = Field(alias="Informational")
    informational_duration: NonNegativeFloat = Field(alias="Informational_Duration")
    product_related: NonNegativeInt = Field(alias="ProductRelated")
    product_related_duration: NonNegativeFloat = Field(alias="ProductRelated_Duration")
    bounce_rates: Rate = Field(alias="BounceRates")
    exit_rates: Rate = Field(alias="ExitRates")
    page_values: NonNegativeFloat = Field(alias="PageValues")
    special_day: Rate = Field(alias="SpecialDay")
    month: Literal["Feb", "Mar", "May", "June", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] = Field(
        alias="Month"
    )
    operating_systems: PositiveCategory = Field(alias="OperatingSystems")
    browser: PositiveCategory = Field(alias="Browser")
    region: PositiveCategory = Field(alias="Region")
    traffic_type: PositiveCategory = Field(alias="TrafficType")
    visitor_type: Literal["New_Visitor", "Returning_Visitor", "Other"] = Field(alias="VisitorType")
    weekend: bool = Field(alias="Weekend", strict=True)


class PredictionResponse(BaseModel):
    """Versioned inference result."""

    will_purchase: bool
    purchase_probability: Annotated[float, Field(ge=0, le=1)]
    threshold: Annotated[float, Field(ge=0, le=1)]
    model_version: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_version: str | None


class MetadataResponse(BaseModel):
    model_version: str
    feature_names: list[str]
    threshold: Annotated[float, Field(ge=0, le=1)]
    champion: str | None = None
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    test_metrics: dict[str, Any] = Field(default_factory=dict)
