from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.utils.audit_logger import AuditLogger
from app.dependencies.auth import get_current_user_optional
import time
import json


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log API requests and responses"""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        # Paths to exclude from audit logging
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/metrics"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip audit logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        # Get request info
        method = request.method
        path = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Get user info if available (for authenticated requests)
        user_id = None
        organization_id = None
        
        try:
            # Try to get current user (this will work if Authorization header is present)
            current_user = await get_current_user_optional(request)
            if current_user:
                user_id = current_user.id
                organization_id = current_user.organization_id
        except Exception:
            # Ignore errors - user might not be authenticated
            pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the request (only for non-GET requests or important GET requests)
        if (method != "GET" or 
            any(important_path in path for important_path in ["/api/auth/", "/api/master/", "/api/logs/"])):
            
            self._log_request(
                method=method,
                path=path,
                user_id=user_id,
                organization_id=organization_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=response.status_code,
                process_time=process_time
            )
        
        return response
    
    def _log_request(
        self,
        method: str,
        path: str,
        user_id: int = None,
        organization_id: int = None,
        ip_address: str = None,
        user_agent: str = None,
        status_code: int = None,
        process_time: float = None
    ):
        """Log the request to audit logs"""
        db: Session = SessionLocal()
        try:
            # Determine action based on method and path
            action = self._determine_action(method, path)
            entity_type = self._determine_entity_type(path)
            
            # Create metadata
            metadata = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "process_time_seconds": round(process_time, 3) if process_time else None
            }
            
            AuditLogger.log_action(
                db=db,
                action=action,
                entity_type=entity_type,
                user_id=user_id,
                organization_id=organization_id,
                changes=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        except Exception as e:
            # Don't let audit logging errors break the request
            print(f"Audit logging error: {e}")
        finally:
            db.close()
    
    def _determine_action(self, method: str, path: str) -> str:
        """Determine the action based on HTTP method and path"""
        if method == "GET":
            return "READ"
        elif method == "POST":
            if "/login" in path or "/token" in path:
                return "LOGIN"
            elif "/register" in path:
                return "REGISTER"
            else:
                return "CREATE"
        elif method == "PUT" or method == "PATCH":
            return "UPDATE"
        elif method == "DELETE":
            return "DELETE"
        else:
            return method
    
    def _determine_entity_type(self, path: str) -> str:
        """Determine entity type based on path"""
        if "/users" in path:
            return "User"
        elif "/organizations" in path:
            return "Organization"
        elif "/plans" in path:
            return "Plan"
        elif "/subscriptions" in path:
            return "Subscription"
        elif "/templates" in path:
            return "DocumentTemplate"
        elif "/auth" in path:
            return "Authentication"
        elif "/logs" in path:
            return "AuditLog"
        elif "/metrics" in path:
            return "SystemMetric"
        else:
            return "API"


