#!/usr/bin/env python3
"""
Mem0 Memory Skill - Save
세션 요약, 학습 이력, 미해결 질문 등을 Mem0 장기 기억에 저장합니다.
모든 에이전트(Claude, Gemini, ZeroClaw, OpenClaw)가 같은 user_id로 공유합니다.

Usage:
    python memory_save.py \
      --content "AI_Study/PyTorch_autograd 학습 완료. 핵심: computational graph. 미해결: custom hook 성능" \
      --agent "claude" \
      --metadata '{"workflow": "knowledge_tutor", "topic": "PyTorch autograd", "category": "AI_Study"}'
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


def _get_mem0_config() -> dict:
    """Anthropic Claude + 로컬 HuggingFace embedder 설정."""
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
        description="Mem0 - 장기 기억 저장",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--content", required=True, help="저장할 기억 내용")
    parser.add_argument("--agent", required=True,
                        help="에이전트 식별자 (claude/gemini/zeroclaw/openclaw)")
    parser.add_argument("--metadata", default="{}", help='추가 메타데이터 JSON (e.g. \'{"topic": "PyTorch"}\')')
    args = parser.parse_args()

    # metadata 파싱
    try:
        metadata = json.loads(args.metadata)
    except json.JSONDecodeError:
        print(f"[ERROR] --metadata 값이 올바른 JSON이 아닙니다: {args.metadata}", file=sys.stderr)
        sys.exit(1)
    metadata["agent"] = args.agent

    # SQLite 스레드 제한 우회 (Mem0 내부 history.db 호환성)
    import sqlite3 as _sqlite3
    _orig_connect = _sqlite3.connect
    def _patched_connect(*args, **kwargs):
        kwargs['check_same_thread'] = False
        return _orig_connect(*args, **kwargs)
    _sqlite3.connect = _patched_connect

    # Mem0 임포트
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
        result = m.add(args.content, user_id=user_id, metadata=metadata)
        # result는 {'results': [...]} 형식
        memory_ids = []
        if isinstance(result, dict):
            for r in result.get("results", []):
                if isinstance(r, dict) and r.get("id"):
                    memory_ids.append(r["id"])
        elif isinstance(result, list):
            memory_ids = [r.get("id", "") for r in result if isinstance(r, dict)]

        print(f"✅ 기억 저장 완료")
        print(f"   에이전트: {args.agent}")
        print(f"   내용: {args.content[:80]}{'...' if len(args.content) > 80 else ''}")
        if memory_ids:
            print(f"   Memory ID: {', '.join(memory_ids)}")
    except Exception as e:
        print(f"[ERROR] 기억 저장 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
