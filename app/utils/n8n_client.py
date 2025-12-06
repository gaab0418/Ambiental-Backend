"""
N8N Client for AI workflow integration.
Handles secure communication with N8N webhooks using JWT and HMAC.
"""

import hmac
import hashlib
import time
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class N8NClientError(Exception):
    """Custom exception for N8N client errors"""
    pass


class N8NClient:
    """Client for interacting with N8N AI workflows"""
    
    def __init__(self):
        self.webhook_url = settings.n8n_webhook_url
        self.jwt_token = settings.n8n_jwt_token
        self.timeout = 30.0  # 30 seconds timeout
        self.max_retries = 2
    
    async def ping(self) -> bool:
        """
        Ping the N8N health endpoint to verify availability.
        Returns True when N8N responds with 200 and {"status":"ok"}.
        """
        if not self.webhook_url:
            logger.warning("n8n_webhook_url not configured - skipping health check")
            return False
        
        # Build base URL by removing the last path segment (e.g., /chat)
        base_url = self.webhook_url.rstrip("/")
        if "/" in base_url:
            base_url = base_url.rsplit("/", 1)[0]
        ping_url = f"{base_url}/healthz"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(ping_url)
                if response.status_code != 200:
                    logger.warning(
                        "N8N health check failed with status %s at %s",
                        response.status_code,
                        ping_url
                    )
                    return False
                
                try:
                    payload = response.json()
                except ValueError:
                    logger.warning("N8N health check returned non-JSON payload")
                    return False
                
                if payload.get("status") == "ok":
                    return True
                
                logger.warning("N8N health check payload missing status=ok: %s", payload)
                return False
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("N8N health check error: %s", exc)
            return False
    
    def _generate_hmac_signature(self, payload: str, timestamp: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: JSON string of the payload
            timestamp: Unix timestamp as string
            
        Returns:
            Hex-encoded HMAC signature
        """
        if not settings.n8n_signing_secret:
            logger.warning("n8n_signing_secret not configured - signature will be empty")
            return ""
        
        # Combine timestamp and payload
        message = f"{timestamp}.{payload}"
        
        # Generate HMAC
        signature = hmac.new(
            settings.n8n_signing_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def start_ai_workflow(
        self,
        thread_id: int,
        organization_id: int,
        user_id: int,
        message_content: str,
        files: Optional[List[Dict[str, Any]]] = None,
        message_history: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger N8N AI workflow with chat message and context.
        
        Args:
            thread_id: Chat thread ID
            organization_id: Organization ID
            user_id: User ID
            message_content: User's message text
            files: List of file metadata dicts (id, filename, mime_type, download_url)
            message_history: Optional list of previous messages for context
            metadata: Optional additional metadata
            
        Returns:
            Response from N8N webhook
            
        Raises:
            N8NClientError: If the request fails after retries
        """
        # Build payload
        payload = {
            "thread_id": thread_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "message": message_content,
            "files": files or [],
            "history": message_history or [],
            "metadata": metadata or {},
            "timestamp": int(time.time())
        }
        
        # Convert to JSON
        payload_json = json.dumps(payload, ensure_ascii=False)
        timestamp_str = str(int(time.time()))
        
        # Generate signature
        signature = self._generate_hmac_signature(payload_json, timestamp_str)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp_str,
            "X-Signature": signature
        }
        
        # Add JWT token if configured
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        # Make request with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        content=payload_json,
                        headers=headers
                    )
                    
                    # Check response
                    response.raise_for_status()
                    
                    logger.info(
                        f"N8N workflow triggered successfully for thread {thread_id} "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    
                    # Return response data
                    try:
                        return response.json()
                    except Exception:
                        return {"status": "success", "message": "Workflow triggered"}
                        
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"N8N request timeout for thread {thread_id} "
                    f"(attempt {attempt + 1}/{self.max_retries + 1})"
                )
                if attempt < self.max_retries:
                    await self._backoff_delay(attempt)
                    
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"N8N request failed with status {e.response.status_code} "
                    f"for thread {thread_id} (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise N8NClientError(
                        f"N8N request failed: {e.response.status_code}"
                    ) from e
                if attempt < self.max_retries:
                    await self._backoff_delay(attempt)
                    
            except Exception as e:
                last_error = e
                logger.error(
                    f"N8N request error for thread {thread_id}: {type(e).__name__} "
                    f"(attempt {attempt + 1}/{self.max_retries + 1})"
                )
                if attempt < self.max_retries:
                    await self._backoff_delay(attempt)
        
        # All retries failed
        logger.error(f"N8N workflow failed after {self.max_retries + 1} attempts for thread {thread_id}")
        raise N8NClientError("Failed to trigger N8N workflow after retries") from last_error
    
    async def _backoff_delay(self, attempt: int):
        """Exponential backoff delay between retries"""
        import asyncio
        delay = min(2 ** attempt, 8)  # Max 8 seconds
        await asyncio.sleep(delay)


def verify_n8n_callback_signature(
    payload: str,
    timestamp: str,
    signature: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Verify HMAC signature from N8N callback.
    
    Args:
        payload: JSON string of the callback payload
        timestamp: Unix timestamp from X-Timestamp header
        signature: HMAC signature from X-Signature header
        max_age_seconds: Maximum age of the request in seconds (default 5 minutes)
        
    Returns:
        True if signature is valid and timestamp is recent, False otherwise
    """
    try:
        # Check if signing secret is configured
        if not settings.n8n_signing_secret:
            logger.warning("n8n_signing_secret not configured - skipping signature verification")
            return True  # Allow in development, but log warning
        
        # Verify timestamp is recent (prevent replay attacks)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            if abs(current_time - request_time) > max_age_seconds:
                logger.warning(f"N8N callback timestamp too old or in future: {timestamp}")
                return False
        except ValueError:
            logger.warning(f"Invalid timestamp in N8N callback: {timestamp}")
            return False
        
        # Generate expected signature
        message = f"{timestamp}.{payload}"
        expected_signature = hmac.new(
            settings.n8n_signing_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying N8N callback signature: {type(e).__name__}")
        return False


# Singleton instance
n8n_client = N8NClient()

