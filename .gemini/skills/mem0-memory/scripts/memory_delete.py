#!/usr/bin/env python3
"""
Mem0 Memory Skill - Delete
저장된 기억을 삭제합니다. 단건 삭제, 토픽별 삭제, 고아(orphan) 정리를 지원합니다.

Usage:
    # 특정 기억 삭제
    python memory_delete.py --id <memory_id>

    # 토픽+카테고리로 삭제
    python memory_delete.py --topic "PyTorch autograd" --category "2-Areas/LLM"

    # Obsidian에 폴더가 없는 고아 기억 정리
    python memory_delete.py --clean-orphans

    # dry-run (기본): 삭제 미리보기만
    python memory_delete.py --clean-orphans --dry-run
"""

import os
import sys
import json
import argparse
from pathlib import Path

# .env 지원 (프로젝트 루트까지 탐색)
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


def _get_mem0_config() -> dict:
    """Anthropic Claude + 로컬 HuggingFace embedder 설정."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print(
            "[ERROR] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "  .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 추가하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

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


def _get_vault_paths() -> set:
    """Obsidian vault에서 존재하는 토픽 경로 집합 반환."""
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        print("[WARN] OBSIDIAN_VAULT_PATH 미설정 — Obsidian 스캔 건너뜀", file=sys.stderr)
        return set()

    # vault_index.py의 scan_topic_folders 로직 재사용
    vault = Path(vault_path)
    if not vault.is_dir():
        return set()

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vault-index" / "scripts"))
    from vault_index import scan_topic_folders, is_topic_folder

    topics = scan_topic_folders(vault)
    return {t["path"] for t in topics}


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


def delete_by_id(m, user_id: str, memory_id: str, dry_run: bool):
    """ID로 단건 삭제."""
    if dry_run:
        print(f"[DRY-RUN] 삭제 예정: {memory_id}")
        return
    m.delete(memory_id)
    print(f"🗑  삭제 완료: {memory_id}")


def delete_by_topic(m, user_id: str, topic: str, category: str, dry_run: bool):
    """토픽+카테고리 매칭 기억 삭제."""
    memories = _load_all_memories(m, user_id)
    safe_topic = safe_filename(topic)

    targets = []
    for mem in memories:
        meta = mem.get("metadata") or {}
        # obsidian_path 직접 매칭
        op = meta.get("obsidian_path", "")
        if op == f"{category}/{safe_topic}":
            targets.append(mem)
            continue
        # topic+category 매칭 (fallback)
        if meta.get("topic") == topic and meta.get("category") == category:
            targets.append(mem)

    if not targets:
        print(f"ℹ️  '{topic}' ({category}) 에 해당하는 기억이 없습니다.")
        return

    for mem in targets:
        mem_id = mem.get("id")
        text = mem.get("memory", "")[:80]
        if dry_run:
            print(f"[DRY-RUN] 삭제 예정: {mem_id} — {text}...")
        else:
            m.delete(mem_id)
            print(f"🗑  삭제: {mem_id} — {text}...")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}총 {len(targets)}건{' 삭제 예정' if dry_run else ' 삭제 완료'}")


def clean_orphans(m, user_id: str, dry_run: bool):
    """Obsidian에 폴더가 없는 고아 기억 정리."""
    vault_paths = _get_vault_paths()
    if not vault_paths:
        print("[ERROR] Obsidian 경로를 스캔할 수 없습니다.", file=sys.stderr)
        return

    memories = _load_all_memories(m, user_id)
    orphans = []
    untraceable = 0

    for mem in memories:
        meta = mem.get("metadata") or {}

        # obsidian_path 우선 확인
        obsidian_path = meta.get("obsidian_path", "")
        if obsidian_path:
            if obsidian_path not in vault_paths:
                orphans.append(mem)
            continue

        # topic+category에서 파생
        expected = _expected_obsidian_path(meta)
        if expected:
            if expected not in vault_paths:
                orphans.append(mem)
        else:
            untraceable += 1

    print(f"\n=== 고아 기억 분석 ===")
    print(f"  전체 기억: {len(memories)}건")
    print(f"  고아 (Obsidian 폴더 없음): {len(orphans)}건")
    print(f"  추적 불가 (topic/category 없음): {untraceable}건")
    print(f"  정상: {len(memories) - len(orphans) - untraceable}건\n")

    if not orphans:
        print("✅ 고아 기억이 없습니다.")
        return

    for mem in orphans:
        mem_id = mem.get("id")
        text = mem.get("memory", "")[:100]
        meta = mem.get("metadata") or {}
        path = meta.get("obsidian_path") or _expected_obsidian_path(meta) or "?"
        label = f"[DRY-RUN] 삭제 예정" if dry_run else "🗑  삭제"
        print(f"  {label}: {path}")
        print(f"    ID: {mem_id}")
        print(f"    내용: {text}{'...' if len(mem.get('memory', '')) > 100 else ''}")

        if not dry_run:
            m.delete(mem_id)

    action = "삭제 예정" if dry_run else "삭제 완료"
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}총 {len(orphans)}건 {action}")
    if dry_run:
        print("💡 --execute 플래그로 실제 삭제를 실행하세요.")


def main():
    parser = argparse.ArgumentParser(
        description="Mem0 - 기억 삭제 및 고아 정리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="삭제할 특정 기억 ID")
    group.add_argument("--topic", help="토픽명 (--category와 함께 사용)")
    group.add_argument("--clean-orphans", action="store_true",
                       help="Obsidian에 폴더가 없는 고아 기억 정리")

    parser.add_argument("--category", help="카테고리 경로 (--topic과 함께 사용)")
    parser.add_argument("--execute", action="store_true",
                        help="실제 삭제 실행 (기본: dry-run)")

    args = parser.parse_args()

    # --topic은 --category 필수
    if args.topic and not args.category:
        parser.error("--topic 사용 시 --category도 함께 지정해야 합니다.")

    dry_run = not args.execute

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
        print(
            "[ERROR] mem0ai 패키지가 설치되지 않았습니다.\n"
            "  pip install mem0ai sentence-transformers",
            file=sys.stderr,
        )
        sys.exit(1)

    user_id = os.getenv("MEM0_USER_ID", "knowledge_engine")

    try:
        config = _get_mem0_config()
        m = Memory.from_config(config)

        if args.id:
            delete_by_id(m, user_id, args.id, dry_run)
        elif args.topic:
            delete_by_topic(m, user_id, args.topic, args.category, dry_run)
        elif args.clean_orphans:
            clean_orphans(m, user_id, dry_run)

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
