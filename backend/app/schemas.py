"""Pydantic request schemas used by the API."""

from typing import Literal

from pydantic import BaseModel, Field

AlertStatus = Literal["New", "In Review", "Escalated", "Confirmed Fraud", "False Positive", "Closed"]
CaseStatus = Literal["Open", "In Progress", "Escalated", "Resolved", "Closed"]
FinalDecision = Literal[
    "Confirmed Fraud",
    "False Positive",
    "Suspicious Activity",
    "No Action",
    "Insufficient Evidence",
]


class AlertPatch(BaseModel):
    alert_status: AlertStatus | None = None
    analyst_id: str | None = Field(default=None, max_length=32)
    disposition: str | None = Field(default=None, max_length=48)
    investigation_notes: str | None = Field(default=None, max_length=5_000)


class CaseCreate(BaseModel):
    alert_id: str
    assigned_analyst: str | None = Field(default=None, max_length=32)
    priority: str = Field(default="P2", max_length=24)
    analyst_comment: str | None = Field(default=None, max_length=5_000)


class CasePatch(BaseModel):
    case_status: CaseStatus | None = None
    priority: str | None = Field(default=None, max_length=24)
    assigned_analyst: str | None = Field(default=None, max_length=32)
    final_decision: FinalDecision | None = None
    estimated_loss: float | None = Field(default=None, ge=0)
    prevented_loss: float | None = Field(default=None, ge=0)
    analyst_comment: str | None = Field(default=None, max_length=5_000)


class RuleSimulationRequest(BaseModel):
    rule_id: str
    threshold: float | None = Field(default=None, ge=0)
    segment: str | None = None
    version: Literal["V1", "V2"] = "V2"
