# src/scheduler.py - Planner-aware, 1 por slot, sem import de http_health

import os
import signal
import threading
import time
import shutil
import json
import socket
import psutil
from dataclasses import dataclass
from typing import Optional, List, Tuple, Set
from pathlib import Path
import datetime as dt
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:  # pragma: no cover - fallback para Python <3.9
    from backports.zoneinfo import ZoneInfo  # type: ignore

try:
    from src import log_service
except ImportError:
    log_service = None

import schedule as schedule_module  # pyright: ignore[reportMissingImports]
from selenium.common.exceptions import WebDriverException  # pyright: ignore[reportMissingImports]

try:
    from urllib3.exceptions import MaxRetryError, NewConnectionError, ConnectTimeoutError
except Exception:
    MaxRetryError = NewConnectionError = ConnectTimeoutError = None

from .paths import account_dirs, ensure_base
from .cookies import load_cookies_for_account
from .config import SCHEDULES, TEST_MODE, DELETE_AFTER_POST

TRANSIENT_DRIVER_ERRORS = [WebDriverException, ConnectionError, socket.error]
for _extra in (MaxRetryError, NewConnectionError, ConnectTimeoutError):
    if isinstance(_extra, type):
        TRANSIENT_DRIVER_ERRORS.append(_extra)
TRANSIENT_DRIVER_ERRORS = tuple(TRANSIENT_DRIVER_ERRORS)

