"""
Initialize database with tables and default users
"""
import asyncio
import sys
import os
import secrets
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.models.base import Base
from app.models.user import User, UserRole
from app.core.config import settings
from app.core.security import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with tables and default data"""
    
    # Create engine
    engine = create_engine(settings.SYNC_DATABASE_URL, echo=True)
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create session
    with Session(engine) as session:
        # Check if admin user exists
        existing_admin = session.query(User).filter_by(email="admin@indoc.local").first()
        
        if not existing_admin:
            logger.info("Creating default users...")
            
            # Create default admin user with secure password
            import secrets
            # Generate secure random password if not provided via environment
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not admin_password:
                admin_password = secrets.token_urlsafe(16)
                print("⚠️  No ADMIN_PASSWORD set, generated random password")
            admin_user = User(
                email="admin@indoc.local",
                username="admin",
                full_name="System Administrator",
                hashed_password=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            
            # Create demo users for each role with secure passwords
            demo_user_configs = [
                ("manager@indoc.local", "manager", "Demo Manager", UserRole.MANAGER),
                ("analyst@indoc.local", "analyst", "Demo Analyst", UserRole.ANALYST),
                # Legacy roles (deprecated but kept for compatibility)
                ("reviewer@indoc.local", "reviewer", "Demo Reviewer", UserRole.REVIEWER),
                ("uploader@indoc.local", "uploader", "Demo Uploader", UserRole.UPLOADER),
                ("viewer@indoc.local", "viewer", "Demo Viewer", UserRole.VIEWER),
                ("compliance@indoc.local", "compliance", "Compliance Officer", UserRole.COMPLIANCE)
            ]
            
            demo_users = []
            for email, username, full_name, role in demo_user_configs:
                # Generate secure password or use environment variable
                env_var = f"{username.upper()}_PASSWORD"
                password = os.getenv(env_var)
                if not password:
                    password = secrets.token_urlsafe(16)
                
                demo_users.append(User(
                    email=email,
                    username=username,
                    full_name=full_name,
                    hashed_password=get_password_hash(password),
                    role=role,
                    is_active=True,
                    is_verified=True
                ))
            
            for user in demo_users:
                session.add(user)
            
            session.commit()
            logger.info("Default users created successfully!")
            
            # Print user credentials (secure passwords)
            print("\n" + "="*50)
            print("DEFAULT USER CREDENTIALS")
            print("="*50)
            print("\nAdmin User:")
            print("  Email: admin@indoc.local")
            print(f"  Password: {admin_password}")
            print("\nDemo Users:")
            for email, username, full_name, role in demo_user_configs:
                env_var = f"{username.upper()}_PASSWORD"
                password = os.getenv(env_var, secrets.token_urlsafe(16))
                print(f"  {role.value}: {email} / {password}")
            print("\n⚠️  Save these passwords! They are randomly generated for security.")
            print("   Set environment variables to use custom passwords:")
            print("   export ADMIN_PASSWORD='your_admin_password'")
            print("   export REVIEWER_PASSWORD='your_reviewer_password'")
            print("="*50 + "\n")
        else:
            logger.info("Admin user already exists, skipping user creation")
        
        # Verify users were created
        user_count = session.query(User).count()
        logger.info(f"Total users in database: {user_count}")
        
        # List all users
        users = session.query(User).all()
        print("\nCurrent users in database:")
        for user in users:
            print(f"  - {user.email} (Role: {user.role.value})")


if __name__ == "__main__":
    init_database()