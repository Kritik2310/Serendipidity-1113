from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from backend.utils.mongo_client import (
    get_collection,
    COLLECTION_CHIEF_REPORTS,
    COLLECTION_OUTLIERS,
    COLLECTION_AUDIT,
)

logger = logging.getLogger(__name__)

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def save_chief_report(report: dict) -> str:
   
    col = get_collection(COLLECTION_CHIEF_REPORTS)
    doc = {
        "subject_id":   report["subject_id"],
        "hadm_id":      report["hadm_id"],
        "generated_at": report.get("generated_at", _utcnow()),
        "agent":        report.get("agent", "chief_agent"),
        "primary_concern":    report.get("primary_concern"),
        "clinical_summary":   report.get("clinical_summary"),
        "prioritized_risks":  report.get("prioritized_risks", []),
        "recommended_actions": report.get("recommended_actions", []),
        "doctor_handoff":     report.get("doctor_handoff"),
        "disease_progression": report.get("disease_progression", []),
        "outlier_summary": report.get("outlier_summary", {}),
        "data_quality":    report.get("data_quality", {}),
        "excluded_outliers": report.get("excluded_outliers", []),
        "stored_at": _utcnow(),
    }

    try:
        result = col.insert_one(doc)
        inserted_id = str(result.inserted_id)
        logger.info(
            "Chief report saved → MongoDB _id=%s (subject=%s hadm=%s)",
            inserted_id, doc["subject_id"], doc["hadm_id"],
        )

        _save_outliers(report)

        _write_audit(
            event="chief_report_saved",
            subject_id=doc["subject_id"],
            hadm_id=doc["hadm_id"],
            detail={"mongo_id": inserted_id},
        )

        return inserted_id

    except PyMongoError as exc:
        logger.error("MongoDB write failed: %s", exc)
        raise

def _save_outliers(report: dict) -> None:
    outliers = report.get("excluded_outliers", [])
    if not outliers:
        return

    col = get_collection(COLLECTION_OUTLIERS)
    docs = [
        {
            "subject_id": report["subject_id"],
            "hadm_id":    report["hadm_id"],
            "generated_at": report.get("generated_at", _utcnow()),
            **o,
            "stored_at": _utcnow(),
        }
        for o in outliers
    ]

    try:
        col.insert_many(docs, ordered=False)
        logger.info(
            "Outlier log → %d records inserted (subject=%s hadm=%s)",
            len(docs), report["subject_id"], report["hadm_id"],
        )
    except PyMongoError as exc:
        logger.warning("Outlier log write partial/failed: %s", exc)

def _write_audit(
    event: str,
    subject_id: int,
    hadm_id: int,
    detail: Optional[dict] = None,
) -> None:
    col = get_collection(COLLECTION_AUDIT)
    try:
        col.insert_one({
            "event":      event,
            "subject_id": subject_id,
            "hadm_id":    hadm_id,
            "detail":     detail or {},
            "ts":         _utcnow(),
        })
    except PyMongoError as exc:
        logger.warning("Audit write failed: %s", exc)

def get_latest_report(subject_id: int, hadm_id: int) -> Optional[dict]:
    col = get_collection(COLLECTION_CHIEF_REPORTS)
    doc = col.find_one(
        {"subject_id": subject_id, "hadm_id": hadm_id},
        sort=[("generated_at", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])  
    return doc


def get_all_reports_for_patient(subject_id: int) -> list[dict]:
    col = get_collection(COLLECTION_CHIEF_REPORTS)
    docs = list(
        col.find({"subject_id": subject_id}, sort=[("generated_at", -1)])
    )
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


def get_outliers_for_admission(subject_id: int, hadm_id: int) -> list[dict]:
    col = get_collection(COLLECTION_OUTLIERS)
    docs = list(col.find({"subject_id": subject_id, "hadm_id": hadm_id}))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs