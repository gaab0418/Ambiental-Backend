
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH para permitir imports da app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import User
from app.config import settings
from app.core.security import get_password_hash

def reset_password():
    print(f"Tentando resetar senha para: {settings.initial_admin_email}")
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == settings.initial_admin_email).first()
        
        if not user:
            print(f"❌ Usuário {settings.initial_admin_email} não encontrado no banco de dados!")
            return False
            
        print(f"✅ Usuário encontrado (ID: {user.id})")
        
        new_password = settings.initial_admin_password
        hashed = get_password_hash(new_password)
        
        user.hashed_password = hashed
        session.commit()
        
        print("✅ Senha atualizada com sucesso para o valor definido no .env")
        print(f"   Email: {settings.initial_admin_email}")
        print(f"   Nova Senha: {new_password}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar senha: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    reset_password()
