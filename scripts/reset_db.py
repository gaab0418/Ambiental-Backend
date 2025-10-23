#!/usr/bin/env python3
"""
Script para resetar completamente o banco de dados
ATENÇÃO: Este script irá apagar TODOS os dados!
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database import engine
from app.models import Base

def reset_database():
    """Reset the database by dropping all tables."""
    print("ATENCAO: Este script ira APAGAR TODOS os dados do banco!")
    print("Certifique-se de que voce tem um backup se necessario.")
    
    # Ask for confirmation
    confirm = input("\nDigite 'SIM' para confirmar que deseja apagar todos os dados: ")
    if confirm.upper() != 'SIM':
        print("Operacao cancelada.")
        return
    
    print("\nIniciando reset do banco de dados...")
    
    try:
        # Drop all tables
        with engine.connect() as conn:
            # Get all table names (PostgreSQL)
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            tables = [row[0] for row in result]
            
            if not tables:
                print("Nenhuma tabela encontrada no banco.")
                return
            
            print(f"Encontradas {len(tables)} tabelas para remover:")
            for table in tables:
                print(f"   - {table}")
            
            # Drop all tables with CASCADE to handle foreign key constraints
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"   Tabela '{table}' removida")
            
            conn.commit()
        
        print("\nBanco de dados resetado com sucesso!")
        print("\nProximos passos:")
        print("1. Execute: python scripts/init_db.py")
        print("2. Execute: python main.py")
        print("3. Teste os endpoints em: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"Erro ao resetar banco de dados: {e}")
        raise

if __name__ == "__main__":
    reset_database()