# ====== Config de fuso e estado ======
APP_TZ = ZoneInfo(os.getenv("TZ", "America/Sao_Paulo"))
STATE_DIR = Path(os.getenv("BASE_STATE_DIR", "./state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
SCHEDULES_JSON = STATE_DIR / "schedules.json"
LOGS_JSON = STATE_DIR / "logs.json"

def _now_app() -> datetime:
    return datetime.now(APP_TZ)

def _nowstamp() -> str:
    return _now_app().strftime("%Y%m%d_%H%M%S")

# ====== Utilidades locais (sem depender de http_health) ======
def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def add_log(message: str, account_name: str = None):
    """
    Wrapper para log_service.add_log() no scheduler
    
    Args:
        message: Mensagem do log
        account_name: Nome da conta (extraído do contexto do scheduler)
    """
    if log_service:
        log_service.add_log(
            message=message,
            level="info",
            account_name=account_name,
            module="scheduler"
        )
    else:
        # Fallback: print se log_service não disponível
        print(f"[scheduler] {message}")


def _read_schedules() -> List[str]:
    try:
        if SCHEDULES_JSON.exists():
            data = _read_json(SCHEDULES_JSON)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "schedules" in data:
                return [str(x) for x in data["schedules"]]
    except Exception:
        pass
    return SCHEDULES or ["08:00","10:00","12:00","14:00","16:00","18:00","20:00","22:00"]

def safe_move(src_path: str, dst_dir: str) -> str:
    os.makedirs(dst_dir, exist_ok=True)
    base = os.path.basename(src_path)
    name, ext = os.path.splitext(base)
    dst = os.path.join(dst_dir, base)
    if os.path.exists(dst):
        dst = os.path.join(dst_dir, f"{name}_{_nowstamp()}{ext}")
    shutil.move(src_path, dst)
    return dst

def move_sidecars(video_path: str, posted_dir: str, log):
    """
    Move arquivos auxiliares (sidecars) junto com o vídeo.

    Inclui:
    - .json (metadados unificados - PRIORITÁRIO)
    - .meta.json (legado - retrocompatibilidade)
    - .txt (outros metadados)
    """
    root, _ = os.path.splitext(video_path)
    for candidate in (root + ".json", root + ".meta.json", root + ".txt"):
        if os.path.exists(candidate):
            try:
                dst = safe_move(candidate, posted_dir)
                log(f"📝 Sidecar movido: {dst}")
            except Exception as e:
                log(f"⚠️ Falha ao mover sidecar {os.path.basename(candidate)}: {e}")

def _parse_iso_maybe(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dti = datetime.fromisoformat(s)
        if dti.tzinfo is None:
            dti = dti.replace(tzinfo=APP_TZ)
        else:
            dti = dti.astimezone(APP_TZ)
        return dti
    except Exception:
        return None

def _occupied_slots_for_date(videos_dir: str, date_ymd: str) -> Set[str]:
    """
    Conjunto de HH:MM ocupados em VIDEOS_DIR para a data Y-m-d.
    Considera arquivo .json com 'scheduled_at' (prioritário) ou .meta.json com 'schedule_time'.
    """
    taken: Set[str] = set()
    acc_dir = Path(videos_dir)
    for mp4 in acc_dir.glob("*.mp4"):
        hhmm = None
        p_json = mp4.with_suffix(".json")
        p_meta = mp4.with_suffix(".meta.json")
        if p_json.exists():
            try:
                m = _read_json(p_json) or {}
                sat = m.get("scheduled_at")
                if sat:
                    dti = _parse_iso_maybe(sat) or _now_app()
                    if dti.strftime("%Y-%m-%d") == date_ymd:
                        hhmm = dti.strftime("%H:%M")
            except Exception:
                pass
        if not hhmm and p_meta.exists():
            try:
                m = _read_json(p_meta) or {}
                s = (m.get("schedule_time") or "").strip()
                if len(s) == 5:
                    hhmm = s
            except Exception:
                pass
        if hhmm:
            taken.add(hhmm)
    return taken

def _find_next_free_slot(videos_dir: str, schedules: List[str]) -> Tuple[str, str, str]:
    """
    Retorna (date_ymd, hhmm, scheduled_at_iso_utc) no horizonte de 30 dias.
    Garante evitar colisão em VIDEOS_DIR.
    """
    now_local = _now_app()
    ordered = sorted(set(schedules))
    for d in range(0, 31):
        day = (now_local + dt.timedelta(days=d))
        ymd = day.strftime("%Y-%m-%d")
        taken = _occupied_slots_for_date(videos_dir, ymd)
        for hhmm in ordered:
            if d == 0 and hhmm <= now_local.strftime("%H:%M"):
                continue
            if hhmm not in taken:
                hh, mm = map(int, hhmm.split(":"))
                local_dt = dt.datetime.fromisoformat(f"{ymd}T{hh:02d}:{mm:02d}:00").replace(tzinfo=APP_TZ)
                iso_utc = local_dt.astimezone(timezone.utc).isoformat()
                return ymd, hhmm, iso_utc
    # fallback
    ymd = (now_local + dt.timedelta(days=1)).strftime("%Y-%m-%d")
    hhmm = ordered[0] if ordered else "08:00"
    hh, mm = map(int, hhmm.split(":"))
    local_dt = dt.datetime.fromisoformat(f"{ymd}T{hh:02d}:{mm:02d}:00").replace(tzinfo=APP_TZ)
    return ymd, hhmm, local_dt.astimezone(timezone.utc).isoformat()

def _update_sidecars_for(video_path: str, new_hhmm: str, new_iso_utc: str, log):
    """
    Atualiza horário de agendamento nos arquivos de metadados.

    Atualiza AMBOS (transição):
    - .json unificado: scheduled_at (ISO) + schedule_time (HH:MM) - PRIORITÁRIO
    - .meta.json legado: schedule_time (retrocompatibilidade)
    """
    p = Path(video_path)
    p_json = p.with_suffix(".json")
    p_meta = p.with_suffix(".meta.json")

    # Atualiza .json unificado (PRIORITÁRIO)
    try:
        unified = _read_json(p_json) or {}
        unified["scheduled_at"] = new_iso_utc
        unified["schedule_time"] = new_hhmm
        _write_json_atomic(p_json, unified)
    except Exception as e:
        log(f"⚠️ Falha ao atualizar metadados unificados: {e}")

    # Atualiza .meta.json legado (RETROCOMPATIBILIDADE)
    try:
        legacy = _read_json(p_meta) or {}
        legacy["schedule_time"] = new_hhmm
        if "scheduled_at" in legacy:  # Se existir, atualiza também
            legacy["scheduled_at"] = new_iso_utc
        _write_json_atomic(p_meta, legacy)
    except Exception as e:
        log(f"⚠️ Falha ao atualizar meta legado: {e}")

@dataclass
class DueVideo:
    path: str
    meta_path: str
    scheduled_at: datetime  # aware em APP_TZ
    schedule_time: Optional[str] = None

# ====== Scheduler ======
class TikTokScheduler:
    """
    - Usa 'scheduled_at' (ISO) como fonte de verdade.
    - Aceita 'schedule_time' (HH:MM) legado como fallback (mapeado para hoje).
    - Garante 1 postagem por rodízio/slot: excedentes são REAGENDADOS automaticamente.
    """
    def __init__(self, account_name: str, logger=None, visible: bool = False):
        """
        Inicializa o scheduler para uma conta específica

        Args:
            account_name: Nome da conta TikTok (obrigatório)
            logger: Função de log customizada (opcional)
            visible: Se True, mostra o navegador (opcional)
        """
        if not account_name or not account_name.strip():
            raise ValueError("account_name é obrigatório e não pode ser vazio")
        self.account = account_name.strip()
        self.USER_DATA_DIR, self.VIDEO_DIR, self.POSTED_DIR = account_dirs(account_name)
        self.driver = None
        self.scheduler_thread = None
        self.scheduler_active = False
        self.running = True
        self.visible = visible
        self.max_session_attempts = int(os.getenv("TIKTOK_MAX_SESSION_ATTEMPTS", "20"))
        self.session_retry_delay = float(os.getenv("TIKTOK_SESSION_RETRY_DELAY_SECONDS", "5"))
        self._logger = logger or (lambda m: print(f"[{_now_app().strftime('%H:%M:%S')}] {m}"))
        # Instância ISOLADA de scheduler para esta conta (não compartilhada!)
        self.schedule = schedule_module.Scheduler()
        self.kill_chrome_processes()
        self._temp_profile_dir = None
        self.log(f"🟢 Sistema iniciado para conta: {account_name}")

    def log(self, msg: str):
        # _logger já chama log_service.add_log quando vindo do scheduler_daemon
        # Evita duplicação de logs
        self._logger(msg)

    def initial_setup(self):
        ensure_base()
        self.log(f"📂 Pastas configuradas para: {self.account}")

    @staticmethod
    def kill_chrome_processes():
        """Mata processos filhos do Chrome que possam ter ficado órfãos."""
        try:
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                name = child.name().lower()
                if "chrome" in name or "chromedriver" in name:
                    try:
                        child.send_signal(signal.SIGTERM)
                        child.wait(2)
                    except Exception:
                        pass
                    if child.is_running():
                        child.kill()
        except Exception:
            pass

    def close_driver(self):
        if self.driver:
            profile_dir = getattr(self.driver, "_profile_dir", None)
            try:
                self.driver.quit()
            except Exception:
                pass
            try:
                from .driver import release_driver_lock
                release_driver_lock(self.driver)
            except Exception:
                pass
            self.driver = None
            if profile_dir:
                cleaned_path = profile_dir.rstrip(os.sep)
                basename = os.path.basename(cleaned_path)
                parent_basename = os.path.basename(os.path.dirname(cleaned_path))
                is_temp_profile = basename.startswith("chrome-user-data-")
                is_runtime_profile = parent_basename == "runtime"
                if is_runtime_profile:
                    try:
                        shutil.rmtree(cleaned_path, ignore_errors=True)
                    except Exception:
                        pass
                elif is_temp_profile:
                    try:
                        shutil.rmtree(cleaned_path, ignore_errors=True)
                    except Exception:
                        pass
                else:
                    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
                        lock_path = os.path.join(cleaned_path, lock_name)
                        if os.path.exists(lock_path):
                            try:
                                os.remove(lock_path)
                            except Exception:
                                pass
        self.kill_chrome_processes()
        self._temp_profile_dir = None

    def _ensure_logged(self) -> bool:
        if TEST_MODE:
            self.log("🚧 Modo teste: simulação de login OK")
            return True

        from .driver import get_fresh_driver

        attempt_limit = max(1, getattr(self, "max_session_attempts", 20))
        retry_delay = max(0.0, getattr(self, "session_retry_delay", 5.0))
        last_error = None

        for attempt in range(1, attempt_limit + 1):
            ok = False
            if attempt > 1:
                self.log(f"🔁 Tentativa {attempt}/{attempt_limit} para restabelecer sessão do Chrome")
            self.close_driver()
            self.kill_chrome_processes()

            try:
                self.driver = get_fresh_driver(None, profile_base_dir=self.USER_DATA_DIR, account_name=self.account)
                self._temp_profile_dir = getattr(self.driver, "_profile_dir", None)
                self.log(f"🔐 Tentando login com cookies da conta: {self.account} (tentativa {attempt}/{attempt_limit})")
                ok = load_cookies_for_account(self.driver, self.account)
                if ok:
                    if attempt > 1:
                        self.log(f"🟢 Sessão restabelecida após {attempt} tentativas")
                    self.log(f"✅ Login via cookies OK para: {self.account}")
                    return True
                last_error = "cookies inválidos"
                self.log(f"❌ Falha no login com cookies (tentativa {attempt}/{attempt_limit})")
            except TRANSIENT_DRIVER_ERRORS as e:
                last_error = e
                self.log(f"⚠️ Falha na sessão Chrome (tentativa {attempt}/{attempt_limit}): {e}")
            except Exception as e:
                last_error = e
                self.log(f"⚠️ Erro inesperado ao logar (tentativa {attempt}/{attempt_limit}): {e}")

            if ok:
                return True

            if attempt < attempt_limit:
                self.close_driver()
                self.kill_chrome_processes()
                self.log(f"🔁 Recriando driver em {retry_delay:.1f}s…")
                time.sleep(retry_delay)

        if last_error:
            self.log(f"❌ Não foi possível restabelecer sessão após {attempt_limit} tentativas. Último erro: {last_error}")
        else:
            self.log(f"❌ Não foi possível restabelecer sessão após {attempt_limit} tentativas.")
        self.close_driver()
        return False

    def _assign_dynamic_slots(self) -> List[DueVideo]:
        """
        Atribui slots DINAMICAMENTE aos vídeos pending baseado nos horários configurados.

        NOVA LÓGICA COM PERSISTÊNCIA:
        1. Coleta vídeos pending (status != "posted")
        2. Para cada vídeo:
           - Se já tem slot válido (futuro) no metadado → MANTÉM
           - Se não tem ou slot expirou → CALCULA novo slot e PERSISTE
        3. Retorna lista de DueVideo com slots (lidos ou calculados)

        BENEFÍCIO: Slots persistem entre restarts do scheduler!
        """
        # Coleta vídeos pending COM seus slots atuais
        pending_videos = []
        acc_dir = Path(self.VIDEO_DIR)
        if not acc_dir.exists():
            return []

        now_local = _now_app()

        for f in sorted(acc_dir.glob("*.mp4")):
            unified_path = f.with_suffix(".json")
            meta_path_legacy = f.with_suffix(".meta.json")

            meta = None
            meta_path_to_use = None

            # Tenta .json unificado primeiro
            if unified_path.exists():
                meta = _read_json(unified_path)
                meta_path_to_use = unified_path
                if meta:
                    # Ignora se já postado
                    if meta.get("status") == "posted" or meta.get("posted_at"):
                        continue

            # Fallback: .meta.json legado
            if not meta and meta_path_legacy.exists():
                meta = _read_json(meta_path_legacy)
                meta_path_to_use = meta_path_legacy
                if meta and meta.get("posted_at"):
                    continue

            # Se não encontrou metadados, pula
            if not meta or not meta_path_to_use:
                continue

            # Pega timestamp de upload (prioriza uploaded_at, fallback creation time)
            uploaded_at_str = meta.get("uploaded_at")
            if uploaded_at_str:
                try:
                    uploaded_at = _parse_iso_maybe(uploaded_at_str) or now_local
                except:
                    uploaded_at = now_local
            else:
                # Fallback: usa modificação do arquivo
                uploaded_at = datetime.fromtimestamp(f.stat().st_mtime, tz=APP_TZ)

            # Verifica se já tem slot válido (futuro OU ainda hoje)
            existing_slot = None
            scheduled_at_str = meta.get("scheduled_at")
            if scheduled_at_str:
                try:
                    existing_slot = _parse_iso_maybe(scheduled_at_str)
                    # Mantém slots do DIA ATUAL (mesmo se já passaram)
                    # Invalida apenas slots de DIAS ANTERIORES
                    if existing_slot:
                        slot_date = existing_slot.date()
                        today_date = now_local.date()
                        if slot_date < today_date:
                            # Slot de ontem ou antes → invalida
                            existing_slot = None
                        # Slots de hoje ou futuro → mantém
                except:
                    existing_slot = None

            pending_videos.append({
                "path": str(f),
                "meta_path": str(meta_path_to_use),
                "uploaded_at": uploaded_at,
                "existing_slot": existing_slot,
                "meta": meta,  # Guarda meta para atualização posterior
            })

        # Ordena por ordem de chegada (FIFO)
        pending_videos.sort(key=lambda v: v["uploaded_at"])

        # Separa vídeos: com slot vs sem slot
        videos_with_slot = [v for v in pending_videos if v["existing_slot"]]
        videos_without_slot = [v for v in pending_videos if not v["existing_slot"]]

        # Calcula slots disponíveis (hoje → +30 dias) EXCLUINDO slots já usados
        schedules = _read_schedules()
        ordered_slots = sorted(set(schedules))

        used_slots = {v["existing_slot"] for v in videos_with_slot}

        available_slots = []
        for d in range(0, 31):  # Hoje + 30 dias
            day = (now_local + dt.timedelta(days=d))
            ymd = day.strftime("%Y-%m-%d")

            for hhmm in ordered_slots:
                hh, mm = map(int, hhmm.split(":"))
                local_dt = dt.datetime.fromisoformat(f"{ymd}T{hh:02d}:{mm:02d}:00").replace(tzinfo=APP_TZ)

                # Pula slots que já passaram
                if local_dt < now_local:
                    continue

                # Pula slots já usados por outros vídeos
                if local_dt in used_slots:
                    continue

                available_slots.append(local_dt)

        # Atribui novos slots aos vídeos SEM slot e PERSISTE
        for i, video in enumerate(videos_without_slot):
            if i >= len(available_slots):
                self.log(f"⚠️ Vídeo {Path(video['path']).name} sem slot disponível (>30 dias)")
                continue

            new_slot = available_slots[i]

            # PERSISTE o slot no arquivo JSON
            video["meta"]["scheduled_at"] = new_slot.astimezone(timezone.utc).isoformat()
            video["meta"]["schedule_time"] = new_slot.strftime("%H:%M")

            _write_json_atomic(Path(video["meta_path"]), video["meta"])

            video["existing_slot"] = new_slot
            self.log(f"🔄 Slot atribuído: {Path(video['path']).name} → {new_slot.strftime('%Y-%m-%d %H:%M')}")

        # Monta lista final de DueVideo (com slots persistidos)
        out: List[DueVideo] = []
        for video in pending_videos:
            if video["existing_slot"]:
                out.append(DueVideo(
                    path=video["path"],
                    meta_path=video["meta_path"],
                    scheduled_at=video["existing_slot"],
                    schedule_time=video["existing_slot"].strftime("%H:%M")
                ))

        # DEBUG: Log dos candidatos encontrados
        if out:
            self.log(f"🔍 DEBUG: {len(out)} candidatos encontrados:")
            for i, dv in enumerate(out[:5]):  # Mostra apenas os 5 primeiros
                self.log(f"   [{i+1}] {Path(dv.path).name[:40]}... → {dv.scheduled_at.strftime('%Y-%m-%d %H:%M:%S')}")

        return out

    def _collect_candidates(self) -> List[DueVideo]:
        """
        Coleta vídeos com slots DINÂMICOS (não usa horários fixos dos metadados).

        Substitui lógica antiga que lia scheduled_at dos metadados por sistema
        de slots dinâmicos que se adapta às mudanças nos presets de horários.
        """
        return self._assign_dynamic_slots()

    def _due_now(self, candidates: List[DueVideo]) -> List[DueVideo]:
        now = _now_app()
        due = [dv for dv in candidates if dv.scheduled_at <= now]

        # DEBUG: Mostra comparações
        if candidates and not due:
            self.log(f"🔍 DEBUG _due_now: Agora é {now.strftime('%Y-%m-%d %H:%M:%S')}")
            for i, dv in enumerate(candidates[:3]):
                is_due = dv.scheduled_at <= now
                diff_seconds = (now - dv.scheduled_at).total_seconds()
                self.log(f"   [{i+1}] {Path(dv.path).name[:30]}... {dv.scheduled_at.strftime('%H:%M:%S')} <= {now.strftime('%H:%M:%S')} ? {is_due} (diff: {diff_seconds:.0f}s)")

        return due

    # -------- postagem --------
    def _post_one(self, path: str) -> bool:
        """
        Posta um vídeo no TikTok.

        PRIORIDADE para caption/descrição:
        1. Lê 'caption' do .json unificado (N8N/IA ou manual)
        2. Fallback: .meta.json legado
        3. Fallback final: build_caption_for_video() automático
        """
        from .uploader import TikTokUploader
        from .caption import build_caption_for_video

        # Tenta ler caption do arquivo unificado
        p = Path(path)
        unified_path = p.with_suffix(".json")
        meta_path_legacy = p.with_suffix(".meta.json")

        desc = None

        # PRIORIDADE: .json unificado
        if unified_path.exists():
            meta = _read_json(unified_path)
            if meta:
                # Campo 'caption' tem prioridade (vindo de N8N/IA)
                desc = (meta.get("caption") or "").strip()
                if not desc:
                    # Fallback: 'description' (compatibilidade)
                    desc = (meta.get("description") or "").strip()

        # FALLBACK: .meta.json legado
        if not desc and meta_path_legacy.exists():
            meta = _read_json(meta_path_legacy)
            if meta:
                desc = (meta.get("caption") or "").strip()

        # FALLBACK FINAL: Gera caption automaticamente
        if not desc:
            self.log(f"⚠️ Caption não encontrada em metadados, gerando automaticamente")
            desc = build_caption_for_video(path, override_keywords=None, cta=None, extra_tags=None, max_hashtags=8)

        up = TikTokUploader(
            self.driver,
            self.log,
            debug_dir=self.USER_DATA_DIR,
            account_name=self.account,
            reuse_existing_session=True,
        )
        return up.post_video(path, desc)

    def _finalize_success(self, vpath: str):
        """
        Marca vídeo como postado após sucesso.

        Atualiza AMBOS arquivos (transição):
        - .json unificado: status="posted" + posted_at
        - .meta.json legado: posted_at (retrocompatibilidade)
        """
        p = Path(vpath)
        unified_path = p.with_suffix(".json")
        meta_path_legacy = p.with_suffix(".meta.json")
        posted_at_iso = _now_app().astimezone(timezone.utc).isoformat()

        # Atualiza .json unificado (PRIORITÁRIO)
        if unified_path.exists():
            meta = _read_json(unified_path) or {}
            meta["status"] = "posted"
            meta["posted_at"] = posted_at_iso
            _write_json_atomic(unified_path, meta)
            self.log(f"✅ Metadados atualizados: {unified_path.name}")

        # Atualiza .meta.json legado (RETROCOMPATIBILIDADE)
        if meta_path_legacy.exists():
            meta = _read_json(meta_path_legacy) or {}
            meta["posted_at"] = posted_at_iso
            _write_json_atomic(meta_path_legacy, meta)

        move_sidecars(vpath, self.POSTED_DIR, self.log)

        if DELETE_AFTER_POST:
            try:
                os.remove(vpath)
                self.log(f"🗑️ Vídeo excluído: {vpath}")
            except Exception as e:
                self.log(f"⚠️ Erro ao excluir vídeo: {e}")
        else:
            try:
                dst = safe_move(vpath, self.POSTED_DIR)
                self.log(f"♻️ Vídeo movido para: {dst}")
            except Exception as e:
                self.log(f"⚠️ Erro ao mover vídeo: {e}")

    def _reschedule_leftovers(self, leftovers: List[DueVideo]):
        if not leftovers:
            return
        schedules = _read_schedules()
        for dv in leftovers:
            ymd, hhmm, iso_utc = _find_next_free_slot(self.VIDEO_DIR, schedules)
            _update_sidecars_for(dv.path, hhmm, iso_utc, self.log)
            self.log(f"↪️ Reagendado: {Path(dv.path).name} → {ymd} {hhmm}")

    # -------- tick principal --------
    def scheduled_posting(self):
        if not self.scheduler_active:
            self.log("ℹ️ Agendador inativo; pulando.")
            return

        now_str = _now_app().strftime("%H:%M")
        self.log("\n" + "="*50)
        self.log(f"⏰ INICIANDO POSTAGEM AGENDADA ({now_str})")
        self.log("="*50)

        candidates = self._collect_candidates()
        due = self._due_now(candidates)
        self.log(f"📊 Candidatos: {len(candidates)} • Due agora: {len(due)}")
        if not due:
            self.log("📭 Nenhum vídeo due neste momento")
            return

        # garante 1 por rodada; reagenda excedentes
        due.sort(key=lambda dv: dv.scheduled_at)
        to_post = [due[0]]
        leftovers = due[1:]
        self._reschedule_leftovers(leftovers)

        if not self._ensure_logged():
            self.log("❌ Sem sessão válida (cookies inválidos ou ausentes)")
            self.log(f"💡 SOLUÇÃO: Acesse o painel e atualize os cookies da conta '{self.account}'")
            self.log(f"   1. Vá em 'Contas TikTok' → Editar conta '{self.account}'")
            self.log(f"   2. Cole os cookies atualizados do navegador")
            self.log(f"   3. Os vídeos permanecerão na fila até que os cookies sejam atualizados")
            return

        for i, dv in enumerate(to_post, 1):
            self.log(f"\n📤 Postando vídeo {i} de {len(to_post)} :: {Path(dv.path).name}")
            try:
                ok = self._post_one(dv.path)
            except TRANSIENT_DRIVER_ERRORS as e:
                self.log(f"⚠️ Erro de sessão do Chrome ({type(e).__name__}): {e}; tentando relogar…")
                self.close_driver()
                ok = self._ensure_logged() and self._post_one(dv.path)

            if ok:
                self._finalize_success(dv.path)
            else:
                self.log("❌ Postagem não confirmada; manteremos o arquivo em /videos")

        self.log("✅ Tick concluído\n")

    # -------- agendamento dos ticks --------
    def setup_schedules(self):
        # Usa scheduler ISOLADO desta conta (self.schedule) ao invés do global
        self.schedule.clear()
        schedules = _read_schedules()
        for t in sorted(set(schedules)):
            self.schedule.every().day.at(t).do(self.scheduled_posting)
            self.log(f"⏰ Tick diário registrado às {t}")
        # também roda a cada minuto para catch-up de atrasados
        self.schedule.every(1).minutes.do(self.scheduled_posting)
        self.log("⏱️ Tick de 1 em 1 minuto registrado (catch-up).")

    def run_loop(self):
        self.log("🔁 Loop do agendador iniciado")
        while self.running:
            try:
                while self.scheduler_active and self.running:
                    # Usa scheduler ISOLADO desta conta
                    self.schedule.run_pending()
                    time.sleep(1)
            except Exception as e:
                self.log(f"⚠️ Erro no loop do agendador: {e}")
                self.close_driver()
                self.log("🔄 Reiniciando loop em 10 segundos…")
                time.sleep(10)
        self.log("🛑 Loop do agendador encerrado definitivamente.")

    def start(self):
        self.log("⏰ Iniciando agendador…")
        ensure_base()
        self.setup_schedules()
        self.scheduler_active = True
        self.scheduler_thread = threading.Thread(target=self.run_loop, daemon=False)
        self.scheduler_thread.start()
        self.log("✅ Agendador iniciado!")

    def stop(self):
        self.scheduler_active = False
        self.close_driver()
        self.log("🛑 Agendador parado")
