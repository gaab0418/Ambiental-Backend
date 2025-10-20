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
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text

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

class InitDatabaseRequest(BaseModel):
    database: DatabaseConfig
    seed_demo: bool = False

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

def reset_complete_database(db_config: DatabaseConfig, admin_email: str, admin_full_name: str, admin_password: str, seed_demo: bool = False) -> tuple[bool, str]:
    """Reset completo do banco de dados - remove todas as tabelas e recria tudo"""
    try:
        print("Iniciando reset completo do banco de dados...")
        
        # Conectar ao banco
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.username,
            password=db_config.password
        )
        
        with conn.cursor() as cursor:
            # 1. Remover todas as tabelas do schema public (incluindo alembic_version)
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"Removendo {len(tables)} tabelas...")
                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    print(f"   - Tabela '{table}' removida")
            
            # 2. Remover sequências também
            cursor.execute("""
                SELECT sequencename FROM pg_sequences 
                WHERE schemaname = 'public'
            """)
            sequences = [row[0] for row in cursor.fetchall()]
            
            if sequences:
                print(f"Removendo {len(sequences)} sequências...")
                for sequence in sequences:
                    cursor.execute(f"DROP SEQUENCE IF EXISTS {sequence} CASCADE")
                    print(f"   - Sequência '{sequence}' removida")
            
            conn.commit()
            print("Banco de dados resetado com sucesso!")
        
        conn.close()
        
        # 3. Atualizar DATABASE_URL no ambiente
        os.environ["DATABASE_URL"] = f"postgresql://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
        
        # 4. Recriar todas as tabelas usando SQLAlchemy
        print("Recriando tabelas...")
        Base.metadata.create_all(bind=engine)
        print("Tabelas recriadas com sucesso!")
        
        # 5. Marcar migrations do Alembic como aplicadas (stamp head)
        print("Sincronizando histórico de migrations...")
        try:
            # Usar stamp para marcar que o banco está na versão mais recente
            result = subprocess.run(
                ["alembic", "stamp", "head"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                check=True
            )
            print("Histórico de migrations sincronizado!")
        except subprocess.CalledProcessError as e:
            print(f"Aviso: Erro ao sincronizar migrations: {e}")
            print("O banco de dados está criado, mas o histórico de migrations pode estar dessincronizado.")
        except FileNotFoundError:
            print("Aviso: Alembic não encontrado. Ignorando sincronização de migrations.")
        
        # 6. Popular dados iniciais
        print("Populando dados iniciais...")
        init_database(
            admin_email=admin_email,
            admin_full_name=admin_full_name,
            admin_password=admin_password,
            seed_demo=seed_demo
        )
        print("Dados iniciais criados com sucesso!")
        
        return True, "Banco de dados resetado e inicializado com sucesso!"
        
    except Exception as e:
        return False, f"Erro no reset do banco: {str(e)}"

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

                        <!-- Database Options -->
                        <div class="border-b border-gray-200 pb-6">
                            <h3 class="text-lg font-medium text-gray-900 mb-4">⚙️ Opções de Inicialização</h3>
                            <div class="space-y-4">
                                <div class="flex items-center">
                                    <input type="checkbox" id="seedDemo" name="seedDemo"
                                           class="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded">
                                    <label for="seedDemo" class="ml-2 block text-sm text-gray-700">Carregar dados de demonstração (planos, templates, org de teste)</label>
                                </div>
                                <div class="bg-blue-50 border border-blue-200 rounded-md p-4">
                                    <p class="text-sm text-blue-800">
                                        <strong>Nota:</strong> Um usuário administrador padrão será criado automaticamente:
                                    </p>
                                    <ul class="text-sm text-blue-700 mt-2 ml-4 list-disc">
                                        <li>Email: <code>admin@ambiental.com</code></li>
                                        <li>Senha: <code>Admin@123</code></li>
                                    </ul>
                                    <p class="text-sm text-blue-800 mt-2">
                                        <strong>IMPORTANTE:</strong> Altere a senha após o primeiro login!
                                    </p>
                                </div>
                            </div>
                        </div>

                        <!-- Import Button -->
                        <div class="flex justify-end">
                            <button type="button" id="importBtn" 
                                    class="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                                📁 Importar Configuração de Banco
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

                <!-- Database Management Card -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">🗄️ Gerenciar Banco de Dados</h3>
                    <p class="text-sm text-gray-600 mb-4">
                        Inicialize ou reset o banco de dados conforme necessário.
                    </p>
                    <div class="space-y-3">
                        <button id="initDbBtn" 
                                class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
                            🚀 Inicializar Banco de Dados
                        </button>
                        <button id="resetDbBtn" 
                                class="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
                            🗑️ Resetar Banco de Dados
                        </button>
                    </div>
                    <div id="dbResult" class="mt-2 text-sm"></div>
                </div>
            </div>
        </div>

        <!-- Hidden file input for JSON import -->
        <input type="file" id="jsonFileInput" accept=".json" style="display: none;">

        <!-- Reset Database Confirmation Modal -->
        <div id="resetModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full hidden z-50">
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                        <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 text-center mb-4">Confirmar Reset do Banco de Dados</h3>
                    <div class="mt-2 px-7 py-3">
                        <p class="text-sm text-gray-500 mb-4">
                            <strong class="text-red-600">ATENÇÃO:</strong> Esta ação irá apagar TODOS os dados do banco de dados, incluindo:
                        </p>
                        <ul class="text-sm text-gray-500 mb-4 list-disc list-inside">
                            <li>Todas as tabelas e dados</li>
                            <li>Histórico de migrations do Alembic</li>
                            <li>Usuários, organizações e configurações</li>
                        </ul>
                        <p class="text-sm text-gray-500 mb-4">
                            Após o reset, o sistema será reinicializado automaticamente com dados de teste.
                        </p>
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">
                                Digite <strong>CONFIRMAR</strong> para prosseguir:
                            </label>
                            <input type="text" id="confirmResetInput" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                   placeholder="Digite CONFIRMAR aqui">
                        </div>
                    </div>
                    <div class="flex justify-end space-x-3 px-4 py-3">
                        <button id="cancelResetBtn" 
                                class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">
                            Cancelar
                        </button>
                        <button id="confirmResetBtn" 
                                class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled>
                            Resetar Banco
                        </button>
                    </div>
                </div>
            </div>
        </div>
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
        
        // Database Management Elements
        const initDbBtn = document.getElementById('initDbBtn');
        const resetDbBtn = document.getElementById('resetDbBtn');
        const dbResult = document.getElementById('dbResult');
        const resetModal = document.getElementById('resetModal');
        const confirmResetInput = document.getElementById('confirmResetInput');
        const confirmResetBtn = document.getElementById('confirmResetBtn');
        const cancelResetBtn = document.getElementById('cancelResetBtn');

        // Load saved configuration on page load
        async function loadSavedConfig() {
            try {
                const response = await fetch('/api/config/load');
                const result = await response.json();
                
                if (result.success && result.database) {
                    const db = result.database;
                    document.getElementById('dbHost').value = db.host || '';
                    document.getElementById('dbPort').value = db.port || 5432;
                    document.getElementById('dbName').value = db.database || '';
                    document.getElementById('dbUser').value = db.username || '';
                    document.getElementById('dbPassword').value = db.password || '';
                    
                    // Update status to show configuration was loaded
                    configStatus.textContent = 'Carregado';
                    configStatus.className = 'text-sm font-medium text-blue-600';
                }
            } catch (error) {
                console.log('Nenhuma configuração prévia encontrada');
            }
        }

        // Load config when page loads
        window.addEventListener('DOMContentLoaded', loadSavedConfig);

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

                alert('✅ Configurações de banco importadas com sucesso!');
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


        // Initialize Database functionality
        initDbBtn.addEventListener('click', async () => {
            const dbConfig = {
                host: document.getElementById('dbHost').value,
                port: parseInt(document.getElementById('dbPort').value),
                database: document.getElementById('dbName').value,
                username: document.getElementById('dbUser').value,
                password: document.getElementById('dbPassword').value
            };

            const seedDemo = document.getElementById('seedDemo').checked;

            if (!dbConfig.host || !dbConfig.database || !dbConfig.username || !dbConfig.password) {
                dbResult.innerHTML = '<span class="text-red-600">❌ Configure primeiro a conexão com o banco de dados</span>';
                return;
            }

            // Disable button and show loading
            initDbBtn.disabled = true;
            initDbBtn.textContent = '🔄 Inicializando...';

            try {
                const response = await fetch('/api/init-database', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        database: dbConfig,
                        seed_demo: seedDemo
                    })
                });

                const result = await response.json();

                if (result.success) {
                    dbResult.innerHTML = '<span class="text-green-600">✅ ' + result.message.replace(/\\n/g, '<br>') + '</span>';
                    // Update status indicators
                    dbStatus.textContent = 'Inicializado';
                    dbStatus.className = 'text-sm font-medium text-green-600';
                    configStatus.textContent = 'Configurado';
                    configStatus.className = 'text-sm font-medium text-green-600';
                    initStatus.textContent = 'Concluído';
                    initStatus.className = 'text-sm font-medium text-green-600';
                } else {
                    dbResult.innerHTML = '<span class="text-red-600">❌ ' + result.message + '</span>';
                }
            } catch (error) {
                dbResult.innerHTML = '<span class="text-red-600">❌ Erro na requisição: ' + error.message + '</span>';
            }

            // Re-enable button
            initDbBtn.disabled = false;
            initDbBtn.textContent = '🚀 Inicializar Banco de Dados';
        });

        // Reset Database functionality
        resetDbBtn.addEventListener('click', () => {
            resetModal.classList.remove('hidden');
            confirmResetInput.value = '';
            confirmResetBtn.disabled = true;
        });

        cancelResetBtn.addEventListener('click', () => {
            resetModal.classList.add('hidden');
            confirmResetInput.value = '';
            confirmResetBtn.disabled = true;
        });

        // Enable/disable confirm button based on input
        confirmResetInput.addEventListener('input', () => {
            const isValid = confirmResetInput.value === 'CONFIRMAR';
            confirmResetBtn.disabled = !isValid;
        });

        // Confirm reset database
        confirmResetBtn.addEventListener('click', async () => {
            if (confirmResetInput.value !== 'CONFIRMAR') {
                return;
            }

            const dbConfig = {
                host: document.getElementById('dbHost').value,
                port: parseInt(document.getElementById('dbPort').value),
                database: document.getElementById('dbName').value,
                username: document.getElementById('dbUser').value,
                password: document.getElementById('dbPassword').value
            };

            const seedDemo = document.getElementById('seedDemo').checked;

            if (!dbConfig.host || !dbConfig.database || !dbConfig.username || !dbConfig.password) {
                dbResult.innerHTML = '<span class="text-red-600">❌ Configure primeiro a conexão com o banco de dados</span>';
                return;
            }

            // Disable buttons and show loading
            confirmResetBtn.disabled = true;
            confirmResetBtn.textContent = '🔄 Resetando...';
            resetDbBtn.disabled = true;
            resetDbBtn.textContent = '🔄 Processando...';

            try {
                const response = await fetch('/api/reset-database', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        database: dbConfig,
                        seed_demo: seedDemo
                    })
                });

                const result = await response.json();

                if (result.success) {
                    dbResult.innerHTML = '<span class="text-green-600">✅ ' + result.message.replace(/\\n/g, '<br>') + '</span>';
                    // Update status indicators
                    dbStatus.textContent = 'Resetado';
                    dbStatus.className = 'text-sm font-medium text-green-600';
                    configStatus.textContent = 'Configurado';
                    configStatus.className = 'text-sm font-medium text-green-600';
                    initStatus.textContent = 'Concluído';
                    initStatus.className = 'text-sm font-medium text-green-600';
                } else {
                    dbResult.innerHTML = '<span class="text-red-600">❌ ' + result.message + '</span>';
                }
            } catch (error) {
                dbResult.innerHTML = '<span class="text-red-600">❌ Erro na requisição: ' + error.message + '</span>';
            }

            // Re-enable buttons
            confirmResetBtn.disabled = false;
            confirmResetBtn.textContent = 'Resetar Banco';
            resetDbBtn.disabled = false;
            resetDbBtn.textContent = '🗑️ Resetar Banco de Dados';
            
            // Close modal
            resetModal.classList.add('hidden');
        });

        // Close modal when clicking outside
        resetModal.addEventListener('click', (e) => {
            if (e.target === resetModal) {
                resetModal.classList.add('hidden');
                confirmResetInput.value = '';
                confirmResetBtn.disabled = true;
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

@app.post("/api/init-database")
async def init_database_endpoint(payload: InitDatabaseRequest):
    """Endpoint para inicializar o banco de dados"""
    try:
        # Test database connection first
        success, message = test_database_connection(payload.database)
        if not success:
            return JSONResponse({"success": False, "message": message}, status_code=400)
        
        # Save database configuration
        config_manager.set_config("database", payload.database.model_dump())
        
        # Update database URL in environment
        db_config = payload.database
        os.environ["DATABASE_URL"] = f"postgresql://{db_config.username}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
        
        # Create .env file
        create_minimal_env(payload.database)
        
        # Initialize database with default admin credentials
        try:
            init_database(
                admin_email="admin@ambiental.com",
                admin_full_name="Administrador do Sistema",
                admin_password="Admin@123",
                seed_demo=payload.seed_demo
            )
            return JSONResponse({
                "success": True, 
                "message": "Banco de dados inicializado com sucesso!\\n\\nCriado:\\n- Todas as tabelas\\n- Roles do sistema\\n- Organização Administrativa\\n- Usuário Administrador (admin@ambiental.com)\\n\\n⚠️ IMPORTANTE: Altere a senha padrão após o primeiro login!"
            })
        except Exception as e:
            return JSONResponse({
                "success": False, 
                "message": f"Erro na inicialização do banco: {str(e)}"
            }, status_code=500)
            
    except Exception as e:
        return JSONResponse({
            "success": False, 
            "message": f"Erro na inicialização: {str(e)}"
        }, status_code=500)

@app.post("/api/reset-database")
async def reset_database_endpoint(payload: InitDatabaseRequest):
    """Endpoint para resetar completamente o banco de dados"""
    try:
        # Test database connection first
        success, message = test_database_connection(payload.database)
        if not success:
            return JSONResponse({"success": False, "message": message}, status_code=400)
        
        # Save database configuration
        config_manager.set_config("database", payload.database.model_dump())
        
        # Create .env file
        create_minimal_env(payload.database)
        
        # Execute complete database reset with default admin credentials
        success, message = reset_complete_database(
            db_config=payload.database,
            admin_email="admin@ambiental.com",
            admin_full_name="Administrador do Sistema",
            admin_password="Admin@123",
            seed_demo=payload.seed_demo
        )
        
        if success:
            return JSONResponse({
                "success": True, 
                "message": f"Reset completo realizado com sucesso!\\n\\n{message}\\n\\nO banco foi completamente resetado e reinicializado.\\n\\n⚠️ IMPORTANTE: Use admin@ambiental.com / Admin@123 para login e altere a senha!"
            })
        else:
            return JSONResponse({
                "success": False, 
                "message": f"Erro no reset do banco: {message}"
            }, status_code=500)
            
    except Exception as e:
        return JSONResponse({
            "success": False, 
            "message": f"Erro no reset do banco: {str(e)}"
        }, status_code=500)

@app.get("/api/config/load")
async def load_config():
    """Carrega configurações salvas"""
    db_config = config_manager.get_config("database")
    if db_config:
        return JSONResponse({"success": True, "database": db_config})
    return JSONResponse({"success": False, "database": None})

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
