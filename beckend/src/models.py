"""
Models do banco de dados para TikTok Scheduler
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum

from src.database import Base
from src.timezone_utils import now as tz_now


class UserRole(str, enum.Enum):
    """Roles de usuário"""
    ADMIN = "admin"
    USER = "user"


class ScheduleStatus(str, enum.Enum):
    """Status de agendamento"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """Model de Usuário"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    profile_picture = Column(String(500), nullable=True)  # Caminho para foto de perfil

    # Status e permissões
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.USER,
        nullable=False,
    )
    account_quota = Column(Integer, default=-1, nullable=False)  # -1 = ilimitado

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now,
                       onupdate=tz_now, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class APIKey(Base):
    """Model de API Key"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Status e permissões
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(JSON, default=["read", "write"], nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class Schedule(Base):
    """Model de Agendamento de Vídeos"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Informações do vídeo
    video_path = Column(String(500), nullable=False)
    video_title = Column(String(255), nullable=True)
    video_description = Column(Text, nullable=True)
    video_tags = Column(JSON, nullable=True)  # Lista de tags

    # Agendamento
    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        Enum(
            ScheduleStatus,
            name="schedulestatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ScheduleStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Resultado
    posted_at = Column(DateTime(timezone=True), nullable=True)
    tiktok_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    account_name = Column(String(100), nullable=False)
    extra_data = Column(JSON, nullable=True)  # Informações extras (renamed from metadata)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now,
                       onupdate=tz_now, nullable=False)

    # Relacionamentos
    user = relationship("User", back_populates="schedules")

    def __repr__(self):
        return f"<Schedule(id={self.id}, video_title='{self.video_title}', status='{self.status}')>"


class VideoUploadLog(Base):
    """Log de uploads de vídeos"""
    __tablename__ = "video_upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Informações do upload
    video_path = Column(String(500), nullable=False)
    action = Column(String(50), nullable=False)  # upload, retry, failed, etc
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)

    # Metadata
    extra_data = Column(JSON, nullable=True)  # Informações extras (renamed from metadata)

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)

    def __repr__(self):
        return f"<VideoUploadLog(id={self.id}, action='{self.action}', status='{self.status}')>"


class TikTokAccount(Base):
    """Model de Conta TikTok"""
    __tablename__ = "tiktok_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Informações da conta
    account_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Cookies (JSON para armazenar cookies do TikTok)
    cookies_data = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Estatísticas
    total_uploads = Column(Integer, default=0, nullable=False)
    last_upload = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now,
                       onupdate=tz_now, nullable=False)

    # Relacionamentos
    user = relationship("User", backref="tiktok_accounts")
    posting_schedules = relationship("PostingSchedule", back_populates="account", cascade="all, delete-orphan")
    metrics = relationship(
        "TikTokAccountMetric",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(TikTokAccountMetric.captured_at)",
    )

    def __repr__(self):
        return f"<TikTokAccount(id={self.id}, account_name='{self.account_name}', display_name='{self.display_name}')>"


class PostingSchedule(Base):
    """Model de Configuração de Horários de Postagem por Conta"""
    __tablename__ = "posting_schedules"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("tiktok_accounts.id"), nullable=False)

    # Horários de postagem (formato HH:MM)
    time_slot = Column(String(5), nullable=False)  # Ex: "08:00", "10:00"

    # Ativo/Inativo
    is_active = Column(Boolean, default=True, nullable=False)

    # Ordem (para ordenar os horários)
    order_index = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now,
                       onupdate=tz_now, nullable=False)

    # Relacionamentos
    account = relationship("TikTokAccount", back_populates="posting_schedules")

    def __repr__(self):
        return f"<PostingSchedule(id={self.id}, account_id={self.account_id}, time_slot='{self.time_slot}')>"


class TikTokAccountMetric(Base):
    """Métricas históricas de contas TikTok."""

    __tablename__ = "tiktok_account_metrics"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("tiktok_accounts.id"), nullable=False, index=True)
    captured_at = Column(DateTime(timezone=True), default=tz_now, nullable=False, index=True)

    followers = Column(Integer, nullable=True)
    following = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    videos = Column(Integer, nullable=True)
    friend_count = Column(Integer, nullable=True)
    heart = Column(Integer, nullable=True)
    digg_count = Column(Integer, nullable=True)

    verified = Column(Boolean, default=False, nullable=False)
    private_account = Column(Boolean, default=False, nullable=False)
    region = Column(String(100), nullable=True)
    signature = Column(Text, nullable=True)
    profile_pic = Column(String(500), nullable=True)
    social_links = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)

    account = relationship("TikTokAccount", back_populates="metrics")

    def __repr__(self):
        return (
            f"<TikTokAccountMetric(id={self.id}, account_id={self.account_id}, "
            f"captured_at='{self.captured_at}')>"
        )


class LogLevel(str, enum.Enum):
    """Níveis de log"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemLog(Base):
    """Model de Log do Sistema (isolado por usuário e conta)"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    account_name = Column(String(100), nullable=True, index=True)

    # Informações do log
    message = Column(Text, nullable=False)
    level = Column(
        Enum(
            LogLevel,
            name="loglevel",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=LogLevel.INFO,
        nullable=False,
        index=True,
    )

    # Context adicional
    module = Column(String(100), nullable=True)  # scheduler, uploader, etc
    extra_data = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relacionamentos
    user = relationship("User", backref="system_logs")

    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', account='{self.account_name}', message='{self.message[:50]}...')>"


class UserPreferences(Base):
    """Model de Preferências do Usuário"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Preferências de aparência
    theme = Column(String(20), default="dark", nullable=False)  # dark, light, system
    accent_color = Column(String(20), default="#0ea5e9", nullable=False)

    # Preferências de notificações
    notifications = Column(JSON, nullable=False)

    # Preferências regionais
    timezone = Column(String(100), default="America/Sao_Paulo", nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=tz_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=tz_now,
                       onupdate=tz_now, nullable=False)

    # Relacionamentos
    user = relationship("User", backref="preferences", uselist=False)

    def __repr__(self):
        return f"<UserPreferences(id={self.id}, user_id={self.user_id}, theme='{self.theme}')>"
