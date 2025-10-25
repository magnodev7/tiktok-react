"""
Sistema de Analytics para IA e Workflows N8N

Processa metadados de vídeos para gerar estatísticas sobre:
- Performance por modelo de IA (GPT-4, Claude, etc.)
- Performance por workflow N8N
- Taxa de sucesso, falhas, custos estimados
- Alertas automáticos para problemas
"""

import json
from pathlib import Path

from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple



@dataclass
class AIModelStats:
    """Estatísticas de um modelo de IA"""
    model_name: str
    total_videos: int = 0
    posted: int = 0
    failed: int = 0
    pending: int = 0
    success_rate: float = 0.0
    estimated_cost: float = 0.0
    avg_retry_count: float = 0.0
    common_errors: List[str] = None

    def __post_init__(self):
        if self.common_errors is None:
            self.common_errors = []


@dataclass
class WorkflowStats:
    """Estatísticas de um workflow N8N"""
    workflow_id: str
    total_videos: int = 0
    posted: int = 0
    failed: int = 0
    pending: int = 0
    success_rate: float = 0.0
    ai_model_used: Optional[str] = None
    last_video_at: Optional[str] = None
    common_errors: List[str] = None

    def __post_init__(self):
        if self.common_errors is None:
            self.common_errors = []


@dataclass
class SourceStats:
    """Estatísticas por origem (api, web, n8n, manual)"""
    source: str
    total_videos: int = 0
    posted: int = 0
    failed: int = 0
    success_rate: float = 0.0


