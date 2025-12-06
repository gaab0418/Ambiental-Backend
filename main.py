#!/usr/bin/env python3
"""
Ambiental SaaS - Servidor Principal
Wrapper para executar app/main.py com uvicorn
"""

import sys
import uvicorn
from pathlib import Path

# Adiciona o diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from scripts.logger import LOG_ROOT, StartupLogger
from scripts.run_tests import run_test_suite
from scripts.validate_db import ensure_database_ready

def main():
    """Função principal para executar o servidor"""
    print("=" * 60)
    print("Ambiental SaaS - Inicialização Segura")
    print("=" * 60)

    print("\n[1/3] Validando banco de dados...")
    validation = ensure_database_ready()
    if not validation.get("ready"):
        print("❌ Banco de dados não está pronto. Consulte os logs para detalhes.")
        print(f"   Arquivo de log: {LOG_ROOT / 'database.log'}")
        return 1
    print("✅ Banco de dados pronto!")

    print("\n[2/3] Executando suíte completa de testes...")
    test_result = run_test_suite()
    if not test_result["success"]:
        print("❌ Falha nos testes automáticos. Servidor não será iniciado.")
        print(f"   Consulte o log em: {LOG_ROOT / 'tests.log'}")
        return 1
    print(f"✅ Testes concluídos em {test_result['duration_seconds']}s")
    
    # Verificar se os dados do seed ainda existem após os testes
    print("\n[2.5/3] Verificando integridade do banco após testes...")
    from app.database import SessionLocal
    from app.models import Organization, User
    from app.config import settings
    
    check_db = SessionLocal()
    try:
        admin_org = check_db.query(Organization).filter(Organization.slug == "org-admin").first()
        admin_user = check_db.query(User).filter(User.email == settings.initial_admin_email).first()
        
        if not admin_org or not admin_user:
            print("⚠️  Aviso: Dados do seed não encontrados após testes!")
            print("   Tentando restaurar dados mínimos...")
            # Tentar fazer seed novamente
            from scripts.validate_db import _seed_admin_if_needed, ValidationReport
            report = ValidationReport()
            _seed_admin_if_needed(report)
            if report.seeded_admin:
                print("✅ Dados mínimos restaurados após testes")
            else:
                print("⚠️  Não foi possível restaurar dados. Verifique os logs.")
                StartupLogger.error("Dados do seed desapareceram após testes", log_name="database")
        else:
            print(f"✅ Dados do seed intactos (Org: {admin_org.id}, User: {admin_user.id})")
    finally:
        check_db.close()

    print("\n[3/3] Iniciando servidor FastAPI...")
    print("=" * 60)
    print("Sistema configurado e funcionando")
    print("Pressione Ctrl+C para parar")
    StartupLogger.info("Validação concluída. Iniciando servidor.", log_name="startup")
    
    try:
        uvicorn.run(
            "app.main:app",  # Aponta para app/main.py
            host="0.0.0.0",
            port=8000,
            reload=settings.debug,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServidor interrompido pelo usuário")
        return 0
    except Exception as e:
        StartupLogger.exception("Erro ao iniciar servidor", e, log_name="startup")
        print(f"\nErro ao iniciar servidor: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())



