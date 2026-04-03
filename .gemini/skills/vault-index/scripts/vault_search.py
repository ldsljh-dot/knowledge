#!/usr/bin/env python3
"""
Vault Index Skill - Semantic Search
Obsidian vault 인덱스에서 의미적으로 유사한 토픽 폴더를 검색합니다.

Usage:
    python vault_search.py --query "장기기억 메모리 AI"
    python vault_search.py --query "시스토릭 어레이 행렬 연산" --top-k 5
    python vault_search.py --query "MLIR 컴파일러" --threshold 0.3
    python vault_search.py --query "LLM 추론" --para 2-Areas
"""

import os
import sys
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

QDRANT_PATH = str(Path.home() / ".mem0/qdrant")
COLLECTION  = "obsidian_vault_index"


def main():
    parser = argparse.ArgumentParser(description="Vault 의미 검색")
    parser.add_argument("--query",     required=True, help="검색 쿼리")
    parser.add_argument("--top-k",     type=int, default=5, help="반환 결과 수 (기본: 5)")
    parser.add_argument("--threshold", type=float, default=0.2, help="최소 유사도 (기본: 0.2)")
    parser.add_argument("--para",      default=None, help="PARA 필터 (예: 2-Areas, 1-Projects)")
    parser.add_argument("--json",      action="store_true", help="JSON 출력")
    args = parser.parse_args()

    # 컬렉션 존재 확인
    from qdrant_client import QdrantClient
    client = QdrantClient(path=QDRANT_PATH)
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        print(f"[WARN] 인덱스가 없습니다. 먼저 vault_index.py를 실행하세요.", file=sys.stderr)
        sys.exit(0)

    # 쿼리 임베딩
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    query_vec = model.encode([args.query], normalize_embeddings=True).tolist()[0]

    # PARA 필터
    query_filter = None
    if args.para:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[FieldCondition(key="para", match=MatchValue(value=args.para))]
        )

    # 검색 (qdrant-client 1.x: query_points)
    resp = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=args.top_k,
        query_filter=query_filter,
        with_payload=True,
        score_threshold=args.threshold,
    )
    results = resp.points

    if not results:
        print("관련 지식 폴더를 찾지 못했습니다.")
        return

    if args.json:
        import json
        output = [
            {
                "score":    round(r.score, 3),
                "path":     r.payload["path"],
                "topic":    r.payload["topic"],
                "category": r.payload["category"],
                "para":     r.payload["para"],
            }
            for r in results
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # 사람이 읽기 좋은 출력
    print(f"\n🔍 관련 지식 (쿼리: \"{args.query}\")\n")
    for i, r in enumerate(results, 1):
        score_bar = "█" * int(r.score * 10) + "░" * (10 - int(r.score * 10))
        score_pct = int(r.score * 100)
        para_label = {
            "1-Projects": "📁 Projects",
            "2-Areas":    "🗂  Areas",
            "3-Resources":"📚 Resources",
        }.get(r.payload["para"], r.payload["para"])

        print(f"  {i}. [{score_bar}] {score_pct}%  {para_label}")
        print(f"     📂 {r.payload['path']}")
        print()


if __name__ == "__main__":
    main()