class VideoAnalytics:
    """
    Classe principal para análise de vídeos

    Processa arquivos .json de metadados para gerar estatísticas
    """

    # Custos estimados por modelo (USD por geração)
    AI_COSTS = {
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.02,
        "gpt-3.5-turbo": 0.002,
        "claude-3-opus": 0.025,
        "claude-3-sonnet": 0.015,
        "claude-3-haiku": 0.005,
        "claude-3.5-sonnet": 0.018,
    }

    def __init__(self, base_video_dir: str = "./videos"):
        """
        Inicializa analytics

        Args:
            base_video_dir: Diretório base com subpastas por conta
        """
        self.base_video_dir = Path(base_video_dir)

    def _read_json(self, path: Path) -> Optional[Dict]:
        """Lê arquivo JSON com tratamento de erro"""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return None

    def collect_all_metadata(self, account: Optional[str] = None,
                            days_back: Optional[int] = None) -> List[Dict]:
        """
        Coleta todos metadados de vídeos

        Args:
            account: Filtrar por conta específica (None = todas)
            days_back: Filtrar últimos N dias (None = todos)

        Returns:
            Lista de metadados de vídeos
        """
        all_metadata = []
        cutoff_date = None

        if days_back:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Determina quais diretórios escanear
        if account:
            account_dirs = [self.base_video_dir / account]
        else:
            # Escaneia todas subpastas (contas)
            account_dirs = [d for d in self.base_video_dir.iterdir() if d.is_dir()]

        for acc_dir in account_dirs:
            if not acc_dir.exists():
                continue

            # Busca todos arquivos .json (metadados)
            # Permite processar metadados mesmo sem o .mp4 (caso já tenha sido deletado/movido)
            processed_files = set()

            # Primeiro: processa arquivos .mp4 com seus metadados
            for mp4_file in acc_dir.glob("*.mp4"):
                json_file = mp4_file.with_suffix(".json")
                meta_file = mp4_file.with_suffix(".meta.json")

                metadata = None
                if json_file.exists():
                    metadata = self._read_json(json_file)
                    processed_files.add(json_file.name)
                elif meta_file.exists():
                    metadata = self._read_json(meta_file)
                    processed_files.add(meta_file.name)

                if metadata:
                    # Filtro por data
                    if cutoff_date:
                        uploaded_at = self._parse_datetime(metadata.get("uploaded_at"))
                        if uploaded_at and uploaded_at < cutoff_date:
                            continue

                    # Adiciona informação do arquivo
                    metadata["_file_path"] = str(mp4_file)
                    metadata["_account_dir"] = acc_dir.name
                    all_metadata.append(metadata)

            # Segundo: processa arquivos .json órfãos (sem .mp4)
            for json_file in acc_dir.glob("*.json"):
                # Pula .meta.json e arquivos já processados
                if json_file.name.endswith(".meta.json") or json_file.name in processed_files:
                    continue

                metadata = self._read_json(json_file)
                if not metadata:
                    continue

                # Filtro por data
                if cutoff_date:
                    uploaded_at = self._parse_datetime(metadata.get("uploaded_at"))
                    if uploaded_at and uploaded_at < cutoff_date:
                        continue

                # Adiciona informação do arquivo (sem .mp4)
                metadata["_file_path"] = str(json_file.with_suffix(".mp4"))  # Path hipotético
                metadata["_account_dir"] = acc_dir.name
                all_metadata.append(metadata)

        return all_metadata

    def _collect_queue_metadata(self, account: Optional[str] = None) -> List[Dict]:
        """
        Coleta metadados dos vídeos ainda na fila (diretório videos/).
        """
        queue_dir = self.base_video_dir.parent / "videos"
        if not queue_dir.exists():
            return []

        if account:
            dirs = [queue_dir / account]
        else:
            dirs = [d for d in queue_dir.iterdir() if d.is_dir()]

        queue_metadata: List[Dict] = []

        for acc_dir in dirs:
            if not acc_dir.exists():
                continue
            for mp4_file in acc_dir.glob("*.mp4"):
                json_file = mp4_file.with_suffix(".json")
                metadata = self._read_json(json_file) if json_file.exists() else {}
                metadata = metadata or {}
                metadata.setdefault("status", "pending")
                metadata["_file_path"] = str(mp4_file)
                metadata["_account_dir"] = acc_dir.name
                queue_metadata.append(metadata)

        return queue_metadata

    def analyze_ai_performance(self, account: Optional[str] = None,
                              days_back: Optional[int] = 30) -> Dict[str, AIModelStats]:
        """
        Analisa performance por modelo de IA

        Args:
            account: Filtrar por conta (None = todas)
            days_back: Analisar últimos N dias (default: 30)

        Returns:
            Dict {model_name: AIModelStats}
        """
        videos = self.collect_all_metadata(account, days_back)
        state_dir = self.base_video_dir.parent / "videos"
        pending_in_queue = self.collect_all_metadata(account, days_back=None)
        stats: Dict[str, AIModelStats] = {}

        for video in videos:
            # Ignora vídeos não gerados por IA
            if not video.get("ai_generated"):
                continue

            model = video.get("ai_model") or "unknown"

            if model not in stats:
                stats[model] = AIModelStats(model_name=model)

            s = stats[model]
            s.total_videos += 1

            status = video.get("status", "pending")
            if status == "posted":
                s.posted += 1
            elif status == "failed":
                s.failed += 1
                # Coleta erros comuns
                error = video.get("last_error")
                if error and len(s.common_errors) < 5:
                    s.common_errors.append(error)
            else:
                s.pending += 1

            # Retry count
            retry = video.get("retry_count", 0)
            s.avg_retry_count += retry

        # Calcula taxas e custos
        for model, s in stats.items():
            if s.total_videos > 0:
                s.success_rate = round((s.posted / s.total_videos) * 100, 2)
                s.avg_retry_count = round(s.avg_retry_count / s.total_videos, 2)

            # Custo estimado
            cost_per_video = self.AI_COSTS.get(model.lower(), 0.01)
            s.estimated_cost = round(s.total_videos * cost_per_video, 2)

        return stats

    def analyze_workflow_performance(self, account: Optional[str] = None,
                                    days_back: Optional[int] = 30) -> Dict[str, WorkflowStats]:
        """
        Analisa performance por workflow N8N

        Args:
            account: Filtrar por conta (None = todas)
            days_back: Analisar últimos N dias (default: 30)

        Returns:
            Dict {workflow_id: WorkflowStats}
        """
        videos = self.collect_all_metadata(account, days_back)
        stats: Dict[str, WorkflowStats] = {}

        for video in videos:
            workflow_id = video.get("workflow_id")
            if not workflow_id:
                continue

            if workflow_id not in stats:
                stats[workflow_id] = WorkflowStats(workflow_id=workflow_id)

            s = stats[workflow_id]
            s.total_videos += 1

            # Modelo de IA usado (pega o primeiro encontrado)
            if not s.ai_model_used:
                s.ai_model_used = video.get("ai_model")

            # Última postagem
            uploaded_at = video.get("uploaded_at")
            if uploaded_at and (not s.last_video_at or uploaded_at > s.last_video_at):
                s.last_video_at = uploaded_at

            status = video.get("status", "pending")
            if status == "posted":
                s.posted += 1
            elif status == "failed":
                s.failed += 1
                error = video.get("last_error")
                if error and len(s.common_errors) < 5:
                    s.common_errors.append(error)
            else:
                s.pending += 1

        # Calcula taxas
        for workflow_id, s in stats.items():
            if s.total_videos > 0:
                s.success_rate = round((s.posted / s.total_videos) * 100, 2)

        return stats

    def analyze_by_source(self, account: Optional[str] = None,
                         days_back: Optional[int] = 30) -> Dict[str, SourceStats]:
        """
        Analisa performance por origem (api, web, n8n, manual)

        Args:
            account: Filtrar por conta (None = todas)
            days_back: Analisar últimos N dias (default: 30)

        Returns:
            Dict {source: SourceStats}
        """
        videos = self.collect_all_metadata(account, days_back)
        stats: Dict[str, SourceStats] = {}

        for video in videos:
            source = video.get("source", "unknown")

            if source not in stats:
                stats[source] = SourceStats(source=source)

            s = stats[source]
            s.total_videos += 1

            status = video.get("status", "pending")
            if status == "posted":
                s.posted += 1
            elif status == "failed":
                s.failed += 1

        # Calcula taxas
        for source, s in stats.items():
            if s.total_videos > 0:
                s.success_rate = round((s.posted / s.total_videos) * 100, 2)

        return stats

    def detect_issues(self, account: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Detecta problemas automáticos que requerem atenção

        Args:
            account: Filtrar por conta (None = todas)

        Returns:
            Lista de alertas/problemas detectados
        """
        alerts = []

        # Analisa últimos 7 dias
        ai_stats = self.analyze_ai_performance(account, days_back=7)
        workflow_stats = self.analyze_workflow_performance(account, days_back=7)

        # ALERTA 1: Modelo de IA com alta taxa de falha (>30%)
        for model, stats in ai_stats.items():
            if stats.total_videos >= 5 and stats.success_rate < 70:
                alerts.append({
                    "severity": "high",
                    "type": "ai_model_failure",
                    "message": f"Modelo {model} com {stats.success_rate}% de sucesso (últimos 7 dias)",
                    "details": {
                        "model": model,
                        "success_rate": stats.success_rate,
                        "failed": stats.failed,
                        "total": stats.total_videos,
                        "common_errors": stats.common_errors[:3]
                    },
                    "recommendation": f"Considere trocar temporariamente para outro modelo ou revisar prompts"
                })

        # ALERTA 2: Workflow N8N com alta taxa de falha (>30%)
        for workflow_id, stats in workflow_stats.items():
            if stats.total_videos >= 5 and stats.success_rate < 70:
                alerts.append({
                    "severity": "high",
                    "type": "workflow_failure",
                    "message": f"Workflow {workflow_id} com {stats.success_rate}% de sucesso (últimos 7 dias)",
                    "details": {
                        "workflow_id": workflow_id,
                        "success_rate": stats.success_rate,
                        "failed": stats.failed,
                        "total": stats.total_videos,
                        "ai_model": stats.ai_model_used,
                        "common_errors": stats.common_errors[:3]
                    },
                    "recommendation": "Verifique configuração do workflow N8N ou pause até resolver o problema"
                })

        # ALERTA 3: Workflow sem atividade recente (>3 dias)
        now = datetime.now(timezone.utc)
        for workflow_id, stats in workflow_stats.items():
            if stats.last_video_at:
                last_video = self._parse_datetime(stats.last_video_at)
                if last_video and (now - last_video).days > 3:
                    alerts.append({
                        "severity": "low",
                        "type": "workflow_inactive",
                        "message": f"Workflow {workflow_id} sem atividade há {(now - last_video).days} dias",
                        "details": {
                            "workflow_id": workflow_id,
                            "last_video": stats.last_video_at,
                            "days_inactive": (now - last_video).days
                        },
                        "recommendation": "Verifique se o workflow está ativo no N8N"
                    })

        # ALERTA 4: Vídeos presos em "pending" há muito tempo (>48h)
        videos = self.collect_all_metadata(account, days_back=7)
        stuck_videos = []

        for video in videos:
            if video.get("status") == "pending":
                uploaded_at = self._parse_datetime(video.get("uploaded_at"))
                scheduled_at = self._parse_datetime(video.get("scheduled_at"))

                if uploaded_at and (now - uploaded_at).total_seconds() > 48 * 3600:
                    # Verifica se horário agendado já passou
                    if scheduled_at and scheduled_at < now:
                        stuck_videos.append({
                            "file": video.get("_file_path"),
                            "account": video.get("account"),
                            "uploaded_at": video.get("uploaded_at"),
                            "scheduled_at": video.get("scheduled_at")
                        })

        if stuck_videos:
            alerts.append({
                "severity": "medium",
                "type": "stuck_videos",
                "message": f"{len(stuck_videos)} vídeo(s) com horário passado mas não postados",
                "details": {
                    "count": len(stuck_videos),
                    "videos": stuck_videos[:5]  # Primeiros 5
                },
                "recommendation": "Verifique logs do scheduler ou tente reagendar manualmente"
            })

        return alerts

    def generate_summary_report(self, account: Optional[str] = None,
                               days_back: int = 30) -> Dict[str, Any]:
        """
        Gera relatório resumido completo

        Args:
            account: Filtrar por conta (None = todas)
            days_back: Período de análise (default: 30 dias)

        Returns:
            Dict com relatório completo
        """
        ai_stats = self.analyze_ai_performance(account, days_back)
        workflow_stats = self.analyze_workflow_performance(account, days_back)
        source_stats = self.analyze_by_source(account, days_back)
        alerts = self.detect_issues(account)

        # Totais gerais
        all_videos = self.collect_all_metadata(account, days_back)
        queue_videos = self._collect_queue_metadata(account)

        total_videos_posted = len(all_videos)
        total_videos_queue = len(queue_videos)
        total_videos = total_videos_posted + total_videos_queue

        total_posted = sum(1 for v in all_videos if v.get("status") == "posted")
        total_failed = sum(1 for v in all_videos if v.get("status") == "failed")
        pending_in_posted = sum(1 for v in all_videos if v.get("status") == "pending")
        total_pending = pending_in_posted + total_videos_queue

        denominator = total_posted + total_failed + total_pending
        overall_success = round((total_posted / denominator * 100), 2) if denominator > 0 else 0

        # Custo total estimado de IA
        total_ai_cost = sum(s.estimated_cost for s in ai_stats.values())

        return {
            "period": {
                "days": days_back,
                "account": account or "all_accounts"
            },
            "overview": {
                "total_videos": total_videos,
                "total_videos_posted": total_videos_posted,
                "scheduled_queue": total_videos_queue,
                "posted": total_posted,
                "failed": total_failed,
                "pending": total_pending,
                "pending_posted": pending_in_posted,
                "pending_in_queue": total_videos_queue,
                "success_rate": overall_success
            },
            "ai_models": {
                model: asdict(stats)
                for model, stats in sorted(
                    ai_stats.items(),
                    key=lambda x: x[1].total_videos,
                    reverse=True
                )
            },
            "workflows": {
                wf_id: asdict(stats)
                for wf_id, stats in sorted(
                    workflow_stats.items(),
                    key=lambda x: x[1].total_videos,
                    reverse=True
                )
            },
            "sources": {
                source: asdict(stats)
                for source, stats in sorted(
                    source_stats.items(),
                    key=lambda x: x[1].total_videos,
                    reverse=True
                )
            },
            "costs": {
                "total_ai_cost_usd": round(total_ai_cost, 2),
                "cost_per_video": round(total_ai_cost / total_videos, 4) if total_videos > 0 else 0,
                "by_model": {
                    model: stats.estimated_cost
                    for model, stats in ai_stats.items()
                }
            },
            "alerts": alerts,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
