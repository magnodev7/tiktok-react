"""
Sistema de Autenticação JWT para TikTok Scheduler com PostgreSQL
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone


from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User as UserModel, APIKey as APIKeyModel
from src.repositories import UserRepository, APIKeyRepository
from typing import Dict, List, Optional, Set, Tuple


# Configurações de segurança
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 horas

# Configurações de usuário padrão
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Contexto de criptografia
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Esquema de autenticação
security = HTTPBearer(auto_error=False)


# ===== Pydantic Models =====

class User(BaseModel):
    """Schema público do usuário"""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    account_quota: int = -1
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False
    account_quota: int = -1


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str] = ["read", "write"]


class APIKeyPublic(BaseModel):
    """Schema público da API Key"""
    id: int
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    permissions: List[str] = ["read", "write"]

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    """Resposta ao criar API Key (inclui a chave uma única vez)"""
    key_id: int
    api_key: str
    name: str
    message: str


# ===== Funções de Senha =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)


# ===== Autenticação de Usuários =====

def authenticate_user(db: Session, username: str, password: str) -> Optional[UserModel]:
    """Autentica usuário com username e senha"""
    user = UserRepository.get_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verifica e decodifica token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        return None


# ===== Dependencies FastAPI =====

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserModel:
    """Dependency para obter usuário atual autenticado"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception

    user = UserRepository.get_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency para obter usuário ativo atual"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Dependency para obter usuário admin atual"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# ===== Autenticação via API Key =====

def generate_api_key() -> str:
    """Gera uma nova API key"""
    return f"tk_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Gera hash da API key para armazenamento seguro"""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def get_api_key_user(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> APIKeyModel:
    """Dependency para autenticação via API Key"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not x_api_key.startswith("tk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(x_api_key)
    api_key_obj = APIKeyRepository.get_by_hash(db, key_hash)

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Atualiza último uso
    APIKeyRepository.update_last_used(db, api_key_obj.id)

    return api_key_obj


async def get_api_key_user_with_permission(
    permission: str,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> APIKeyModel:
    """Dependency para autenticação via API Key com verificação de permissão"""
    api_key_obj = await get_api_key_user(x_api_key, db)

    if permission not in api_key_obj.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API Key does not have '{permission}' permission"
        )

    return api_key_obj


# ===== Autenticação Híbrida (JWT ou API Key) =====

async def get_current_user_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Tuple[Optional[UserModel], Optional[APIKeyModel]]:
    """Dependency que aceita tanto JWT quanto API Key"""
    user = None
    api_key_obj = None

    # Tenta autenticação via JWT
    if credentials:
        try:
            token_data = verify_token(credentials.credentials)
            if token_data:
                user = UserRepository.get_by_username(db, username=token_data.username)
        except Exception:
            pass

    # Tenta autenticação via API Key
    if not user and x_api_key:
        try:
            if x_api_key.startswith("tk_"):
                key_hash = hash_api_key(x_api_key)
                api_key_obj = APIKeyRepository.get_by_hash(db, key_hash)
                if api_key_obj:
                    APIKeyRepository.update_last_used(db, api_key_obj.id)
        except Exception:
            pass

    if not user and not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (JWT token or API Key)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user, api_key_obj


# ===== Funções Helper =====

def ensure_admin_exists(db: Session) -> None:
    """Garante que o usuário admin existe"""
    admin = UserRepository.get_by_username(db, ADMIN_USERNAME)
    if not admin:
        UserRepository.create(
            db,
            username=ADMIN_USERNAME,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            email="admin@tiktokscheduler.local",
            full_name="Administrador",
            is_admin=True
        )
        print(f"✅ Usuário admin '{ADMIN_USERNAME}' criado com sucesso!")
