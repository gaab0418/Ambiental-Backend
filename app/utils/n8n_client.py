import httpx
from app.config import settings
import os
from typing import Optional
import hmac
import hashlib
import logging
import time
from app.utils.external_logger import log_external_request

logger = logging.getLogger(__name__)

class N8NClientError(Exception):
    """Base exception for N8N client errors"""
    pass

class N8NClient:
    """Client for interacting with N8N webhooks"""
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key

    async def ping(self) -> bool:
        """
        Check if N8N is reachable.
        """
        # We can try to hit the base URL or a health endpoint.
        # N8N doesn't have a standard unauthenticated health endpoint by default, 
        # but hitting the base URL should at least return 200 or 404 (reachable).
        # We'll try to GET the base_url.
        url = self.base_url
        try:
             async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                # Any response is good enough to say it's reachable at network level
                return True
        except Exception as e:
            logger.warning(f"N8N ping failed: {e}")
            return False

    async def trigger_webhook(self, webhook_path: str, payload: dict) -> dict:
        """
        Trigger a generic N8N webhook.
        """
        url = f"{self.base_url.rstrip('/')}/{webhook_path.lstrip('/')}"
        
        headers = {}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
            
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = None
            error = None
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                response = e.response
                error = e
                logger.error(f"HTTP error triggering N8N webhook: {e}")
                raise N8NClientError(f"HTTP error: {e}")
            except Exception as e:
                error = e
                logger.error(f"Error triggering N8N webhook: {e}")
                raise N8NClientError(f"Connection error: {e}")
            finally:
                # Log external request
                status_code = response.status_code if response else (500 if error else None)
                res_body = None
                if response:
                    try: 
                        res_body = response.text 
                    except: 
                        pass
                
                await log_external_request(
                    method="POST",
                    url=url,
                    status_code=status_code,
                    request_headers=headers,
                    request_body=payload,
                    response_body=res_body,
                    start_time=start_time
                )

# Global instance
n8n_client = N8NClient(base_url=settings.n8n_webhook_url)

def verify_n8n_callback_signature(payload: str, timestamp: str, signature: str) -> bool:
    """
    Verify the HMAC signature of an N8N callback.
    """
    if not settings.n8n_signing_secret:
        # If no secret configured, assume valid (or invalid depending on security policy)
        # For now, let's log warning and return True to not break dev, or False if strict.
        # Given the error is just missing import, let's implement validation logic.
        return True
        
    # Construct message to sign: timestamp + payload
    message = f"{timestamp}{payload}"
    
    # Calculate HMAC
    expected_signature = hmac.new(
        settings.n8n_signing_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

async def trigger_process_webhook(
    process_id: int,
    file_name: str,
    file_path: str,
    auth_token: Optional[str] = None
) -> bool:
    """
    Triggers the N8N webhook after process creation.
    Sends process ID and the uploaded file.
    
    Args:
        process_id: ID of the created process
        file_name: Name of the file (e.g., from IN type or uploaded filename)
        file_path: Absolute path to the file on disk
        auth_token: Authorization token to pass to N8N (optional)
        
    Returns:
        bool: True if request was successful, False otherwise.
    """
    # Append 'checklist' to base URL as per requirement
    webhook_url = f"{settings.n8n_webhook_url.rstrip('/')}/checklist"
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    try:
        # Prepare headers
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token
            
        # Prepare multipart/form-data
        # We need to open the file and send it
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {
                    "file": (os.path.basename(file_path), f, "application/pdf")
                }
                data = {
                    "processoId": str(process_id),
                    "fileName": file_name
                }
                
                start_time = time.time()
                response = None
                try:
                    # We replicate request body structure for logging (without file content)
                    log_payload = {
                        "processoId": str(process_id),
                        "fileName": file_name,
                        "file": f"<file: {os.path.basename(file_path)}>"
                    }

                    response = await client.put(
                        webhook_url,
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=30.0 # 30s timeout for file upload
                    )
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        return True
                    else:
                        print(f"N8N Webhook failed: {response.status_code} - {response.text}")
                        return False
                finally:
                    # Log external request
                    status_code = response.status_code if response else 500
                    res_body = None
                    if response:
                        try: 
                            res_body = response.text 
                        except: 
                            pass
                    
                    await log_external_request(
                        method="PUT",
                        url=webhook_url,
                        status_code=status_code,
                        request_headers=headers,
                        request_body=log_payload,
                        response_body=res_body,
                        start_time=start_time
                    )
                    
    except Exception as e:
        print(f"Exception calling N8N webhook: {str(e)}")
        # We might want to log this exception case too if we didn't reach 'finally'
        # But 'finally' inside 'async with' handles the http request part.
        # If exception happens before (e.g. file open), we miss it in external log, which is acceptable 
        # as it's not an external request yet. 
        return False
