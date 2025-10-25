# src/planner.py
from __future__ import annotations
import os, json, re
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

TZ_NAME = os.getenv("TZ", "America/Bahia")
TZ = ZoneInfo(TZ_NAME)

# Config padrão
SLOT_INTERVAL_HOURS = int(os.getenv("SLOT_INTERVAL_HOURS", "2"))  # 2
SLOT_START = os.getenv("SLOT_START", "08:00")                      # 08:00
SLOT_END   = os.getenv("SLOT_END", "22:00")                        # 22:00 (inclusivo)
HORIZON_DAYS = int(os.getenv("HORIZON_DAYS", "30"))                # 30
CATCH_UP = os.getenv("CATCH_UP", "false").lower() == "true"        # false por padrão

BASE_VIDEOS_DIR = os.getenv("BASE_VIDEOS_DIR", "./videos")         # no host
BASE_STATE_DIR = os.getenv("BASE_STATE_DIR", "./state")
SCHEDULE_INDEX_FILE = os.path.join(BASE_STATE_DIR, "schedule_index.json")

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

@dataclass(frozen=True)
class Slot:
    dt: datetime  # timezone aware

def _parse_hhmm(s: str) -> time:
    m = re.match(r"^(\d{2}):(\d{2})$", s)
    if not m:
        raise ValueError(f"horário inválido: {s}")
    return time(int(m.group(1)), int(m.group(2)))

def _daterange(start_date: datetime, days: int) -> List[datetime]:
    base = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    return [base + timedelta(days=i) for i in range(days)]

def _day_slots(day: datetime) -> List[Slot]:
    t0 = _parse_hhmm(SLOT_START)
    t1 = _parse_hhmm(SLOT_END)
    if t1 < t0:
        raise ValueError("SLOT_END não pode ser menor que SLOT_START")
    slots: List[Slot] = []
    cur = datetime.combine(day.date(), t0, tzinfo=TZ)
    end = datetime.combine(day.date(), t1, tzinfo=TZ)
    step = timedelta(hours=SLOT_INTERVAL_HOURS)
    while cur <= end:
        slots.append(Slot(dt=cur))
        cur += step
    return slots

def generate_slots_now(horizon_days: int = HORIZON_DAYS) -> List[Slot]:
    now = datetime.now(TZ)
    days = _daterange(now, horizon_days)
    slots: List[Slot] = []
    for i, d in enumerate(days):
        ds = _day_slots(d)
        if i == 0:
            # no dia de hoje, inclui slots futuros e o próximo slot se um novo horário for adicionado
            ds = [s for s in ds if s.dt >= now.replace(second=0, microsecond=0)]
            if not ds:
                # Se não há slots futuros hoje, pega o próximo slot do dia seguinte
                continue
        slots.extend(ds)
    return slots

def _list_accounts(base_videos_dir: str) -> List[str]:
    if not os.path.isdir(base_videos_dir):
        return []
    accs = []
    for name in os.listdir(base_videos_dir):
        path = os.path.join(base_videos_dir, name)
        if os.path.isdir(path):
            accs.append(name)
    return sorted(accs)

def _iter_videos_with_sidecar(account_dir: str):
    for name in sorted(os.listdir(account_dir)):
        p = os.path.join(account_dir, name)
        if not os.path.isfile(p):
            continue
        root, ext = os.path.splitext(name)
        if ext.lower() not in VIDEO_EXTS:
            continue
        sidecar = os.path.join(account_dir, f"{root}.json")
        yield p, sidecar

def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _collect_occupied_slots(account_dir: str) -> Dict[str, str]:
    """map[iso_scheduled_at] = video_basename

    Normaliza todos os scheduled_at para o timezone local (TZ) para garantir
    comparação consistente com os slots gerados por generate_slots_now().
    """
    occ: Dict[str, str] = {}
    for video_path, sidecar in _iter_videos_with_sidecar(account_dir):
        root, _ = os.path.splitext(os.path.basename(video_path))
        meta = _read_json(sidecar) or {}
        sch = meta.get("scheduled_at")
        status = (meta.get("status") or "pending").lower()
        if sch and status in ("pending", "posting"):
            try:
                # Parse e converte para timezone local
                sch_dt = datetime.fromisoformat(sch)
                if sch_dt.tzinfo is None:
                    sch_dt = sch_dt.replace(tzinfo=TZ)
                else:
                    sch_dt = sch_dt.astimezone(TZ)
                # Usa formato ISO normalizado no timezone local
                occ[sch_dt.isoformat()] = root
            except Exception:
                # Se falhar o parse, usa o valor original
                occ[sch] = root
    return occ

def _set_status(sidecar: str, new_data: dict):
    meta = _read_json(sidecar) or {}
    meta.update(new_data)
    _write_json(sidecar, meta)

