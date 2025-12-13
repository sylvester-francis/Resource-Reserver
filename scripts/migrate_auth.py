"""Database migration script for AuthN/AuthZ/OAuth2 features."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import SQLALCHEMY_DATABASE_URL
from app.models import Base, Role, User, UserRole
from app.rbac import create_default_roles

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate():
    """Run database migration."""
    print("Starting database migration...")
    
    # Create all tables
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create default roles
        print("Creating default roles...")
        create_default_roles(db)
        print("✓ Default roles created (admin, user, guest)")
        
        # Assign 'user' role to all existing users
        print("Assigning default roles to existing users...")
        user_role = db.query(Role).filter(Role.name == "user").first()
        
        if user_role:
            users = db.query(User).all()
            for user in users:
                # Check if user already has this role
                existing = db.query(UserRole).filter(
                    UserRole.user_id == user.id,
                    UserRole.role_id == user_role.id
                ).first()
                
                if not existing:
                    user_role_assignment = UserRole(
                        user_id=user.id,
                        role_id=user_role.id
                    )
                    db.add(user_role_assignment)
            
            db.commit()
            print(f"✓ Assigned 'user' role to {len(users)} users")
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Default roles created: admin, user, guest")
        print("2. All existing users have 'user' role")
        print("3. To make a user admin, use: rbac.assign_role(user_id, 'admin', db)")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
