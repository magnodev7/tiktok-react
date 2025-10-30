"""
Repositórios para acesso ao banco de dados
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import (
    User,
    APIKey,
    Schedule,
    VideoUploadLog,
    TikTokAccount,
    TikTokAccountMetric,
    ScheduleStatus,
    UserRole,
    UserPreferences,
)


class UserRepository:
    """Repositório para operações de usuários"""

    @staticmethod
    def create(db: Session, username: str, hashed_password: str, email: Optional[str] = None,
               full_name: Optional[str] = None, is_admin: bool = False) -> User:
        """Cria novo usuário"""
        role = UserRole.ADMIN if is_admin else UserRole.USER
        role_value = role.value if isinstance(role, UserRole) else str(role)
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_admin=is_admin,
            role=role_value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Busca usuário por username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Busca usuário por email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Busca usuário por ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Lista todos os usuários"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update_last_login(db: Session, user_id: int) -> None:
        """Atualiza último login do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def update_password(db: Session, user_id: int, new_hashed_password: str) -> bool:
        """Atualiza senha do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.hashed_password = new_hashed_password
            db.commit()
            return True
        return False

    @staticmethod
    def update_full_name(db: Session, user_id: int, full_name: str) -> bool:
        """Atualiza nome completo do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.full_name = full_name
            db.commit()
            return True
        return False

    @staticmethod
    def update_email(db: Session, user_id: int, email: str) -> bool:
        """Atualiza email do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.email = email
            db.commit()
            return True
        return False

    @staticmethod
    def update_quota(db: Session, user_id: int, new_quota: int) -> bool:
        """Atualiza quota de contas do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.account_quota = new_quota
            db.commit()
            return True
        return False

    @staticmethod
    def update(db: Session, user_id: int, **kwargs) -> bool:
        """Atualiza campos do usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['id', 'hashed_password']:
                setattr(user, key, value)

        db.commit()
        return True

    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Remove usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False

    @staticmethod
    def count_admins(db: Session) -> int:
        """Conta quantos administradores existem"""
        return db.query(User).filter(User.is_admin == True).count()


class APIKeyRepository:
    """Repositório para operações de API Keys"""

    @staticmethod
    def create(db: Session, user_id: int, name: str, key_hash: str,
               permissions: List[str] = None) -> APIKey:
        """Cria nova API key"""
        if permissions is None:
            permissions = ["read", "write"]

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key

    @staticmethod
    def get_by_hash(db: Session, key_hash: str) -> Optional[APIKey]:
        """Busca API key por hash"""
        return db.query(APIKey).filter(
            and_(APIKey.key_hash == key_hash, APIKey.is_active == True)
        ).first()

    @staticmethod
    def get_by_id(db: Session, api_key_id: int) -> Optional[APIKey]:
        """Busca API key por ID"""
        return db.query(APIKey).filter(APIKey.id == api_key_id).first()

    @staticmethod
    def list_by_user(db: Session, user_id: int) -> List[APIKey]:
        """Lista todas as API keys de um usuário"""
        return db.query(APIKey).filter(APIKey.user_id == user_id).all()

    @staticmethod
    def update_last_used(db: Session, api_key_id: int) -> None:
        """Atualiza último uso da API key"""
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if api_key:
            api_key.last_used = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def update_status(db: Session, api_key_id: int, is_active: bool) -> bool:
        """Ativa/desativa API key"""
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if api_key:
            api_key.is_active = is_active
            db.commit()
            return True
        return False

    @staticmethod
    def delete(db: Session, api_key_id: int) -> bool:
        """Remove API key"""
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if api_key:
            db.delete(api_key)
            db.commit()
            return True
        return False


class ScheduleRepository:
    """Repositório para operações de agendamentos"""

    @staticmethod
    def create(db: Session, user_id: int, video_path: str, scheduled_time: datetime,
               video_title: Optional[str] = None, video_description: Optional[str] = None,
               video_tags: Optional[List[str]] = None, account_name: str = None) -> Schedule:
        """Cria novo agendamento - account_name é obrigatório"""
        if not account_name:
            raise ValueError("account_name é obrigatório")
        schedule = Schedule(
            user_id=user_id,
            video_path=video_path,
            video_title=video_title,
            video_description=video_description,
            video_tags=video_tags,
            scheduled_time=scheduled_time,
            account_name=account_name
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def get_by_id(db: Session, schedule_id: int) -> Optional[Schedule]:
        """Busca agendamento por ID"""
        return db.query(Schedule).filter(Schedule.id == schedule_id).first()

    @staticmethod
    def list_pending(db: Session, account_name: str) -> List[Schedule]:
        """Lista agendamentos pendentes para uma conta específica"""
        if not account_name:
            raise ValueError("account_name é obrigatório")
        return db.query(Schedule).filter(
            and_(
                Schedule.status == ScheduleStatus.PENDING,
                Schedule.account_name == account_name,
                Schedule.scheduled_time <= datetime.now(timezone.utc)
            )
        ).order_by(Schedule.scheduled_time).all()

    @staticmethod
    def list_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Schedule]:
        """Lista agendamentos de um usuário"""
        return db.query(Schedule).filter(
            Schedule.user_id == user_id
        ).order_by(Schedule.scheduled_time.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def list_by_status(db: Session, status: ScheduleStatus, skip: int = 0, limit: int = 100) -> List[Schedule]:
        """Lista agendamentos por status"""
        return db.query(Schedule).filter(
            Schedule.status == status
        ).order_by(Schedule.scheduled_time.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, schedule_id: int, status: ScheduleStatus,
                     error_message: Optional[str] = None) -> bool:
        """Atualiza status do agendamento"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            schedule.status = status
            if error_message:
                schedule.error_message = error_message
            if status == ScheduleStatus.COMPLETED:
                schedule.posted_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @staticmethod
    def update_tiktok_url(db: Session, schedule_id: int, tiktok_url: str) -> bool:
        """Atualiza URL do TikTok após upload"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            schedule.tiktok_url = tiktok_url
            db.commit()
            return True
        return False

    @staticmethod
    def delete(db: Session, schedule_id: int) -> bool:
        """Remove agendamento"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            return True
        return False


