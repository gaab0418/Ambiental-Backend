"""
Database Validation Utility
Validates database connection and table existence
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from typing import Dict, Any, List, Tuple
import sys

from app.models import Base


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


def _get_defined_tables() -> List[str]:
    """Retorna lista de tabelas definidas nos modelos, excluindo alembic_version"""
    all_tables = list(Base.metadata.tables.keys())
    # Excluir alembic_version da lista de tabelas requeridas
    return [t for t in all_tables if t != "alembic_version"]


def check_tables_exist() -> tuple[bool, str, list]:
    """
    Verify if required tables exist in the database
    
    Returns:
        tuple: (tables_exist: bool, message: str, missing_tables: list)
    """
    required_tables = _get_defined_tables()
    
    try:
        from app.database import engine
        
        # Get inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Filtrar alembic_version das tabelas existentes para comparação
        existing_tables_filtered = [t for t in existing_tables if t != "alembic_version"]
        
        # Check which required tables are missing
        missing_tables = [table for table in required_tables if table not in existing_tables_filtered]
        
        if missing_tables:
            return False, f"Missing tables: {', '.join(missing_tables[:5])}{'...' if len(missing_tables) > 5 else ''} ({len(missing_tables)} total)", missing_tables
        
        return True, "All required tables exist", []
    
    except OperationalError as e:
        return False, f"Error checking tables: {str(e)}", required_tables
    
    except Exception as e:
        return False, f"Unexpected error checking tables: {str(e)}", required_tables


def ensure_tables_exist(auto_create: bool = False) -> Tuple[bool, str, list, list]:
    """
    Ensure tables exist, optionally attempting to create missing ones.
    
    Returns:
        tuple: (tables_ok, message, missing_tables, created_tables)
    """
    tables_exist, message, missing_tables = check_tables_exist()
    created_tables: list = []

    if tables_exist or not auto_create:
        return tables_exist, message, missing_tables, created_tables

    # PRIMEIRO: Tentar executar Alembic antes de criar tabelas manualmente
    alembic_success = False
    try:
        from pathlib import Path
        import subprocess
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # Verificar se há múltiplas heads
        heads_result = subprocess.run(
            ["alembic", "heads"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        heads_output = heads_result.stdout.strip() if heads_result.returncode == 0 else ""
        heads_list = [h.strip() for h in heads_output.split('\n') if h.strip() and not h.startswith('INFO')]
        
        # Escolher target baseado no número de heads
        if len(heads_list) > 1:
            upgrade_target = "heads"
        else:
            upgrade_target = "head"
        
        alembic_result = subprocess.run(
            ["alembic", "upgrade", upgrade_target],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if alembic_result.returncode == 0:
            # Alembic executou com sucesso, verificar novamente
            tables_exist_after, message_after, missing_after = check_tables_exist()
            if tables_exist_after:
                alembic_success = True
                return True, "Tables created via Alembic migrations", [], []
    except Exception as e:
        # Se Alembic falhar, continuar com criação manual
        pass
    
    # Se Alembic não funcionou, criar tabelas manualmente
    if not alembic_success:
        try:
            from app.database import engine
            from sqlalchemy import text
            print("[ensure_tables_exist] Alembic não criou todas as tabelas. Iniciando fallback create_all().")
            print(f"   Criando {len(missing_tables)} tabelas manualmente...")
            
            # Garantir que estamos no schema public
            with engine.connect() as conn:
                # Verificar se o schema public existe
                result = conn.execute(text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name = 'public'
                """))
                if not result.fetchone():
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
                    conn.commit()
            
            # Criar tabelas no schema public (fallback se Alembic não funcionou)
            print(f"   Executando Base.metadata.create_all()...")
            Base.metadata.create_all(bind=engine)
            print(f"   ✅ Base.metadata.create_all() executado")
            
            # Verificar novamente
            inspector = inspect(engine)
            current_tables = inspector.get_table_names()
            print(f"   Tabelas encontradas no banco (após create_all): {len(current_tables)} -> {current_tables}")
            print(f"   Tabelas requeridas (models): {len(_get_defined_tables())} -> {_get_defined_tables()}")
            
            missing_after = [table for table in _get_defined_tables() if table not in current_tables]
            created_tables = [table for table in current_tables if table in missing_tables and table != "alembic_version"]

            if missing_after:
                error_msg = f"Still missing tables: {', '.join(missing_after)}"
                print(f"   ❌ {error_msg}")
                return False, error_msg, missing_after, created_tables
            
            success_msg = f"Missing tables created automatically ({len(created_tables)} created)"
            print(f"   ✅ {success_msg}")
            return True, success_msg, [], created_tables

        except (OperationalError, ProgrammingError, SQLAlchemyError) as e:
            error_msg = f"Error creating tables automatically: {str(e)}"
            print(f"   ❌ {error_msg}")
            return False, error_msg, missing_tables, created_tables
    
    # Se chegou aqui e ainda faltam tabelas, retornar erro
    return tables_exist, message, missing_tables, created_tables


def get_database_status(auto_fix_tables: bool = False) -> Dict[str, Any]:
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
    tables_exist, tables_msg, missing_tables, created_tables = ensure_tables_exist(auto_create=auto_fix_tables)
    
    return {
        "connected": True,
        "connection_message": connection_msg,
        "tables_exist": tables_exist,
        "tables_message": tables_msg,
        "missing_tables": missing_tables,
        "created_tables": created_tables,
        "ready": connected and tables_exist
    }


def validate_database_or_exit(auto_fix_tables: bool = True):
    """
    Validate database connection and tables, exit with error if not ready
    This is meant to be called during application startup
    """
    print("=" * 60)
    print("[INFO] Validando configuracao do banco de dados...")
    print("=" * 60)
    
    status = get_database_status(auto_fix_tables)
    
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
        if status.get("created_tables"):
            print(f"   Tabelas criadas automaticamente: {', '.join(status['created_tables'])}")
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

