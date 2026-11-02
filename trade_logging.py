"""
Persistent logging, filtering, and history management for analysis logs.
"""

import os
import uuid
from datetime import datetime

import pandas as pd

LOG_FILE = "logs.csv"
LEGACY_SESSION = "legacy_session"

LOG_COLUMNS = [
    "log_id",
    "timestamp",
    "symbol",
    "decision",
    "total_score",
    "technical_score",
    "fundamental_score",
    "supporting_score",
    "confidence",
    "current_price",
    "entry_price",
    "stop_loss",
    "target_min",
    "target_max",
    "risk_reward",
    "position_size",
    "session_id",
    "is_deleted",
]

NUMERIC_COLUMNS = [
    "total_score",
    "technical_score",
    "fundamental_score",
    "supporting_score",
    "confidence",
    "current_price",
    "entry_price",
    "stop_loss",
    "target_min",
    "target_max",
    "risk_reward",
    "position_size",
]


def _safe_float(value, default=0.0):
    """Safely convert any value to float with a fallback."""
    try:
        if value is None:
            return float(default)
        parsed = float(value)
        if pd.isna(parsed):
            return float(default)
        return parsed
    except (TypeError, ValueError):
        return float(default)


def _normalize_is_deleted_series(series):
    """Convert mixed CSV values to integer 0/1."""
    if series is None or len(series) == 0:
        return pd.Series(dtype=int)
    as_bool = series.astype(str).str.strip().str.lower().isin(("1", "true", "yes", "y"))
    as_num = pd.to_numeric(series, errors="coerce").fillna(0)
    out = (as_num >= 1) | as_bool
    return out.astype(int)


def _ensure_log_file():
    """Create CSV file with header when missing; migrate older schemas."""
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=LOG_COLUMNS).to_csv(LOG_FILE, index=False)
        return

    try:
        df = pd.read_csv(LOG_FILE)

        if "total_score" not in df.columns:
            if "score" in df.columns:
                df["total_score"] = df["score"]
            else:
                df["total_score"] = 0.0

        if "current_price" not in df.columns:
            if "price_now" in df.columns:
                df["current_price"] = df["price_now"]
            else:
                df["current_price"] = 0.0

        if "session_id" not in df.columns:
            df["session_id"] = LEGACY_SESSION
        else:
            sid = df["session_id"].astype(str).replace("nan", "").replace("None", "")
            sid = sid.fillna("")
            df["session_id"] = sid.replace("", LEGACY_SESSION)
            df.loc[df["session_id"].str.strip() == "", "session_id"] = LEGACY_SESSION

        if "is_deleted" not in df.columns:
            df["is_deleted"] = 0
        else:
            df["is_deleted"] = _normalize_is_deleted_series(df["is_deleted"])

        for col in LOG_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0 if col in NUMERIC_COLUMNS else ""

        df = df[LOG_COLUMNS]
        df.to_csv(LOG_FILE, index=False)
    except Exception:
        pass


def save_log(analysis_result: dict):
    """
    Save one analysis record in append mode.
    Never overwrites existing log records.
    """
    try:
        _ensure_log_file()
        data = analysis_result or {}
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "symbol": str(data.get("symbol") or "UNKNOWN").upper(),
            "decision": str(data.get("decision") or "UNKNOWN"),
            "total_score": _safe_float(data.get("total_score", data.get("score")), 0.0),
            "technical_score": _safe_float(data.get("technical_score"), 0.0),
            "fundamental_score": _safe_float(data.get("fundamental_score"), 0.0),
            "supporting_score": _safe_float(data.get("supporting_score"), 0.0),
            "confidence": _safe_float(data.get("confidence"), 0.0),
            "current_price": _safe_float(data.get("current_price", data.get("price_now")), 0.0),
            "entry_price": _safe_float(data.get("entry_price"), 0.0),
            "stop_loss": _safe_float(data.get("stop_loss"), 0.0),
            "target_min": _safe_float(data.get("target_min"), 0.0),
            "target_max": _safe_float(data.get("target_max"), 0.0),
            "risk_reward": _safe_float(data.get("risk_reward"), 0.0),
            "position_size": _safe_float(data.get("position_size"), 0.0),
            "session_id": str(data.get("session_id") or LEGACY_SESSION).strip() or LEGACY_SESSION,
            "is_deleted": 0,
        }
        pd.DataFrame([log_entry]).to_csv(LOG_FILE, mode="a", header=False, index=False)
    except Exception:
        pass


def load_logs(include_deleted=False):
    """Load logs as a cleaned DataFrame with stable dtypes."""
    _ensure_log_file()
    df = pd.read_csv(LOG_FILE)

    for col in LOG_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[LOG_COLUMNS].copy()

    if "session_id" in df.columns:
        sid = df["session_id"].astype(str).replace("nan", "").replace("None", "")
        sid = sid.fillna("")
        df["session_id"] = sid.replace("", LEGACY_SESSION)
        df.loc[df["session_id"].str.strip() == "", "session_id"] = LEGACY_SESSION

    df["is_deleted"] = _normalize_is_deleted_series(df["is_deleted"])

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].fillna(0.0)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["timestamp"] = df["timestamp"].fillna(pd.Timestamp("1970-01-01"))

    df["symbol"] = df["symbol"].fillna("UNKNOWN").astype(str).str.upper()
    df["decision"] = df["decision"].fillna("UNKNOWN").astype(str)
    df["log_id"] = df["log_id"].fillna("").astype(str)

    if not include_deleted:
        df = df[df["is_deleted"] == 0]

    return df