class VideoUploadLogRepository:
    """Repositório para logs de upload"""

    @staticmethod
    def create(db: Session, video_path: str, action: str, status: str,
               schedule_id: Optional[int] = None, user_id: Optional[int] = None,
               message: Optional[str] = None, extra_data: Optional[dict] = None) -> VideoUploadLog:
        """Cria novo log de upload"""
        log = VideoUploadLog(
            schedule_id=schedule_id,
            user_id=user_id,
            video_path=video_path,
            action=action,
            status=status,
            message=message,
            extra_data=extra_data
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_by_schedule(db: Session, schedule_id: int) -> List[VideoUploadLog]:
        """Lista logs de um agendamento"""
        return db.query(VideoUploadLog).filter(
            VideoUploadLog.schedule_id == schedule_id
        ).order_by(VideoUploadLog.created_at.desc()).all()



class TikTokAccountRepository:
    """Repositório para operações de contas TikTok"""

    @staticmethod
    def create(db: Session, user_id: int, account_name: str, display_name: Optional[str] = None,
               description: Optional[str] = None, cookies_data: Optional[dict] = None,
               is_default: bool = False) -> TikTokAccount:
        """Cria nova conta TikTok"""
        from src.account_storage import AccountStorage

        # Se é default, remove default de outras contas do usuário
        if is_default:
            db.query(TikTokAccount).filter(
                TikTokAccount.user_id == user_id
            ).update({TikTokAccount.is_default: False})

        account = TikTokAccount(
            user_id=user_id,
            account_name=account_name,
            display_name=display_name,
            description=description,
            cookies_data=cookies_data,
            is_default=is_default
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        # Inicializa estrutura de pastas da conta
        storage = AccountStorage()
        try:
            storage.initialize_account_folders(account_name)

            # Salva cookies em arquivo se fornecidos
            if cookies_data:
                storage.save_cookies(account_name, cookies_data)

            # Cria arquivo de informações da conta
            storage.create_account_info_file(account_name, {
                "display_name": display_name,
                "description": description,
                "is_default": is_default
            })

            print(f"✅ Estrutura de pastas criada para conta: {account_name}")
        except Exception as e:
            print(f"⚠️ Erro ao criar estrutura de pastas para {account_name}: {e}")

        # Cria horários padrão de postagem para a conta
        try:
            PostingScheduleRepository.create_default_schedules(db, account.id)
            print(f"✅ Horários padrão criados para conta: {account_name}")
        except Exception as e:
            print(f"⚠️ Erro ao criar horários padrão para {account_name}: {e}")

        return account

    @staticmethod
    def get_by_id(db: Session, account_id: int) -> Optional[TikTokAccount]:
        """Busca conta por ID"""
        return db.query(TikTokAccount).filter(TikTokAccount.id == account_id).first()

    @staticmethod
    def get_by_name(db: Session, account_name: str) -> Optional[TikTokAccount]:
        """Busca conta por nome"""
        return db.query(TikTokAccount).filter(TikTokAccount.account_name == account_name).first()

    @staticmethod
    def get_default_by_user(db: Session, user_id: int) -> Optional[TikTokAccount]:
        """Busca conta default do usuário"""
        return db.query(TikTokAccount).filter(
            and_(TikTokAccount.user_id == user_id, TikTokAccount.is_default == True)
        ).first()

    @staticmethod
    def list_by_user(db: Session, user_id: int, active_only: bool = False) -> List[TikTokAccount]:
        """Lista todas as contas de um usuário"""
        query = db.query(TikTokAccount).filter(TikTokAccount.user_id == user_id)
        if active_only:
            query = query.filter(TikTokAccount.is_active == True)
        return query.order_by(TikTokAccount.is_default.desc(), TikTokAccount.created_at.desc()).all()

    @staticmethod
    def list_all_active(db: Session) -> List[TikTokAccount]:
        """Lista todas as contas ativas de todos os usuários (para scheduler daemon)"""
        return db.query(TikTokAccount).filter(TikTokAccount.is_active == True).all()

    @staticmethod
    def update(db: Session, account_id: int, display_name: Optional[str] = None,
               description: Optional[str] = None, cookies_data: Optional[dict] = None,
               is_active: Optional[bool] = None, is_default: Optional[bool] = None) -> bool:
        """Atualiza conta TikTok"""
        from src.account_storage import AccountStorage

        account = db.query(TikTokAccount).filter(TikTokAccount.id == account_id).first()
        if not account:
            return False

        # Se está marcando como default, remove default de outras contas
        if is_default is True:
            db.query(TikTokAccount).filter(
                TikTokAccount.user_id == account.user_id
            ).update({TikTokAccount.is_default: False})

        if display_name is not None:
            account.display_name = display_name
        if description is not None:
            account.description = description
        if cookies_data is not None:
            account.cookies_data = cookies_data

            # Salva novos cookies em arquivo
            storage = AccountStorage()
            try:
                storage.save_cookies(account.account_name, cookies_data)
                print(f"✅ Cookies atualizados para conta: {account.account_name}")
            except Exception as e:
                print(f"⚠️ Erro ao salvar cookies de {account.account_name}: {e}")

        if is_active is not None:
            account.is_active = is_active
        if is_default is not None:
            account.is_default = is_default

        db.commit()
        return True

    @staticmethod
    def update_statistics(db: Session, account_id: int) -> bool:
        """Atualiza estatísticas da conta (incrementa total_uploads e atualiza last_upload)"""
        account = db.query(TikTokAccount).filter(TikTokAccount.id == account_id).first()
        if account:
            account.total_uploads += 1
            account.last_upload = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @staticmethod
    def delete(db: Session, account_id: int, remove_files: bool = False) -> bool:
        """
        Remove conta TikTok

        Args:
            db: Sessão do banco de dados
            account_id: ID da conta
            remove_files: Se True, remove também arquivos da conta (padrão: False)

        Returns:
            True se removeu com sucesso
        """
        from src.account_storage import AccountStorage

        account = db.query(TikTokAccount).filter(TikTokAccount.id == account_id).first()
        if account:
            # Não permite deletar se for a única conta ativa do usuário
            active_count = db.query(TikTokAccount).filter(
                and_(TikTokAccount.user_id == account.user_id, TikTokAccount.is_active == True)
            ).count()
            if active_count <= 1 and account.is_active:
                return False

            account_name = account.account_name

            # Remove conta do banco
            db.delete(account)
            db.commit()

            # Remove dados da conta se solicitado
            if remove_files:
                storage = AccountStorage()
                try:
                    storage.delete_account_data(account_name, remove_videos=True)
                    print(f"✅ Dados removidos para conta: {account_name}")
                except Exception as e:
                    print(f"⚠️ Erro ao remover dados de {account_name}: {e}")

            return True
        return False


class TikTokAccountMetricsRepository:
    """Operações relacionadas às métricas históricas das contas TikTok."""

    @staticmethod
    def create(
        db: Session,
        account_id: int,
        *,
        followers: Optional[int] = None,
        following: Optional[int] = None,
        likes: Optional[int] = None,
        videos: Optional[int] = None,
        friend_count: Optional[int] = None,
        heart: Optional[int] = None,
        digg_count: Optional[int] = None,
        verified: bool = False,
        private_account: bool = False,
        region: Optional[str] = None,
        signature: Optional[str] = None,
        profile_pic: Optional[str] = None,
        social_links: Optional[List[str]] = None,
        extra: Optional[dict] = None,
    ) -> TikTokAccountMetric:
        record = TikTokAccountMetric(
            account_id=account_id,
            followers=followers,
            following=following,
            likes=likes,
            videos=videos,
            friend_count=friend_count,
            heart=heart,
            digg_count=digg_count,
            verified=verified,
            private_account=private_account,
            region=region,
            signature=signature,
            profile_pic=profile_pic,
            social_links=social_links,
            extra=extra or {},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_latest(db: Session, account_id: int) -> Optional[TikTokAccountMetric]:
        return (
            db.query(TikTokAccountMetric)
            .filter(TikTokAccountMetric.account_id == account_id)
            .order_by(TikTokAccountMetric.captured_at.desc())
            .first()
        )

    @staticmethod
    def list_history(
        db: Session,
        account_id: int,
        *,
        days_back: Optional[int] = None,
        limit: int = 90,
    ) -> List[TikTokAccountMetric]:
        query = db.query(TikTokAccountMetric).filter(TikTokAccountMetric.account_id == account_id)
        if days_back:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            query = query.filter(TikTokAccountMetric.captured_at >= cutoff)

        return (
            query.order_by(TikTokAccountMetric.captured_at.desc())
            .limit(limit)
            .all()
        )

class PostingScheduleRepository:
    # IMPORTANTE: Sempre use add_schedule(db, account_id, time_slot) para adicionar horários, nunca métodos globais.
    # Ao exibir horários, use get_active_schedules(db, account_id) ou get_all_schedules(db, account_id) para garantir o filtro por conta.
    # IMPORTANTE: Sempre use list_by_account(db, account_id) para exibir logs, nunca métodos globais ou sem filtro.
    """Repositório para operações de horários de postagem"""

    @staticmethod
    def create_default_schedules(db: Session, account_id: int) -> List:
        """Cria horários padrão (2 em 2 horas, 8 slots diários) para uma conta"""
        from src.models import PostingSchedule
        
        default_times = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
        schedules = []
        
        for idx, time_slot in enumerate(default_times):
            schedule = PostingSchedule(
                account_id=account_id,
                time_slot=time_slot,
                is_active=True,
                order_index=idx
            )
            db.add(schedule)
            schedules.append(schedule)
        
        db.commit()
        return schedules

    @staticmethod
    def get_active_schedules(db: Session, account_id: int) -> List:
        """Retorna horários ativos de uma conta, ordenados"""
        from src.models import PostingSchedule
        
        return db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id,
            PostingSchedule.is_active == True
        ).order_by(PostingSchedule.order_index).all()

    @staticmethod
    def get_all_schedules(db: Session, account_id: int) -> List:
        """Retorna todos os horários de uma conta (ativos e inativos)"""
        from src.models import PostingSchedule
        
        return db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id
        ).order_by(PostingSchedule.order_index).all()

    @staticmethod
    def add_schedule(db: Session, account_id: int, time_slot: str) -> Optional:
        """Adiciona novo horário para uma conta"""
        from src.models import PostingSchedule
        
        # Valida formato HH:MM
        if len(time_slot) != 5 or time_slot[2] != ':':
            return None
        
        # Verifica se já existe
        existing = db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id,
            PostingSchedule.time_slot == time_slot
        ).first()
        
        if existing:
            # Se existe mas está inativo, reativa
            if not existing.is_active:
                existing.is_active = True
                db.commit()
            return existing
        
        # Pega o próximo order_index
        max_order = db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id
        ).count()
        
        schedule = PostingSchedule(
            account_id=account_id,
            time_slot=time_slot,
            is_active=True,
            order_index=max_order
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def remove_schedule(db: Session, schedule_id: int) -> bool:
        """Remove (desativa) um horário"""
        from src.models import PostingSchedule
        
        schedule = db.query(PostingSchedule).filter(PostingSchedule.id == schedule_id).first()
        if schedule:
            schedule.is_active = False
            db.commit()
            return True
        return False

    @staticmethod
    def delete_schedule(db: Session, schedule_id: int) -> bool:
        """Deleta permanentemente um horário"""
        from src.models import PostingSchedule
        
        schedule = db.query(PostingSchedule).filter(PostingSchedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            return True
        return False

    @staticmethod
    def update_schedules_bulk(db: Session, account_id: int, time_slots: List[str]) -> List:
        """Atualiza todos os horários de uma conta de uma vez"""
        from src.models import PostingSchedule
        
        # Remove todos os horários antigos
        db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id
        ).delete()
        
        # Cria novos
        schedules = []
        for idx, time_slot in enumerate(time_slots):
            schedule = PostingSchedule(
                account_id=account_id,
                time_slot=time_slot,
                is_active=True,
                order_index=idx
            )
            db.add(schedule)
            schedules.append(schedule)
        
        db.commit()
        return schedules

    @staticmethod
    def get_account_by_name(db: Session, account_name: str) -> Optional:
        """Busca conta por nome (helper)"""
        from src.models import TikTokAccount
        return db.query(TikTokAccount).filter(TikTokAccount.account_name == account_name).first()

    @staticmethod
    def get_by_account(db: Session, account_id: int) -> List:
        """Retorna todos os horários de uma conta (alias para get_all_schedules)"""
        return PostingScheduleRepository.get_all_schedules(db, account_id)

    @staticmethod
    def get_by_id(db: Session, schedule_id: int) -> Optional:
        """Busca horário por ID"""
        from src.models import PostingSchedule
        return db.query(PostingSchedule).filter(PostingSchedule.id == schedule_id).first()

    @staticmethod
    def get_by_time_slot(db: Session, account_id: int, time_slot: str) -> Optional:
        """Busca horário específico de uma conta"""
        from src.models import PostingSchedule
        return db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id,
            PostingSchedule.time_slot == time_slot
        ).first()

    @staticmethod
    def create(db: Session, account_id: int, time_slot: str, is_active: bool = True,
               order_index: int = None) -> Optional:
        """Cria novo horário de postagem"""
        from src.models import PostingSchedule

        # Se order_index não foi fornecido, calcula o próximo
        if order_index is None:
            order_index = db.query(PostingSchedule).filter(
                PostingSchedule.account_id == account_id
            ).count()

        schedule = PostingSchedule(
            account_id=account_id,
            time_slot=time_slot,
            is_active=is_active,
            order_index=order_index
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def update(db: Session, schedule_id: int, **kwargs) -> Optional:
        """Atualiza horário de postagem"""
        from src.models import PostingSchedule

        schedule = db.query(PostingSchedule).filter(PostingSchedule.id == schedule_id).first()
        if not schedule:
            return None

        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def delete(db: Session, schedule_id: int) -> bool:
        """Remove permanentemente um horário"""
        from src.models import PostingSchedule

        schedule = db.query(PostingSchedule).filter(PostingSchedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            return True
        return False

    @staticmethod
    def delete_by_account(db: Session, account_id: int) -> int:
        """Remove todos os horários de uma conta, retorna quantidade removida"""
        from src.models import PostingSchedule

        count = db.query(PostingSchedule).filter(
            PostingSchedule.account_id == account_id
        ).delete()
        db.commit()
        return count


class SystemLogRepository:
    """Repositório para gerenciar logs do sistema"""

    @staticmethod
    def create(
        db: Session,
        message: str,
        level: str = "info",
        user_id: Optional[int] = None,
        account_name: Optional[str] = None,
        module: Optional[str] = None,
        extra_data: Optional[dict] = None
    ):
        """Cria um novo log"""
        from src.models import SystemLog, LogLevel

        # Valida level
        try:
            log_level = LogLevel(level.lower())
        except ValueError:
            log_level = LogLevel.INFO

        log_entry = SystemLog(
            user_id=user_id,
            account_name=account_name,
            message=message,
            level=log_level,
            module=module,
            extra_data=extra_data
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        limit: int = 50,
        account_name: Optional[str] = None,
        level: Optional[str] = None
    ):
        """Busca logs de um usuário específico"""
        from src.models import SystemLog, LogLevel

        query = db.query(SystemLog).filter(SystemLog.user_id == user_id)

        if account_name:
            query = query.filter(SystemLog.account_name == account_name)

        if level:
            try:
                log_level = LogLevel(level.lower())
                query = query.filter(SystemLog.level == log_level)
            except ValueError:
                pass

        return query.order_by(SystemLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_by_account(
        db: Session,
        account_name: str,
        limit: int = 50,
        user_id: Optional[int] = None
    ):
        """Busca logs de uma conta específica"""
        from src.models import SystemLog

        query = db.query(SystemLog).filter(SystemLog.account_name == account_name)

        if user_id:
            query = query.filter(SystemLog.user_id == user_id)

        return query.order_by(SystemLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_all(db: Session, limit: int = 50, level: Optional[str] = None):
        """Busca todos os logs (apenas admin)"""
        from src.models import SystemLog, LogLevel

        query = db.query(SystemLog)

        if level:
            try:
                log_level = LogLevel(level.lower())
                query = query.filter(SystemLog.level == log_level)
            except ValueError:
                pass

        return query.order_by(SystemLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def delete_old_logs(db: Session, days: int = 30) -> int:
        """Remove logs mais antigos que X dias, retorna quantidade removida"""
        from src.models import SystemLog
        from datetime import datetime, timedelta, timezone

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        count = db.query(SystemLog).filter(
            SystemLog.created_at < cutoff_date
        ).delete()
        db.commit()
        return count

    @staticmethod
    def delete_by_account(db: Session, account_name: str) -> int:
        """Remove todos os logs associados a uma conta específica."""
        from src.models import SystemLog

        count = db.query(SystemLog).filter(SystemLog.account_name == account_name).delete()
        db.commit()
        return count

    @staticmethod
    def delete_all(db: Session) -> int:
        """Remove todos os logs do sistema."""
        from src.models import SystemLog

        count = db.query(SystemLog).delete()
        db.commit()
        return count


class UserPreferencesRepository:
    """Repositório para operações de preferências de usuário"""

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> Optional[UserPreferences]:
        """Busca preferências do usuário"""
        return db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()

    @staticmethod
    def create_or_update(db: Session, user_id: int, **preferences) -> UserPreferences:
        """Cria ou atualiza preferências do usuário"""
        user_prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()

        if user_prefs:
            # Atualiza preferências existentes
            for key, value in preferences.items():
                if hasattr(user_prefs, key):
                    setattr(user_prefs, key, value)
        else:
            # Define valores padrão se não fornecidos
            defaults = {
                'theme': 'dark',
                'accent_color': '#0ea5e9',
                'notifications': {
                    'videoPublished': True,
                    'publicationFailed': True,
                    'highCapacity': True
                },
                'timezone': 'America/Sao_Paulo'
            }
            # Merge com preferências fornecidas
            merged_prefs = {**defaults, **preferences}

            # Cria novas preferências
            user_prefs = UserPreferences(user_id=user_id, **merged_prefs)
            db.add(user_prefs)

        db.commit()
        db.refresh(user_prefs)
        return user_prefs

    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Remove preferências do usuário"""
        user_prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        if user_prefs:
            db.delete(user_prefs)
            db.commit()
            return True
        return False
