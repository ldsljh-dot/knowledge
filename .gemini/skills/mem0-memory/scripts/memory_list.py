#!/usr/bin/env python3
"""
Mem0 Memory Skill - List
저장된 모든 기억 목록을 최근순으로 출력합니다.
어떤 세션 이력이 있는지 한눈에 파악할 때 사용합니다.

Usage:
    python memory_list.py --limit 20
    python memory_list.py --agent "claude" --limit 10
    python memory_list.py --format json
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
            load_dotenv(_p / ".env")
            break
        _p = _p.parent
except ImportError:
    pass


def _get_mem0_config() -> dict:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print(
            "[ERROR] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "  .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 추가하세요.",
            file=sys.stderr
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
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "knowledge_engine",
                "path": str(Path.home() / ".mem0" / "qdrant"),
                "embedding_model_dims": 384,
            }
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Mem0 - 장기 기억 목록 조회",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--agent", help="특정 에이전트 결과만 필터 (선택)")
    parser.add_argument("--limit", type=int, default=20, help="최대 결과 수 (기본: 20)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="출력 형식")
    args = parser.parse_args()

    # SQLite 스레드 제한 우회
    import sqlite3 as _sqlite3
    _orig_connect = _sqlite3.connect
    def _patched_connect(*args, **kwargs):
        kwargs['check_same_thread'] = False
        return _orig_connect(*args, **kwargs)
    _sqlite3.connect = _patched_connect

    try:
        from mem0 import Memory
    except ImportError:
        print(
            "[ERROR] mem0ai 패키지가 설치되지 않았습니다.\n"
            "  pip install mem0ai sentence-transformers",
            file=sys.stderr
        )
        sys.exit(1)

    user_id = os.getenv("MEM0_USER_ID", "knowledge_engine")

    try:
        config = _get_mem0_config()
        m = Memory.from_config(config)
        raw = m.get_all(user_id=user_id)

        # 반환값이 {'results': [...]} 형식
        if isinstance(raw, dict):
            memories = raw.get("results", raw.get("memories", []))
        else:
            memories = raw or []

        # agent 필터
        if args.agent:
            memories = [
                r for r in memories
                if (r.get("metadata") or {}).get("agent") == args.agent
            ]

        # 최근순 정렬 (updated_at 또는 created_at 기준, None 안전 처리)
        def _sort_key(r):
            return r.get("updated_at") or r.get("created_at") or ""
        memories = sorted(memories, key=_sort_key, reverse=True)
        memories = memories[:args.limit]

        if args.format == "json":
            print(json.dumps(memories, ensure_ascii=False, indent=2))
            return

        count = len(memories)
        print(f"\n=== 기억 목록 ({count}건) ===\n")
        if count == 0:
            print("  저장된 기억이 없습니다.")
            return

        for i, r in enumerate(memories, 1):
            memory_text = r.get("memory", r.get("text", str(r)))
            metadata = r.get("metadata") or {}
            agent = metadata.get("agent", "-")
            workflow = metadata.get("workflow", "")
            topic = metadata.get("topic", "")
            _ts = r.get("updated_at") or r.get("created_at") or ""
            updated = _ts[:10] if _ts else ""

            label_parts = [agent]
            if workflow:
                label_parts.append(workflow)
            if topic:
                label_parts.append(f"'{topic}'")
            label = " / ".join(label_parts)

            date_str = f"  [{updated[:10]}]" if updated else ""
            print(f"[{i}]{date_str} ({label})")
            print(f"    {memory_text[:120]}{'...' if len(memory_text) > 120 else ''}")
            print()

    except Exception as e:
        print(f"[ERROR] 기억 목록 조회 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
