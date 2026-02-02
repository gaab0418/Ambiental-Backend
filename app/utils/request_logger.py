import json
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.request_log import RequestLog
from app.database import SessionLocal

# Setup paths
LOG_ROOT = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_ROOT.mkdir(parents=True, exist_ok=True)
REQUEST_LOG_FILE = LOG_ROOT / "requests.jsonl"

# Configure rotating file handler
# Max size: 10MB, Backups: 5
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

request_logger = logging.getLogger("request_logger")
request_logger.setLevel(logging.INFO)
request_logger.propagate = False # Prevent propagation to root logger

# Check if handler already exists to avoid duplicates on reload
if not request_logger.handlers:
    handler = RotatingFileHandler(
        REQUEST_LOG_FILE, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)

# Standard logger for errors
logger = logging.getLogger(__name__)

def _serialize(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def write_log_entry(
    correlation_id: str,
    method: str,
    url: str,
    direction: str,
    status_code: Optional[int] = None,
    request_headers: Optional[Dict] = None,
    request_body: Optional[Any] = None,
    response_headers: Optional[Dict] = None,
    response_body: Optional[Any] = None,
    duration_ms: Optional[float] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Write a log entry to configured destinations (file and/or db).
    """
    
    # Prepare data object
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "direction": direction,
        "method": method,
        "url": str(url),
        "status_code": status_code,
        "duration_ms": duration_ms,
        "ip_address": ip_address,
        "request": {
            "headers": request_headers,
            "body": request_body
        },
        "response": {
            "headers": response_headers,
            "body": response_body
        }
    }

    # 1. Write to specific JSONL file utilizing rotation
    if settings.log_requests_to_file:
        try:
            message = json.dumps(log_data, default=_serialize, ensure_ascii=False)
            request_logger.info(message)
        except Exception as e:
            # Fallback to standard logger if file write fails
            logger.error(f"Failed to write to request log file: {e}")

    # 2. Write to Database
    if settings.log_requests_to_db:
        try:
            db_entry = RequestLog(
                correlation_id=correlation_id,
                method=method,
                url=str(url),
                direction=direction,
                status_code=status_code,
                request_headers=json.dumps(request_headers, default=_serialize) if request_headers else None,
                request_body=str(request_body) if request_body is not None else None,
                response_headers=json.dumps(response_headers, default=_serialize) if response_headers else None,
                response_body=str(response_body) if response_body is not None else None,
                duration_ms=duration_ms,
                ip_address=ip_address
            )
            
            with SessionLocal() as db:
                db.add(db_entry)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to write request log to DB: {e}")
