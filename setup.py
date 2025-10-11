#!/usr/bin/env python3
"""
Ambiental SaaS - Setup Wizard
Script completo de pré-inicialização com interface web
"""

import os
import sys
import json
import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from app.database import engine, SessionLocal, Base
from scripts.init_db import init_database

app = FastAPI(title="Ambiental Setup Wizard", version="1.0.0")

# Modelos Pydantic para validação
class DatabaseConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str

class SystemConfig(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    environment: str = "development"
    debug: bool = True
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8080"]

class FullConfig(BaseModel):
    database: DatabaseConfig
    system: SystemConfig

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
    
    def set_config(self, key: str, value: Any):
        """Salva uma configuração"""
        conn = sqlite3.connect(self.config_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO configs (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, json.dumps(value)))
        
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
    
    def export_config(self) -> Dict[str, Any]:
        """Exporta todas as configurações para JSON"""
        return self.get_all_configs()
    
    def import_config(self, config_data: Dict[str, Any]):
        """Importa configurações de um JSON"""
        for key, value in config_data.items():
            self.set_config(key, value)

config_manager = ConfigManager()

def test_database_connection(db_config: DatabaseConfig) -> tuple[bool, str]:
    """Testa a conexão com o banco PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.username,
            password=db_config.password
        )
        conn.close()
        return True, "Conexão com banco de dados bem-sucedida!"
    except Exception as e:
        return False, f"Erro na conexão: {str(e)}"

def create_minimal_env(db_config: DatabaseConfig):
    """Cria um .env mínimo apenas com configurações de banco"""
    env_content = f"""# Database Configuration
DATABASE_URL=postgresql://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}

# Security (will be configured via web interface)
SECRET_KEY=change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development
DEBUG=True

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
"""
    
    env_path = Path(__file__).parent / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

@app.get("/", response_class=HTMLResponse)
async def setup_page():
    """Página principal do setup wizard"""
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ambiental SaaS - Setup Wizard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: '#059669',
                        secondary: '#0891b2'
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-gray-900">🌱 Ambiental SaaS</h1>
                    <p class="text-gray-600 mt-2">Setup Wizard - Configuração Inicial do Sistema</p>
                </div>
                <div class="text-right">
                    <div class="text-sm text-gray-500">Versão 1.0.0</div>
                    <div class="text-xs text-gray-400">Setup Wizard</div>
                </div>
            </div>
        </div>

        <!-- Progress Steps -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                        <span class="ml-2 text-sm font-medium text-gray-700">Banco de Dados</span>
                    </div>
                    <div class="w-8 h-1 bg-gray-300"></div>
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-gray-300 text-gray-600 rounded-full flex items-center justify-center text-sm font-bold">2</div>
                        <span class="ml-2 text-sm font-medium text-gray-500">Sistema</span>
                    </div>
                    <div class="w-8 h-1 bg-gray-300"></div>
                    <div class="flex items-center">
                        <div class="w-8 h-8 bg-gray-300 text-gray-600 rounded-full flex items-center justify-center text-sm font-bold">3</div>
                        <span class="ml-2 text-sm font-medium text-gray-500">Finalizar</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Configuration Form -->
            <div class="lg:col-span-2">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold text-gray-900 mb-6">Configuração do Sistema</h2>
                    
                    <form id="setupForm" class="space-y-6">
                        <!-- Database Configuration -->
                        <div class="border-b border-gray-200 pb-6">
                            <h3 class="text-lg font-medium text-gray-900 mb-4">📊 Configuração do Banco de Dados</h3>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Host</label>
                                    <input type="text" id="dbHost" name="dbHost" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="localhost" required>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Porta</label>
                                    <input type="number" id="dbPort" name="dbPort" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="5432" value="5432" required>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Nome do Banco</label>
                                    <input type="text" id="dbName" name="dbName" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="ambiental_db" required>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Usuário</label>
                                    <input type="text" id="dbUser" name="dbUser" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="postgres" required>
                                </div>
                                <div class="md:col-span-2">
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Senha</label>
                                    <input type="password" id="dbPassword" name="dbPassword" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="••••••••" required>
                                </div>
                            </div>
                            <button type="button" id="testDbBtn" 
                                    class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                                🔍 Testar Conexão
                            </button>
                            <div id="dbTestResult" class="mt-2 text-sm"></div>
                        </div>

                        <!-- System Configuration -->
                        <div class="border-b border-gray-200 pb-6">
                            <h3 class="text-lg font-medium text-gray-900 mb-4">⚙️ Configuração do Sistema</h3>
                            <div class="space-y-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Chave Secreta</label>
                                    <input type="text" id="secretKey" name="secretKey" 
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                           placeholder="sua-chave-secreta-super-segura" required>
                                </div>
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-2">Expiração Token (min)</label>
                                        <input type="number" id="tokenExpire" name="tokenExpire" 
                                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                               value="15" required>
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-2">Expiração Refresh (dias)</label>
                                        <input type="number" id="refreshExpire" name="refreshExpire" 
                                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                                               value="7" required>
                                    </div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-2">Ambiente</label>
                                    <select id="environment" name="environment" 
                                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent">
                                        <option value="development">Development</option>
                                        <option value="staging">Staging</option>
                                        <option value="production">Production</option>
                                    </select>
                                </div>
                                <div class="flex items-center">
                                    <input type="checkbox" id="debug" name="debug" 
                                           class="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded">
                                    <label for="debug" class="ml-2 block text-sm text-gray-700">Modo Debug</label>
                                </div>
                            </div>
                        </div>

                        <!-- Submit Button -->
                        <div class="flex justify-end space-x-4">
                            <button type="button" id="importBtn" 
                                    class="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                                📁 Importar JSON
                            </button>
                            <button type="submit" 
                                    class="px-6 py-2 bg-primary text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                                🚀 Configurar Sistema
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Sidebar -->
            <div class="space-y-6">
                <!-- Status Card -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">📊 Status do Sistema</h3>
                    <div class="space-y-3">
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-600">Banco de Dados</span>
                            <span id="dbStatus" class="text-sm font-medium text-gray-400">Não testado</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-600">Configuração</span>
                            <span id="configStatus" class="text-sm font-medium text-gray-400">Pendente</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-600">Inicialização</span>
                            <span id="initStatus" class="text-sm font-medium text-gray-400">Pendente</span>
                        </div>
                    </div>
                </div>

                <!-- Help Card -->
                <div class="bg-blue-50 rounded-lg p-6">
                    <h3 class="text-lg font-semibold text-blue-900 mb-4">💡 Ajuda</h3>
                    <div class="space-y-3 text-sm text-blue-800">
                        <div>
                            <strong>Banco de Dados:</strong> Configure a conexão com seu PostgreSQL
                        </div>
                        <div>
                            <strong>Chave Secreta:</strong> Use uma chave forte e única
                        </div>
                        <div>
                            <strong>Importar JSON:</strong> Carregue configurações salvas anteriormente
                        </div>
                    </div>
                </div>

                <!-- Export Card -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">💾 Exportar</h3>
                    <p class="text-sm text-gray-600 mb-4">Salve suas configurações para uso futuro</p>
                    <button id="exportBtn" 
                            class="w-full px-4 py-2 bg-secondary text-white rounded-md hover:bg-cyan-700 focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2">
                        📤 Exportar Configurações
                    </button>
                </div>
            </div>
        </div>

        <!-- Hidden file input for JSON import -->
        <input type="file" id="jsonFileInput" accept=".json" style="display: none;">
    </div>

    <script>
        // DOM Elements
        const form = document.getElementById('setupForm');
        const testDbBtn = document.getElementById('testDbBtn');
        const dbTestResult = document.getElementById('dbTestResult');
        const importBtn = document.getElementById('importBtn');
        const exportBtn = document.getElementById('exportBtn');
        const jsonFileInput = document.getElementById('jsonFileInput');
        const dbStatus = document.getElementById('dbStatus');
        const configStatus = document.getElementById('configStatus');
        const initStatus = document.getElementById('initStatus');

        // Test database connection
        testDbBtn.addEventListener('click', async () => {
            const dbConfig = {
                host: document.getElementById('dbHost').value,
                port: parseInt(document.getElementById('dbPort').value),
                database: document.getElementById('dbName').value,
                username: document.getElementById('dbUser').value,
                password: document.getElementById('dbPassword').value
            };

            if (!dbConfig.host || !dbConfig.database || !dbConfig.username || !dbConfig.password) {
                dbTestResult.innerHTML = '<span class="text-red-600">❌ Preencha todos os campos do banco</span>';
                return;
            }

            testDbBtn.disabled = true;
            testDbBtn.textContent = '🔄 Testando...';

            try {
                const response = await fetch('/api/test-database', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dbConfig)
                });

                const result = await response.json();

                if (result.success) {
                    dbTestResult.innerHTML = '<span class="text-green-600">✅ ' + result.message + '</span>';
                    dbStatus.textContent = 'Conectado';
                    dbStatus.className = 'text-sm font-medium text-green-600';
                } else {
                    dbTestResult.innerHTML = '<span class="text-red-600">❌ ' + result.message + '</span>';
                    dbStatus.textContent = 'Erro';
                    dbStatus.className = 'text-sm font-medium text-red-600';
                }
            } catch (error) {
                dbTestResult.innerHTML = '<span class="text-red-600">❌ Erro na requisição: ' + error.message + '</span>';
                dbStatus.textContent = 'Erro';
                dbStatus.className = 'text-sm font-medium text-red-600';
            }

            testDbBtn.disabled = false;
            testDbBtn.textContent = '🔍 Testar Conexão';
        });

        // Import JSON configuration
        importBtn.addEventListener('click', () => {
            jsonFileInput.click();
        });

        jsonFileInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (!file) return;

            try {
                const text = await file.text();
                const config = JSON.parse(text);

                // Fill form with imported data
                if (config.database) {
                    document.getElementById('dbHost').value = config.database.host || '';
                    document.getElementById('dbPort').value = config.database.port || 5432;
                    document.getElementById('dbName').value = config.database.database || '';
                    document.getElementById('dbUser').value = config.database.username || '';
                    document.getElementById('dbPassword').value = config.database.password || '';
                }

                if (config.system) {
                    document.getElementById('secretKey').value = config.system.secret_key || '';
                    document.getElementById('tokenExpire').value = config.system.access_token_expire_minutes || 15;
                    document.getElementById('refreshExpire').value = config.system.refresh_token_expire_days || 7;
                    document.getElementById('environment').value = config.system.environment || 'development';
                    document.getElementById('debug').checked = config.system.debug || false;
                }

                alert('✅ Configurações importadas com sucesso!');
            } catch (error) {
                alert('❌ Erro ao importar arquivo: ' + error.message);
            }
        });

        // Export configuration
        exportBtn.addEventListener('click', async () => {
            const config = {
                database: {
                    host: document.getElementById('dbHost').value,
                    port: parseInt(document.getElementById('dbPort').value),
                    database: document.getElementById('dbName').value,
                    username: document.getElementById('dbUser').value,
                    password: document.getElementById('dbPassword').value
                },
                system: {
                    secret_key: document.getElementById('secretKey').value,
                    access_token_expire_minutes: parseInt(document.getElementById('tokenExpire').value),
                    refresh_token_expire_days: parseInt(document.getElementById('refreshExpire').value),
                    environment: document.getElementById('environment').value,
                    debug: document.getElementById('debug').checked
                }
            };

            const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ambiental-config.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });

        // Form submission
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const formData = new FormData(form);
            const config = {
                database: {
                    host: document.getElementById('dbHost').value,
                    port: parseInt(document.getElementById('dbPort').value),
                    database: document.getElementById('dbName').value,
                    username: document.getElementById('dbUser').value,
                    password: document.getElementById('dbPassword').value
                },
                system: {
                    secret_key: document.getElementById('secretKey').value,
                    access_token_expire_minutes: parseInt(document.getElementById('tokenExpire').value),
                    refresh_token_expire_days: parseInt(document.getElementById('refreshExpire').value),
                    environment: document.getElementById('environment').value,
                    debug: document.getElementById('debug').checked
                }
            };

            try {
                const response = await fetch('/api/setup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });

                const result = await response.json();

                if (result.success) {
                    alert('🎉 Sistema configurado com sucesso!\\n\\n' + result.message);
                    configStatus.textContent = 'Configurado';
                    configStatus.className = 'text-sm font-medium text-green-600';
                    initStatus.textContent = 'Concluído';
                    initStatus.className = 'text-sm font-medium text-green-600';
                } else {
                    alert('❌ Erro na configuração: ' + result.message);
                }
            } catch (error) {
                alert('❌ Erro na requisição: ' + error.message);
            }
        });

        // Generate random secret key
        document.addEventListener('DOMContentLoaded', () => {
            const secretKeyField = document.getElementById('secretKey');
            if (!secretKeyField.value) {
                const randomKey = Math.random().toString(36).substring(2, 15) + 
                                Math.random().toString(36).substring(2, 15) + 
                                Math.random().toString(36).substring(2, 15);
                secretKeyField.value = randomKey;
            }
        });
    </script>
</body>
</html>
    """

@app.post("/api/test-database")
async def test_database_endpoint(db_config: DatabaseConfig):
    """Endpoint para testar conexão com banco de dados"""
    success, message = test_database_connection(db_config)
    return JSONResponse({"success": success, "message": message})

@app.post("/api/setup")
async def setup_system(config: FullConfig):
    """Endpoint para configurar o sistema completo"""
    try:
        # Test database connection first
        success, message = test_database_connection(config.database)
        if not success:
            return JSONResponse({"success": False, "message": message}, status_code=400)
        
        # Save configurations
        config_manager.set_config("database", config.database.model_dump())
        config_manager.set_config("system", config.system.model_dump())
        
        # Create minimal .env file
        create_minimal_env(config.database)
        
        # Update database URL in settings
        os.environ["DATABASE_URL"] = f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database}"
        
        # Initialize database
        try:
            init_database()
            return JSONResponse({
                "success": True, 
                "message": "Sistema configurado com sucesso!\\n\\nBanco de dados inicializado.\\nArquivo .env criado.\\n\\nVocê pode agora iniciar o servidor principal com: python main.py"
            })
        except Exception as e:
            return JSONResponse({
                "success": False, 
                "message": f"Erro na inicialização do banco: {str(e)}"
            }, status_code=500)
            
    except Exception as e:
        return JSONResponse({
            "success": False, 
            "message": f"Erro na configuração: {str(e)}"
        }, status_code=500)

@app.get("/api/config/export")
async def export_config():
    """Exporta configurações atuais"""
    config = config_manager.export_config()
    return JSONResponse(config)

@app.post("/api/config/import")
async def import_config(config_data: dict):
    """Importa configurações de JSON"""
    try:
        config_manager.import_config(config_data)
        return JSONResponse({"success": True, "message": "Configurações importadas com sucesso!"})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

def main():
    """Função principal para executar o setup wizard"""
    print("Ambiental SaaS - Setup Wizard")
    print("=" * 50)
    print("Iniciando servidor de configuração...")
    print("Acesse: http://localhost:8001")
    print("Pressione Ctrl+C para parar")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001, 
        log_level="info"
    )

if __name__ == "__main__":
    main()
