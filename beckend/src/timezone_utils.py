"""
Utilitários para gerenciamento de timezone da aplicação.

Define timezone padrão como America/Sao_Paulo (Brasília) e fornece
funções para trabalhar consistentemente com datas/horários.
"""

from datetime import datetime, timezone
import os

# Importar ZoneInfo com fallback para Python < 3.9
try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore
    except ImportError:
        # Fallback final usando pytz (mais comum)
        import pytz
        class ZoneInfo:  # type: ignore
            def __new__(cls, key):
                return pytz.timezone(key)

# Timezone padrão da aplicação (pode ser configurado via env)
DEFAULT_TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

def get_app_timezone() -> ZoneInfo:
    """
    Retorna o timezone configurado para a aplicação.

    Returns:
        ZoneInfo: Objeto de timezone (ex: America/Sao_Paulo)
    """
    try:
        return ZoneInfo(DEFAULT_TIMEZONE)
    except Exception:
        # Fallback para America/Sao_Paulo se timezone inválido
        return ZoneInfo("America/Sao_Paulo")


def now() -> datetime:
    """
    Retorna datetime atual no timezone da aplicação.

    Returns:
        datetime: Data/hora atual com timezone da aplicação

    Example:
        >>> from src.timezone_utils import now
        >>> current_time = now()  # 2025-01-23 14:30:00-03:00 (horário de Brasília)
    """
    return datetime.now(get_app_timezone())


def utc_to_local(dt: datetime) -> datetime:
    """
    Converte datetime UTC para timezone local da aplicação.

    Args:
        dt: Datetime em UTC

    Returns:
        datetime: Datetime convertido para timezone local

    Example:
        >>> utc_time = datetime(2025, 1, 23, 17, 30, tzinfo=timezone.utc)
        >>> local_time = utc_to_local(utc_time)  # 2025-01-23 14:30:00-03:00
    """
    if dt.tzinfo is None:
        # Se não tem timezone, assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_app_timezone())


def local_to_utc(dt: datetime) -> datetime:
    """
    Converte datetime local para UTC.

    Args:
        dt: Datetime no timezone local

    Returns:
        datetime: Datetime convertido para UTC

    Example:
        >>> local_time = datetime(2025, 1, 23, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        >>> utc_time = local_to_utc(local_time)  # 2025-01-23 17:30:00+00:00
    """
    if dt.tzinfo is None:
        # Se não tem timezone, assume timezone local
        dt = dt.replace(tzinfo=get_app_timezone())
    return dt.astimezone(timezone.utc)


def parse_datetime(dt_string: str) -> datetime:
    """
    Parse string de data/hora e garante timezone correto.

    Args:
        dt_string: String no formato ISO 8601 ou similar

    Returns:
        datetime: Datetime com timezone da aplicação

    Example:
        >>> dt = parse_datetime("2025-01-23T14:30:00")  # Assume timezone local
        >>> dt = parse_datetime("2025-01-23T14:30:00-03:00")  # Mantém timezone especificado
    """
    # Parse da string
    if dt_string.endswith('Z'):
        # UTC timezone
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return utc_to_local(dt)

    try:
        dt = datetime.fromisoformat(dt_string)
    except ValueError:
        # Tentar outros formatos
        from dateutil import parser
        dt = parser.parse(dt_string)

    # Se não tem timezone, assume local
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_app_timezone())

    return dt


def format_datetime(dt: datetime, format_type: str = "iso") -> str:
    """
    Formata datetime para string.

    Args:
        dt: Datetime para formatar
        format_type: Tipo de formato ('iso', 'display', 'db')

    Returns:
        str: String formatada

    Example:
        >>> dt = now()
        >>> format_datetime(dt, 'iso')  # '2025-01-23T14:30:00-03:00'
        >>> format_datetime(dt, 'display')  # '23/01/2025 14:30'
        >>> format_datetime(dt, 'db')  # '2025-01-23 14:30:00'
    """
    # Garantir que está no timezone local
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_app_timezone())
    else:
        dt = utc_to_local(dt)

    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "display":
        return dt.strftime("%d/%m/%Y %H:%M")
    elif format_type == "db":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return str(dt)


def get_timezone_offset() -> str:
    """
    Retorna offset do timezone em formato string.

    Returns:
        str: Offset (ex: '-03:00', '+00:00')

    Example:
        >>> get_timezone_offset()  # '-03:00' para America/Sao_Paulo
    """
    dt = now()
    offset = dt.strftime("%z")
    # Formatar como -03:00 ao invés de -0300
    return f"{offset[:-2]}:{offset[-2:]}"


def is_aware(dt: datetime) -> bool:
    """
    Verifica se datetime tem timezone.

    Args:
        dt: Datetime para verificar

    Returns:
        bool: True se tem timezone, False caso contrário
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def make_aware(dt: datetime, tz: ZoneInfo = None) -> datetime:
    """
    Adiciona timezone a datetime naive.

    Args:
        dt: Datetime naive (sem timezone)
        tz: Timezone a usar (padrão: timezone da aplicação)

    Returns:
        datetime: Datetime com timezone
    """
    if is_aware(dt):
        return dt

    if tz is None:
        tz = get_app_timezone()

    return dt.replace(tzinfo=tz)


# Atalhos para facilitar uso
tz = get_app_timezone()
tz_offset = get_timezone_offset()
