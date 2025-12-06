#!/usr/bin/env python3
"""
Script de diagnóstico para verificar dados no banco de dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine
from app.models import Organization, User, Role, UserOrganizationAssociation
from sqlalchemy import inspect, text

def check_database():
    print("=" * 60)
    print("🔍 Diagnóstico do Banco de Dados")
    print("=" * 60)
    
    from app.config import settings
    
    # Verificar conexão
    print("\n[1] Verificando conexão...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexão OK")
            
            # Mostrar banco e schema atuais
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            schema = conn.execute(text("SELECT current_schema()")).scalar()
            print(f"   Banco atual: {db_name}")
            print(f"   Schema atual: {schema}")
            
            # Listar tabelas direto do catálogo
            result_tables = conn.execute(text("""
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename
            """)).fetchall()
            print(f"   Total de tabelas (pg_tables): {len(result_tables)}")
            for schemaname, tablename in result_tables:
                print(f"      - {schemaname}.{tablename}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return
    
    # Verificar tabelas
    print("\n[2] Verificando tabelas...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   Tabelas encontradas: {len(tables)}")
    for table in sorted(tables):
        print(f"   - {table}")
    
    # Verificar dados
    print("\n[3] Verificando dados...")
    db = SessionLocal()
    try:
        # Contar registros
        org_count = db.query(Organization).count()
        user_count = db.query(User).count()
        role_count = db.query(Role).count()
        assoc_count = db.query(UserOrganizationAssociation).count()
        
        print(f"   • Organizações: {org_count}")
        print(f"   • Usuários: {user_count}")
        print(f"   • Roles: {role_count}")
        print(f"   • Associações: {assoc_count}")
        
        # Verificar admin org
        print("\n[4] Verificando organização admin...")
        admin_org = db.query(Organization).filter(Organization.slug == "org-admin").first()
        if admin_org:
            print(f"   ✅ Org encontrada: {admin_org.name} (ID: {admin_org.id})")
        else:
            print("   ❌ Org admin não encontrada")
        
        # Verificar admin user
        print("\n[5] Verificando usuário admin...")
        from app.config import settings
        admin_user = db.query(User).filter(User.email == settings.initial_admin_email).first()
        if admin_user:
            print(f"   ✅ User encontrado: {admin_user.email} (ID: {admin_user.id})")
        else:
            print(f"   ❌ User admin não encontrado (email: {settings.initial_admin_email})")
            # Listar todos os usuários
            all_users = db.query(User).all()
            print(f"   Total de usuários no banco: {len(all_users)}")
            for u in all_users:
                print(f"     - {u.email} (ID: {u.id})")
        
        # Verificar associação
        if admin_user and admin_org:
            print("\n[6] Verificando associação...")
            assoc = db.query(UserOrganizationAssociation).filter(
                UserOrganizationAssociation.user_id == admin_user.id,
                UserOrganizationAssociation.organization_id == admin_org.id
            ).first()
            if assoc:
                print(f"   ✅ Associação encontrada (User: {assoc.user_id}, Org: {assoc.organization_id}, Role: {assoc.role_id})")
            else:
                print("   ❌ Associação não encontrada")
        
        # Verificar URL do banco
        print("\n[7] Informações da conexão...")
        print(f"   Database URL: {settings.database_url}")
        
    finally:
        db.close()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        from app.config import settings
        check_database()
    except Exception as e:
        import traceback
        print(f"❌ Erro ao executar diagnóstico: {e}")
        print(traceback.format_exc())
        sys.exit(1)

