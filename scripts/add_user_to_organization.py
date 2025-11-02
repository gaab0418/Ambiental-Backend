"""
Script to add an existing user to an organization.

Usage:
    python scripts/add_user_to_organization.py <user_email> <organization_id> <role_name>

Example:
    python scripts/add_user_to_organization.py admin@empresa.com 2 CONSULTANT
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


def add_user_to_organization(user_email: str, organization_id: int, role_name: str):
    """Add an existing user to an organization with a specific role."""
    db: Session = SessionLocal()
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User with email '{user_email}' not found.")
            return False
        
        # Find organization
        organization = db.query(Organization).filter(Organization.id == organization_id).first()
        if not organization:
            print(f"❌ Organization with ID {organization_id} not found.")
            return False
        
        # Find role
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            print(f"❌ Role '{role_name}' not found.")
            print("Available roles:")
            roles = db.query(Role).all()
            for r in roles:
                print(f"  - {r.name} ({r.display_name})")
            return False
        
        # Check if association already exists
        existing = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == user.id,
            UserOrganizationAssociation.organization_id == organization_id
        ).first()
        
        if existing:
            print(f"⚠️  User '{user.full_name}' is already associated with '{organization.name}'")
            print(f"   Current role: {db.query(Role).filter(Role.id == existing.role_id).first().name}")
            
            # Ask if user wants to update the role
            response = input("Do you want to update the role? (y/n): ")
            if response.lower() == 'y':
                existing.role_id = role.id
                db.commit()
                print(f"✅ Role updated to {role_name}")
                return True
            else:
                print("❌ No changes made.")
                return False
        
        # Create new association
        assoc = UserOrganizationAssociation(
            user_id=user.id,
            organization_id=organization_id,
            role_id=role.id
        )
        
        db.add(assoc)
        db.commit()
        
        print(f"✅ Successfully added user to organization!")
        print(f"   User: {user.full_name} ({user.email})")
        print(f"   Organization: {organization.name}")
        print(f"   Role: {role.display_name} ({role.name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False
        
    finally:
        db.close()


def list_user_organizations(user_email: str):
    """List all organizations a user belongs to."""
    db: Session = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User with email '{user_email}' not found.")
            return
        
        assocs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == user.id
        ).all()
        
        if not assocs:
            print(f"User '{user.full_name}' is not associated with any organization.")
            return
        
        print(f"\n🏢 Organizations for {user.full_name} ({user.email}):")
        print("=" * 70)
        
        for assoc in assocs:
            org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            
            if org and role:
                print(f"  • {org.name} (ID: {org.id})")
                print(f"    CNPJ/CPF: {org.cnpj_cpf}")
                print(f"    Role: {role.display_name} ({role.name})")
                print()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Add user to org:    python scripts/add_user_to_organization.py <user_email> <org_id> <role_name>")
        print("  List user's orgs:   python scripts/add_user_to_organization.py list <user_email>")
        print("\nExample:")
        print("  python scripts/add_user_to_organization.py admin@empresa.com 2 CONSULTANT")
        print("  python scripts/add_user_to_organization.py list admin@empresa.com")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        if len(sys.argv) < 3:
            print("❌ Please provide user email")
            print("Usage: python scripts/add_user_to_organization.py list <user_email>")
            sys.exit(1)
        
        list_user_organizations(sys.argv[2])
    else:
        if len(sys.argv) < 4:
            print("❌ Missing arguments")
            print("Usage: python scripts/add_user_to_organization.py <user_email> <org_id> <role_name>")
            sys.exit(1)
        
        user_email = sys.argv[1]
        try:
            organization_id = int(sys.argv[2])
        except ValueError:
            print("❌ Organization ID must be a number")
            sys.exit(1)
        
        role_name = sys.argv[3]
        
        success = add_user_to_organization(user_email, organization_id, role_name)
        sys.exit(0 if success else 1)

