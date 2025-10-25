"""
Routes para gerenciamento de horários de postagem por conta TikTok
Cada conta possui seus próprios horários configurados de forma isolada
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from src.database import get_db
from src.auth import get_current_user, get_current_user_or_api_key
from src.models import User, APIKey as APIKeyModel
from src.repositories import PostingScheduleRepository, TikTokAccountRepository
from typing import Dict, List, Optional, Set, Tuple



router = APIRouter(prefix="/api/posting-schedules", tags=["posting-schedules"])


# Helper para obter user_id de JWT ou API Key
async def get_user_id_from_auth(
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]]
) -> int:
    """Extrai user_id de autenticação JWT ou API Key"""
    user, api_key = auth_data
    if user:
        return user.id
    elif api_key:
        return api_key.user_id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )


# Schema para notificações
class ScheduleCapacityAlert(BaseModel):
    """Alerta de capacidade de agendamento"""
    account_id: int
    account_name: str
    alert_type: str  # warning, critical, info
    message: str
    current_slots: int
    total_capacity: int
    percentage: float
    days_until_full: Optional[int] = None


# Schemas
class PostingScheduleCreate(BaseModel):
    """Schema para criar horário de postagem"""
    time_slot: str = Field(..., description="Horário no formato HH:MM", example="08:00")
    is_active: bool = Field(default=True, description="Se o horário está ativo")

    @validator('time_slot')
    def validate_time_slot(cls, v):
        """Valida formato HH:MM"""
        import re
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Formato inválido. Use HH:MM (ex: 08:00)')
        return v


class PostingScheduleUpdate(BaseModel):
    """Schema para atualizar horário de postagem"""
    time_slot: Optional[str] = Field(None, description="Horário no formato HH:MM")
    is_active: Optional[bool] = Field(None, description="Se o horário está ativo")

    @validator('time_slot')
    def validate_time_slot(cls, v):
        """Valida formato HH:MM"""
        if v is None:
            return v
        import re
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Formato inválido. Use HH:MM (ex: 08:00)')
        return v


class PostingScheduleBulkCreate(BaseModel):
    """Schema para criar múltiplos horários de uma vez"""
    time_slots: List[str] = Field(..., description="Lista de horários no formato HH:MM")

    @validator('time_slots')
    def validate_time_slots(cls, v):
        """Valida cada horário"""
        import re
        for slot in v:
            if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', slot):
                raise ValueError(f'Formato inválido em "{slot}". Use HH:MM (ex: 08:00)')
        return v


class PostingScheduleResponse(BaseModel):
    """Schema de resposta de horário de postagem"""
    id: int
    account_id: int
    time_slot: str
    is_active: bool
    order_index: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# Endpoints
@router.get("/{account_id}", response_model=List[PostingScheduleResponse])
async def list_account_schedules(
    account_id: int,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Lista todos os horários configurados para uma conta específica

    - **account_id**: ID da conta TikTok
    - Retorna lista ordenada de horários
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica se conta existe e pertence ao usuário
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    # Verifica permissão (admin bypass)
    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar horários desta conta"
        )

    # Busca horários da conta (isolados por account_id)
    schedules = PostingScheduleRepository.get_by_account(db, account_id)

    return [
        PostingScheduleResponse(
            id=s.id,
            account_id=s.account_id,
            time_slot=s.time_slot,
            is_active=s.is_active,
            order_index=s.order_index,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in schedules
    ]


@router.get("/{account_id}/active", response_model=List[str])
async def list_active_schedules(
    account_id: int,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Lista apenas os horários ativos de uma conta

    - **account_id**: ID da conta TikTok
    - Retorna lista de strings HH:MM ordenadas
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar horários desta conta"
        )

    # Busca apenas horários ativos (isolados por account_id)
    schedules = PostingScheduleRepository.get_active_schedules(db, account_id)

    return [s.time_slot for s in schedules]


@router.post("/{account_id}", response_model=PostingScheduleResponse)
async def create_schedule(
    account_id: int,
    schedule_data: PostingScheduleCreate,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Cria um novo horário de postagem para uma conta específica

    - **account_id**: ID da conta TikTok
    - **time_slot**: Horário no formato HH:MM
    - **is_active**: Se o horário está ativo (padrão: true)
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para configurar horários desta conta"
        )

    # Verifica se horário já existe para esta conta
    existing = PostingScheduleRepository.get_by_time_slot(db, account_id, schedule_data.time_slot)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Horário {schedule_data.time_slot} já existe para esta conta"
        )

    # Cria horário (isolado por account_id)
    schedule = PostingScheduleRepository.create(
        db,
        account_id=account_id,
        time_slot=schedule_data.time_slot,
        is_active=schedule_data.is_active
    )

    return PostingScheduleResponse(
        id=schedule.id,
        account_id=schedule.account_id,
        time_slot=schedule.time_slot,
        is_active=schedule.is_active,
        order_index=schedule.order_index,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat()
    )


@router.post("/{account_id}/bulk", response_model=List[PostingScheduleResponse])
async def create_bulk_schedules(
    account_id: int,
    bulk_data: PostingScheduleBulkCreate,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Cria múltiplos horários de postagem de uma vez

    - **account_id**: ID da conta TikTok
    - **time_slots**: Lista de horários no formato HH:MM
    - Remove horários existentes e cria os novos
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para configurar horários desta conta"
        )

    # Remove horários existentes desta conta (apenas desta conta)
    PostingScheduleRepository.delete_by_account(db, account_id)

    # Cria novos horários (isolados por account_id)
    created_schedules = []
    for idx, time_slot in enumerate(sorted(set(bulk_data.time_slots))):
        schedule = PostingScheduleRepository.create(
            db,
            account_id=account_id,
            time_slot=time_slot,
            is_active=True,
            order_index=idx
        )
        created_schedules.append(schedule)

    return [
        PostingScheduleResponse(
            id=s.id,
            account_id=s.account_id,
            time_slot=s.time_slot,
            is_active=s.is_active,
            order_index=s.order_index,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in created_schedules
    ]


@router.put("/{account_id}/schedules/{schedule_id}", response_model=PostingScheduleResponse)
async def update_schedule(
    account_id: int,
    schedule_id: int,
    schedule_data: PostingScheduleUpdate,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Atualiza um horário de postagem existente

    - **account_id**: ID da conta TikTok
    - **schedule_id**: ID do horário
    - Apenas horários da própria conta podem ser atualizados
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões da conta
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para configurar horários desta conta"
        )

    # Busca horário (validando que pertence à conta)
    schedule = PostingScheduleRepository.get_by_id(db, schedule_id)
    if not schedule or schedule.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Horário {schedule_id} não encontrado para esta conta"
        )

    # Atualiza apenas campos fornecidos
    update_data = schedule_data.dict(exclude_unset=True)

    # Se mudou o horário, verifica duplicação
    if 'time_slot' in update_data:
        existing = PostingScheduleRepository.get_by_time_slot(db, account_id, update_data['time_slot'])
        if existing and existing.id != schedule_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Horário {update_data['time_slot']} já existe para esta conta"
            )

    # Atualiza
    updated = PostingScheduleRepository.update(db, schedule_id, **update_data)

    return PostingScheduleResponse(
        id=updated.id,
        account_id=updated.account_id,
        time_slot=updated.time_slot,
        is_active=updated.is_active,
        order_index=updated.order_index,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat()
    )


@router.delete("/{account_id}/schedules/{schedule_id}")
async def delete_schedule(
    account_id: int,
    schedule_id: int,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Remove um horário de postagem

    - **account_id**: ID da conta TikTok
    - **schedule_id**: ID do horário
    - Apenas horários da própria conta podem ser removidos
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões da conta
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para configurar horários desta conta"
        )

    # Busca horário (validando que pertence à conta)
    schedule = PostingScheduleRepository.get_by_id(db, schedule_id)
    if not schedule or schedule.account_id != account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Horário {schedule_id} não encontrado para esta conta"
        )

    # Remove
    PostingScheduleRepository.delete(db, schedule_id)

    return {"message": f"Horário {schedule.time_slot} removido com sucesso"}


@router.delete("/{account_id}/schedules")
async def delete_all_schedules(
    account_id: int,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Remove todos os horários de uma conta

    - **account_id**: ID da conta TikTok
    - Remove apenas horários desta conta específica
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para configurar horários desta conta"
        )

    # Remove todos os horários desta conta (isolado por account_id)
    deleted_count = PostingScheduleRepository.delete_by_account(db, account_id)

    return {"message": f"{deleted_count} horários removidos com sucesso"}


@router.get("/{account_id}/capacity")
async def get_account_capacity(
    account_id: int,
    days: int = 30,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Retorna informações sobre capacidade de agendamento da conta

    - **account_id**: ID da conta TikTok
    - **days**: Quantidade de dias para analisar (padrão: 30)
    - Retorna capacidade total, slots ocupados e alertas
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar dados desta conta"
        )

    # Busca horários ativos
    schedules = PostingScheduleRepository.get_active_schedules(db, account_id)
    daily_capacity = len(schedules)

    # TODO: Implementar contagem real de vídeos agendados
    # Por enquanto, retorna dados simulados para não quebrar o frontend
    total_capacity = daily_capacity * days
    total_occupied = 0  # Será implementado quando houver sistema de agendamento
    percentage = 0
    days_until_full = days if daily_capacity > 0 else None
    count_by_day = {}

    return {
        "account_id": account_id,
        "account_name": account.account_name,
        "daily_capacity": daily_capacity,
        "total_capacity": total_capacity,
        "total_occupied": total_occupied,
        "percentage_full": round(percentage, 2),
        "days_until_full": days_until_full,
        "occupation_by_day": count_by_day,
        "time_slots": [s.time_slot for s in schedules]
    }


@router.get("/{account_id}/alerts", response_model=List[ScheduleCapacityAlert])
async def get_capacity_alerts(
    account_id: int,
    days: int = 7,
    auth_data: Tuple[Optional[User], Optional[APIKeyModel]] = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Retorna alertas sobre capacidade de agendamento

    - **account_id**: ID da conta TikTok
    - **days**: Dias para verificar alertas (padrão: 7)
    - Retorna lista de alertas (warning, critical, info)
    - Aceita autenticação via JWT ou API Key
    """
    # Obtém user_id da autenticação
    user_id = await get_user_id_from_auth(auth_data)
    user, _ = auth_data

    # Verifica permissões
    account = TikTokAccountRepository.get_by_id(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta {account_id} não encontrada"
        )

    is_admin = user.is_admin if user else False
    if account.user_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar dados desta conta"
        )

    # Busca horários ativos
    schedules = PostingScheduleRepository.get_active_schedules(db, account_id)
    daily_capacity = len(schedules)

    if daily_capacity == 0:
        return [ScheduleCapacityAlert(
            account_id=account_id,
            account_name=account.account_name,
            alert_type="warning",
            message="Nenhum horário de postagem configurado",
            current_slots=0,
            total_capacity=0,
            percentage=0.0
        )]

    # TODO: Implementar contagem real de vídeos agendados
    # Por enquanto, retorna alerta informativo de que tudo está OK
    alerts = []
    alerts.append(ScheduleCapacityAlert(
        account_id=account_id,
        account_name=account.account_name,
        alert_type="info",
        message=f"Capacidade saudável - {daily_capacity} slots diários disponíveis",
        current_slots=0,
        total_capacity=daily_capacity * days,
        percentage=0.0
    ))

    return alerts
