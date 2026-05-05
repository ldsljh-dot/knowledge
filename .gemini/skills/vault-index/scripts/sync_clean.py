#!/usr/bin/env python3
"""
Sync Clean - 3계층 동기화 정리 스크립트
Obsidian Vault (SoT) ↔ Vault Index ↔ Mem0 간 일관성을 검사하고 고아 데이터를 정리합니다.

Obsidian을 Source of Truth로 삼고, Vault Index와 Mem0을 파생 캐시로 취급합니다.
Obsidian에 폴더가 없는 Vault Index 항목과 Mem0 기억을 orphan으로 판단하여 삭제합니다.

Usage:
    # dry-run (기본): 삭제 미리보기
    python sync_clean.py

    # 실제 삭제 실행
    python sync_clean.py --execute

    # Mem0만 검사
    python sync_clean.py --mem0-only

    # Vault Index만 검사
    python sync_clean.py --vault-only

    # 기존 기억에 obsidian_path 메타데이터 보강
    python sync_clean.py --backfill
"""

import os
import sys
import json
import argparse
from pathlib import Path

# .env 지원
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    _p = _here.parent
    for _ in range(6):
        if (_p / ".env").exists():
            load_dotenv(_p / ".env", override=True)
            break
        _p = _p.parent
except ImportError:
    pass

# common/utils.py 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))
from utils import safe_filename

# vault_index.py 함수 재사용
from vault_index import (
    scan_topic_folders,
    get_indexed,
    delete_points,
    folder_uuid,
    get_qdrant_client,
    COLLECTION as VAULT_COLLECTION,
    QDRANT_PATH,
)


