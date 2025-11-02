"""
Módulo 6: Gerenciamento de Arquivos
Manipula, exclui ou move arquivos JSON e vídeos com segurança
"""
import os
import shutil
import json
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime


class FileManagerModule:
    """
    Módulo responsável pelo gerenciamento de arquivos no sistema.
    Gerencia vídeos, metadados JSON, locks de postagem e movimentação de arquivos.
    """

    def __init__(self, logger: Optional[Callable] = None):
        """
        Inicializa o módulo de gerenciamento de arquivos.

        Args:
            logger: Função de logging (opcional, usa print por padrão)
        """
        self.log = logger if logger else print

    # ===================== OPERAÇÕES COM JSON =====================

    def read_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Lê arquivo JSON com segurança.

        Args:
            file_path: Caminho do arquivo JSON

        Returns:
            Dicionário com dados ou None se falhar
        """
        if not os.path.isfile(file_path):
            self.log(f"⚠️ Arquivo JSON não encontrado: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            self.log(f"❌ Erro ao decodificar JSON {file_path}: {e}")
            return None
        except Exception as e:
            self.log(f"❌ Erro ao ler JSON {file_path}: {e}")
            return None

    def write_json(self, file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
        """
        Escreve dados em arquivo JSON com segurança.

        Args:
            file_path: Caminho do arquivo JSON
            data: Dados a serem escritos
            indent: Indentação (padrão: 2)

        Returns:
            True se escreveu com sucesso, False caso contrário
        """
        try:
            # Cria diretório se não existe
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            self.log(f"❌ Erro ao escrever JSON {file_path}: {e}")
            return False

    def delete_json(self, file_path: str, safe: bool = True) -> bool:
        """
        Deleta arquivo JSON.

        Args:
            file_path: Caminho do arquivo JSON
            safe: Se True, não falha se arquivo não existe

        Returns:
            True se deletou ou não existia (safe=True), False caso contrário
        """
        if not os.path.isfile(file_path):
            if safe:
                return True
            else:
                self.log(f"❌ Arquivo não encontrado: {file_path}")
                return False

        try:
            os.remove(file_path)
            self.log(f"🗑️ JSON deletado: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao deletar JSON {file_path}: {e}")
            return False

    # ===================== OPERAÇÕES COM VÍDEOS =====================

    def move_video(self, source: str, destination_dir: str, overwrite: bool = False) -> Optional[str]:
        """
        Move vídeo de um local para outro.

        Args:
            source: Caminho do vídeo original
            destination_dir: Diretório de destino
            overwrite: Se True, sobrescreve arquivo existente

        Returns:
            Caminho do arquivo movido ou None se falhar
        """
        if not os.path.isfile(source):
            self.log(f"❌ Vídeo não encontrado: {source}")
            return None

        try:
            # Cria diretório de destino se não existe
            os.makedirs(destination_dir, exist_ok=True)

            # Define caminho de destino
            filename = os.path.basename(source)
            destination = os.path.join(destination_dir, filename)

            # Verifica se já existe
            if os.path.exists(destination) and not overwrite:
                self.log(f"⚠️ Arquivo já existe no destino: {destination}")
                return None

            # Move arquivo
            shutil.move(source, destination)
            self.log(f"📦 Vídeo movido: {filename} -> {destination_dir}")
            return destination

        except Exception as e:
            self.log(f"❌ Erro ao mover vídeo: {e}")
            return None

    def copy_video(self, source: str, destination_dir: str, overwrite: bool = False) -> Optional[str]:
        """
        Copia vídeo de um local para outro.

        Args:
            source: Caminho do vídeo original
            destination_dir: Diretório de destino
            overwrite: Se True, sobrescreve arquivo existente

        Returns:
            Caminho do arquivo copiado ou None se falhar
        """
        if not os.path.isfile(source):
            self.log(f"❌ Vídeo não encontrado: {source}")
            return None

        try:
            # Cria diretório de destino se não existe
            os.makedirs(destination_dir, exist_ok=True)

            # Define caminho de destino
            filename = os.path.basename(source)
            destination = os.path.join(destination_dir, filename)

            # Verifica se já existe
            if os.path.exists(destination) and not overwrite:
                self.log(f"⚠️ Arquivo já existe no destino: {destination}")
                return None

            # Copia arquivo
            shutil.copy2(source, destination)
            self.log(f"📋 Vídeo copiado: {filename} -> {destination_dir}")
            return destination

        except Exception as e:
            self.log(f"❌ Erro ao copiar vídeo: {e}")
            return None

    def delete_video(self, file_path: str, safe: bool = True) -> bool:
        """
        Deleta arquivo de vídeo.

        Args:
            file_path: Caminho do vídeo
            safe: Se True, não falha se arquivo não existe

        Returns:
            True se deletou ou não existia (safe=True), False caso contrário
        """
        if not os.path.isfile(file_path):
            if safe:
                return True
            else:
                self.log(f"❌ Vídeo não encontrado: {file_path}")
                return False

        try:
            os.remove(file_path)
            self.log(f"🗑️ Vídeo deletado: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao deletar vídeo {file_path}: {e}")
            return False

    # ===================== LOCKS DE POSTAGEM =====================

    def create_lock(self, file_path: str) -> bool:
        """
        Cria arquivo .lock para indicar que vídeo está sendo processado.

        Args:
            file_path: Caminho do vídeo (lock será criado com mesmo nome + .posting.lock)

        Returns:
            True se criou lock, False caso contrário
        """
        lock_path = f"{file_path}.posting.lock"

        try:
            # Cria arquivo lock vazio
            Path(lock_path).touch()
            self.log(f"🔒 Lock criado: {os.path.basename(lock_path)}")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao criar lock: {e}")
            return False

    def remove_lock(self, file_path: str) -> bool:
        """
        Remove arquivo .lock de postagem.

        Args:
            file_path: Caminho do vídeo (lock será removido com mesmo nome + .posting.lock)

        Returns:
            True se removeu ou não existia, False caso contrário
        """
        lock_path = f"{file_path}.posting.lock"

        if not os.path.exists(lock_path):
            return True

        try:
            os.remove(lock_path)
            self.log(f"🔓 Lock removido: {os.path.basename(lock_path)}")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao remover lock: {e}")
            return False

    def check_lock(self, file_path: str, max_age_seconds: Optional[int] = None) -> bool:
        """
        Verifica se existe lock para um vídeo.

        Args:
            file_path: Caminho do vídeo
            max_age_seconds: Se especificado, considera lock inválido se for mais antigo

        Returns:
            True se lock existe e é válido, False caso contrário
        """
        lock_path = f"{file_path}.posting.lock"

        if not os.path.exists(lock_path):
            return False

        # Se não precisa verificar idade, retorna True
        if max_age_seconds is None:
            return True

        try:
            # Verifica idade do lock
            lock_age = os.path.getmtime(lock_path)
            current_time = datetime.now().timestamp()
            age_seconds = current_time - lock_age

            if age_seconds > max_age_seconds:
                self.log(f"⚠️ Lock expirado ({age_seconds:.0f}s): {os.path.basename(lock_path)}")
                return False

            return True

        except Exception as e:
            self.log(f"❌ Erro ao verificar lock: {e}")
            return False

    # ===================== METADADOS DE VÍDEO =====================

    def get_video_metadata(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Busca arquivo JSON de metadados associado ao vídeo.

        Args:
            video_path: Caminho do vídeo

        Returns:
            Dicionário com metadados ou None se não encontrado
        """
        # Procura JSON com mesmo nome
        json_path = os.path.splitext(video_path)[0] + '.json'

        if not os.path.isfile(json_path):
            # Tenta no mesmo diretório
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]

            # Procura qualquer JSON com nome similar
            for file in os.listdir(video_dir):
                if file.endswith('.json') and video_name in file:
                    json_path = os.path.join(video_dir, file)
                    break
            else:
                self.log(f"⚠️ Metadados não encontrados para: {os.path.basename(video_path)}")
                return None

        return self.read_json(json_path)

    # ===================== LIMPEZA E ORGANIZAÇÃO =====================

    def cleanup_failed_post(self, video_path: str) -> bool:
        """
        Limpa arquivos de uma postagem que falhou.
        Remove lock e mantém vídeo para nova tentativa.

        Args:
            video_path: Caminho do vídeo

        Returns:
            True se limpeza foi bem-sucedida, False caso contrário
        """
        self.log(f"🧹 Limpando postagem falhada: {os.path.basename(video_path)}")

        # Remove lock
        lock_removed = self.remove_lock(video_path)

        return lock_removed

    def finalize_successful_post(
        self,
        video_path: str,
        posted_dir: str,
        keep_original: bool = False
    ) -> bool:
        """
        Finaliza postagem bem-sucedida movendo arquivos para pasta 'posted'.

        Args:
            video_path: Caminho do vídeo original
            posted_dir: Diretório de destino (posted)
            keep_original: Se True, copia ao invés de mover

        Returns:
            True se finalização foi bem-sucedida, False caso contrário
        """
        self.log(f"✅ Finalizando postagem: {os.path.basename(video_path)}")

        # Remove lock
        self.remove_lock(video_path)

        # Move ou copia vídeo
        if keep_original:
            video_result = self.copy_video(video_path, posted_dir, overwrite=True)
        else:
            video_result = self.move_video(video_path, posted_dir, overwrite=True)

        if not video_result:
            self.log("⚠️ Falha ao mover/copiar vídeo")
            return False

        # Procura e move JSON associado
        json_path = os.path.splitext(video_path)[0] + '.json'
        if os.path.isfile(json_path):
            if keep_original:
                json_result = self.copy_video(json_path, posted_dir, overwrite=True)
            else:
                json_result = self.move_video(json_path, posted_dir, overwrite=True)

            if not json_result:
                self.log("⚠️ Falha ao mover/copiar JSON")

        self.log("✅ Postagem finalizada com sucesso")
        return True

    # ===================== UTILITÁRIOS =====================

    def ensure_directory(self, directory: str) -> bool:
        """
        Garante que um diretório existe, criando se necessário.

        Args:
            directory: Caminho do diretório

        Returns:
            True se diretório existe ou foi criado, False caso contrário
        """
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            self.log(f"❌ Erro ao criar diretório {directory}: {e}")
            return False

    def list_videos_in_directory(self, directory: str, extensions: tuple = ('.mp4', '.mov', '.avi')) -> list:
        """
        Lista vídeos em um diretório.

        Args:
            directory: Caminho do diretório
            extensions: Extensões de vídeo aceitas

        Returns:
            Lista de caminhos de vídeos
        """
        if not os.path.isdir(directory):
            self.log(f"⚠️ Diretório não encontrado: {directory}")
            return []

        videos = []
        try:
            for file in os.listdir(directory):
                if file.lower().endswith(extensions):
                    full_path = os.path.join(directory, file)
                    videos.append(full_path)

            videos.sort()  # Ordena alfabeticamente
            return videos

        except Exception as e:
            self.log(f"❌ Erro ao listar vídeos: {e}")
            return []

    def get_file_size_mb(self, file_path: str) -> Optional[float]:
        """
        Retorna tamanho do arquivo em MB.

        Args:
            file_path: Caminho do arquivo

        Returns:
            Tamanho em MB ou None se arquivo não existe
        """
        if not os.path.isfile(file_path):
            return None

        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return round(size_mb, 2)
        except Exception as e:
            self.log(f"❌ Erro ao obter tamanho: {e}")
            return None
