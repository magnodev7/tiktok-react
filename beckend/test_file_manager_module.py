#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_file_manager_module.py
Teste de integração para o Módulo 6: FileManagerModule

Uso:
  python3 test_file_manager_module.py
"""

import os
import sys
import json
import time
import shutil
import socket
import getpass
import tempfile
import datetime as dt
from pathlib import Path
from typing import Dict, Any

# ───────────────────────── Helpers ─────────────────────────

def log(msg: str):
    print(msg, flush=True)

def measure_time(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    end = time.perf_counter()
    return result, end - start

def write_bytes(path: Path, size_kb: int = 8):
    """Cria arquivo binário de tamanho aproximado (KB)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\0" * 1024 * size_kb)

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)

def assert_eq(a, b, msg: str):
    if a != b:
        raise AssertionError(f"{msg} (got={a!r}, expected={b!r})")

def assert_exists(path: Path, msg: str):
    if not path.exists():
        raise AssertionError(msg)

def assert_not_exists(path: Path, msg: str):
    if path.exists():
        raise AssertionError(msg)

def touch_old(file: Path, seconds_ago: int):
    """Ajusta mtime para simular arquivo antigo."""
    past = time.time() - seconds_ago
    os.utime(file, (past, past))

def export_metrics_jsonl(path: Path, payload: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

# ───────────────────── Imports do módulo ────────────────────

def _bootstrap_sys_path():
    here = Path(__file__).resolve().parent
    candidates = [
        here / "src",
        here / "beckend" / "src",
        here.parent / "src",
        here.parent / "beckend" / "src",
    ]
    for c in candidates:
        if (c / "modules").exists():
            sys.path.insert(0, str(c))
            return True
    return False

_bootstrap_sys_path()

try:
    from modules.file_manager_module import FileManagerModule
except Exception:
    try:
        from src.modules.file_manager_module import FileManagerModule
    except Exception:
        from src.modules import FileManagerModule  # type: ignore

# ─────────────────────—— Caso de Teste ──────────────────────

class FileManagerIntegrationTest:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fm_test_")
        self.root = Path(self.temp.name)
        self.videos_dir = self.root / "videos"
        self.posted_dir = self.root / "posted"
        self.misc_dir = self.root / "misc"
        self.metrics: Dict[str, float] = {}
        self.fm = FileManagerModule(logger=log)

        self.video_name = "Video de Teste.mp4"
        self.video_path = self.videos_dir / self.video_name
        self.json_path = self.videos_dir / (self.video_path.stem + ".json")

        self.meta = {
            "title": "Video de Teste",
            "id": "vid_123",
            "account": "mundoparalelodm",
            "tags": ["tiktok", "automation"],
        }

    def setup_fs(self):
        write_bytes(self.video_path, size_kb=64)  # 64 KB para evitar 0.00 MB
        write_text(self.json_path, json.dumps(self.meta, ensure_ascii=False))
        self.misc_dir.mkdir(parents=True, exist_ok=True)
        self.posted_dir.mkdir(parents=True, exist_ok=True)

    # ——————— Testes ———————

    def test_json_ops(self):
        data, dt_read = measure_time(self.fm.read_json, str(self.json_path))
        self.metrics["read_json"] = dt_read
        assert_true(isinstance(data, dict), "read_json não retornou dict")
        assert_eq(data.get("title"), self.meta["title"], "Título lido no JSON está incorreto")

        new_json_path = self.misc_dir / "sample.json"
        payload = {"ok": True, "when": "now"}
        ok, dt_write = measure_time(self.fm.write_json, str(new_json_path), payload)
        self.metrics["write_json"] = dt_write
        assert_true(ok, "write_json falhou")
        assert_exists(new_json_path, "JSON não foi criado pelo write_json()")

        missing = self.fm.read_json(str(self.misc_dir / "nope.json"))
        assert_true(missing is None, "read_json deveria retornar None quando não existe")

        ok = self.fm.delete_json(str(self.misc_dir / "inexistent.json"), safe=True)
        assert_true(ok, "delete_json(safe=True) deveria considerar OK se não existe")

        ok = self.fm.delete_json(str(self.misc_dir / "inexistent.json"), safe=False)
        assert_true(ok is False, "delete_json(safe=False) deveria falhar se não existe")

        ok = self.fm.delete_json(str(new_json_path), safe=False)
        assert_true(ok, "delete_json deveria deletar JSON existente")
        assert_not_exists(new_json_path, "JSON deveria ter sido removido")

    def test_video_ops(self):
        dest_dir = self.misc_dir / "copies"
        copied, dt_copy = measure_time(self.fm.copy_video, str(self.video_path), str(dest_dir), False)
        self.metrics["copy_video"] = dt_copy
        assert_true(copied is not None, "copy_video falhou")
        assert_exists(Path(copied), "Arquivo copiado não existe")

        copied2 = self.fm.copy_video(str(self.video_path), str(dest_dir), False)
        assert_true(copied2 is None, "copy_video deveria retornar None quando já existe e overwrite=False")

        copied3 = self.fm.copy_video(str(self.video_path), str(dest_dir), True)
        assert_true(copied3 is not None, "copy_video overwrite=True deveria funcionar")

        moved, dt_move = measure_time(self.fm.move_video, str(self.video_path), str(self.posted_dir), False)
        self.metrics["move_video"] = dt_move
        assert_true(moved is not None, "move_video falhou")
        assert_not_exists(self.video_path, "Vídeo original deveria ter sido movido")
        assert_exists(Path(moved), "Vídeo movido não apareceu no destino")

        ok = self.fm.delete_video(str(self.video_path), safe=True)
        assert_true(ok, "delete_video(safe=True) deveria retornar True quando não existe")

        ok = self.fm.delete_video(str(self.video_path), safe=False)
        assert_true(ok is False, "delete_video(safe=False) deveria retornar False quando não existe")

        ok = self.fm.delete_video(copied3, safe=False)
        assert_true(ok, "delete_video deveria remover o arquivo copiado")

    def test_locks(self):
        # re-cria um vídeo pequeno para lock
        write_bytes(self.video_path, 4)

        ok, dt_lock = measure_time(self.fm.create_lock, str(self.video_path))
        self.metrics["create_lock"] = dt_lock

        lock_path = Path(str(self.video_path) + ".posting.lock")
        assert_exists(lock_path, "Lock não foi criado")

        assert_true(self.fm.check_lock(str(self.video_path)) is True, "check_lock deveria retornar True com lock presente")

        touch_old(lock_path, seconds_ago=600)  # 10 min
        assert_true(self.fm.check_lock(str(self.video_path), max_age_seconds=60) is False, "Lock antigo deveria ser inválido")

        ok, dt_unlock = measure_time(self.fm.remove_lock, str(self.video_path))
        self.metrics["remove_lock"] = dt_unlock
        assert_true(ok, "remove_lock falhou")
        assert_not_exists(lock_path, "Lock deveria ter sido removido")

    def test_metadata_discovery(self):
        # garante vídeo e JSON presentes
        if not self.video_path.exists():
            write_bytes(self.video_path, 8)
        if not self.json_path.exists():
            write_text(self.json_path, json.dumps(self.meta, ensure_ascii=False))

        data, dt_meta = measure_time(self.fm.get_video_metadata, str(self.video_path))
        self.metrics["get_video_metadata"] = dt_meta
        assert_true(isinstance(data, dict), "get_video_metadata deveria retornar dict")
        assert_eq(data.get("id"), "vid_123", "get_video_metadata não leu o ID esperado")

        # JSON alternativo
        alt_json = self.videos_dir / f"{self.video_path.stem}.info.json"
        write_text(alt_json, json.dumps({"alt": True, "id": "vid_123"}, ensure_ascii=False))

        # remove o principal e força descoberta do alternativo
        self.json_path.unlink(missing_ok=True)
        data2 = self.fm.get_video_metadata(str(self.video_path))
        assert_true(isinstance(data2, dict), "get_video_metadata deveria encontrar JSON alternativo")
        assert_true("alt" in data2, "get_video_metadata não retornou o JSON alternativo esperado")

    def test_finalize_and_cleanup(self):
        if not self.video_path.exists():
            write_bytes(self.video_path, 4)
        if not self.json_path.exists():
            write_text(self.json_path, json.dumps(self.meta, ensure_ascii=False))

        self.fm.create_lock(str(self.video_path))

        ok, dt_final = measure_time(self.fm.finalize_successful_post, str(self.video_path), str(self.posted_dir), False)
        self.metrics["finalize_successful_post"] = dt_final
        assert_true(ok, "finalize_successful_post deveria retornar True")
        moved_video = self.posted_dir / self.video_name
        moved_json = self.posted_dir / (self.video_path.stem + ".json")
        assert_exists(moved_video, "Vídeo não foi movido para posted")
        assert_exists(moved_json, "JSON não foi movido para posted")

        new_video = self.videos_dir / "novo.mp4"
        write_bytes(new_video, 2)
        self.fm.create_lock(str(new_video))
        lock = Path(str(new_video) + ".posting.lock")
        assert_exists(lock, "Lock do novo vídeo não foi criado")

        ok, dt_clean = measure_time(self.fm.cleanup_failed_post, str(new_video))
        self.metrics["cleanup_failed_post"] = dt_clean
        assert_true(ok, "cleanup_failed_post deveria retornar True")
        assert_not_exists(lock, "Lock deveria ter sido removido no cleanup_failed_post")
        assert_exists(new_video, "Vídeo não deveria ser removido no cleanup_failed_post")

    def test_utils(self):
        new_dir = self.root / "ensure" / "inner"
        ok, dt_ens = measure_time(self.fm.ensure_directory, str(new_dir))
        self.metrics["ensure_directory"] = dt_ens
        assert_true(ok, "ensure_directory deveria criar diretório")
        assert_exists(new_dir, "ensure_directory não criou o diretório")

        # cria 3 vídeos para listar
        v1 = self.videos_dir / "b.mp4"
        v2 = self.videos_dir / "a.MOV"
        v3 = self.videos_dir / "c.avi"
        write_bytes(v1, 1)
        write_bytes(v2, 1)
        write_bytes(v3, 1)

        lst, dt_list = measure_time(self.fm.list_videos_in_directory, str(self.videos_dir))
        self.metrics["list_videos_in_directory"] = dt_list
        names = [Path(p).name for p in lst]
        # deve conter os três (ordem alfabética simples)
        for expected in ["a.MOV", "b.mp4", "c.avi"]:
            assert_true(expected in names, f"list_videos_in_directory não retornou {expected}")
        # checa ordem base (A, b, c)
        sorted_subset = sorted(["a.MOV", "b.mp4", "c.avi"], key=lambda s: s.lower())
        assert_eq(sorted(names[:3], key=lambda s: s.lower()), sorted_subset, "Ordenação inesperada na listagem")

        # get_file_size_mb: cria arquivo com 64KB para não dar 0.00MB
        big_file = self.videos_dir / "size_test.mp4"
        write_bytes(big_file, 64)  # 64 KB ≈ 0.06 MB
        size_mb, dt_size = measure_time(self.fm.get_file_size_mb, str(big_file))
        self.metrics["get_file_size_mb"] = dt_size
        assert_true(size_mb is not None and size_mb >= 0.05, f"get_file_size_mb deveria ser >= 0.05 MB, got {size_mb}")

    # ——————— Runner ———————

    def run(self) -> bool:
        log("🔧 Preparando ambiente temporário…")
        self.setup_fs()

        passed = True
        errors = []

        def _run_step(name, fn):
            nonlocal passed
            log(f"\n🧪 {name} …")
            try:
                _, dt_s = measure_time(fn)
                self.metrics[f"__{name}__"] = dt_s
                log(f"✅ {name} ok em {dt_s:.2f}s")
            except Exception as e:
                passed = False
                errors.append((name, str(e)))
                log(f"❌ {name} falhou: {e}")

        _run_step("JSON Ops", self.test_json_ops)
        _run_step("Vídeo Ops", self.test_video_ops)
        _run_step("Locks", self.test_locks)
        _run_step("Metadata Discovery", self.test_metadata_discovery)
        _run_step("Finalize & Cleanup", self.test_finalize_and_cleanup)
        _run_step("Utils", self.test_utils)

        log("\n📊 MÉTRICAS:")
        for k in sorted(self.metrics.keys()):
            if k.startswith("__"):
                continue
            log(f"  - {k:<28} {self.metrics[k]:6.3f}s")

        payload = {
            "when": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "host": socket.gethostname(),
            "user": getpass.getuser(),
            "metrics": self.metrics,
            "root": str(self.root),
            "result": "PASS" if passed else "FAIL",
            "python": sys.version.split()[0],
        }
        export_metrics_jsonl(self.root / "perf_file_manager.jsonl", payload)
        log(f"📦 Relatório salvo em: {self.root / 'perf_file_manager.jsonl'}")

        if not passed:
            log("\n❌ FALHAS:")
            for name, err in errors:
                log(f"   - {name}: {err}")

        return passed

# ───────────────────────── Main ─────────────────────────

def main():
    log("🧪 Teste de Integração — FileManagerModule (Módulo 6)")
    t = FileManagerIntegrationTest()
    ok = t.run()
    if not ok:
        sys.exit(1)
    log("\n✅ Todos os testes passaram!")

if __name__ == "__main__":
    main()
