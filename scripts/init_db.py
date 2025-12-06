#!/usr/bin/env python3
"""
Script para inicializar o banco de dados com dados básicos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Organization, User, Role, Plan, Subscription, License, UserOrganizationAssociation
from app.core.security import get_password_hash
from datetime import datetime, timedelta

def create_system_roles(db: Session):
    """Create system roles"""
    roles = [
        {
            "name": "ADMINISTRATOR",
            "display_name": "System Administrator",
            "description": "Full system access and management",
            "is_system": True
        },
        {
            "name": "CONSULTANT",
            "display_name": "Consultant",
            "description": "External consultant with special permissions",
            "is_system": True
        },
        {
            "name": "ADMIN",
            "display_name": "Organization Administrator",
            "description": "Organization administrator",
            "is_system": True
        },
        {
            "name": "MANAGER",
            "display_name": "Manager",
            "description": "Organization manager",
            "is_system": True
        },
        {
            "name": "MEMBER",
            "display_name": "Member",
            "description": "Regular member",
            "is_system": True
        }
    ]
    
    for role_data in roles:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)
    
    db.commit()
    print("System roles created")

def create_system_plans(db: Session):
    """Create system plans"""
    plans = [
        {
            "name": "TRIAL",
            "display_name": "Trial",
            "description": "Free trial plan - 30 days",
            "price": 0.00,
            "currency": "BRL",
            "max_users": 1,
            "is_system": True
        },
        {
            "name": "BASIC",
            "display_name": "Basic",
            "description": "Basic plan for small teams",
            "price": 0.00,
            "currency": "BRL",
            "max_users": 5,
            "is_system": True
        }
    ]
    
    for plan_data in plans:
        existing_plan = db.query(Plan).filter(Plan.name == plan_data["name"]).first()
        if not existing_plan:
            plan = Plan(**plan_data)
            db.add(plan)
    
    db.commit()
    print("System plans created")

def create_demo_plans_and_templates(db: Session):
    """Create demo plans and templates ONLY - no extra orgs or users"""
    # Create plans
    create_system_plans(db)
    
    # Create templates
    # Get the admin user to be the creator
    admin_user = db.query(User).first()
    if admin_user:
        create_sample_templates(db)
    
    print("   ✅ Demo plans and templates created")

def create_sample_templates(db: Session):
    """Create sample document templates"""
    from app.models.document_template import DocumentTemplate
    
    # Get the first admin user to be the creator
    admin_user = db.query(User).first()
    if not admin_user:
        print("Admin user not found for template creation!")
        return
    
    # Template 1: Relatório Ambiental Básico
    template1 = db.query(DocumentTemplate).filter(DocumentTemplate.name == "Relatório Ambiental Básico").first()
    if not template1:
        template1 = DocumentTemplate(
            name="Relatório Ambiental Básico",
            description="Template básico para relatórios ambientais",
            content="""# RELATÓRIO AMBIENTAL

## 1. IDENTIFICAÇÃO DA EMPRESA
- **Razão Social:** {empresa_nome}
- **CNPJ:** {cnpj}
- **Endereço:** {endereco}
- **Responsável:** {responsavel}

## 2. ATIVIDADES DESENVOLVIDAS
{descricao_atividades}

## 3. ASPECTOS AMBIENTAIS
### 3.1 Emissões Atmosféricas
{emissoes_atmosfericas}

### 3.2 Resíduos Sólidos
{residuos_solidos}

### 3.3 Efluentes Líquidos
{efluentes_liquidos}

## 4. CONFORMIDADE LEGAL
{conformidade_legal}

## 5. MEDIDAS MITIGADORAS
{medidas_mitigadoras}

## 6. CONCLUSÕES
{conclusoes}

---
*Relatório gerado em {data_relatorio}*""",
            created_by_user_id=admin_user.id,
            organization_id=None,  # Global template
            is_global=True,
            is_active=True
        )
        db.add(template1)
    
    # Template 2: Licença Ambiental Padrão
    template2 = db.query(DocumentTemplate).filter(DocumentTemplate.name == "Licença Ambiental Padrão").first()
    if not template2:
        template2 = DocumentTemplate(
            name="Licença Ambiental Padrão",
            description="Template padrão para licenças ambientais",
            content="""# LICENÇA AMBIENTAL

**Licença:** {numero_licenca}
**Órgão Emissor:** {orgao_emissor}
**Data de Emissão:** {data_emissao}
**Validade:** {data_validade}

## DADOS DO EMPREENDIMENTO
- **Razão Social:** {empresa_nome}
- **CNPJ:** {cnpj}
- **Endereço:** {endereco}
- **Atividade:** {atividade}

## CONDIÇÕES DA LICENÇA

### 1. MONITORAMENTO AMBIENTAL
{condicoes_monitoramento}

