"""
Módulo 7: Proteção contra Duplicatas
Garante que o mesmo vídeo NUNCA seja postado mais de uma vez
Implementa proteção tripla contra race conditions
"""
import os
import time
import json
from pathlib import Path
from typing import Optional, Callable, Tuple
from datetime import datetime, timezone


class DuplicateProtectionModule:
    """
    Módulo responsável pela proteção contra postagens duplicadas.

    Implementa PROTEÇÃO TRIPLA:
    1. Verificação de lock de postagem (.posting.lock)
    2. Verificação de status nos metadados (status="posted" ou posted_at)
    3. Criação atômica de lock antes de postar

    Esta proteção previne race conditions onde múltiplos processos
    tentam postar o mesmo vídeo simultaneamente.
    """

    def __init__(self, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de proteção contra duplicatas.

        Args:
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.log = logger if logger else print
        self.lock_valid_duration = 600  # Lock válido por 10 minutos (600 segundos)

    # ===================== MÉTODOS UTILITÁRIOS =====================

    @staticmethod
    def _read_json(file_path: Path) -> Optional[dict]:
        """Lê arquivo JSON com segurança"""
        try:
            if not file_path.exists():
                return None
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json_atomic(file_path: Path, data: dict) -> None:
        """Escreve JSON atomicamente usando arquivo temporário"""
        tmp = file_path.with_suffix(file_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(file_path)

    @staticmethod
    def _get_lock_path(video_path: str) -> Path:
        """Retorna caminho do arquivo .posting.lock"""
        return Path(video_path).with_suffix(".posting.lock")

    @staticmethod
    def _get_metadata_path(video_path: str) -> Path:
        """Retorna caminho do arquivo de metadados (.json)"""
        return Path(video_path).with_suffix(".json")

    # ===================== VERIFICAÇÕES DE DUPLICAÇÃO =====================

    def check_posting_lock_exists(self, video_path: str) -> Tuple[bool, Optional[float]]:
        """
        Verifica se existe lock de postagem ativo.

        Args:
            video_path: Caminho do vídeo

        Returns:
            Tupla (lock_exists: bool, lock_age_seconds: Optional[float])
            - lock_exists: True se lock existe e é válido
            - lock_age_seconds: Idade do lock em segundos (None se não existe)
        """
        lock_path = self._get_lock_path(video_path)

        if not lock_path.exists():
            return False, None

        try:
            lock_age = time.time() - lock_path.stat().st_mtime

            # Lock válido por 10 minutos
            if lock_age < self.lock_valid_duration:
                self.log(f"🔒 Lock ativo detectado: {Path(video_path).name} (idade: {lock_age:.0f}s)")
                return True, lock_age
            else:
                # Lock antigo/travado
                self.log(f"⚠️ Lock antigo detectado: {Path(video_path).name} (idade: {lock_age:.0f}s)")
                return False, lock_age

        except Exception as e:
            self.log(f"⚠️ Erro ao verificar lock: {e}")
            return False, None

    def is_video_already_posted(self, video_path: str) -> bool:
        """
        Verifica se vídeo já foi postado através dos metadados.

        Verifica múltiplos indicadores:
        - status = "posted"
        - posted_at existe
        - Também verifica .meta.json legado

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se vídeo já foi postado, False caso contrário
        """
        video_name = Path(video_path).name

        # Verifica .json unificado (PRIORITÁRIO)
        unified_path = self._get_metadata_path(video_path)
        if unified_path.exists():
            meta = self._read_json(unified_path)
            if meta:
                # Verifica status="posted"
                if meta.get("status") == "posted":
                    self.log(f"⚠️ Vídeo já postado (status='posted'): {video_name}")
                    return True

                # Verifica posted_at existe
                if meta.get("posted_at"):
                    self.log(f"⚠️ Vídeo já postado (posted_at existe): {video_name}")
                    return True

        # Verifica .meta.json legado (RETROCOMPATIBILIDADE)
        legacy_path = Path(video_path).with_suffix(".meta.json")
        if legacy_path.exists():
            meta = self._read_json(legacy_path)
            if meta and meta.get("posted_at"):
                self.log(f"⚠️ Vídeo já postado (meta legado): {video_name}")
                return True

        return False

    def is_video_in_posted_folder(self, video_path: str, posted_dir: str) -> bool:
        """
        Verifica se vídeo já está na pasta 'posted'.

        Args:
            video_path: Caminho do vídeo
            posted_dir: Diretório 'posted'

        Returns:
            True se vídeo está em posted/, False caso contrário
        """
        if not os.path.isdir(posted_dir):
            return False

        video_name = os.path.basename(video_path)

        # Verifica se arquivo existe em posted/
        posted_video_path = os.path.join(posted_dir, video_name)
        if os.path.isfile(posted_video_path):
            self.log(f"⚠️ Vídeo encontrado em posted/: {video_name}")
            return True

        return False

    # ===================== VERIFICAÇÃO COMPLETA (PROTEÇÃO TRIPLA) =====================

    def can_post_video(self, video_path: str, posted_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verificação COMPLETA: pode postar este vídeo?
        Implementa PROTEÇÃO TRIPLA contra duplicação.

        Args:
            video_path: Caminho do vídeo
            posted_dir: Diretório 'posted' (opcional)

        Returns:
            Tupla (can_post: bool, reason: str)
            - can_post: True se pode postar, False caso contrário
            - reason: Motivo (sucesso ou bloqueio)
        """
        video_name = Path(video_path).name

        # PROTEÇÃO 1: Verifica lock de postagem
        lock_exists, lock_age = self.check_posting_lock_exists(video_path)
        if lock_exists:
            return False, f"Lock ativo - outro processo está postando (idade: {lock_age:.0f}s)"

        # PROTEÇÃO 2: Verifica metadados (status/posted_at)
        if self.is_video_already_posted(video_path):
            return False, "Vídeo já postado (verificado em metadados)"

        # PROTEÇÃO 3: Verifica pasta posted/ (opcional)
        if posted_dir and self.is_video_in_posted_folder(video_path, posted_dir):
            return False, "Vídeo já está na pasta posted/"

        # Todas as verificações passaram
        self.log(f"✅ Vídeo aprovado para postagem: {video_name}")
        return True, "Aprovado para postagem"

    # ===================== GERENCIAMENTO DE LOCKS =====================

    def create_posting_lock(self, video_path: str) -> bool:
        """
        Cria lock de postagem ANTES de iniciar upload.
        Criação atômica previne race conditions.

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se lock foi criado com sucesso, False se falhou
        """
        lock_path = self._get_lock_path(video_path)
        video_name = Path(video_path).name

        try:
            # Cria lock atomicamente
            now_iso = datetime.now(timezone.utc).isoformat()
            lock_content = f"posting_started_at={now_iso}\n"

            lock_path.write_text(lock_content, encoding="utf-8")
            self.log(f"🔒 Lock criado: {lock_path.name}")
            return True

        except Exception as e:
            self.log(f"❌ Falha ao criar lock (outro processo pode ter criado primeiro): {e}")
            return False

    def remove_posting_lock(self, video_path: str, force: bool = False) -> bool:
        """
        Remove lock de postagem APÓS concluir (sucesso ou falha).

        Args:
            video_path: Caminho do vídeo
            force: Se True, remove mesmo locks antigos

        Returns:
            True se lock foi removido ou não existia, False se falhou
        """
        lock_path = self._get_lock_path(video_path)

        if not lock_path.exists():
            return True

        try:
            # Se não é force, verifica idade do lock
            if not force:
                lock_age = time.time() - lock_path.stat().st_mtime
                if lock_age > self.lock_valid_duration:
                    self.log(f"⚠️ Removendo lock antigo ({lock_age:.0f}s)")

            lock_path.unlink(missing_ok=True)
            self.log(f"🔓 Lock removido: {lock_path.name}")
            return True

        except Exception as e:
            self.log(f"⚠️ Erro ao remover lock: {e}")
            return False

    def cleanup_stale_locks(self, directory: str, max_age_seconds: int = 600) -> int:
        """
        Limpa locks antigos/travados em um diretório.

        Args:
            directory: Diretório a verificar
            max_age_seconds: Idade máxima do lock em segundos (padrão: 10 min)

        Returns:
            Número de locks removidos
        """
        if not os.path.isdir(directory):
            return 0

        removed_count = 0
        now = time.time()

        try:
            for file in os.listdir(directory):
                if not file.endswith(".posting.lock"):
                    continue

                lock_path = os.path.join(directory, file)
                try:
                    lock_age = now - os.path.getmtime(lock_path)

                    if lock_age > max_age_seconds:
                        os.remove(lock_path)
                        self.log(f"🧹 Lock antigo removido: {file} (idade: {lock_age:.0f}s)")
                        removed_count += 1

                except Exception as e:
                    self.log(f"⚠️ Erro ao processar lock {file}: {e}")
                    continue

        except Exception as e:
            self.log(f"⚠️ Erro ao limpar locks: {e}")

        if removed_count > 0:
            self.log(f"✅ {removed_count} lock(s) antigo(s) removido(s)")

        return removed_count

    # ===================== MARCAÇÃO DE VÍDEO COMO POSTADO =====================

    def mark_video_as_posted(self, video_path: str) -> bool:
        """
        Marca vídeo como postado nos metadados.
        Atualiza AMBOS arquivos (.json e .meta.json).

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se marcou com sucesso, False caso contrário
        """
        p = Path(video_path)
        unified_path = p.with_suffix(".json")
        meta_path_legacy = p.with_suffix(".meta.json")
        posted_at_iso = datetime.now(timezone.utc).isoformat()

        success = False

        # Atualiza .json unificado (PRIORITÁRIO)
        if unified_path.exists():
            try:
                meta = self._read_json(unified_path) or {}
                meta["status"] = "posted"
                meta["posted_at"] = posted_at_iso
                self._write_json_atomic(unified_path, meta)
                self.log(f"✅ Metadados atualizados: {unified_path.name}")
                success = True
            except Exception as e:
                self.log(f"⚠️ Erro ao atualizar metadados unificados: {e}")

        # Atualiza .meta.json legado (RETROCOMPATIBILIDADE)
        if meta_path_legacy.exists():
            try:
                meta = self._read_json(meta_path_legacy) or {}
                meta["posted_at"] = posted_at_iso
                self._write_json_atomic(meta_path_legacy, meta)
                success = True
            except Exception as e:
                self.log(f"⚠️ Erro ao atualizar meta legado: {e}")

        return success

    # ===================== FLUXO COMPLETO (MÉTODO PRINCIPAL) =====================

    def protect_post_operation(
        self,
        video_path: str,
        posted_dir: Optional[str] = None,
        check_before: bool = True,
        create_lock: bool = True
    ) -> Tuple[bool, str]:
        """
        Método principal: prepara proteção antes de postar.

        Fluxo:
        1. Verifica se pode postar (se check_before=True)
        2. Cria lock de postagem (se create_lock=True)

        Args:
            video_path: Caminho do vídeo
            posted_dir: Diretório 'posted' (opcional)
            check_before: Se True, verifica antes de criar lock
            create_lock: Se True, cria lock de postagem

        Returns:
            Tupla (success: bool, message: str)
        """
        video_name = Path(video_path).name

        # PASSO 1: Verificação prévia
        if check_before:
            can_post, reason = self.can_post_video(video_path, posted_dir)
            if not can_post:
                return False, reason

        # PASSO 2: Cria lock atômico
        if create_lock:
            if not self.create_posting_lock(video_path):
                return False, "Falha ao criar lock (race condition detectada)"

        return True, f"Proteção ativada para: {video_name}"

    def finalize_post_operation(
        self,
        video_path: str,
        success: bool,
        mark_as_posted: bool = True,
        remove_lock: bool = True
    ) -> bool:
        """
        Finaliza operação de postagem (sucesso ou falha).

        Args:
            video_path: Caminho do vídeo
            success: Se postagem foi bem-sucedida
            mark_as_posted: Se True, marca como postado (apenas se success=True)
            remove_lock: Se True, remove lock

        Returns:
            True se finalização foi bem-sucedida, False caso contrário
        """
        # Marca como postado (apenas se sucesso)
        if success and mark_as_posted:
            if not self.mark_video_as_posted(video_path):
                self.log("⚠️ Falha ao marcar vídeo como postado")

        # Remove lock
        if remove_lock:
            if not self.remove_posting_lock(video_path):
                self.log("⚠️ Falha ao remover lock")
                return False

        return True

    # ===================== RELATÓRIOS E ESTATÍSTICAS =====================

    def get_protection_status(self, video_path: str, posted_dir: Optional[str] = None) -> dict:
        """
        Obtém status detalhado de proteção para um vídeo.

        Args:
            video_path: Caminho do vídeo
            posted_dir: Diretório 'posted' (opcional)

        Returns:
            Dicionário com informações detalhadas
        """
        lock_exists, lock_age = self.check_posting_lock_exists(video_path)
        already_posted = self.is_video_already_posted(video_path)
        in_posted_folder = self.is_video_in_posted_folder(video_path, posted_dir) if posted_dir else None
        can_post, reason = self.can_post_video(video_path, posted_dir)

        return {
            "video_name": Path(video_path).name,
            "lock_exists": lock_exists,
            "lock_age_seconds": lock_age,
            "already_posted": already_posted,
            "in_posted_folder": in_posted_folder,
            "can_post": can_post,
            "block_reason": None if can_post else reason,
            "protection_level": "PROTECTED" if not can_post else "CLEAR",
        }

    def print_protection_status(self, video_path: str, posted_dir: Optional[str] = None):
        """Imprime status de proteção formatado (útil para debug)"""
        status = self.get_protection_status(video_path, posted_dir)

        self.log(f"\n🛡️ Status de Proteção: {status['video_name']}")
        self.log(f"   Lock ativo: {status['lock_exists']}")
        if status['lock_age_seconds']:
            self.log(f"   Idade do lock: {status['lock_age_seconds']:.0f}s")
        self.log(f"   Já postado: {status['already_posted']}")
        if status['in_posted_folder'] is not None:
            self.log(f"   Em posted/: {status['in_posted_folder']}")
        self.log(f"   Pode postar: {status['can_post']}")
        if status['block_reason']:
            self.log(f"   Motivo bloqueio: {status['block_reason']}")
        self.log(f"   Nível proteção: {status['protection_level']}")