def allocate_new_videos_for_account(account: str) -> Dict:
    """
    - Varre videos/<account>
    - Para itens sem scheduled_at/status relevante, atribui slots 1:1.
    - Retorna um resumo.
    """
    acc_dir = os.path.join(BASE_VIDEOS_DIR, account)
    os.makedirs(acc_dir, exist_ok=True)

    slots = generate_slots_now(HORIZON_DAYS)
    occ = _collect_occupied_slots(acc_dir)
    occ_set = set(occ.keys())
    free_slots: List[Slot] = [s for s in slots if s.dt.isoformat() not in occ_set]

    new_assigned = 0
    waitlisted = 0
    assigned_items: List[Tuple[str, str]] = []  # (video, scheduled_at)

    # coleta fila FIFO (sem scheduled_at)
    queue: List[Tuple[str, str, dict]] = []  # (video_path, sidecar, meta)
    for video_path, sidecar in _iter_videos_with_sidecar(acc_dir):
        meta = _read_json(sidecar) or {}
        sch = meta.get("scheduled_at")
        status = (meta.get("status") or "pending").lower()
        if sch:
            continue  # já tem slot
        if status not in ("pending", "failed", "waitlist"):  # não mexe em posted
            continue
        queue.append((video_path, sidecar, meta))

    # ordena FIFO por uploaded_at (fallback: mtime)
    def _uploaded_at(meta, path):
        ua = meta.get("uploaded_at")
        if ua:
            try:
                return datetime.fromisoformat(ua)
            except Exception:
                pass
        return datetime.fromtimestamp(os.path.getmtime(path), tz=TZ)

    queue.sort(key=lambda x: _uploaded_at(x[2], x[0]))

    it = iter(free_slots)
    for video_path, sidecar, meta in queue:
        try:
            s = next(it)
            sch = s.dt.isoformat()
            _set_status(sidecar, {
                "scheduled_at": sch,
                "status": "pending"
            })
            assigned_items.append((os.path.basename(video_path), sch))
            new_assigned += 1
        except StopIteration:
            # sem capacidade no horizonte → waitlist
            _set_status(sidecar, {
                "status": "waitlist",
                "waitlist_reason": f"capacity_exceeded_{HORIZON_DAYS}d"
            })
            waitlisted += 1

    # salva índice (opcional; útil para painel)
    _persist_schedule_index(account)

    return {
        "account": account,
        "assigned": new_assigned,
        "waitlisted": waitlisted,
        "items": assigned_items,
        "horizon_days": HORIZON_DAYS,
        "slots_per_day": len(_day_slots(datetime.now(TZ))),
    }

def reallocate_missed_slots_for_account(account: str) -> Dict:
    """
    Se CATCH_UP = false:
      - para vídeos com scheduled_at < now e status pending, move para próximo slot livre.
    Se CATCH_UP = true: não mexe (o scheduler tentará postar “em modo atraso”).
    """
    if CATCH_UP:
        return {"account": account, "changed": 0, "catch_up": True}

    acc_dir = os.path.join(BASE_VIDEOS_DIR, account)
    slots = generate_slots_now(HORIZON_DAYS)
    now = datetime.now(TZ)

    occ = _collect_occupied_slots(acc_dir)
    occ_set = set(occ.keys())
    free_slots = [s for s in slots if s.dt.isoformat() not in occ_set]

    changed = 0
    it = iter(free_slots)
    for video_path, sidecar in _iter_videos_with_sidecar(acc_dir):
        meta = _read_json(sidecar) or {}
        sch = meta.get("scheduled_at")
        status = (meta.get("status") or "pending").lower()
        if not sch or status not in ("pending", "failed"):
            continue
        try:
            sch_dt = datetime.fromisoformat(sch)
        except Exception:
            continue
        if sch_dt < now:
            try:
                s = next(it)
                new_sch = s.dt.isoformat()
                _set_status(sidecar, {"scheduled_at": new_sch, "status": "pending"})
                changed += 1
            except StopIteration:
                # sem espaço → waitlist
                _set_status(sidecar, {"status": "waitlist", "waitlist_reason": f"capacity_exceeded_{HORIZON_DAYS}d"})

    _persist_schedule_index(account)
    return {"account": account, "changed": changed, "catch_up": False}

def _persist_schedule_index(account: str):
    os.makedirs(BASE_STATE_DIR, exist_ok=True)
    idx = _read_json(SCHEDULE_INDEX_FILE) or {}
    idx.setdefault(account, {})

    # reconstroi visão do índice (somente futuro)
    acc_dir = os.path.join(BASE_VIDEOS_DIR, account)
    mapping: Dict[str, str] = {}
    for video_path, sidecar in _iter_videos_with_sidecar(acc_dir):
        meta = _read_json(sidecar) or {}
        sch = meta.get("scheduled_at")
        status = (meta.get("status") or "pending").lower()
        if sch and status in ("pending", "posting"):
            root, _ = os.path.splitext(os.path.basename(video_path))
            mapping[sch] = root

    idx[account] = mapping
    _write_json(SCHEDULE_INDEX_FILE, idx)

def plan_all_accounts() -> Dict[str, Dict]:
    summary: Dict[str, Dict] = {}
    for acc in _list_accounts(BASE_VIDEOS_DIR):
        reallocate_missed_slots_for_account(acc)
        summary[acc] = allocate_new_videos_for_account(acc)
    return summary

def preview_schedule(account: str) -> Dict:
    """
    Retorna a grade dos próximos 30 dias: cada slot com (vazio | vídeo)
    """
    slots = generate_slots_now(HORIZON_DAYS)
    acc_dir = os.path.join(BASE_VIDEOS_DIR, account)
    occ = _collect_occupied_slots(acc_dir)

    grid = []
    for s in slots:
        iso = s.dt.isoformat()
        grid.append({
            "slot": iso,
            "video": occ.get(iso)  # None = livre
        })
    return {
        "account": account,
        "tz": TZ_NAME,
        "horizon_days": HORIZON_DAYS,
        "slots_per_day": len(_day_slots(datetime.now(TZ))),
        "grid": grid
    }
