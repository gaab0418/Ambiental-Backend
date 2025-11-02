"""
Script to list all user-organization associations in the system.

Usage:
    python scripts/list_user_org_associations.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.user_organization_association import UserOrganizationAssociation


def list_all_associations():
    """List all user-organization associations."""
    db: Session = SessionLocal()
    
    try:
        assocs = db.query(UserOrganizationAssociation).all()
        
        if not assocs:
            print("No user-organization associations found in the system.")
            return
        
        print("\n" + "=" * 100)
        print("USER-ORGANIZATION ASSOCIATIONS")
        print("=" * 100 + "\n")
        
        # Group by user
        users_dict = {}
        for assoc in assocs:
            if assoc.user_id not in users_dict:
                users_dict[assoc.user_id] = []
            users_dict[assoc.user_id].append(assoc)
        
        for user_id, user_assocs in users_dict.items():
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue
            
            print(f"👤 {user.full_name} ({user.email})")
            print(f"   ID: {user.id}")
            print(f"   Active: {'✅ Yes' if user.is_active else '❌ No'}")
            print(f"   Organizations ({len(user_assocs)}):")
            
            for assoc in user_assocs:
                org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
                role = db.query(Role).filter(Role.id == assoc.role_id).first()
                
                if org and role:
                    print(f"      • {org.name} (ID: {org.id})")
                    print(f"        CNPJ/CPF: {org.cnpj_cpf}")
                    print(f"        Role: {role.display_name} ({role.name})")
                    print(f"        Since: {assoc.created_at.strftime('%d/%m/%Y %H:%M')}")
            
            print()
        
        # Summary
        total_users = len(users_dict)
        total_orgs = db.query(Organization).count()
        total_assocs = len(assocs)
        users_with_multiple_orgs = sum(1 for u in users_dict.values() if len(u) > 1)
        
        print("=" * 100)
        print("SUMMARY")
        print("=" * 100)
        print(f"Total Users: {total_users}")
        print(f"Total Organizations: {total_orgs}")
        print(f"Total Associations: {total_assocs}")
        print(f"Users with Multiple Organizations: {users_with_multiple_orgs}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    finally:
        db.close()


def list_organizations():
    """List all organizations in the system."""
    db: Session = SessionLocal()
    
    try:
        orgs = db.query(Organization).all()
        
        if not orgs:
            print("No organizations found in the system.")
            return
        
        print("\n" + "=" * 100)
        print("ALL ORGANIZATIONS")
        print("=" * 100 + "\n")
        
        for org in orgs:
            # Count users
            user_count = db.query(UserOrganizationAssociation).filter(
                UserOrganizationAssociation.organization_id == org.id
            ).count()
            
            print(f"🏢 {org.name} (ID: {org.id})")
            print(f"   CNPJ/CPF: {org.cnpj_cpf}")
            print(f"   Email: {org.email}")
            print(f"   Active: {'✅ Yes' if org.is_active else '❌ No'}")
            print(f"   Users: {user_count}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "orgs":
        list_organizations()
    else:
        list_all_associations()
        
        if len(sys.argv) > 1 and sys.argv[1] == "--help":
            print("\nUsage:")
            print("  python scripts/list_user_org_associations.py        # List all associations")
            print("  python scripts/list_user_org_associations.py orgs   # List all organizations")

