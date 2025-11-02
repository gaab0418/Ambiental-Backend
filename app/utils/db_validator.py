"""
Database Validation Utility
Validates database connection and table existence
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from typing import Dict, Any
import sys


def check_database_connection() -> tuple[bool, str]:
    """
    Test if DATABASE_URL is valid and database is reachable
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        from app.database import engine
        
        # Try to connect and execute a simple query
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return True, "Database connection successful"
    
    except OperationalError as e:
        return False, f"Database connection failed: {str(e)}"
    
    except Exception as e:
        return False, f"Unexpected error connecting to database: {str(e)}"


def check_tables_exist() -> tuple[bool, str, list]:
    """
    Verify if required tables exist in the database
    
    Returns:
        tuple: (tables_exist: bool, message: str, missing_tables: list)
    """
    required_tables = [
        "users",
        "organizations", 
        "roles",
        "plans",
        "subscriptions",
        "licenses"
    ]
    
    try:
        from app.database import engine
        
        # Get inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Check which required tables are missing
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            return False, f"Missing tables: {', '.join(missing_tables)}", missing_tables
        
        return True, "All required tables exist", []
    
    except OperationalError as e:
        return False, f"Error checking tables: {str(e)}", required_tables
    
    except Exception as e:
        return False, f"Unexpected error checking tables: {str(e)}", required_tables


def get_database_status() -> Dict[str, Any]:
    """
    Get comprehensive database status including connection and tables
    
    Returns:
        dict: {
            "connected": bool,
            "connection_message": str,
            "tables_exist": bool,
            "tables_message": str,
            "missing_tables": list,
            "ready": bool
        }
    """
    # Check connection first
    connected, connection_msg = check_database_connection()
    
    if not connected:
        return {
            "connected": False,
            "connection_message": connection_msg,
            "tables_exist": False,
            "tables_message": "Cannot check tables - database not connected",
            "missing_tables": [],
            "ready": False
        }
    
    # Check tables
    tables_exist, tables_msg, missing_tables = check_tables_exist()
    
    return {
        "connected": True,
        "connection_message": connection_msg,
        "tables_exist": tables_exist,
        "tables_message": tables_msg,
        "missing_tables": missing_tables,
        "ready": connected and tables_exist
    }


def validate_database_or_exit():
    """
    Validate database connection and tables, exit with error if not ready
    This is meant to be called during application startup
    """
    print("=" * 60)
    print("[INFO] Validando configuracao do banco de dados...")
    print("=" * 60)
    
    status = get_database_status()
    
    if not status["connected"]:
        print("\n[ERRO] Nao foi possivel conectar ao banco de dados!")
        print(f"   Motivo: {status['connection_message']}")
        print("\n[SOLUCAO]")
        print("   1. Verifique se o PostgreSQL esta rodando")
        print("   2. Execute: python setup.py")
        print("   3. Configure a conexao com o banco de dados via interface web")
        print("=" * 60)
        sys.exit(1)
    
    if not status["tables_exist"]:
        print("\n[ERRO] Tabelas do banco de dados nao encontradas!")
        print(f"   Motivo: {status['tables_message']}")
        if status["missing_tables"]:
            print(f"   Tabelas faltando: {', '.join(status['missing_tables'])}")
        print("\n[SOLUCAO]")
        print("   1. Execute: python setup.py")
        print("   2. Acesse: http://localhost:8001")
        print("   3. Inicialize o banco de dados via interface web")
        print("=" * 60)
        sys.exit(1)
    
    print("\n[OK] Banco de dados validado com sucesso!")
    print(f"   {status['connection_message']}")
    print(f"   {status['tables_message']}")
    print("=" * 60)

