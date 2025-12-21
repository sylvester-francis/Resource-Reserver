"""Database migration script for AuthN/AuthZ/OAuth2 features."""

import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.database import SessionLocal, engine
from app.models import Base, Role, User, UserRole
from app.rbac import create_default_roles


def migrate():
    """Run database migration."""
    print("Starting database migration...")

    # Create all new tables (will skip existing ones)
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ New tables created")

    # Create session
    db = SessionLocal()

    try:
        # Add new columns to users table if they don't exist
        print("Adding new columns to users table...")
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        existing_columns = [col["name"] for col in inspector.get_columns("users")]

        columns_to_add = []
        if "mfa_enabled" not in existing_columns:
            columns_to_add.append("ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0 NOT NULL")
        if "mfa_secret" not in existing_columns:
            columns_to_add.append("ADD COLUMN mfa_secret VARCHAR(32)")
        if "mfa_backup_codes" not in existing_columns:
            columns_to_add.append("ADD COLUMN mfa_backup_codes JSON")
        if "email" not in existing_columns:
            columns_to_add.append("ADD COLUMN email VARCHAR(255)")
        if "email_verified" not in existing_columns:
            columns_to_add.append(
                "ADD COLUMN email_verified BOOLEAN DEFAULT 0 NOT NULL"
            )

        if columns_to_add:
            # SQLite doesn't support multiple ALTER TABLE in one statement
            for col_def in columns_to_add:
                try:
                    db.execute(text(f"ALTER TABLE users {col_def}"))
                    db.commit()
                except Exception as e:
                    print(f"  Note: {e}")
            print(f"✓ Added {len(columns_to_add)} new columns to users table")
        else:
            print("✓ All columns already exist in users table")

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
                existing = (
                    db.query(UserRole)
                    .filter(
                        UserRole.user_id == user.id, UserRole.role_id == user_role.id
                    )
                    .first()
                )

                if not existing:
                    user_role_assignment = UserRole(
                        user_id=user.id, role_id=user_role.id
                    )
                    db.add(user_role_assignment)

            db.commit()
            print(f"✓ Assigned 'user' role to {len(users)} users")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Default roles created: admin, user, guest")
        print("2. All existing users have 'user' role")
        print("3. To make a user admin, use: rbac.assign_role(user_id, 'admin', db)")
        print("\nNew features available:")
        print("  • Multi-Factor Authentication (MFA)")
        print("  • Role-Based Access Control (RBAC)")
        print("  • OAuth2 Authorization Server")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
