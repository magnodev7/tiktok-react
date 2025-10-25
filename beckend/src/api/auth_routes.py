"""Rotas relacionadas à autenticação e gestão de usuários."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.auth import (
    APIKeyPublic,
    APIKeyResponse,
    ChangePasswordRequest,
    CreateAPIKeyRequest,
    CreateUserRequest,
    LoginRequest,
    Token,
    User,
    authenticate_user,
    create_access_token,
    ensure_admin_exists,  # noqa: F401 (mantém compatibilidade)
    get_api_key_user,
    get_current_active_user,
    get_current_admin_user,
    get_db,
)
from src.models import User as UserModel
from src.repositories import APIKeyRepository, UserRepository

from .. import log_service
from .schemas import APIResponse
from .utils import raise_http_error, success_response


router = APIRouter(prefix="/auth", tags=["auth"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
USERDATA_DIR = Path(os.getenv("BASE_USERDATA_DIR") or (BASE_DIR / "user_data"))


def _add_log(message: str, level: str = "info", user_id: Optional[int] = None) -> None:
    """Wrapper para o serviço de logs com módulo padronizado."""
    log_service.add_log(message=message, level=level, user_id=user_id, module="api-auth")


@router.post("/login", response_model=APIResponse[Token])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)) -> APIResponse[Token]:
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise_http_error(status.HTTP_401_UNAUTHORIZED, error="invalid_credentials", message="Usuário ou senha incorretos")
    if not user.is_active:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="inactive_user", message="Usuário inativo")

    access_token = create_access_token(data={"sub": user.username})
    UserRepository.update_last_login(db, user.id)

    token_payload = Token(
        access_token=access_token,
        token_type="bearer",
        user=User.from_orm(user),
    )
    return success_response(data=token_payload)


@router.get("/verify", response_model=APIResponse[User])
async def verify_token(current_user: UserModel = Depends(get_current_active_user)) -> APIResponse[User]:
    return success_response(data=User.from_orm(current_user))


@router.get("/me", response_model=APIResponse[User])
async def get_current_user_info(current_user: UserModel = Depends(get_current_active_user)) -> APIResponse[User]:
    return success_response(data=User.from_orm(current_user))


@router.put("/me", response_model=APIResponse[User])
async def update_current_user_profile(
    request: dict,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[User]:
    if "full_name" in request:
        UserRepository.update_full_name(db, current_user.id, request["full_name"])

    if "email" in request:
        existing_user = UserRepository.get_by_email(db, request["email"])
        if existing_user and existing_user.id != current_user.id:
            raise_http_error(status.HTTP_400_BAD_REQUEST, error="email_in_use", message="Email já está em uso")
        UserRepository.update_email(db, current_user.id, request["email"])

    updated_user = UserRepository.get_by_id(db, current_user.id)
    return success_response(data=User.from_orm(updated_user))


@router.post("/me/profile-picture", response_model=APIResponse[dict])
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    import shutil
    from fastapi import HTTPException

    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="invalid_file_type", message="Tipo de arquivo não permitido. Use: JPG, PNG, GIF ou WebP")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 5 * 1024 * 1024:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="file_too_large", message="Arquivo muito grande. Tamanho máximo: 5MB")

    user_dir = USERDATA_DIR / "users" / str(current_user.id)
    profile_dir = user_dir / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    file_extension = Path(file.filename).suffix or ".jpg"
    unique_filename = f"avatar_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}{file_extension}"
    file_path = profile_dir / unique_filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:  # pragma: no cover - erro raro de filesystem
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {exc}") from exc

    if current_user.profile_picture:
        old_file = BASE_DIR / current_user.profile_picture.lstrip("/")
        if old_file.exists():
            try:
                old_file.unlink()
            except Exception:
                pass

    relative_path = file_path.relative_to(BASE_DIR)
    if not str(relative_path).startswith("user_data"):
        profile_picture_path = f"/user_data/users/{current_user.id}/profile/{unique_filename}"
    else:
        profile_picture_path = f"/{relative_path}"
    success = UserRepository.update(
        db,
        current_user.id,
        profile_picture=profile_picture_path,
    )
    if not success:
        file_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error="profile_update_failed", message="Erro ao atualizar foto de perfil")

    _add_log(f"Foto de perfil atualizada para usuário {current_user.username}", user_id=current_user.id)
    updated_user = UserRepository.get_by_id(db, current_user.id)
    return success_response(
        data={
            "profile_picture": profile_picture_path,
            "user": User.from_orm(updated_user),
        },
        message="Foto de perfil atualizada com sucesso",
    )


@router.delete("/me/profile-picture", response_model=APIResponse[dict])
async def delete_profile_picture(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    if not current_user.profile_picture:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="not_found", message="Usuário não possui foto de perfil")

    old_file = BASE_DIR / current_user.profile_picture.lstrip("/")
    if old_file.exists():
        try:
            old_file.unlink()
        except Exception:
            _add_log(f"Erro ao remover arquivo de foto de perfil: {old_file}", level="warning", user_id=current_user.id)

    UserRepository.update(db, current_user.id, profile_picture=None)
    _add_log(f"Foto de perfil removida para usuário {current_user.username}", user_id=current_user.id)

    updated_user = UserRepository.get_by_id(db, current_user.id)
    return success_response(
        data={"user": User.from_orm(updated_user)},
        message="Foto de perfil removida com sucesso",
    )


@router.post("/logout", response_model=APIResponse[dict])
@router.get("/logout", response_model=APIResponse[dict])
async def logout() -> APIResponse[dict]:
    return success_response(message="Logout realizado com sucesso")


@router.get("/users", response_model=APIResponse[List[User]])
async def get_users(
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[User]]:
    users = UserRepository.list_all(db)
    return success_response(data=[User.from_orm(u) for u in users])


@router.post("/users", response_model=APIResponse[dict])
async def create_new_user(
    request: CreateUserRequest,
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.auth import get_password_hash

    existing = UserRepository.get_by_username(db, request.username)
    if existing:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="user_exists", message="Usuário já existe")

    UserRepository.create(
        db,
        request.username,
        get_password_hash(request.password),
        request.email,
        request.full_name,
        request.is_admin,
    )
    _add_log(f"Admin {current_user.username} criou usuário {request.username}", user_id=current_user.id)
    return success_response(message=f"Usuário {request.username} criado com sucesso")


@router.post("/register", response_model=APIResponse[dict])
async def register_user(
    request: CreateUserRequest,
    authorization: Optional[str] = None,
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.auth import get_password_hash, verify_token

    user_count = db.query(UserModel).count()

    if user_count == 0:
        UserRepository.create(
            db,
            request.username,
            get_password_hash(request.password),
            request.email,
            request.full_name,
            True,
        )
        return success_response(message=f"Primeiro usuário {request.username} criado com sucesso (admin)")

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        token_data = verify_token(token)
        if token_data:
            user = UserRepository.get_by_username(db, token_data.username)
            if user and user.is_admin:
                existing = UserRepository.get_by_username(db, request.username)
                if existing:
                    raise_http_error(status.HTTP_400_BAD_REQUEST, error="user_exists", message="Usuário já existe")
                UserRepository.create(
                    db,
                    request.username,
                    get_password_hash(request.password),
                    request.email,
                    request.full_name,
                    request.is_admin,
                )
                return success_response(message=f"Usuário {request.username} criado com sucesso")

    raise_http_error(status.HTTP_403_FORBIDDEN, error="forbidden", message="Apenas administradores podem criar usuários")


@router.delete("/users/{username}", response_model=APIResponse[dict])
async def delete_user_endpoint(
    username: str,
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    user_to_delete = UserRepository.get_by_username(db, username)
    if not user_to_delete:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="user_not_found", message="Usuário não encontrado")

    if user_to_delete.is_admin:
        admin_count = UserRepository.count_admins(db)
        if admin_count <= 1:
            raise_http_error(status.HTTP_400_BAD_REQUEST, error="last_admin", message="Não é possível remover o último administrador")

    if UserRepository.delete(db, user_to_delete.id):
        _add_log(f"Admin {current_user.username} removeu usuário {username}", user_id=current_user.id)
        return success_response(message=f"Usuário {username} removido com sucesso")

    raise_http_error(status.HTTP_400_BAD_REQUEST, error="delete_failed", message="Não foi possível remover o usuário")


@router.put("/users/{username}/password", response_model=APIResponse[dict])
async def admin_reset_user_password(
    username: str,
    request: dict,
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.auth import get_password_hash

    user = UserRepository.get_by_username(db, username)
    if not user:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="user_not_found", message="Usuário não encontrado")

    new_password = request.get("new_password")
    if not new_password or len(new_password) < 6:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="weak_password", message="Senha deve ter pelo menos 6 caracteres")

    UserRepository.update_password(db, user.id, get_password_hash(new_password))
    _add_log(f"Admin {current_user.username} resetou senha do usuário {username}", user_id=current_user.id)
    return success_response(message=f"Senha resetada com sucesso para {username}")


@router.put("/users/{username}/quota", response_model=APIResponse[dict])
async def admin_update_user_quota(
    username: str,
    request: dict,
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    user = UserRepository.get_by_username(db, username)
    if not user:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="user_not_found", message="Usuário não encontrado")

    new_quota = request.get("account_quota")
    if new_quota is None:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="quota_missing", message="Campo account_quota é obrigatório")

    if not isinstance(new_quota, int):
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="quota_invalid", message="account_quota deve ser inteiro")

    UserRepository.update_quota(db, user.id, new_quota)
    _add_log(f"Admin {current_user.username} atualizou quota do usuário {username} para {new_quota}", user_id=current_user.id)
    return success_response(message=f"Quota atualizada para {username}")


@router.put("/users/{username}/quota/{quota}", response_model=APIResponse[dict])
async def admin_update_user_quota_simple(
    username: str,
    quota: int,
    current_user: UserModel = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    user = UserRepository.get_by_username(db, username)
    if not user:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="user_not_found", message="Usuário não encontrado")

    UserRepository.update_quota(db, user.id, quota)
    _add_log(f"Admin {current_user.username} atualizou quota do usuário {username} para {quota}", user_id=current_user.id)
    return success_response(message=f"Quota atualizada para {username}")


@router.post("/change-password", response_model=APIResponse[dict])
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.auth import get_password_hash, verify_password

    if not verify_password(request.old_password, current_user.hashed_password):
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="invalid_password", message="Senha atual incorreta")

    if len(request.new_password) < 6:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="weak_password", message="Nova senha deve ter pelo menos 6 caracteres")

    UserRepository.update_password(db, current_user.id, get_password_hash(request.new_password))
    _add_log(f"Usuário {current_user.username} atualizou a própria senha", user_id=current_user.id)
    return success_response(message="Senha alterada com sucesso")


@router.get("/preferences", response_model=APIResponse[dict])
async def get_preferences(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.repositories import UserPreferencesRepository

    prefs = UserPreferencesRepository.get_by_user_id(db, current_user.id)
    if not prefs:
        prefs = UserPreferencesRepository.create_default(db, current_user.id)
    return success_response(data=prefs.to_dict())


@router.put("/preferences", response_model=APIResponse[dict])
async def update_preferences(
    request: dict,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    from src.repositories import UserPreferencesRepository

    prefs = UserPreferencesRepository.upsert(db, current_user.id, request)
    return success_response(data=prefs.to_dict(), message="Preferências atualizadas")


@router.get("/api-keys", response_model=APIResponse[List[APIKeyPublic]])
async def list_api_keys(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[APIKeyPublic]]:
    api_keys = APIKeyRepository.list_by_user(db, current_user.id)
    return success_response(data=[APIKeyPublic.from_orm(k) for k in api_keys])


@router.post("/api-keys", response_model=APIResponse[APIKeyResponse])
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyResponse]:
    from src.auth import generate_api_key, hash_api_key

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    api_key = APIKeyRepository.create(
        db,
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        permissions=request.permissions,
    )
    response = APIKeyResponse(
        key_id=api_key.id,
        api_key=raw_key,
        name=api_key.name,
        message="API Key criada com sucesso",
    )
    _add_log(f"Usuário {current_user.username} criou nova API Key {api_key.name}", user_id=current_user.id)
    return success_response(data=response)


@router.delete("/api-keys/{key_id}", response_model=APIResponse[dict])
async def delete_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    api_key = APIKeyRepository.get_by_id(db, key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="api_key_not_found", message="API Key não encontrada")

    APIKeyRepository.delete(db, key_id)
    _add_log(f"Usuário {current_user.username} removeu API Key {api_key.name}", user_id=current_user.id)
    return success_response(message="API Key removida com sucesso")


@router.patch("/api-keys/{key_id}/status", response_model=APIResponse[dict])
async def update_api_key_status(
    key_id: int,
    request: dict,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    api_key = APIKeyRepository.get_by_id(db, key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise_http_error(status.HTTP_404_NOT_FOUND, error="api_key_not_found", message="API Key não encontrada")

    is_active = request.get("is_active")
    if is_active is None:
        raise_http_error(status.HTTP_400_BAD_REQUEST, error="status_missing", message="Campo is_active é obrigatório")

    APIKeyRepository.update_status(db, key_id, bool(is_active))
    _add_log(f"Usuário {current_user.username} atualizou status da API Key {api_key.name} para {is_active}", user_id=current_user.id)
    return success_response(message="Status atualizado com sucesso")


@router.get("/api-keys/verify", response_model=APIResponse[dict])
async def verify_api_key(api_key_obj=Depends(get_api_key_user)) -> APIResponse[dict]:  # type: ignore[annotation-unchecked]
    return success_response(
        data={
            "valid": True,
            "key_id": api_key_obj.id,
            "name": api_key_obj.name,
            "permissions": api_key_obj.permissions,
            "last_used": api_key_obj.last_used,
        }
    )