### 2. CONTROLE DE EMISSÕES
{condicoes_emissoes}

### 3. GESTÃO DE RESÍDUOS
{condicoes_residuos}

### 4. MEDIDAS COMPENSATÓRIAS
{medidas_compensatorias}

## RESPONSABILIDADES DO EMPREENDEDOR
{responsabilidades}

## PENALIDADES
Em caso de descumprimento das condições desta licença, o empreendedor estará sujeito às penalidades previstas na Lei nº 9.605/98.

---
*Licença válida até {data_validade}*""",
            created_by_user_id=admin_user.id,
            organization_id=None,  # Global template
            is_global=True,
            is_active=True
        )
        db.add(template2)
    
    db.commit()
    print("Sample templates created:")
    print("   - Relatorio Ambiental Basico")
    print("   - Licenca Ambiental Padrao")

def create_admin_org_and_user(db: Session, admin_email: str, admin_full_name: str, admin_password: str):
    """Create minimal admin organization and admin user - NO licenses, NO subscriptions."""
    try:
        # Ensure roles exist (ADMINISTRATOR at minimum)
        print("   [1/4] Criando roles do sistema...")
        create_system_roles(db)
        print("   ✅ Roles criados")

        # Get admin role
        print("   [2/4] Verificando role ADMINISTRATOR...")
        admin_role = db.query(Role).filter(Role.name == "ADMINISTRATOR").first()
        if not admin_role:
            raise ValueError("ADMINISTRATOR role not found after role initialization")
        print(f"   ✅ Role ADMINISTRATOR encontrado (ID: {admin_role.id})")

        # Check if admin already exists
        print(f"   [3/4] Verificando se admin já existe: {admin_email}")
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"   ⚠️  Admin user already exists: {admin_email}")
            # Buscar a organização associada
            assoc = db.query(UserOrganizationAssociation).filter(
                UserOrganizationAssociation.user_id == existing_admin.id
            ).first()
            if assoc:
                org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
                if org:
                    print(f"   ✅ Organização encontrada: {org.name} (ID: {org.id})")
                    return org, existing_admin
            print(f"   ⚠️  Usuário existe mas sem organização associada")
            return None, existing_admin

        # Create admin organization (system org)
        print("   [4/6] Criando organização administrativa...")
        admin_org = Organization(
            name="Organização Administrativa",
            slug="org-admin",
            cnpj_cpf="00.000.000/0001-00",
            email=admin_email,
            is_active=True
        )
        db.add(admin_org)
        db.flush()  # Flush para obter o ID sem commit
        print(f"   ✅ Organização administrativa adicionada (ID: {admin_org.id})")

        # Create admin user
        print("   [5/6] Criando usuário administrador...")
        admin_user = User(
            email=admin_email,
            full_name=admin_full_name,
            hashed_password=get_password_hash(admin_password),
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)
        db.flush()  # Flush para obter o ID sem commit
        print(f"   ✅ Usuário administrador adicionado (ID: {admin_user.id})")
        
        # Create user-organization association
        print("   [6/6] Criando associação usuário-organização...")
        user_org_assoc = UserOrganizationAssociation(
            user_id=admin_user.id,
            organization_id=admin_org.id,
            role_id=admin_role.id
        )
        db.add(user_org_assoc)
        
        # Commit tudo de uma vez
        db.commit()
        db.refresh(admin_org)
        db.refresh(admin_user)
        print(f"   ✅ Commit realizado - Org: {admin_org.id}, User: {admin_user.id}, Associação criada")
        
        print(f"✅ Usuário administrador criado com sucesso: {admin_email}")

        return admin_org, admin_user
    except Exception as e:
        import traceback
        print(f"❌ Erro ao criar admin org/user: {e}")
        print(f"Traceback completo:\n{traceback.format_exc()}")
        db.rollback()
        raise


def init_database(admin_email: str, admin_full_name: str, admin_password: str, seed_demo: bool = False):
    """Initialize database with minimal data and optional demo data.

    Minimal seed: roles, ONE admin organization, ONE admin user (NO licenses, NO subscriptions).
    Demo seed (optional): plans, test org, templates, subscriptions, licenses.
    """
    if not admin_email or not admin_full_name or not admin_password:
        raise ValueError("admin_email, admin_full_name and admin_password are required for initialization")

    print("=" * 60)
    print("🚀 Initializing Ambiental SaaS Database...")
    print("=" * 60)

    # PRIMEIRO: Executar migrações Alembic para garantir schema atualizado
    print("\n[1/3] Executando migrações Alembic...")
    try:
        from scripts.run_alembic import run_alembic_upgrade
        alembic_result = run_alembic_upgrade()
        if not alembic_result["success"]:
            print("⚠️  Aviso: Migrações Alembic falharam, mas continuando...")
            print(f"   Erro: {alembic_result.get('stderr', 'Unknown')}")
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível executar Alembic: {e}")
        print("   Continuando com criação manual de tabelas...")

    # Verificar se as tabelas já existem antes de criar
    from sqlalchemy import inspect, text
    from app.models import Base
    
    # Verificar schema atual
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_schema()"))
        current_schema = result.scalar()
        print(f"📋 Schema atual: {current_schema}")
        
        # Verificar se o schema public existe
        result = conn.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'public'
        """))
        if not result.fetchone():
            print("⚠️  Schema 'public' não existe. Criando...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
            conn.commit()
            print("✅ Schema 'public' criado")
    
    # Verificar tabelas após Alembic
    print("\n[2/3] Verificando tabelas...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = list(Base.metadata.tables.keys())
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    if missing_tables:
        print(f"📋 {len(missing_tables)} tabelas ainda faltando após Alembic. Criando manualmente...")
        # Garantir que as tabelas sejam criadas no schema public (fallback)
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas manualmente")
        
        # Verificar novamente
        inspector = inspect(engine)
        existing_after = inspector.get_table_names()
        still_missing = [t for t in required_tables if t not in existing_after]
        if still_missing:
            print(f"⚠️  Ainda faltam tabelas: {still_missing}")
        else:
            print("✅ Todas as tabelas foram criadas com sucesso")
    else:
        print("✅ Todas as tabelas já existem (criadas pelo Alembic)")

    # Usar uma sessão com autocommit=False mas garantir commit explícito
    db = SessionLocal()
    try:
        # Minimal seed - ONLY admin org + admin user
        print("\n[3/3] Criando dados mínimos do seed...")
        admin_org, admin_user = create_admin_org_and_user(db, admin_email, admin_full_name, admin_password)
        
        # Garantir que tudo foi commitado EXPLICITAMENTE
        db.flush()
        db.commit()
        print("✅ Commit realizado")
        
        # Fechar sessão atual para garantir que o commit foi processado
        db.close()
        
        # Aguardar um momento para garantir que o commit foi processado pelo banco
        import time
        time.sleep(0.2)
        
        # Verificar imediatamente após commit usando uma NOVA sessão
        verify_db = SessionLocal()
        try:
            verify_org = verify_db.query(Organization).filter(Organization.slug == "org-admin").first()
            verify_user = verify_db.query(User).filter(User.email == admin_email).first()
            if verify_org and verify_user:
                print("✅ Dados commitados e verificados no banco")
                print(f"   Org ID: {verify_org.id}, User ID: {verify_user.id}")
                # Atualizar referências
                admin_org = verify_org
                admin_user = verify_user
            else:
                print("⚠️  Aviso: Dados commitados mas não encontrados na verificação")
                print(f"   Org encontrada: {verify_org is not None}, User encontrado: {verify_user is not None}")
                # Tentar buscar novamente
                admin_org = verify_db.query(Organization).filter(Organization.slug == "org-admin").first()
                admin_user = verify_db.query(User).filter(User.email == admin_email).first()
        finally:
            verify_db.close()
        
        # Reabrir sessão para continuar
        db = SessionLocal()

        # Optional demo data (ONLY plans and templates, NO extra orgs/users)
        if seed_demo:
            print("\n📦 Criando dados demo (opcional)...")
            create_demo_plans_and_templates(db)
            db.commit()
            print("✅ Dados demo criados")

        # Verificar novamente após commit usando uma sessão limpa
        final_db = SessionLocal()
        try:
            final_org = final_db.query(Organization).filter(Organization.slug == "org-admin").first()
            final_user = final_db.query(User).filter(User.email == admin_email).first()
            
            print("\n" + "=" * 60)
            print("✅ Inicialização do banco concluída com sucesso!")
            print("=" * 60)
            print(f"\n📊 Resumo:")
            
            org_count = final_db.query(Organization).count()
            user_count = final_db.query(User).count()
            
            print(f"   • Organizações: {org_count}")
            print(f"   • Usuários: {user_count}")
            print(f"   • Admin: {admin_email}")
            print(f"   • Org ID: {final_org.id if final_org else 'N/A'}")
            print(f"   • User ID: {final_user.id if final_user else 'N/A'}")
            if seed_demo:
                print(f"   • Dados demo: Planos e templates carregados")
            else:
                print(f"   • Dados demo: Não carregados")
            print("=" * 60)
            
            # Verificação final crítica
            if not final_org or not final_user:
                raise RuntimeError("Dados do seed não foram persistidos corretamente no banco!")
        finally:
            final_db.close()

    except Exception as e:
        import traceback
        error_msg = f"❌ Erro ao inicializar banco de dados: {e}"
        print(error_msg)
        print(f"Traceback completo:\n{traceback.format_exc()}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    raise SystemExit("Run initialization via setup.py wizard or import init_database() with proper parameters")
