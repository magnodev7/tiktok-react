# Patch para adicionar logging em scheduler_daemon.py
import re

with open('scheduler_daemon.py', 'r') as f:
    content = f.read()

# Adiciona import logging após os imports existentes
if 'import logging' not in content:
    content = content.replace('import traceback', 'import logging\nimport traceback')

# Modifica a função _log para usar logging
old_log = '''def _log(message: str, level: str = "info", account_name: Optional[str] = None) -> None:
    """Dispara logs tanto para stdout quanto para o serviço centralizado."""
    prefix = "[scheduler-daemon]"
    if account_name:
        prefix = f"{prefix}[{account_name}]"
    print(f"{prefix} {message}")'''

new_log = '''def _log(message: str, level: str = "info", account_name: Optional[str] = None) -> None:
    """Dispara logs tanto para stdout quanto para o serviço centralizado."""
    logger = logging.getLogger("scheduler_daemon")
    prefix = "[scheduler-daemon]"
    if account_name:
        prefix = f"{prefix}[{account_name}]"
    
    # Log via logging module
    log_method = getattr(logger, level, logger.info)
    log_method(f"{prefix} {message}")
    
    # Também print para compatibilidade
    print(f"{prefix} {message}")'''

content = content.replace(old_log, new_log)

with open('scheduler_daemon.py', 'w') as f:
    f.write(content)

print(Patch aplicado!)
