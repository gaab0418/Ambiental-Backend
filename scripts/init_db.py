#!/usr/bin/env python3
"""
Script para inicializar o banco de dados com dados básicos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Organization, User, Role, Plan, Subscription, License
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
            "max_users": 5,
            "is_system": True
        },
        {
            "name": "BASIC",
            "display_name": "Basic",
            "description": "Basic plan for small teams",
            "price": 29.90,
            "currency": "BRL",
            "max_users": 10,
            "is_system": True
        },
        {
            "name": "PROFESSIONAL",
            "display_name": "Professional",
            "description": "Professional plan for growing teams",
            "price": 79.90,
            "currency": "BRL",
            "max_users": 50,
            "is_system": True
        },
        {
            "name": "ENTERPRISE",
            "display_name": "Enterprise",
            "description": "Enterprise plan for large organizations",
            "price": 199.90,
            "currency": "BRL",
            "max_users": 200,
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
    # Ensure roles exist (ADMINISTRATOR at minimum)
    create_system_roles(db)

    # Get admin role
    admin_role = db.query(Role).filter(Role.name == "ADMINISTRATOR").first()
    if not admin_role:
        raise ValueError("ADMINISTRATOR role not found after role initialization")

    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        print(f"Admin user already exists: {admin_email}")
        return existing_admin.organization, existing_admin

    # Create admin organization (system org)
    admin_org = Organization(
        name="Organização Administrativa",
        slug="org-admin",
        cnpj_cpf="00.000.000/0001-00",
        email=admin_email,
        is_active=True
    )
    db.add(admin_org)
    db.commit()
    db.refresh(admin_org)
    print(f"✅ Organização administrativa criada: {admin_org.name}")

    # Create admin user
    admin_user = User(
        email=admin_email,
        full_name=admin_full_name,
        hashed_password=get_password_hash(admin_password),
        organization_id=admin_org.id,
        role_id=admin_role.id,
        is_active=True,
        is_verified=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    print(f"✅ Usuário administrador criado: {admin_email}")

    return admin_org, admin_user


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

    # Create all tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    db = SessionLocal()
    try:
        # Minimal seed - ONLY admin org + admin user
        print("\n📦 Creating minimal seed data...")
        admin_org, admin_user = create_admin_org_and_user(db, admin_email, admin_full_name, admin_password)

        # Optional demo data (ONLY plans and templates, NO extra orgs/users)
        if seed_demo:
            print("\n📦 Creating demo data (optional)...")
            create_demo_plans_and_templates(db)
            print("✅ Demo data created")

        print("\n" + "=" * 60)
        print("✅ Database initialization completed successfully!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        
        org_count = db.query(Organization).count()
        user_count = db.query(User).count()
        
        print(f"   • Organizations: {org_count}")
        print(f"   • Users: {user_count}")
        print(f"   • Admin: {admin_email}")
        if seed_demo:
            print(f"   • Demo data: Plans and templates loaded")
        else:
            print(f"   • Demo data: Not loaded")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    raise SystemExit("Run initialization via setup.py wizard or import init_database() with proper parameters")
