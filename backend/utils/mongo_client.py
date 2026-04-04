from __future__ import annotations
import logging
import os
from functools import lru_cache
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

COLLECTION_CHIEF_REPORTS = "chief_reports"
COLLECTION_OUTLIERS = "outlier_log"
COLLECTION_AUDIT = "audit_trail"

@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=5_000)
    client.admin.command("ping")
    logger.info("mongodb connected - %s", uri)
    return client

def get_db() -> Database:
    db_name = os.environ.get("MONGO_DB", "icu_decision_support")
    return get_mongo_client()[db_name]

def get_collection(name: str) -> Collection:
    return get_db()[name]

def ensure_indexes() -> None:
    reports = get_collection(COLLECTION_CHIEF_REPORTS)
    reports.create_index(
        [("subject_id", ASCENDING), ("hadm_id", ASCENDING)],
        name="subject_hadm",
    )
    reports.create_index(
        [("generated_at", DESCENDING)],
        name="generated_at_desc",
    )

    outliers = get_collection(COLLECTION_OUTLIERS)
    outliers.create_index(
        [("subject_id", ASCENDING), ("hadm_id", ASCENDING), ("layer", ASCENDING)],
        name="outlier_lookup",
    )

    logger.info("Mongodb indexes are ensured")