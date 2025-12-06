#!/usr/bin/env python3
"""
Script para executar migrações Alembic automaticamente
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

from scripts.logger import StartupLogger

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_alembic_upgrade() -> Dict[str, Any]:
    """
    Executa 'alembic upgrade head' para aplicar todas as migrações pendentes.
    Se houver múltiplas heads, tenta fazer merge ou usar 'heads'.
    
    Returns:
        dict: Resultado da execução com success, stdout, stderr, returncode
    """
    print("=" * 60)
    print("🔄 Executando migrações Alembic...")
    print("=" * 60)
    
    try:
        # Primeiro, verificar se há múltiplas heads
        heads_result = subprocess.run(
            ["alembic", "heads"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        heads_output = heads_result.stdout.strip() if heads_result.returncode == 0 else ""
        heads_list = [h.strip() for h in heads_output.split('\n') if h.strip() and not h.startswith('INFO')]
        
        # Se houver múltiplas heads, tentar fazer merge ou usar 'heads'
        if len(heads_list) > 1:
            print(f"⚠️  Múltiplas heads detectadas: {len(heads_list)}")
            print(f"   Heads: {', '.join(heads_list)}")
            print("   Tentando fazer upgrade de todas as heads...")
            upgrade_target = "heads"
            
            # Tentar criar uma migração de merge se não existir
            try:
                # Verificar se já existe uma migração de merge
                merge_check = subprocess.run(
                    ["alembic", "history", "--verbose"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if "merge" not in merge_check.stdout.lower():
                    print("   💡 Dica: Considere criar uma migração de merge com:")
                    print(f"      alembic merge -m 'merge_heads' {' '.join(heads_list)}")
            except Exception:
                pass
        else:
            upgrade_target = "head"
        
        # Executar alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", upgrade_target],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutos de timeout
        )
        
        success = result.returncode == 0
        
        if success:
            print("✅ Migrações Alembic aplicadas com sucesso")
            if result.stdout:
                print(result.stdout)
        else:
            print("❌ Erro ao executar migrações Alembic")
            if result.stderr:
                print(f"Erro: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
        
        log_details = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        
        if success:
            StartupLogger.info(
                "Migrações Alembic aplicadas com sucesso",
                log_name="database",
                details=log_details,
            )
        else:
            StartupLogger.error(
                "Falha ao aplicar migrações Alembic",
                log_name="database",
                details=log_details,
            )
        
        return {
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "Timeout ao executar migrações Alembic (mais de 2 minutos)"
        print(f"❌ {error_msg}")
        StartupLogger.error(error_msg, log_name="database")
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": error_msg,
        }
    except FileNotFoundError:
        error_msg = "Alembic não encontrado. Instale com: pip install alembic"
        print(f"❌ {error_msg}")
        StartupLogger.error(error_msg, log_name="database")
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": error_msg,
        }
    except Exception as e:
        error_msg = f"Erro inesperado ao executar Alembic: {e}"
        print(f"❌ {error_msg}")
        StartupLogger.error(error_msg, log_name="database")
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def check_alembic_current() -> Dict[str, Any]:
    """
    Verifica a versão atual do Alembic no banco.
    
    Returns:
        dict: Informações sobre a versão atual
    """
    try:
        result = subprocess.run(
            ["alembic", "current"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        return {
            "success": result.returncode == 0,
            "current": result.stdout.strip() if result.returncode == 0 else None,
            "stderr": result.stderr if result.returncode != 0 else None,
        }
    except Exception as e:
        return {
            "success": False,
            "current": None,
            "stderr": str(e),
        }


if __name__ == "__main__":
    # Verificar versão atual
    print("Verificando versão atual do Alembic...")
    current = check_alembic_current()
    if current["success"]:
        print(f"Versão atual: {current['current']}")
    else:
        print(f"Erro ao verificar versão: {current.get('stderr', 'Unknown error')}")
    
    # Executar upgrade
    result = run_alembic_upgrade()
    sys.exit(0 if result["success"] else 1)

