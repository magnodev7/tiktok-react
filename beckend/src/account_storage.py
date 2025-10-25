"""
Gerenciamento de estrutura de pastas e arquivos por conta TikTok
"""

import json
import os
from pathlib import Path

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


TEMPLATE_IGNORE_KEYS = {"value", "expires", "expiry", "expirationDate"}
DEFAULT_COOKIE_DOMAIN = ".tiktok.com"
DEFAULT_COOKIE_PATH = "/"


class AccountStorage:
    """Gerencia a estrutura de pastas e arquivos de cada conta TikTok"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador de armazenamento

        Args:
            base_dir: Diretório base do projeto (padrão: /app ou diretório atual)
        """
        if base_dir is None:
            env_base_dir = os.getenv("BASE_DIR")
            if env_base_dir:
                base_dir = Path(env_base_dir)
            else:
                # Fallback para a raiz do projeto (evita diretório /app em ambientes não containerizados)
                base_dir = Path(__file__).resolve().parent.parent

        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir = Path(os.getenv("BASE_VIDEOS_DIR") or (self.base_dir / "videos"))
        self.posted_dir = Path(os.getenv("BASE_POSTED_DIR") or (self.base_dir / "posted"))
        self.userdata_dir = Path(os.getenv("BASE_USERDATA_DIR") or (self.base_dir / "user_data"))
        self.state_dir = Path(os.getenv("BASE_STATE_DIR") or (self.base_dir / "state"))

    def _load_cookie_template(self, account_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Recupera metadados de cookies já salvos para reaproveitar atributos
        como domínio/caminho ao normalizar novas entradas.
        """
        structure = self.get_account_structure(account_name)
        cookies_dir = structure["cookies"]

        candidates: List[Path] = []
        latest_file = cookies_dir / "cookies_latest.json"
        if latest_file.exists():
            candidates.append(latest_file)

        # Mantém compatibilidade com arquivos antigos caso ainda existam
        history = sorted(
            cookies_dir.glob("cookies_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidates.extend(history)

        for cookie_file in candidates:
            try:
                data = json.loads(cookie_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            cookies = data.get("cookies")
            if isinstance(cookies, dict):
                # Converte dict simples em lista para reaproveitar campos
                cookies = [
                    {
                        "name": name,
                        "value": value,
                        "domain": DEFAULT_COOKIE_DOMAIN,
                        "path": DEFAULT_COOKIE_PATH,
                    }
                    for name, value in cookies.items()
                ]

            if not isinstance(cookies, list):
                continue

            template: Dict[str, Dict[str, Any]] = {}
            for entry in cookies:
                name = entry.get("name")
                if not name:
                    continue
                template[name] = {
                    key: value for key, value in entry.items() if key not in TEMPLATE_IGNORE_KEYS
                }

            if template:
                return template

        return {}

    def _normalize_cookies(self, account_name: str, cookies_data: Any) -> Any:
        """
        Garante que os cookies sejam armazenados no formato esperado (lista de objetos).
        """
        if isinstance(cookies_data, list):
            return cookies_data

        if isinstance(cookies_data, dict):
            template = self._load_cookie_template(account_name)
            normalized: List[Dict[str, Any]] = []
            for name, value in cookies_data.items():
                entry = dict(template.get(name, {}))
                entry["name"] = name
                entry["value"] = value
                entry.setdefault("domain", DEFAULT_COOKIE_DOMAIN)
                entry.setdefault("path", DEFAULT_COOKIE_PATH)
                normalized.append(entry)
            return normalized

        return cookies_data

    def get_account_structure(self, account_name: str) -> Dict[str, Path]:
        """
        Retorna a estrutura de pastas de uma conta

        Args:
            account_name: Nome da conta TikTok

        Returns:
            Dicionário com os caminhos de cada pasta
        """
        return {
            "videos": self.videos_dir / account_name,
            "posted": self.posted_dir / account_name,
            "userdata": self.userdata_dir / account_name,
            "cookies": self.userdata_dir / account_name / "cookies",
            "sessions": self.userdata_dir / account_name / "sessions",
            "logs": self.userdata_dir / account_name / "logs",
        }

    def initialize_account_folders(self, account_name: str) -> Dict[str, Path]:
        """
        Cria toda a estrutura de pastas para uma conta TikTok

        Args:
            account_name: Nome da conta TikTok

        Returns:
            Dicionário com os caminhos criados
        """
        structure = self.get_account_structure(account_name)

        # Cria todas as pastas
        for folder_type, folder_path in structure.items():
            folder_path.mkdir(parents=True, exist_ok=True)

        # Cria arquivo README na pasta principal
        readme_path = structure["userdata"] / "README.txt"
        if not readme_path.exists():
            readme_content = f"""
===========================================
CONTA TIKTOK: {account_name}
===========================================

Esta pasta contém todos os dados relacionados à conta TikTok "{account_name}".

ESTRUTURA DE PASTAS:
--------------------
cookies/    - Arquivos de cookies para autenticação
sessions/   - Dados de sessão do navegador
logs/       - Logs de atividades da conta

IMPORTANTE:
-----------
⚠️ NÃO compartilhe esta pasta com terceiros!
⚠️ Os cookies contêm informações sensíveis de autenticação
⚠️ Faça backup regular desta pasta para não perder suas configurações

Criado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            readme_path.write_text(readme_content, encoding="utf-8")

        return structure

    def save_cookies(self, account_name: str, cookies_data: Any) -> Path:
        """
        Salva cookies da conta em arquivo JSON

        Args:
            account_name: Nome da conta TikTok
            cookies_data: Dados dos cookies (dict ou list)

        Returns:
            Caminho do arquivo salvo
        """
        structure = self.get_account_structure(account_name)
        cookies_dir = structure["cookies"]
        cookies_dir.mkdir(parents=True, exist_ok=True)

        # Normaliza estrutura (suporta dict ou lista)
        normalized_cookies = self._normalize_cookies(account_name, cookies_data)

        # Remove histórico antigo para evitar confusão com cookies expirados
        for old_file in cookies_dir.glob("cookies_*.json"):
            try:
                old_file.unlink()
            except Exception:
                pass

        cookies_file = cookies_dir / "cookies_latest.json"

        with open(cookies_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "account_name": account_name,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "cookies": normalized_cookies,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        return cookies_file

    def get_latest_cookies(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        Recupera os cookies mais recentes de uma conta

        Args:
            account_name: Nome da conta TikTok

        Returns:
            Dados dos cookies ou None se não existir
        """
        structure = self.get_account_structure(account_name)
        latest_link = structure["cookies"] / "cookies_latest.json"

        if not latest_link.exists():
            return None

        try:
            with open(latest_link, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cookies")
        except Exception as e:
            print(f"Erro ao ler cookies de {account_name}: {e}")
            return None

    def list_cookie_files(self, account_name: str) -> List[Path]:
        """
        Lista todos os arquivos de cookies de uma conta (ordenados por data)

        Args:
            account_name: Nome da conta TikTok

        Returns:
            Lista de caminhos de arquivos de cookies
        """
        structure = self.get_account_structure(account_name)
        cookies_dir = structure["cookies"]

        if not cookies_dir.exists():
            return []

        # Lista apenas arquivos com padrão cookies_*.json (não o latest)
        cookie_files = sorted(
            cookies_dir.glob("cookies_[0-9]*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        return cookie_files

    def create_account_info_file(self, account_name: str, info: Dict[str, Any]) -> Path:
        """
        Cria arquivo de informações da conta

        Args:
            account_name: Nome da conta TikTok
            info: Informações da conta (display_name, description, etc)

        Returns:
            Caminho do arquivo criado
        """
        structure = self.get_account_structure(account_name)
        info_file = structure["userdata"] / "account_info.json"

        account_info = {
            "account_name": account_name,
            "display_name": info.get("display_name"),
            "description": info.get("description"),
            "is_default": info.get("is_default", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(account_info, f, indent=2, ensure_ascii=False)

        return info_file

    def delete_account_data(self, account_name: str, remove_videos: bool = False) -> bool:
        """
        Remove dados de uma conta

        Args:
            account_name: Nome da conta TikTok
            remove_videos: Se True, remove também vídeos e postados (padrão: False)

        Returns:
            True se removeu com sucesso
        """
        import shutil

        structure = self.get_account_structure(account_name)

        # Sempre remove userdata (cookies, sessions, logs)
        if structure["userdata"].exists():
            shutil.rmtree(structure["userdata"])

        # Remove vídeos apenas se solicitado
        if remove_videos:
            if structure["videos"].exists():
                shutil.rmtree(structure["videos"])
            if structure["posted"].exists():
                shutil.rmtree(structure["posted"])

        return True