def _get_mem0_config() -> dict:
    """Mem0 설정 (다른 Mem0 스크립트와 동일)."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return None

    return {
        "llm": {
            "provider": "anthropic",
            "config": {
                "model": "claude-haiku-4-5-20251001",
                "api_key": anthropic_key,
                "temperature": 0.1,
                "max_tokens": 2000,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "knowledge_engine",
                "path": str(Path.home() / ".mem0" / "qdrant"),
                "embedding_model_dims": 384,
            },
        },
    }


def _load_all_memories(m, user_id: str) -> list:
    """Mem0에서 전체 기억 로드."""
    raw = m.get_all(user_id=user_id)
    if isinstance(raw, dict):
        return raw.get("results", raw.get("memories", []))
    return raw or []


def _expected_obsidian_path(metadata: dict) -> str | None:
    """metadata에서 예상 Obsidian 경로 생성."""
    obsidian_path = metadata.get("obsidian_path", "")
    if obsidian_path:
        return obsidian_path
    topic = metadata.get("topic", "")
    category = metadata.get("category", "")
    # 일반 워크플로우: topic + category
    if topic and category:
        return f"{category}/{safe_filename(topic)}"
    # code_analyze: category + layer
    layer = metadata.get("layer", "")
    if layer and category:
        return f"{category}/{safe_filename(layer)}"
    return None


def scan_vault(vault_path: str) -> set:
    """Obsidian vault에서 존재하는 토픽 경로 집합 반환."""
    vault = Path(vault_path)
    if not vault.is_dir():
        print(f"[ERROR] Vault 경로 없음: {vault}", file=sys.stderr)
        sys.exit(1)
    topics = scan_topic_folders(vault)
    return {t["path"] for t in topics}


def clean_vault_index(existing_paths: set, dry_run: bool) -> int:
    """Vault Index에서 orphan 항목 정리. 삭제된 개수 반환."""
    print("\n=== Phase 2: Vault Index 정리 ===")
    client = get_qdrant_client()
    indexed = get_indexed(client)

    orphan_paths = [p for p in indexed if p not in existing_paths]

    if not orphan_paths:
        print("  ✅ Vault Index 고아 없음")
        return 0

    for p in orphan_paths:
        label = "[DRY-RUN] 삭제 예정" if dry_run else "🗑  삭제"
        print(f"  {label}: {p}")

    if not dry_run:
        delete_points(client, [folder_uuid(p) for p in orphan_paths])

    action = "삭제 예정" if dry_run else "삭제 완료"
    print(f"\n  Vault Index: {len(orphan_paths)}개 {action}")
    return len(orphan_paths)


def clean_mem0(existing_paths: set, dry_run: bool) -> tuple[int, int]:
    """Mem0에서 orphan 기억 정리. (삭제된 수, 추적불가 수) 반환."""
    print("\n=== Phase 3: Mem0 정리 ===")

    mem0_config = _get_mem0_config()
    if not mem0_config:
        print("  ℹ️  ANTHROPIC_API_KEY 미설정 — Mem0 정리 건너뜀")
        return 0, 0

    # SQLite 스레드 제한 우회
    import sqlite3 as _sqlite3
    _orig_connect = _sqlite3.connect
    def _patched_connect(*a, **kw):
        kw["check_same_thread"] = False
        return _orig_connect(*a, **kw)
    _sqlite3.connect = _patched_connect

    try:
        from mem0 import Memory
    except ImportError:
        print("  [ERROR] mem0ai 패키지 미설치 — Mem0 정리 건너뜀", file=sys.stderr)
        return 0, 0

    user_id = os.getenv("MEM0_USER_ID", "knowledge_engine")
    m = Memory.from_config(mem0_config)
    memories = _load_all_memories(m, user_id)

    orphans = []
    untraceable = 0

    for mem in memories:
        meta = mem.get("metadata") or {}
        expected = _expected_obsidian_path(meta)
        if expected:
            if expected not in existing_paths:
                orphans.append(mem)
        else:
            untraceable += 1

    print(f"  전체 기억: {len(memories)}건")
    print(f"  고아 (Obsidian 폴더 없음): {len(orphans)}건")
    print(f"  추적 불가 (topic/category 없음): {untraceable}건")
    print(f"  정상: {len(memories) - len(orphans) - untraceable}건")

    if not orphans:
        print("  ✅ Mem0 고아 없음")
        return 0, untraceable

    print()
    for mem in orphans:
        mem_id = mem.get("id")
        text = mem.get("memory", "")[:80]
        meta = mem.get("metadata") or {}
        path = _expected_obsidian_path(meta) or "?"
        label = "[DRY-RUN] 삭제 예정" if dry_run else "🗑  삭제"
        print(f"  {label}: {path}")
        print(f"    내용: {text}...")

        if not dry_run:
            m.delete(mem_id)

    action = "삭제 예정" if dry_run else "삭제 완료"
    print(f"\n  Mem0: {len(orphans)}건 {action}")
    if dry_run:
        print("  💡 --execute 플래그로 실제 삭제")
    return len(orphans), untraceable


def discover_untracked(vault_path: str, json_output: bool = False):
    """미편입 지식 폴더 탐색 (Knowledge Engine에 등록되지 않은 수동 생성 노트 폴더)"""
    vault = Path(vault_path)
    if not vault.is_dir():
        if json_output:
            print(json.dumps({"error": f"Vault 경로 없음: {vault}"}))
        else:
            print(f"[ERROR] Vault 경로 없음: {vault}", file=sys.stderr)
        sys.exit(1)

    existing_paths = scan_vault(vault_path)
    SKIP_DIRS = {'node_modules', '.agent', '.obsidian', '.git', '.trash', '.cache'}
    SKIP_FILES = {'readme.md', 'changelog.md', 'changes.md', 'license.md', 'sponsors.md'}
    SKIP_PREFIXES = ['3-Resources/Life']
    MIN_SIZE_KB = 3

    untracked = []

    for root, dirs, files in os.walk(vault):
        root_path = Path(root)
        rel_root = root_path.relative_to(vault)
        rel_str = str(rel_root).replace('\\', '/')

        # Filter dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

        if rel_str == '.':
            continue

        skip = False
        for prefix in SKIP_PREFIXES:
            if rel_str.startswith(prefix):
                skip = True
                break
        if skip:
            continue

        if rel_str in existing_paths:
            dirs[:] = []
            continue

        is_container = any(ep.startswith(rel_str + '/') for ep in existing_paths)
        if is_container:
            continue

        md_files = [f for f in files if f.endswith('.md') and f.lower() not in SKIP_FILES]
        if not md_files:
            continue

        if (root_path / 'sources').is_dir() or (root_path / 'rag').is_dir():
            continue

        total_size = sum((root_path / f).stat().st_size for f in md_files)
        if total_size < MIN_SIZE_KB * 1024:
            continue

        untracked.append({
            'path': rel_str,
            'files_count': len(md_files),
            'size_kb': total_size / 1024
        })

    if json_output:
        print(json.dumps(untracked))
        return

    grouped = {}
    for item in untracked:
        category = item['path'].split('/', 1)[0]
        grouped.setdefault(category, []).append(item)

    print("\n=== 미편입 지식 탐색 결과 ===")
    if not untracked:
        print("  ✅ 모든 지식이 편입되어 있습니다.")
        return

    print(f"  발견된 미편입 폴더: {len(untracked)}개 (최소 {MIN_SIZE_KB}KB 이상)\n")
    for category in sorted(grouped.keys()):
        print(f"📁 {category}")
        for item in sorted(grouped[category], key=lambda x: x['path']):
            name = item['path'][len(category)+1:] if '/' in item['path'] else item['path']
            print(f"  - {name} ({item['files_count']}개 파일, {item['size_kb']:.1f}KB)")
    print("\n💡 편입하려면 /housekeeping 워크플로우를 사용하세요.")


def backfill_mem0() -> int:
    """기존 Mem0 기억에 obsidian_path 메타데이터 보강. 업데이트된 수 반환."""
    print("\n=== Mem0 obsidian_path 백필 ===")

    mem0_config = _get_mem0_config()
    if not mem0_config:
        print("  ℹ️  ANTHROPIC_API_KEY 미설정 — 백필 건너뜀")
        return 0

    import sqlite3 as _sqlite3
    _orig_connect = _sqlite3.connect
    def _patched_connect(*a, **kw):
        kw["check_same_thread"] = False
        return _orig_connect(*a, **kw)
    _sqlite3.connect = _patched_connect

    from mem0 import Memory

    user_id = os.getenv("MEM0_USER_ID", "knowledge_engine")
    m = Memory.from_config(mem0_config)
    memories = _load_all_memories(m, user_id)

    updated = 0
    skipped_no_path = 0
    already_has = 0

    for mem in memories:
        meta = mem.get("metadata") or {}
        mem_id = mem.get("id")
        text = mem.get("memory", "")

        if meta.get("obsidian_path"):
            already_has += 1
            continue

        expected = _expected_obsidian_path(meta)
        if not expected:
            skipped_no_path += 1
            continue

        new_meta = {**meta, "obsidian_path": expected}
        m.update(memory_id=mem_id, data=text, metadata=new_meta)
        print(f"  ✏️  {mem_id[:12]}... → {expected}")
        updated += 1

    print(f"\n  결과: {updated}건 업데이트, {already_has}건 이미 있음, {skipped_no_path}건 추적불가")
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="3계층 동기화 정리 (Obsidian ↔ Vault Index ↔ Mem0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true",
                        help="실제 삭제 실행 (기본: dry-run)")
    parser.add_argument("--mem0-only", action="store_true",
                        help="Mem0만 검사")
    parser.add_argument("--vault-only", action="store_true",
                        help="Vault Index만 검사")
    parser.add_argument("--backfill", action="store_true",
                        help="Mem0 기억에 obsidian_path 메타데이터 보강")
    parser.add_argument("--discover", action="store_true",
                        help="미편입 지식 폴더 탐색")
    parser.add_argument("--json", action="store_true",
                        help="JSON 출력 (워크플로우 파싱용)")
    parser.add_argument("--vault-path", default=os.getenv("OBSIDIAN_VAULT_PATH"),
                        help="Obsidian vault 경로")
    args = parser.parse_args()

    if not args.vault_path and not args.backfill:
        print("[ERROR] OBSIDIAN_VAULT_PATH 환경변수 또는 --vault-path 필요", file=sys.stderr)
        sys.exit(1)

    if args.discover:
        discover_untracked(args.vault_path, args.json)
        return

    dry_run = not args.execute
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"╔══════════════════════════════════════╗")
    print(f"║  Sync Clean — 모드: {mode:^10s}       ║")
    print(f"╚══════════════════════════════════════╝")

    # Phase 1: Obsidian 스캔
    existing_paths = set()
    if not args.mem0_only or args.backfill:
        if args.vault_path:
            existing_paths = scan_vault(args.vault_path)
            print(f"\n=== Phase 1: Obsidian 스캔 ===")
            print(f"  발견된 토픽 폴더: {len(existing_paths)}개")

    # 백필 모드
    if args.backfill:
        backfill_mem0()
        return

    vault_orphans = 0
    mem0_orphans = 0
    mem0_untraceable = 0

    # Phase 2: Vault Index 정리
    if not args.mem0_only:
        vault_orphans = clean_vault_index(existing_paths, dry_run)

    # Phase 3: Mem0 정리
    if not args.vault_only:
        mem0_orphans, mem0_untraceable = clean_mem0(existing_paths, dry_run)

    # Phase 4: 결과 요약
    print(f"\n{'='*45}")
    print(f"  📊 결과 요약")
    print(f"{'='*45}")
    print(f"  Obsidian 토픽 폴더: {len(existing_paths)}개")
    if not args.mem0_only:
        print(f"  Vault Index orphan: {vault_orphans}개")
    if not args.vault_only:
        print(f"  Mem0 orphan:        {mem0_orphans}개")
        print(f"  Mem0 추적불가:       {mem0_untraceable}개")
    if dry_run and (vault_orphans or mem0_orphans):
        print(f"\n  💡 --execute 플래그로 실제 삭제를 실행하세요.")


if __name__ == "__main__":
    main()