def soft_delete_logs(log_ids):
    """Soft-delete rows by log_id (sets is_deleted=1). Rewrites CSV."""
    if not log_ids:
        return False
    try:
        _ensure_log_file()
        df = pd.read_csv(LOG_FILE)
        for col in LOG_COLUMNS:
            if col not in df.columns:
                df[col] = "" if col not in NUMERIC_COLUMNS and col != "is_deleted" else 0
        df["is_deleted"] = _normalize_is_deleted_series(df["is_deleted"])
        id_set = {str(x).strip() for x in log_ids if str(x).strip()}
        mask = df["log_id"].astype(str).isin(id_set)
        df.loc[mask, "is_deleted"] = 1
        df = df[LOG_COLUMNS]
        df.to_csv(LOG_FILE, index=False)
        return True
    except Exception:
        return False


def soft_delete_all_logs():
    """Soft-delete every row (audit-friendly; rows remain in file)."""
    try:
        _ensure_log_file()
        df = pd.read_csv(LOG_FILE)
        for col in LOG_COLUMNS:
            if col not in df.columns:
                df[col] = "" if col not in NUMERIC_COLUMNS and col != "is_deleted" else 0
        df["is_deleted"] = 1
        df = df[LOG_COLUMNS]
        df.to_csv(LOG_FILE, index=False)
        return True
    except Exception:
        return False


def filter_logs(
    df,
    decision=None,
    min_total_score=None,
    max_total_score=None,
    min_confidence=None,
    max_confidence=None,
    symbol=None,
    search_text=None,
    session_id=None,
    exclude_deleted=True,
    min_technical_score=None,
    max_technical_score=None,
    min_fundamental_score=None,
    max_fundamental_score=None,
    min_supporting_score=None,
    max_supporting_score=None,
    min_current_price=None,
    max_current_price=None,
    min_target_price=None,
    max_target_price=None,
    min_stop_loss=None,
    max_stop_loss=None,
):
    """Apply flexible combined filters to logs."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LOG_COLUMNS)

    filtered = df.copy()

    if exclude_deleted and "is_deleted" in filtered.columns:
        filtered = filtered[filtered["is_deleted"].fillna(0).astype(int) == 0]

    if session_id:
        if "session_id" in filtered.columns:
            filtered = filtered[filtered["session_id"].astype(str) == str(session_id)]

    if decision and decision != "All":
        filtered = filtered[filtered["decision"].fillna("").str.upper() == str(decision).upper()]
    if min_total_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["total_score"], errors="coerce").fillna(0.0) >= float(min_total_score)
        ]
    if max_total_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["total_score"], errors="coerce").fillna(0.0) <= float(max_total_score)
        ]
    if min_confidence is not None:
        filtered = filtered[
            pd.to_numeric(filtered["confidence"], errors="coerce").fillna(0.0) >= float(min_confidence)
        ]
    if max_confidence is not None:
        filtered = filtered[
            pd.to_numeric(filtered["confidence"], errors="coerce").fillna(0.0) <= float(max_confidence)
        ]
    if symbol:
        filtered = filtered[filtered["symbol"].fillna("").str.upper() == str(symbol).strip().upper()]

    if search_text and str(search_text).strip():
        q = str(search_text).strip().lower()
        sym = filtered["symbol"].fillna("").astype(str).str.lower().str.contains(q, na=False, regex=False)
        dec = filtered["decision"].fillna("").astype(str).str.lower().str.contains(q, na=False, regex=False)
        lid = filtered["log_id"].fillna("").astype(str).str.lower().str.contains(q, na=False, regex=False)
        filtered = filtered[sym | dec | lid]

    if min_technical_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["technical_score"], errors="coerce").fillna(0.0) >= float(min_technical_score)
        ]
    if max_technical_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["technical_score"], errors="coerce").fillna(0.0) <= float(max_technical_score)
        ]
    if min_fundamental_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["fundamental_score"], errors="coerce").fillna(0.0) >= float(min_fundamental_score)
        ]
    if max_fundamental_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["fundamental_score"], errors="coerce").fillna(0.0) <= float(max_fundamental_score)
        ]
    if min_supporting_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["supporting_score"], errors="coerce").fillna(0.0) >= float(min_supporting_score)
        ]
    if max_supporting_score is not None:
        filtered = filtered[
            pd.to_numeric(filtered["supporting_score"], errors="coerce").fillna(0.0) <= float(max_supporting_score)
        ]
    if min_current_price is not None:
        filtered = filtered[
            pd.to_numeric(filtered["current_price"], errors="coerce").fillna(0.0) >= float(min_current_price)
        ]
    if max_current_price is not None:
        filtered = filtered[
            pd.to_numeric(filtered["current_price"], errors="coerce").fillna(0.0) <= float(max_current_price)
        ]
    if min_target_price is not None:
        filtered = filtered[
            pd.to_numeric(filtered["target_min"], errors="coerce").fillna(0.0) >= float(min_target_price)
        ]
    if max_target_price is not None:
        filtered = filtered[
            pd.to_numeric(filtered["target_min"], errors="coerce").fillna(0.0) <= float(max_target_price)
        ]
    if min_stop_loss is not None:
        filtered = filtered[pd.to_numeric(filtered["stop_loss"], errors="coerce").fillna(0.0) >= float(min_stop_loss)]
    if max_stop_loss is not None:
        filtered = filtered[pd.to_numeric(filtered["stop_loss"], errors="coerce").fillna(0.0) <= float(max_stop_loss)]

    return filtered


def sort_logs(df, by="total_score", ascending=False):
    """Sort logs by allowed fields only."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LOG_COLUMNS)

    allowed = {
        "total_score",
        "confidence",
        "technical_score",
        "fundamental_score",
        "supporting_score",
        "current_price",
        "target_min",
        "timestamp",
    }
    sort_col = by if by in allowed else "total_score"
    return df.sort_values(by=sort_col, ascending=ascending, na_position="last")
