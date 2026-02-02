import json
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from starlette.concurrency import iterate_in_threadpool
from starlette.background import BackgroundTask

from app.core.logging_context import set_correlation_id
from app.utils.request_logger import write_log_entry

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exclude endpoints if needed (adjust as per requirements)
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # 1. Setup Context
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # 2. Capture Request Body
        # We need to read the body, but it can only be read once.
        # We read it, store it, and then replace the receive method so FastAPI can read it again.
        request_body_bytes = await self._read_body(request)
        request.state.body = request_body_bytes # Store for potential usage
        
        # 3. Process Request
        response = await call_next(request)
        
        # 4. Capture Response Body
        # Different handling for StreamingResponse vs regular Response
        response_body_bytes = b""
        response_headers = dict(response.headers)
        status_code = response.status_code
        
        # We wrap the response body iterator to capture chunks as they are sent
        # precise capture depends on response type.
        # For standard JSON responses, we can often consume it. 
        # For streaming/files, we might want to skip or limit logging.
        
        content_type = response_headers.get("content-type", "")
        is_stream = "text/event-stream" in content_type or "application/octet-stream" in content_type
        
        if hasattr(response, "body_iterator") and not is_stream:
            # We reconstruct the body iterator to spy on it
            original_iterator = response.body_iterator
            
            async def body_iterator_wrapper():
                nonlocal response_body_bytes
                chunks = []
                try:
                    # If it's an async iterator/generator, iterate directly
                    if hasattr(original_iterator, "__aiter__"):
                        async for chunk in original_iterator:
                            chunks.append(chunk)
                            yield chunk
                    # If it's a sync iterator, use threadpool
                    else:
                        async for chunk in iterate_in_threadpool(original_iterator):
                            chunks.append(chunk)
                            yield chunk
                except Exception:
                    # In case of error during stream, re-raise
                    raise
                finally:
                    response_body_bytes = b"".join(chunks)
                    # Now we can log, but we need to do it after response is sent?
                    # Actually, the logging must happen after the generator is exhausted.
                    # We can use a background task or just log right here? 
                    # Dispatch must return 'response', so we can't await logging here if it blocks
                    # But writing to file/db is 'fast enough' or should be backgrounded.
                    # Ideally, we use BackgroundTask, but we need the body which is only available *after* iteration.
                    
                    # We can trigger the log write here
                    self._log_transaction(
                         correlation_id, request, request_body_bytes, status_code, 
                         response_headers, response_body_bytes, start_time
                    )
            
            response.body_iterator = body_iterator_wrapper()
        else:
            # If we can't tap into iterator safely (or it's a stream we don't want to log fully),
            # we log metadata only or placeholder
            response_body_bytes = b"<stream/unavailable>"
            
            # Since we are not wrapping the iterator, we log immediately (response headers are ready)
            # But the 'process_time' won't include streaming time. 
            # For non-streaming responses, this is fine.
            
            # Using BackgroundTask to ensure we don't block main thread too much
            # But we want to reuse the logic.
            # If it IS a stream, we probably don't want to log the full body anyway.
            
            background = response.background_tasks or BackgroundTask(lambda: None)
            
            # We chain our logging task
            original_bg = background # effectively no-op if None, but we need a Task
            
            async def log_after():
                # Execute original background tasks if any
                # (FastAPI executes response.background_tasks after sending response)
                if original_bg:
                     await original_bg()
                
                self._log_transaction(
                     correlation_id, request, request_body_bytes, status_code, 
                     response_headers, response_body_bytes, start_time
                )

            # Re-assign background tasks (this might be slightly hacky if response already has complex tasks)
            # Better: a dedicated BackgroundTask that calls the logging function
            response.background = BackgroundTask(log_after)

        return response

    async def _read_body(self, request: Request) -> bytes:
        """Reads request body and restores it for the next handler."""
        body = await request.body()
        
        async def receive() -> Message:
            return {"type": "http.request", "body": body}
            
        request._receive = receive
        return body

    def _log_transaction(
        self, 
        correlation_id: str, 
        request: Request, 
        req_body: bytes, 
        status: int, 
        res_headers: dict, 
        res_body: bytes,
        start_time: float
    ):
        duration = (time.time() - start_time) * 1000
        
        # Sanitize / Decode
        try:
            req_text = req_body.decode("utf-8")
        except:
            req_text = "<binary>"
            
        try:
            res_text = res_body.decode("utf-8")
        except:
            res_text = "<binary>"
            
        # Headers to sanitize
        req_headers = dict(request.headers)
        if "authorization" in req_headers:
            req_headers["authorization"] = "Bearer <MASKED>"
            
        write_log_entry(
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            direction="INCOMING",
            status_code=status,
            request_headers=req_headers,
            request_body=req_text,
            response_headers=res_headers,
            response_body=res_text,
            duration_ms=duration,
            ip_address=request.client.host if request.client else None
        )
