import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_scheduler_logging(log_file: str = "logs/scheduler.log", level=logging.INFO):
    """Configure logging para o scheduler com arquivo rotativo"""
    
    # Cria diretório de logs se não existir
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configura formato
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para arquivo com rotação (max 10MB, 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Removido console_handler para evitar duplicação
    # O systemd já redireciona stdout para o arquivo de log
    # Adicionar ambos file_handler e console_handler causava logs duplicados

    # Configura root logger
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    # Não adiciona console_handler para evitar duplicação com systemd
    
    return root_logger

def get_logger(name: str):
    """Retorna logger com nome específico"""
    return logging.getLogger(name)
