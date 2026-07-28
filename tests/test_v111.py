# tests/test_v111.py

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure core/ is in Python path for test execution context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from services.auth.models import Base, Tenant, User, Scenario
from services.auth.auth_service import hash_password, verify_password, create_jwt_token, decode_jwt_token
from services.tenant.tenant_service import onboard_new_tenant
from services.users.user_service import create_user, get_user_by_email

# SQLite memory database fixture
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_password_hashing():
    pwd = "cyber_grid_sec"
    pwd_hash = hash_password(pwd)
    assert pwd_hash != pwd
    assert verify_password(pwd, pwd_hash) is True
    assert verify_password("wrong_password", pwd_hash) is False

def test_jwt_token_generation_and_decoding():
    payload = {
        "user_id": "user-uuid-1234",
        "tenant_id": "tenant-uuid-5678",
        "role": "admin",
        "email": "admin@mit.edu",
        "plan_tier": "academic_premium"
    }
    
    token = create_jwt_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_jwt_token(token)
    assert decoded["user_id"] == payload["user_id"]
    assert decoded["tenant_id"] == payload["tenant_id"]
    assert decoded["role"] == payload["role"]
    assert decoded["plan_tier"] == payload["plan_tier"]

def test_tenant_onboarding_and_user_creation(db_session):
    # Register first tenant
    tenant = onboard_new_tenant(
        db=db_session,
        name="MIT Grid Lab",
        subdomain="mit",
        admin_email="admin@mit.edu",
        admin_password="mit_secure_password_1"
    )
    
    assert tenant.id is not None
    assert tenant.name == "MIT Grid Lab"
    assert tenant.subdomain == "mit"
    
    # Check default premium trial subscription created on onboarding
    assert tenant.plan_tier == "academic_premium"
    
    # Verify admin user is created in the DB
    user = get_user_by_email(db_session, "admin@mit.edu")
    assert user is not None
    assert user.tenant_id == tenant.id
    assert user.role == "admin"
    assert verify_password("mit_secure_password_1", user.password_hash) is True

def test_onboard_tenant_validation_rules(db_session):
    # Onboard MIT tenant
    onboard_new_tenant(
        db=db_session,
        name="MIT Lab",
        subdomain="mit",
        admin_email="admin@mit.edu",
        admin_password="password123"
    )
    
    # Verify duplicate subdomain onboarding fails
    with pytest.raises(ValueError) as exc:
        onboard_new_tenant(
            db=db_session,
            name="Harvard Lab",
            subdomain="mit",  # Duplicate subdomain
            admin_email="admin@harvard.edu",
            admin_password="password456"
        )
    assert "Subdomain already registered" in str(exc.value)

    # Verify duplicate admin email fails
    with pytest.raises(ValueError) as exc2:
        onboard_new_tenant(
            db=db_session,
            name="MIT Research Lab",
            subdomain="mit-research",
            admin_email="admin@mit.edu",  # Duplicate email
            admin_password="password789"
        )
    assert "Admin email already registered" in str(exc2.value)

def test_tenant_isolation(db_session):
    # Onboard Tenant A
    tenant_a = onboard_new_tenant(
        db=db_session,
        name="MIT Lab",
        subdomain="mit",
        admin_email="admin@mit.edu",
        admin_password="password123"
    )
    
    # Onboard Tenant B
    tenant_b = onboard_new_tenant(
        db=db_session,
        name="Harvard Lab",
        subdomain="harvard",
        admin_email="admin@harvard.edu",
        admin_password="password456"
    )
    
    # Scenario belongs to Tenant A
    scenario_a = Scenario(
        tenant_id=tenant_a.id,
        name="MIT Playbook",
        grid_type="IEEE14",
        config={}
    )
    db_session.add(scenario_a)
    db_session.commit()
    
    # Verify Tenant B queries cannot access Scenario A
    harvard_scenarios = db_session.query(Scenario).filter(Scenario.tenant_id == tenant_b.id).all()
    assert scenario_a not in harvard_scenarios
    for scenario in harvard_scenarios:
        assert scenario.tenant_id == tenant_b.id
        assert scenario.tenant_id != tenant_a.id
