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
            "name": "SUPER_ADMIN",
            "display_name": "Super Administrator",
            "description": "Full system access",
            "is_system": True
        },
        {
            "name": "ADMIN",
            "display_name": "Administrator",
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
    print("✅ System roles created")

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
    print("✅ System plans created")

def create_super_admin(db: Session):
    """Create super admin user"""
    # Create super admin organization
    super_org = db.query(Organization).filter(Organization.slug == "ambiental-admin").first()
    if not super_org:
        super_org = Organization(
            name="Ambiental Admin",
            slug="ambiental-admin",
            email="admin@ambiental.com",
            is_active=True
        )
        db.add(super_org)
        db.commit()
        db.refresh(super_org)
    
    # Get SUPER_ADMIN role
    super_role = db.query(Role).filter(Role.name == "SUPER_ADMIN").first()
    
    # Create super admin user
    super_user = db.query(User).filter(User.email == "admin@ambiental.com").first()
    if not super_user:
        super_user = User(
            email="admin@ambiental.com",
            full_name="Super Administrator",
            hashed_password=get_password_hash("admin123"),
            organization_id=super_org.id,
            role_id=super_role.id,
            is_active=True,
            is_verified=True
        )
        db.add(super_user)
        db.commit()
        db.refresh(super_user)
    
    print("✅ Super admin user created")
    print(f"   Email: admin@ambiental.com")
    print(f"   Password: admin123")
    print(f"   Organization: {super_org.name}")

def init_database():
    """Initialize database with basic data"""
    print("🚀 Initializing Ambiental SaaS Database...")
    
    # Create all tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    db = SessionLocal()
    try:
        create_system_roles(db)
        create_system_plans(db)
        create_super_admin(db)
        
        print("\n🎉 Database initialization completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update the .env file with your database credentials")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Access the API docs at: http://localhost:8000/docs")
        print("4. Login with super admin credentials to test the API")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
