#!/usr/bin/env python3
"""
Ambiental SaaS - Servidor Principal
Script consolidado para executar toda a aplicação
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from app.config import settings
from app.api.v1 import auth, organization, billing, master
from app.database import engine, SessionLocal
from app.models import Base

# Configuração da aplicação principal
app = FastAPI(
    title="Ambiental SaaS API",
    description="Backend completo para plataforma SaaS Ambiental",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(organization.router, prefix="/api/organization", tags=["Organization"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(master.router, prefix="/api/master", tags=["Master Admin"])

class ConfigManager:
    """Gerenciador de configurações usando SQLite para armazenamento"""
    
    def __init__(self):
        self.config_db_path = Path(__file__).parent / "config.db"
        self.init_config_db()
    
    def init_config_db(self):
        """Inicializa o banco SQLite para configurações"""
        conn = sqlite3.connect(self.config_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_config(self, key: str) -> Optional[Any]:
        """Recupera uma configuração"""
        conn = sqlite3.connect(self.config_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM configs WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Recupera todas as configurações"""
        conn = sqlite3.connect(self.config_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM configs")
        results = cursor.fetchall()
        
        conn.close()
        
        return {key: json.loads(value) for key, value in results}

config_manager = ConfigManager()

def check_system_status():
    """Verifica o status do sistema"""
    try:
        # Verifica se o banco de dados está configurado
        db_config = config_manager.get_config("database")
        if not db_config:
            return False, "Sistema não configurado. Execute: python setup.py"
        
        # Verifica se o .env existe
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            return False, "Arquivo .env não encontrado. Execute: python setup.py"
        
        # Verifica conexão com banco
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return True, "Sistema funcionando corretamente"
        
    except Exception as e:
        return False, f"Erro no sistema: {str(e)}"

@app.get("/")
async def root():
    """Endpoint raiz com informações do sistema"""
    is_healthy, message = check_system_status()
    
    return {
        "message": "Ambiental SaaS API - Backend completo e escalável",
        "status": "healthy" if is_healthy else "error",
        "message_detail": message,
        "version": "1.0.0",
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    is_healthy, message = check_system_status()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "message": message,
        "environment": settings.environment,
        "database": "connected" if is_healthy else "disconnected"
    }

@app.get("/status")
async def system_status():
    """Endpoint detalhado de status do sistema"""
    is_healthy, message = check_system_status()
    
    # Recupera configurações do sistema
    system_config = config_manager.get_config("system")
    db_config = config_manager.get_config("database")
    
    return {
        "system": {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": message,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "database": {
            "status": "connected" if is_healthy else "disconnected",
            "host": db_config.get("host", "N/A") if db_config else "N/A",
            "database": db_config.get("database", "N/A") if db_config else "N/A"
        },
        "configuration": {
            "system_configured": system_config is not None,
            "database_configured": db_config is not None,
            "env_file_exists": (Path(__file__).parent / ".env").exists()
        }
    }

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Painel administrativo simples"""
    is_healthy, message = check_system_status()
    
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ambiental SaaS - Admin Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900">🌱 Ambiental SaaS</h1>
                    <p class="text-gray-600 mt-2">Painel Administrativo</p>
                </div>
                <div class="text-right">
                    <div class="text-sm text-gray-500">Versão 1.0.0</div>
                    <div class="text-xs text-gray-400">Servidor Principal</div>
                </div>
            </div>
        </div>

        <!-- Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center">
                    <div class="p-2 rounded-full bg-green-100">
                        <div class="w-6 h-6 text-green-600">✅</div>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Status</p>
                        <p class="text-lg font-semibold text-gray-900">{'Saudável' if is_healthy else 'Erro'}</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center">
                    <div class="p-2 rounded-full bg-blue-100">
                        <div class="w-6 h-6 text-blue-600">🌐</div>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Ambiente</p>
                        <p class="text-lg font-semibold text-gray-900">{settings.environment.title()}</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center">
                    <div class="p-2 rounded-full bg-purple-100">
                        <div class="w-6 h-6 text-purple-600">📊</div>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Debug</p>
                        <p class="text-lg font-semibold text-gray-900">{'Ativo' if settings.debug else 'Inativo'}</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center">
                    <div class="p-2 rounded-full bg-yellow-100">
                        <div class="w-6 h-6 text-yellow-600">🔧</div>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Porta</p>
                        <p class="text-lg font-semibold text-gray-900">8000</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Message Card -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">📋 Status do Sistema</h3>
            <div class="bg-gray-50 rounded-lg p-4">
                <p class="text-sm text-gray-700">{message}</p>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">🚀 Ações Rápidas</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <a href="/docs" class="block p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors">
                    <div class="text-center">
                        <div class="text-2xl mb-2">📚</div>
                        <p class="text-sm font-medium text-blue-900">API Docs</p>
                        <p class="text-xs text-blue-700">Swagger UI</p>
                    </div>
                </a>
                
                <a href="/redoc" class="block p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors">
                    <div class="text-center">
                        <div class="text-2xl mb-2">📖</div>
                        <p class="text-sm font-medium text-green-900">ReDoc</p>
                        <p class="text-xs text-green-700">Documentação</p>
                    </div>
                </a>
                
                <a href="/status" class="block p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors">
                    <div class="text-center">
                        <div class="text-2xl mb-2">📊</div>
                        <p class="text-sm font-medium text-purple-900">Status</p>
                        <p class="text-xs text-purple-700">Detalhado</p>
                    </div>
                </a>
                
                <a href="/health" class="block p-4 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition-colors">
                    <div class="text-center">
                        <div class="text-2xl mb-2">❤️</div>
                        <p class="text-sm font-medium text-yellow-900">Health</p>
                        <p class="text-xs text-yellow-700">Check</p>
                    </div>
                </a>
            </div>
        </div>

        <!-- System Info -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">ℹ️ Informações do Sistema</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                    <p><strong>Versão:</strong> 1.0.0</p>
                    <p><strong>Ambiente:</strong> {settings.environment}</p>
                    <p><strong>Debug:</strong> {'Ativo' if settings.debug else 'Inativo'}</p>
                </div>
                <div>
                    <p><strong>Porta:</strong> 8000</p>
                    <p><strong>Host:</strong> 0.0.0.0</p>
                    <p><strong>Status:</strong> {'Funcionando' if is_healthy else 'Erro'}</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    """

@app.get("/api/config")
async def get_config():
    """Endpoint para recuperar configurações do sistema"""
    try:
        config = config_manager.get_all_configs()
        return JSONResponse(config)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

def main():
    """Função principal para executar o servidor"""
    print("Ambiental SaaS - Servidor Principal")
    print("=" * 50)
    
    # Verifica se o sistema foi configurado
    is_healthy, message = check_system_status()
    if not is_healthy:
        print(f"ERRO: {message}")
        print("\nPara configurar o sistema, execute:")
        print("python setup.py")
        return 1
    
    print("Sistema configurado e funcionando")
    print("Iniciando servidor...")
    print("=" * 50)
    print("API Documentation: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("Admin Panel: http://localhost:8000/admin")
    print("Health Check: http://localhost:8000/health")
    print("Status: http://localhost:8000/status")
    print("=" * 50)
    print("Pressione Ctrl+C para parar")
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug"
        )
    except KeyboardInterrupt:
        print("\nServidor interrompido pelo usuário")
        return 0
    except Exception as e:
        print(f"\nErro ao iniciar servidor: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
