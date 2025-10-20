#!/usr/bin/env python3
"""
Script para configurar o arquivo .env e testar a conexão
"""

import os
from pathlib import Path

def create_env_file():
    """Cria o arquivo .env com as configurações corretas"""
    env_content = """# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ambiental_db

# Security
SECRET_KEY=your-super-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development
DEBUG=True

# CORS
ALLOWED_ORIGINS_STR=http://localhost:3000,http://localhost:8080,http://localhost:4200
"""
    
    env_path = Path(__file__).parent / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print(f"Arquivo .env criado em: {env_path}")
    return env_path

def test_database_connection():
    """Testa a conexão com o banco de dados"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='ambiental_db',
            user='postgres',
            password='postgres'
        )
        conn.close()
        print("OK - Conexao com banco de dados OK!")
        return True
    except Exception as e:
        print(f"ERRO - Erro na conexao: {e}")
        return False

def main():
    print("Configurando ambiente...")
    
    # Criar arquivo .env
    env_path = create_env_file()
    
    # Testar conexão
    if test_database_connection():
        print("\nSUCESSO - Configuracao concluida com sucesso!")
        print("Agora voce pode executar: python main.py")
    else:
        print("\nERRO - Erro na configuracao. Verifique se o PostgreSQL esta rodando.")

if __name__ == "__main__":
    main()
