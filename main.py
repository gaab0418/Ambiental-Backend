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

def main():
    """Função principal para executar o servidor"""
    print("=" * 50)
    print("Sistema configurado e funcionando")
    print("Iniciando servidor...")
    print("=" * 50)
    print("Pressione Ctrl+C para parar")
    
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
        print(f"\nErro ao iniciar servidor: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())



