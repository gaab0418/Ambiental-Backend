"""
Organization credentials resolver for multi-tenant database routing.
Handles SaaS and on-prem connection resolution with encryption.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.organization import Organization
from app.models.org_connection import OrgConnection
from app.core.encryption import EncryptionUtils
from app.config import settings

logger = logging.getLogger(__name__)


class OrgCredentialsResolver:
    """Resolves database credentials for organizations based on deployment mode"""
    
    def __init__(self, db: Session):
        self.db = db
        self.encryption = EncryptionUtils()
    
    def resolve_credentials(
        self, 
        org_id: int, 
        db_type: str = "app"
    ) -> Dict[str, Any]:
        """
        Resolve database credentials for an organization.
        
        Args:
            org_id: Organization ID
            db_type: Type of database (app, vector, logs)
            
        Returns:
            Dictionary with connection details:
            {
                "mode": "saas" | "on_prem",
                "connection_string": "...",
                "host": "...",
                "port": 5432,
                "database": "...",
                "username": "...",
                "password": "...",
                "location": "cloud" | "on_prem"
            }
            
        Raises:
            ValueError: If organization not found or no valid connection configured
        """
        # Get organization
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError(f"Organization {org_id} not found")
        
        if org.status != "active":
            raise ValueError(f"Organization {org_id} is not active (status: {org.status})")
        
        # If SaaS mode, return default cloud database
        if org.mode == "saas":
            return self._get_saas_credentials(db_type)
        
        # If on-prem mode, look up connection details
        if org.mode == "on_prem":
            return self._get_onprem_credentials(org_id, db_type)
        
        raise ValueError(f"Unknown organization mode: {org.mode}")
    
    def _get_saas_credentials(self, db_type: str) -> Dict[str, Any]:
        """Get default SaaS database credentials"""
        # For SaaS, use the default database URL from settings
        # Can be extended to support separate vector/logs databases
        
        connection_string = settings.database_url
        
        # Parse connection string (basic PostgreSQL format)
        # postgresql://username:password@host:port/database
        credentials = {
            "mode": "saas",
            "location": "cloud",
            "db_type": db_type,
            "connection_string": connection_string
        }
        
        # Optional: parse details for convenience
        try:
            if connection_string.startswith("postgresql://"):
                parts = connection_string.replace("postgresql://", "").split("@")
                if len(parts) == 2:
                    user_pass = parts[0].split(":")
                    host_db = parts[1].split("/")
                    host_port = host_db[0].split(":")
                    
                    credentials.update({
                        "username": user_pass[0] if len(user_pass) > 0 else None,
                        "password": user_pass[1] if len(user_pass) > 1 else None,
                        "host": host_port[0] if len(host_port) > 0 else None,
                        "port": int(host_port[1]) if len(host_port) > 1 else 5432,
                        "database": host_db[1] if len(host_db) > 1 else None
                    })
        except Exception as e:
            logger.warning(f"Failed to parse connection string: {e}")
        
        return credentials
    
    def _get_onprem_credentials(self, org_id: int, db_type: str) -> Dict[str, Any]:
        """Get on-prem database credentials from org_connections table"""
        
        # Query for active connection of specified type
        connection = self.db.query(OrgConnection).filter(
            OrgConnection.org_id == org_id,
            OrgConnection.db_type == db_type,
            OrgConnection.is_active == True
        ).first()
        
        if not connection:
            raise ValueError(
                f"No active {db_type} connection found for organization {org_id}"
            )
        
        # Decrypt credentials
        credentials = {
            "mode": "on_prem",
            "location": connection.location,
            "db_type": db_type
        }
        
        # Decrypt and add connection string if available
        if connection.connection_string_encrypted:
            try:
                credentials["connection_string"] = self.encryption.decrypt(
                    connection.connection_string_encrypted
                )
            except Exception as e:
                logger.error(f"Failed to decrypt connection string: {e}")
                raise ValueError("Failed to decrypt connection credentials")
        
        # Decrypt individual fields if available
        try:
            if connection.host_encrypted:
                credentials["host"] = self.encryption.decrypt(connection.host_encrypted)
            
            if connection.database_name_encrypted:
                credentials["database"] = self.encryption.decrypt(connection.database_name_encrypted)
            
            if connection.username_encrypted:
                credentials["username"] = self.encryption.decrypt(connection.username_encrypted)
            
            if connection.password_encrypted:
                credentials["password"] = self.encryption.decrypt(connection.password_encrypted)
            
            if connection.port:
                credentials["port"] = connection.port
            
            # Build connection string if not provided but parts are available
            if "connection_string" not in credentials and all(
                k in credentials for k in ["host", "database", "username", "password"]
            ):
                port = credentials.get("port", 5432)
                credentials["connection_string"] = (
                    f"postgresql://{credentials['username']}:{credentials['password']}"
                    f"@{credentials['host']}:{port}/{credentials['database']}"
                )
        
        except Exception as e:
            logger.error(f"Failed to decrypt connection fields: {e}")
            raise ValueError("Failed to decrypt connection credentials")
        
        return credentials
    
    def add_onprem_connection(
        self,
        org_id: int,
        db_type: str,
        location: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None
    ) -> OrgConnection:
        """
        Add or update on-prem connection credentials for an organization.
        
        Args:
            org_id: Organization ID
            db_type: Type of database (app, vector, logs)
            location: on_prem or cloud
            host, port, database, username, password: Individual connection parameters
            connection_string: Full connection string (alternative to individual params)
            
        Returns:
            Created or updated OrgConnection instance
        """
        # Check if connection already exists
        existing = self.db.query(OrgConnection).filter(
            OrgConnection.org_id == org_id,
            OrgConnection.db_type == db_type
        ).first()
        
        if existing:
            # Update existing
            connection = existing
        else:
            # Create new
            connection = OrgConnection(
                org_id=org_id,
                db_type=db_type,
                location=location
            )
            self.db.add(connection)
        
        # Encrypt and set fields
        if host:
            connection.host_encrypted = self.encryption.encrypt(host)
        if port:
            connection.port = port
        if database:
            connection.database_name_encrypted = self.encryption.encrypt(database)
        if username:
            connection.username_encrypted = self.encryption.encrypt(username)
        if password:
            connection.password_encrypted = self.encryption.encrypt(password)
        if connection_string:
            connection.connection_string_encrypted = self.encryption.encrypt(connection_string)
        
        connection.location = location
        connection.is_active = True
        
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def get_all_connections(self, org_id: int) -> list[OrgConnection]:
        """Get all connections for an organization"""
        return self.db.query(OrgConnection).filter(
            OrgConnection.org_id == org_id
        ).all()


def resolve_org_credentials(db: Session, org_id: int, db_type: str = "app") -> Dict[str, Any]:
    """
    Helper function to resolve organization credentials.
    Use this in n8n workflows and backend services.
    """
    resolver = OrgCredentialsResolver(db)
    return resolver.resolve_credentials(org_id, db_type)



