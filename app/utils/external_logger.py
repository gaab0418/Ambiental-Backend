import time
import json
from typing import Optional, Dict, Any
from app.core.logging_context import get_correlation_id
from app.utils.request_logger import write_log_entry

async def log_external_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    request_headers: Optional[Dict] = None,
    request_body: Optional[Any] = None,
    response_headers: Optional[Dict] = None,
    response_body: Optional[Any] = None,
    start_time: float = None,
    duration_ms: float = None
) -> None:
    """
    Log an outgoing external API request.
    """
    if start_time and not duration_ms:
        duration_ms = (time.time() - start_time) * 1000
    
    correlation_id = get_correlation_id()
    
    # Sanitize Authorization if present
    sanitized_req_headers = None
    if request_headers:
        sanitized_req_headers = request_headers.copy()
        for k in sanitized_req_headers:
             if k.lower() in ["authorization", "x-api-key", "x-n8n-api-key"]:
                 sanitized_req_headers[k] = "MASKED"
                 
    write_log_entry(
        correlation_id=correlation_id,
        method=method,
        url=str(url),
        direction="OUTGOING",
        status_code=status_code,
        request_headers=sanitized_req_headers,
        request_body=request_body,
        response_headers=response_headers,
        response_body=response_body,
        duration_ms=duration_ms
    )
