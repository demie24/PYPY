# core/services/users/user_service.py

import uuid
from sqlalchemy.orm import Session
from services.auth.models import User
from services.auth.auth_service import hash_password

def create_user(db: Session, tenant_id: uuid.UUID, email: str, plain_password: str, first_name: str = None, last_name: str = None, role: str = 'operator') -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError(f"User with email {email} already exists.")
        
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(plain_password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).first()

def get_users_by_tenant(db: Session, tenant_id: uuid.UUID) -> list:
    return db.query(User).filter(User.tenant_id == tenant_id).all()
