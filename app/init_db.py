"""
Database initialization and default admin / permissions seeder.
"""
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.core.security import hash_password
from app.services.role_service import RoleService

logger = logging.getLogger("init_db")


def init_db():
    """Create all tables and seed default permissions and admin user."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Seed permissions and roles
        role_service = RoleService(db)
        role_service.seed_default_permissions_and_roles()

        # Seed initial admin if none exists
        admin_user = db.query(User).filter(User.role == "administrador").first()
        if not admin_user:
            admin_user = User(
                email="admin@stylestore.com",
                name="Administrador StyleStore",
                hashed_password=hash_password("Admin@1234"),
                role="administrador",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default administrator user: admin@stylestore.com / Admin@1234")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
