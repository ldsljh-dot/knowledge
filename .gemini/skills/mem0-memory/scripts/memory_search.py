#!/usr/bin/env python3
"""
Mem0 Memory Skill - Search
저장된 기억에서 관련 내용을 검색합니다.
세션 시작 시 이전 문맥을 로드하거나, 관련 학습 이력을 찾을 때 사용합니다.

Usage:
    python memory_search.py --query "PyTorch 관련 학습 이력" --limit 5
    python memory_search.py --query "미해결 질문" --agent "claude" --limit 3
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
        description="Mem0 - 장기 기억 검색",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--query", required=True, help="검색 쿼리")
    parser.add_argument("--agent", help="특정 에이전트 결과만 필터 (선택)")
    parser.add_argument("--limit", type=int, default=5, help="최대 결과 수 (기본: 5)")
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
        raw = m.search(args.query, user_id=user_id, limit=args.limit * 2)
        # 반환값이 {'results': [...]} 형식일 수 있음
        if isinstance(raw, dict):
            results = raw.get("results", [])
        else:
            results = raw or []

        # agent 필터 적용
        if args.agent:
            results = [
                r for r in results
                if (r.get("metadata") or {}).get("agent") == args.agent
            ]
        results = results[:args.limit]

        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return

        count = len(results)
        print(f"\n=== 관련 기억 ({count}건) ===\n")
        if count == 0:
            print("  관련된 이전 기억이 없습니다.")
            return

        for i, r in enumerate(results, 1):
            memory_text = r.get("memory", r.get("text", str(r)))
            metadata = r.get("metadata") or {}
            agent = metadata.get("agent", "-")
            workflow = metadata.get("workflow", "")
            topic = metadata.get("topic", "")
            score = r.get("score", r.get("relevance_score", ""))
            score_str = f"  관련도: {score:.2f}" if isinstance(score, float) else ""

            label_parts = [agent]
            if workflow:
                label_parts.append(workflow)
            if topic:
                label_parts.append(topic)
            label = " / ".join(label_parts)

            print(f"[{i}] ({label})")
            print(f"    {memory_text}")
            if score_str:
                print(f"   {score_str}")
            print()

    except Exception as e:
        print(f"[ERROR] 기억 검색 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
