"""Application API routes.

The demo keeps read aggregation in pandas so the business metrics are easy to
inspect and move into SQL later. Mutating workflow endpoints use SQLAlchemy
transactions and validated Pydantic payloads.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from backend.app.db.session import engine
from backend.app.schemas import AlertPatch, CaseCreate, CasePatch, RuleSimulationRequest
from pipeline.rules.engine import _rule_mask

router = APIRouter(prefix="/api")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = PROJECT_ROOT / "data" / "generated"
ALLOWED_TABLES = {
    "customers",
    "accounts",
    "devices",
    "device_customer_links",
    "beneficiaries",
    "transactions",
    "transaction_features",
    "rule_definitions",
    "rule_results",
    "alerts",
    "alert_score_components",
    "cases",
    "analysts",
    "model_metrics",
    "data_quality_results",
    "business_insights",
}


def _table(name: str) -> pd.DataFrame:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Table is not allowed: {name}")
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(text(f"SELECT * FROM {name}"), connection)
    except Exception:
        return pd.DataFrame()


def _artifact(name: str, fallback: Any) -> Any:
    path = ARTIFACT_DIR / name
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    if pd.isna(value) if not isinstance(value, (dict, list, tuple, bool, str)) else False:
        return None
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return [{key: _json_value(value) for key, value in row.items()} for row in frame.to_dict("records")]


def _paginate(frame: pd.DataFrame, page: int, page_size: int) -> dict[str, Any]:
    total = len(frame)
    start = (page - 1) * page_size
    return {
        "items": _records(frame.iloc[start : start + page_size]),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": int(np.ceil(total / page_size)) if total else 0,
        },
    }


def _parse_date(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise HTTPException(status_code=422, detail=f"Invalid date: {value}")
    return parsed


def _filter_transactions(
    frame: pd.DataFrame,
    *,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    customer_id: str | None = None,
    account_id: str | None = None,
    beneficiary_id: str | None = None,
    country: str | None = None,
    city: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    is_fraud: bool | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start is not None:
        result = result[result["timestamp"] >= start]
    if end is not None:
        result = result[result["timestamp"] <= end + pd.Timedelta(days=1)]
    if min_amount is not None:
        result = result[result["amount"] >= min_amount]
    if max_amount is not None:
        result = result[result["amount"] <= max_amount]
    for column, value in {
        "sender_customer_id": customer_id,
        "sender_account_id": account_id,
        "beneficiary_id": beneficiary_id,
        "country": country,
        "city": city,
        "channel": channel,
        "status": status,
    }.items():
        if value:
            result = result[result[column].astype(str).str.casefold() == value.casefold()]
    if is_fraud is not None:
        result = result[result["is_fraud"].astype(bool) == is_fraud]
    if risk_level and "risk_level" in result:
        result = result[result["risk_level"].astype(str).str.casefold() == risk_level.casefold()]
    if search:
        pattern = search.casefold()
        searchable = result.fillna("").astype(str).apply(lambda column: column.str.casefold())
        result = result[searchable.apply(lambda row: row.str.contains(pattern, regex=False).any(), axis=1)]
    return result


def _alert_enriched() -> pd.DataFrame:
    alerts = _table("alerts")
    transactions = _table("transactions")
    customers = _table("customers")
    if alerts.empty:
        return alerts
    columns = ["transaction_id", "amount", "currency", "channel", "country", "city", "is_fraud", "fraud_scenario", "timestamp", "sender_account_id", "device_id", "beneficiary_id"]
    tx = transactions[[column for column in columns if column in transactions.columns]] if not transactions.empty else pd.DataFrame()
    result = alerts.merge(tx, on="transaction_id", how="left", suffixes=("", "_transaction"))
    if not customers.empty:
        result = result.merge(
            customers[["customer_id", "anonymized_name", "region", "customer_risk_level", "customer_type"]],
            on="customer_id",
            how="left",
        )
    if "created_at" in result:
        created = pd.to_datetime(result["created_at"], utc=True, errors="coerce")
        result["sla_age_hours"] = ((pd.Timestamp.now(tz="UTC") - created).dt.total_seconds() / 3600).round(1)
    result["recommended_action"] = result.apply(_recommended_action, axis=1)
    return result


def _recommended_action(row: Any) -> str:
    if row.get("risk_level") == "Critical":
        return "Escalate immediately"
    if row.get("risk_level") == "High":
        return "Review within SLA"
    if row.get("risk_level") == "Medium":
        return "Review with customer context"
    return "Monitor / close if explained"


@router.get("/overview", tags=["analytics"])
def overview(
    date_from: str | None = None,
    date_to: str | None = None,
    region: str | None = None,
    channel: str | None = None,
    segment: str | None = None,
    risk_level: str | None = None,
    rule: str | None = None,
    alert_status: str | None = None,
) -> dict[str, Any]:
    tx = _table("transactions")
    customers = _table("customers")
    alerts = _alert_enriched()
    if tx.empty:
        return {"kpis": {}, "series": {}, "message": "No generated dataset. Run the pipeline first."}
    tx = _filter_transactions(tx, date_from=date_from, date_to=date_to, channel=channel)
    if not customers.empty and region:
        customer_ids = set(customers.loc[customers["region"].str.casefold() == region.casefold(), "customer_id"])
        tx = tx[tx["sender_customer_id"].isin(customer_ids)]
    if not customers.empty and segment:
        customer_ids = set(customers.loc[customers["customer_type"].str.casefold() == segment.casefold(), "customer_id"])
        tx = tx[tx["sender_customer_id"].isin(customer_ids)]
    if not tx.empty:
        tx_ids = set(tx["transaction_id"])
        alerts = alerts[alerts["transaction_id"].isin(tx_ids)] if not alerts.empty else alerts
    if risk_level and not alerts.empty:
        alerts = alerts[alerts["risk_level"].str.casefold() == risk_level.casefold()]
    if alert_status and not alerts.empty:
        alerts = alerts[alerts["alert_status"].str.casefold() == alert_status.casefold()]
    if rule and not alerts.empty:
        alerts = alerts[alerts["triggered_rules_json"].astype(str).str.contains(rule, regex=False)]
    tx["timestamp"] = pd.to_datetime(tx["timestamp"], utc=True)
    alerts["created_at"] = pd.to_datetime(alerts["created_at"], utc=True) if not alerts.empty else pd.Series(dtype="datetime64[ns, UTC]")
    alert_tx = tx[tx["transaction_id"].isin(set(alerts["transaction_id"]))] if not alerts.empty else tx.iloc[0:0]
    confirmed_fraud = int(alert_tx["is_fraud"].sum())
    suspicious_amount = float(alert_tx["amount"].sum())
    fraud_amount = float(alert_tx.loc[alert_tx["is_fraud"].astype(bool), "amount"].sum())
    open_statuses = {"New", "In Review", "Escalated"}
    kpis = {
        "total_transactions": int(len(tx)),
        "total_transaction_volume": round(float(tx["amount"].sum()), 2),
        "suspicious_transactions": int(len(alerts)),
        "suspicious_amount": round(suspicious_amount, 2),
        "open_alerts": int(alerts["alert_status"].isin(open_statuses).sum()) if not alerts.empty else 0,
        "critical_alerts": int((alerts["risk_level"] == "Critical").sum()) if not alerts.empty else 0,
        "confirmed_fraud": confirmed_fraud,
        "estimated_prevented_loss": round(fraud_amount * 0.70, 2),
        "false_positive_rate": round((1 - confirmed_fraud / max(len(alerts), 1)) * 100, 2),
        "data_note": "Synthetic evaluation label is used as a proxy for confirmed fraud; this is not a production disposition.",
    }
    daily = tx.assign(period=tx["timestamp"].dt.strftime("%Y-%m-%d")).groupby("period").agg(transaction_volume=("amount", "sum"), transaction_count=("transaction_id", "count"), fraud_count=("is_fraud", "sum")).reset_index()
    daily["fraud_rate"] = (daily["fraud_count"] / daily["transaction_count"].clip(lower=1) * 100).round(4)
    alert_daily = alerts.assign(period=alerts["created_at"].dt.strftime("%Y-%m-%d")).groupby("period").size().rename("alerts").reset_index() if not alerts.empty else pd.DataFrame(columns=["period", "alerts"])
    volume_series = daily[["period", "transaction_volume", "transaction_count", "fraud_rate"]].to_dict("records")
    for row in volume_series:
        alert_row = alert_daily.loc[alert_daily["period"] == row["period"], "alerts"]
        row["alerts"] = int(alert_row.iloc[0]) if not alert_row.empty else 0
    risk_series = alerts.groupby("risk_level").size().reindex(["Low", "Medium", "High", "Critical"], fill_value=0).rename_axis("risk_level").reset_index(name="alerts").to_dict("records") if not alerts.empty else []
    channel_series = alert_tx.groupby("channel").agg(alerts=("transaction_id", "count"), suspicious_amount=("amount", "sum")).reset_index().to_dict("records")
    region_series = alert_tx.merge(customers[["customer_id", "region"]], left_on="sender_customer_id", right_on="customer_id", how="left").groupby("region")["amount"].sum().sort_values(ascending=False).reset_index(name="suspicious_amount").to_dict("records") if not alert_tx.empty else []
    rules = _table("rule_results")
    top_rules = rules[rules["triggered"].astype(bool)].groupby(["rule_id", "rule_name"]).size().sort_values(ascending=False).head(12).reset_index(name="triggered").to_dict("records") if not rules.empty else []
    rule_performance = _artifact("rule_performance.json", {"rules": []}).get("rules", [])
    disposition = alerts.assign(disposition=alerts["disposition"].fillna("Unreviewed")).groupby("disposition").size().reset_index(name="count").to_dict("records") if not alerts.empty else []
    workload = alert_daily.assign(analyst_minutes=alert_daily["alerts"] * 8).to_dict("records")
    return {
        "kpis": kpis,
        "filters": {"date_from": date_from, "date_to": date_to, "region": region, "channel": channel, "segment": segment, "risk_level": risk_level, "rule": rule, "alert_status": alert_status},
        "series": {
            "volume_over_time": volume_series,
            "alerts_over_time": volume_series,
            "fraud_rate_over_time": volume_series,
            "alerts_by_risk_level": risk_series,
            "alerts_by_channel": channel_series,
            "suspicious_amount_by_region": region_series,
            "top_triggered_rules": top_rules,
            "rule_precision": rule_performance,
            "disposition_funnel": disposition,
            "analyst_workload_over_time": workload,
        },
    }


@router.get("/transactions", tags=["transactions"])
def transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: float | None = Query(None, ge=0),
    max_amount: float | None = Query(None, ge=0),
    customer_id: str | None = None,
    account_id: str | None = None,
    beneficiary_id: str | None = None,
    country: str | None = None,
    city: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    is_fraud: bool | None = None,
) -> dict[str, Any]:
    frame = _table("transactions")
    alerts = _table("alerts")
    if not alerts.empty:
        frame = frame.merge(alerts[["transaction_id", "risk_score", "risk_level"]], on="transaction_id", how="left")
    frame = _filter_transactions(frame, search=search, date_from=date_from, date_to=date_to, min_amount=min_amount, max_amount=max_amount, customer_id=customer_id, account_id=account_id, beneficiary_id=beneficiary_id, country=country, city=city, channel=channel, status=status, risk_level=risk_level, is_fraud=is_fraud)
    allowed_sort = {"timestamp", "amount", "transaction_id", "risk_score", "status", "country", "channel"}
    if sort_by not in allowed_sort:
        raise HTTPException(status_code=422, detail=f"Unsupported sort field: {sort_by}")
    frame = frame.sort_values(sort_by, ascending=sort_order.casefold() == "asc", na_position="last") if not frame.empty else frame
    return _paginate(frame, page, page_size)


@router.get("/transactions/{transaction_id}", tags=["transactions"])
def transaction_detail(transaction_id: str) -> dict[str, Any]:
    tx = _table("transactions")
    row = tx[tx["transaction_id"] == transaction_id] if not tx.empty else tx
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    transaction = _records(row.iloc[[0]])[0]
    features = _table("transaction_features")
    feature_row = features[features["transaction_id"] == transaction_id] if not features.empty else features
    alerts = _table("alerts")
    alert_rows = alerts[alerts["transaction_id"] == transaction_id] if not alerts.empty else alerts
    rules = _table("rule_results")
    rule_rows = rules[(rules["transaction_id"] == transaction_id) & rules["triggered"].astype(bool)] if not rules.empty else rules
    customer_id = str(row.iloc[0]["sender_customer_id"])
    customer_tx = tx[tx["sender_customer_id"] == customer_id].sort_values("timestamp", ascending=False).head(10)
    device_id = str(row.iloc[0]["device_id"])
    beneficiary_id = str(row.iloc[0]["beneficiary_id"])
    devices = _table("devices")
    device_rows = devices[devices["device_id"] == device_id] if not devices.empty else devices
    beneficiary = _table("beneficiaries")
    beneficiary_rows = beneficiary[beneficiary["beneficiary_id"] == beneficiary_id] if not beneficiary.empty else beneficiary
    return {"transaction": transaction, "features": _records(feature_row), "alerts": _records(alert_rows), "triggered_rules": _records(rule_rows), "recent_customer_transactions": _records(customer_tx), "device": _records(device_rows), "beneficiary": _records(beneficiary_rows)}


@router.get("/customers", tags=["customers"])
def customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: str | None = None,
    risk_level: str | None = None,
    customer_type: str | None = None,
) -> dict[str, Any]:
    frame = _table("customers")
    tx = _table("transactions")
    alerts = _table("alerts")
    if not frame.empty and not tx.empty:
        stats = tx.groupby("sender_customer_id").agg(transaction_count=("transaction_id", "count"), total_volume=("amount", "sum"), average_amount=("amount", "mean"), max_amount=("amount", "max")).reset_index().rename(columns={"sender_customer_id": "customer_id"})
        frame = frame.merge(stats, on="customer_id", how="left")
    if not alerts.empty:
        alert_stats = alerts.groupby("customer_id").size().rename("alert_count").reset_index()
        frame = frame.merge(alert_stats, on="customer_id", how="left")
    for column, value in {"customer_risk_level": risk_level, "customer_type": customer_type}.items():
        if value:
            frame = frame[frame[column].astype(str).str.casefold() == value.casefold()]
    if search:
        pattern = search.casefold()
        frame = frame[frame.astype(str).apply(lambda row: row.str.casefold().str.contains(pattern, regex=False).any(), axis=1)]
    frame = frame.fillna(0)
    return _paginate(frame.sort_values("total_volume", ascending=False) if "total_volume" in frame else frame, page, page_size)


@router.get("/customers/{customer_id}", tags=["customers"])
def customer_detail(customer_id: str) -> dict[str, Any]:
    customers_frame = _table("customers")
    profile_frame = customers_frame[customers_frame["customer_id"] == customer_id] if not customers_frame.empty else customers_frame
    if profile_frame.empty:
        raise HTTPException(status_code=404, detail=f"Customer not found: {customer_id}")
    tx = _table("transactions")
    customer_tx = tx[tx["sender_customer_id"] == customer_id].sort_values("timestamp") if not tx.empty else tx
    alerts = _table("alerts")
    customer_alerts = alerts[alerts["customer_id"] == customer_id] if not alerts.empty else alerts
    devices = _table("device_customer_links")
    device_ids = devices.loc[devices["customer_id"] == customer_id, "device_id"].tolist() if not devices.empty else []
    device_frame = _table("devices")
    customer_devices = device_frame[device_frame["device_id"].isin(device_ids)] if not device_frame.empty else device_frame
    if customer_tx.empty:
        stats = {"transaction_count": 0, "total_volume": 0, "average_amount": 0, "max_amount": 0, "confirmed_fraud_count": 0}
    else:
        stats = {"transaction_count": int(len(customer_tx)), "total_volume": round(float(customer_tx["amount"].sum()), 2), "average_amount": round(float(customer_tx["amount"].mean()), 2), "max_amount": round(float(customer_tx["amount"].max()), 2), "confirmed_fraud_count": int(customer_tx["is_fraud"].sum())}
    top_beneficiaries = customer_tx.groupby("beneficiary_id")["amount"].agg(transaction_count="count", total_amount="sum").sort_values("total_amount", ascending=False).head(10).reset_index() if not customer_tx.empty else pd.DataFrame()
    activity = customer_tx.assign(period=pd.to_datetime(customer_tx["timestamp"], utc=True).dt.strftime("%Y-%m-%d")).groupby("period").agg(transaction_count=("transaction_id", "count"), total_amount=("amount", "sum")).reset_index() if not customer_tx.empty else pd.DataFrame()
    return {"profile": _records(profile_frame)[0], "stats": {**stats, "alert_count": int(len(customer_alerts)), "false_positive_count": int((customer_alerts.get("disposition", pd.Series(dtype=str)) == "False Positive").sum()) if not customer_alerts.empty else 0}, "recent_transactions": _records(customer_tx.sort_values("timestamp", ascending=False).head(20)), "alerts": _records(customer_alerts.sort_values("created_at", ascending=False).head(20)), "devices": _records(customer_devices), "countries": customer_tx["country"].value_counts().rename_axis("country").reset_index(name="transactions").to_dict("records") if not customer_tx.empty else [], "cities": customer_tx["city"].value_counts().rename_axis("city").reset_index(name="transactions").to_dict("records") if not customer_tx.empty else [], "top_beneficiaries": _records(top_beneficiaries), "activity_timeline": _records(activity)}


@router.get("/alerts", tags=["alerts"])
def alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: str | None = None,
    alert_status: str | None = None,
    priority: str | None = None,
    risk_level: str | None = None,
    sort_by: str = "risk_score",
    sort_order: str = "desc",
) -> dict[str, Any]:
    frame = _alert_enriched()
    if frame.empty:
        return _paginate(frame, page, page_size)
    if alert_status:
        frame = frame[frame["alert_status"].str.casefold() == alert_status.casefold()]
    if priority:
        frame = frame[frame["alert_priority"].str.casefold() == priority.casefold()]
    if risk_level:
        frame = frame[frame["risk_level"].str.casefold() == risk_level.casefold()]
    if search:
        pattern = search.casefold()
        frame = frame[frame.astype(str).apply(lambda row: row.str.casefold().str.contains(pattern, regex=False).any(), axis=1)]
    if sort_by not in {"risk_score", "created_at", "amount", "sla_age_hours"}:
        raise HTTPException(status_code=422, detail=f"Unsupported sort field: {sort_by}")
    frame = frame.sort_values(sort_by, ascending=sort_order.casefold() == "asc", na_position="last")
    frame["triggered_rules"] = frame["triggered_rules_json"].apply(_json_value)
    return _paginate(frame, page, page_size)


@router.get("/alerts/{alert_id}", tags=["alerts"])
def alert_detail(alert_id: str) -> dict[str, Any]:
    alerts_frame = _alert_enriched()
    selected = alerts_frame[alerts_frame["alert_id"] == alert_id] if not alerts_frame.empty else alerts_frame
    if selected.empty:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    alert = _records(selected.iloc[[0]])[0]
    transaction_id = str(selected.iloc[0]["transaction_id"])
    customer_id = str(selected.iloc[0]["customer_id"])
    tx = _table("transactions")
    transaction = tx[tx["transaction_id"] == transaction_id] if not tx.empty else tx
    features = _table("transaction_features")
    feature = features[features["transaction_id"] == transaction_id] if not features.empty else features
    rules = _table("rule_results")
    triggered = rules[(rules["transaction_id"] == transaction_id) & rules["triggered"].astype(bool)] if not rules.empty else rules
    components = _table("alert_score_components")
    score_components = components[components["alert_id"] == alert_id] if not components.empty else components
    customer = _table("customers")
    profile = customer[customer["customer_id"] == customer_id] if not customer.empty else customer
    customer_tx = tx[tx["sender_customer_id"] == customer_id].sort_values("timestamp", ascending=False).head(15) if not tx.empty else tx
    devices = _table("devices")
    device = devices[devices["device_id"] == str(transaction.iloc[0]["device_id"])] if not devices.empty and not transaction.empty else devices
    beneficiaries = _table("beneficiaries")
    beneficiary = beneficiaries[beneficiaries["beneficiary_id"] == str(transaction.iloc[0]["beneficiary_id"])] if not beneficiaries.empty and not transaction.empty else beneficiaries
    similar = alerts_frame[(alerts_frame["customer_id"] == customer_id) & (alerts_frame["alert_id"] != alert_id)].head(10) if not alerts_frame.empty else alerts_frame
    recommendation = _recommended_action(selected.iloc[0])
    return {"alert": alert, "transaction": _records(transaction)[0] if not transaction.empty else {}, "customer": _records(profile)[0] if not profile.empty else {}, "features": _records(feature)[0] if not feature.empty else {}, "triggered_rules": _records(triggered), "score_components": _records(score_components), "timeline": _records(customer_tx), "device": _records(device)[0] if not device.empty else {}, "beneficiary": _records(beneficiary)[0] if not beneficiary.empty else {}, "related_accounts": _records(_table("accounts").query("customer_id == @customer_id")) if not _table("accounts").empty else [], "similar_alerts": _records(similar), "recommendation": recommendation, "why_flagged": _why_flagged(alert, triggered, feature)}


def _why_flagged(alert: dict[str, Any], rules: pd.DataFrame, feature: pd.DataFrame) -> str:
    reasons = rules["rule_reason"].tolist() if not rules.empty and "rule_reason" in rules else []
    if reasons:
        return "High-priority alert because " + "; ".join(reason.rstrip(".").lower() for reason in reasons[:5]) + "."
    return f"Alert was prioritized at risk score {alert.get('risk_score', 0)} based on the configured composite score."


@router.patch("/alerts/{alert_id}", tags=["alerts"])
def update_alert(alert_id: str, payload: AlertPatch) -> dict[str, Any]:
    existing = _table("alerts")
    if existing.empty or alert_id not in set(existing["alert_id"]):
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    values = payload.model_dump(exclude_none=True)
    if not values:
        return alert_detail(alert_id)
    if "analyst_id" in values:
        values["assigned_at"] = datetime.now(timezone.utc).isoformat()
    if values.get("alert_status") in {"Closed", "Confirmed Fraud", "False Positive"}:
        values["closed_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    values["alert_id"] = alert_id
    with engine.begin() as connection:
        connection.execute(text(f"UPDATE alerts SET {assignments} WHERE alert_id = :alert_id"), values)
    return alert_detail(alert_id)


@router.get("/rules", tags=["rules"])
def rules() -> dict[str, Any]:
    definitions = _table("rule_definitions")
    performance = _artifact("rule_performance.json", {"rules": [], "versions": []})
    return {"definitions": _records(definitions), "performance": performance}


@router.get("/rules/performance", tags=["rules"])
def rule_performance() -> dict[str, Any]:
    return _artifact("rule_performance.json", {"rules": [], "versions": [], "pareto": []})


@router.post("/rules/simulate", tags=["rules"])
def simulate_rule(payload: RuleSimulationRequest) -> dict[str, Any]:
    features = _table("transaction_features")
    tx = _table("transactions")
    customers_frame = _table("customers")
    if features.empty or tx.empty:
        raise HTTPException(status_code=409, detail="Run the analytics pipeline before simulation")
    rule_id = payload.rule_id.upper()
    frame = tx.merge(features, on="transaction_id", how="inner").merge(
        customers_frame[["customer_id", "customer_type", "customer_risk_level"]],
        left_on="sender_customer_id",
        right_on="customer_id",
        how="left",
    )
    if payload.segment:
        frame = frame[frame["customer_type"].str.casefold() == payload.segment.casefold()]
    definitions = _table("rule_definitions")
    if definitions.empty or rule_id not in set(definitions["rule_id"]):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    definition = definitions.loc[definitions["rule_id"] == rule_id].iloc[0]
    default_threshold = definition.get(f"threshold_{payload.version.lower()}")
    threshold = default_threshold if payload.threshold is None else payload.threshold
    if rule_id == "R006" and float(threshold) > 1:
        threshold = float(threshold) / 100
    triggered = _rule_mask(rule_id, frame, threshold).fillna(False).astype(bool)
    selected = frame[triggered]
    confirmed = int(selected["is_fraud"].sum())
    false_positives = int(len(selected) - confirmed)
    total_fraud = int(frame["is_fraud"].sum())
    return {"rule_id": rule_id, "version": payload.version, "segment": payload.segment, "threshold": threshold, "alert_volume": int(len(selected)), "confirmed_fraud": confirmed, "false_positives": false_positives, "precision": round(confirmed / max(len(selected), 1), 6), "recall": round(confirmed / max(total_fraud, 1), 6), "false_positive_rate": round(false_positives / max(int((~frame["is_fraud"].astype(bool)).sum()), 1), 6), "estimated_workload_minutes": int(len(selected) * 8), "note": "Simulation uses synthetic labels for evaluation and does not optimize solely for alert volume."}


@router.get("/cases", tags=["cases"])
def cases(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), status: str | None = None, priority: str | None = None, search: str | None = None) -> dict[str, Any]:
    frame = _table("cases")
    if frame.empty:
        return _paginate(frame, page, page_size)
    if status:
        frame = frame[frame["case_status"].str.casefold() == status.casefold()]
    if priority:
        frame = frame[frame["priority"].str.casefold() == priority.casefold()]
    if search:
        frame = frame[frame.astype(str).apply(lambda row: row.str.contains(search, case=False, regex=False).any(), axis=1)]
    return _paginate(frame.sort_values("opened_at", ascending=False), page, page_size)


@router.get("/cases/analytics", tags=["cases"])
def case_analytics() -> dict[str, Any]:
    frame = _table("cases")
    if frame.empty:
        return {"average_resolution_hours": 0, "cases_per_analyst": [], "confirmed_fraud_rate": 0, "false_positive_rate": 0, "open_cases_by_priority": [], "overdue_investigations": 0}
    opened = pd.to_datetime(frame["opened_at"], utc=True, errors="coerce")
    closed = pd.to_datetime(frame["closed_at"], utc=True, errors="coerce")
    resolution_hours = (closed - opened).dt.total_seconds() / 3600
    resolved = resolution_hours.dropna()
    decisions = frame["final_decision"].fillna("")
    open_cases = frame[frame["case_status"].isin(["Open", "In Progress", "Escalated"])]
    overdue = int((((pd.Timestamp.now(tz="UTC") - opened).dt.total_seconds() / 3600 > 48) & frame["case_status"].isin(["Open", "In Progress", "Escalated"])).sum())
    return {"average_resolution_hours": round(float(resolved.mean()), 2) if not resolved.empty else 0, "cases_per_analyst": frame.fillna({"assigned_analyst": "Unassigned"}).groupby("assigned_analyst").size().rename_axis("assigned_analyst").reset_index(name="cases").to_dict("records"), "confirmed_fraud_rate": round(float((decisions == "Confirmed Fraud").mean()), 6), "false_positive_rate": round(float((decisions == "False Positive").mean()), 6), "open_cases_by_priority": open_cases.groupby("priority").size().rename_axis("priority").reset_index(name="cases").to_dict("records"), "overdue_investigations": overdue}


@router.post("/cases", tags=["cases"])
def create_case(payload: CaseCreate) -> dict[str, Any]:
    alerts_frame = _table("alerts")
    if alerts_frame.empty or payload.alert_id not in set(alerts_frame["alert_id"]):
        raise HTTPException(status_code=404, detail=f"Alert not found: {payload.alert_id}")
    alert = alerts_frame[alerts_frame["alert_id"] == payload.alert_id].iloc[0]
    current = _table("cases")
    next_number = len(current) + 1 if not current.empty else 1
    case_id = f"CASE{next_number:06d}"
    opened_at = datetime.now(timezone.utc).isoformat()
    values = {"case_id": case_id, "alert_id": payload.alert_id, "customer_id": alert["customer_id"], "case_status": "Open", "priority": payload.priority, "assigned_analyst": payload.assigned_analyst, "opened_at": opened_at, "closed_at": None, "final_decision": None, "estimated_loss": None, "prevented_loss": None, "analyst_comment": payload.analyst_comment}
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO cases (case_id, alert_id, customer_id, case_status, priority, assigned_analyst, opened_at, closed_at, final_decision, estimated_loss, prevented_loss, analyst_comment) VALUES (:case_id, :alert_id, :customer_id, :case_status, :priority, :assigned_analyst, :opened_at, :closed_at, :final_decision, :estimated_loss, :prevented_loss, :analyst_comment)"), values)
    return {"case": values}


@router.patch("/cases/{case_id}", tags=["cases"])
def update_case(case_id: str, payload: CasePatch) -> dict[str, Any]:
    current = _table("cases")
    if current.empty or case_id not in set(current["case_id"]):
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    values = payload.model_dump(exclude_none=True)
    if values.get("case_status") in {"Resolved", "Closed"}:
        values["closed_at"] = datetime.now(timezone.utc).isoformat()
    if not values:
        return {"case": _records(current[current["case_id"] == case_id])[0]}
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    values["case_id"] = case_id
    with engine.begin() as connection:
        connection.execute(text(f"UPDATE cases SET {assignments} WHERE case_id = :case_id"), values)
    updated = _table("cases")
    return {"case": _records(updated[updated["case_id"] == case_id])[0]}


@router.get("/network/related/{entity_id}", tags=["network"])
def network_related(entity_id: str) -> dict[str, Any]:
    tx = _table("transactions")
    accounts = _table("accounts")
    links = _table("device_customer_links")
    nodes: list[dict[str, Any]] = [{"id": entity_id, "type": entity_id[:3], "label": entity_id}]
    edges: list[dict[str, Any]] = []
    connected_customers: set[str] = set()
    if entity_id.startswith("CUS"):
        customer_transactions = tx[tx["sender_customer_id"] == entity_id] if not tx.empty else tx
        device_ids = set(links.loc[links["customer_id"] == entity_id, "device_id"]) if not links.empty else set()
        beneficiary_ids = set(customer_transactions["beneficiary_id"]) if not customer_transactions.empty else set()
        account_ids = set(accounts.loc[accounts["customer_id"] == entity_id, "account_id"]) if not accounts.empty else set()
        for device_id in device_ids:
            related = set(links.loc[links["device_id"] == device_id, "customer_id"]) - {entity_id}
            connected_customers |= related
            nodes.append({"id": device_id, "type": "device", "label": device_id, "degree": len(related) + 1})
            edges.append({"source": entity_id, "target": device_id, "relationship": "uses"})
        for beneficiary_id in list(beneficiary_ids)[:30]:
            senders = set(tx.loc[tx["beneficiary_id"] == beneficiary_id, "sender_customer_id"]) - {entity_id} if not tx.empty else set()
            nodes.append({"id": beneficiary_id, "type": "beneficiary", "label": beneficiary_id, "degree": len(senders) + 1})
            edges.append({"source": entity_id, "target": beneficiary_id, "relationship": "sends_to"})
        for account_id in account_ids:
            nodes.append({"id": account_id, "type": "account", "label": account_id})
            edges.append({"source": entity_id, "target": account_id, "relationship": "owns"})
    elif entity_id.startswith("DEV"):
        connected_customers = set(links.loc[links["device_id"] == entity_id, "customer_id"]) if not links.empty else set()
        for customer_id in connected_customers:
            nodes.append({"id": customer_id, "type": "customer", "label": customer_id})
            edges.append({"source": entity_id, "target": customer_id, "relationship": "shared_by"})
    elif entity_id.startswith("BEN"):
        connected_customers = set(tx.loc[tx["beneficiary_id"] == entity_id, "sender_customer_id"]) if not tx.empty else set()
        for customer_id in connected_customers:
            nodes.append({"id": customer_id, "type": "customer", "label": customer_id})
            edges.append({"source": customer_id, "target": entity_id, "relationship": "sends_to"})
    elif entity_id.startswith("ACC") and not accounts.empty:
        owners = set(accounts.loc[accounts["account_id"] == entity_id, "customer_id"])
        connected_customers |= owners
        for customer_id in owners:
            nodes.append({"id": customer_id, "type": "customer", "label": customer_id})
            edges.append({"source": customer_id, "target": entity_id, "relationship": "owns"})
    shared_devices = links.groupby("device_id")["customer_id"].nunique().sort_values(ascending=False).head(20).reset_index(name="customer_count").to_dict("records") if not links.empty else []
    shared_beneficiaries = tx.groupby("beneficiary_id")["sender_customer_id"].nunique().sort_values(ascending=False).head(20).reset_index(name="sender_count").to_dict("records") if not tx.empty else []
    circular_candidates = tx[tx["beneficiary_id"].isin(tx.groupby("beneficiary_id")["sender_customer_id"].nunique().loc[lambda series: series >= 2].index)].head(25) if not tx.empty else tx
    return {"entity_id": entity_id, "nodes": nodes, "edges": edges, "degree_count": len(nodes) - 1, "connected_customers": sorted(connected_customers), "shared_devices": shared_devices, "shared_beneficiaries": shared_beneficiaries, "circular_flow_candidates": _records(circular_candidates), "warning": "Network relationships are analytical signals and require investigator review. They do not prove fraud by themselves."}


@router.get("/model/metrics", tags=["models"])
def model_metrics() -> dict[str, Any]:
    return _artifact("model_metrics.json", {"metrics": {}, "class_distribution": {}, "model_limitations": []})


@router.get("/data-quality", tags=["data-quality"])
def data_quality() -> dict[str, Any]:
    artifact = _artifact("data_quality.json", None)
    if artifact is not None:
        artifact.setdefault("checks", _records(_table("data_quality_results")))
        return artifact
    return {"quality_score": None, "checks": _records(_table("data_quality_results")), "issues": []}


@router.get("/insights", tags=["insights"])
def insights() -> dict[str, Any]:
    return _artifact("insights.json", {"insights": []})


@router.get("/export/alerts", tags=["exports"])
def export_alerts(
    search: str | None = None,
    alert_status: str | None = None,
    priority: str | None = None,
    risk_level: str | None = None,
) -> StreamingResponse:
    frame = _alert_enriched()
    if not frame.empty:
        if alert_status:
            frame = frame[frame["alert_status"].str.casefold() == alert_status.casefold()]
        if priority:
            frame = frame[frame["alert_priority"].str.casefold() == priority.casefold()]
        if risk_level:
            frame = frame[frame["risk_level"].str.casefold() == risk_level.casefold()]
        if search:
            frame = frame[frame.astype(str).apply(lambda row: row.str.contains(search, case=False, regex=False).any(), axis=1)]
    frame = frame.drop(columns=[column for column in ["triggered_rules_json"] if column in frame], errors="ignore")
    output = io.StringIO()
    frame.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fraud-alerts.csv"})
