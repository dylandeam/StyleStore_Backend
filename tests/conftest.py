"""
Pytest configuration and fixtures for backend tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
settings.ALLOW_MOCK_PAYPAL = True
from app.database import Base, get_db
from app.main import app

# Test database engine
test_engine = create_engine(
    settings.DATABASE_URL_TEST,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables before testing and drop them after."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    # Seed default permissions and roles for test DB
    db = TestingSessionLocal()
    from app.services.role_service import RoleService
    from app.models.empresa import Empresa
    RoleService(db).seed_default_permissions_and_roles()
    default_empresa = Empresa(codigo="stylestore", nombre="StyleStore", active=True)
    db.add(default_empresa)
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional database session for a test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    # Cada commit/rollback de la aplicación queda contenido en un savepoint.
    # Así las rutas transaccionales se prueban de forma realista sin cerrar la
    # transacción externa que permite limpiar por completo cada caso.
    session = TestingSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(db_session, client):
    """Fixture providing an authenticated administrator token."""
    from app.models.user import User
    from app.core.security import hash_password

    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").first()
    if not admin:
        from app.models.empresa import Empresa
        default_empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
        admin = User(
            empresa_id=default_empresa.id,
            email="admin_test@stylestore.com",
            name="Admin Test",
            apellido="StyleStore",
            ci="1234567",
            hashed_password=hash_password("AdminPass123!"),
            role="administrador",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

    # This shared fixture represents the platform owner. Tenant-admin scenarios
    # create their own isolated accounts explicitly in the corresponding tests.
    if not admin.is_platform_admin:
        admin.is_platform_admin = True
        db_session.commit()

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@stylestore.com", "password": "AdminPass123!"},
    )
    return login_res.json()["access_token"]
