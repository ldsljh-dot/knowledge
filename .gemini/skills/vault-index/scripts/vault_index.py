#!/usr/bin/env python3
"""
Vault Index Skill - Incremental Indexer
Obsidian vault의 토픽 폴더를 스캔하여 Qdrant에 벡터 인덱스를 구축합니다.

변경된 폴더만 재임베딩하는 incremental 방식으로 동작합니다.

Usage:
    python vault_index.py
    python vault_index.py --vault-path /path/to/vault
    python vault_index.py --full   # 전체 재빌드
    python vault_index.py --dry-run  # 실행 없이 대상 폴더만 출력
"""

import os
import sys
import uuid
import time
import argparse
from pathlib import Path
from datetime import datetime

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
VECTOR_SIZE = 384  # all-MiniLM-L6-v2
PARA_ROOTS  = ["1-Projects", "2-Areas", "3-Resources"]


def get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(path=QDRANT_PATH)


def ensure_collection(client):
    from qdrant_client.models import Distance, VectorParams
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[INFO] 컬렉션 생성: {COLLECTION}")


def folder_uuid(path: str) -> str:
    """폴더 경로를 결정론적 UUID로 변환."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, path))


def is_topic_folder(folder: Path) -> bool:
    """sources/ 또는 rag/ 가 있으면 토픽 폴더로 판단."""
    return (folder / "sources").is_dir() or (folder / "rag").is_dir()


def get_folder_mtime(folder: Path) -> float:
    """sources/ 내 파일들의 최신 mtime 반환."""
    sources = folder / "sources"
    rag = folder / "rag"
    mtimes = []
    for d in [sources, rag]:
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file():
                    mtimes.append(f.stat().st_mtime)
    return max(mtimes) if mtimes else folder.stat().st_mtime


def extract_text(folder: Path, topic: str) -> str:
    """토픽명 + AI 요약 + 파일 제목을 하나의 텍스트로 조합."""
    parts = [topic.replace("_", " ")]
    sources = folder / "sources"
    if sources.is_dir():
        # Tavily AI summary 파일 우선 탐색
        for f in sorted(sources.glob("*_summary_*.md")):
            text = f.read_text(encoding="utf-8", errors="ignore")
            # frontmatter 제거 후 첫 500자
            lines = [l for l in text.splitlines() if not l.startswith("---") and l.strip()]
            parts.append(" ".join(lines)[:500])
            break
        # 파일 제목 목록 추가
        titles = [f.stem.replace("_", " ") for f in sources.glob("*.md") if "summary" not in f.name]
        if titles:
            parts.append("관련 문서: " + ", ".join(titles[:10]))
    return " | ".join(parts)


def scan_topic_folders(vault_path: Path) -> list[dict]:
    """PARA 루트 하위의 토픽 폴더 목록 반환."""
    topics = []
    for para in PARA_ROOTS:
        root = vault_path / para
        if not root.is_dir():
            continue
        for folder in sorted(root.rglob("*")):
            if not folder.is_dir():
                continue
            if any(p.startswith(".") for p in folder.parts):
                continue
            if is_topic_folder(folder):
                rel = str(folder.relative_to(vault_path))
                parts = rel.split(os.sep)
                category = "/".join(parts[:-1])
                topic    = parts[-1]
                topics.append({
                    "path":     rel,
                    "folder":   folder,
                    "topic":    topic,
                    "category": category,
                    "para":     para,
                })
    return topics


def get_indexed(client) -> dict[str, dict]:
    """Qdrant에서 기존 인덱스 목록 조회. {path: payload}"""
    result = {}
    offset = None
    while True:
        resp, offset = client.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in resp:
            result[point.payload["path"]] = point.payload
        if offset is None:
            break
    return result


def embed_texts(texts: list[str]) -> list:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return model.encode(texts, normalize_embeddings=True).tolist()


def upsert_points(client, points: list[dict]):
    from qdrant_client.models import PointStruct
    client.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ],
    )


def delete_points(client, ids: list[str]):
    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=COLLECTION,
        points_selector=PointIdsList(points=ids),
    )


def main():
    parser = argparse.ArgumentParser(description="Vault 인덱스 빌드 (incremental)")
    parser.add_argument("--vault-path", default=os.getenv("OBSIDIAN_VAULT_PATH"), help="Obsidian vault 경로")
    parser.add_argument("--full",    action="store_true", help="전체 재빌드")
    parser.add_argument("--dry-run", action="store_true", help="실행 없이 대상 폴더만 출력")
    args = parser.parse_args()

    if not args.vault_path:
        print("[ERROR] OBSIDIAN_VAULT_PATH 환경변수 또는 --vault-path 필요", file=sys.stderr)
        sys.exit(1)

    vault_path = Path(args.vault_path)
    if not vault_path.is_dir():
        print(f"[ERROR] Vault 경로 없음: {vault_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Vault: {vault_path}")
    print(f"[INFO] Qdrant: {QDRANT_PATH}")

    client = get_qdrant_client()
    ensure_collection(client)

    # 현재 vault 스캔
    all_topics = scan_topic_folders(vault_path)
    all_paths  = {t["path"] for t in all_topics}
    print(f"[INFO] 발견된 토픽 폴더: {len(all_topics)}개")

    # 기존 인덱스 조회
    indexed = {} if args.full else get_indexed(client)

    # 삭제된 폴더 제거
    deleted = [p for p in indexed if p not in all_paths]
    if deleted:
        delete_points(client, [folder_uuid(p) for p in deleted])
        print(f"[INFO] 삭제: {len(deleted)}개")
        for p in deleted:
            print(f"  🗑  {p}")

    # 신규/변경 폴더 분류
    to_index = []
    skipped  = 0
    for t in all_topics:
        mtime = get_folder_mtime(t["folder"])
        prev  = indexed.get(t["path"])
        if prev and not args.full:
            if mtime <= prev.get("indexed_at", 0):
                skipped += 1
                continue
        to_index.append((t, mtime))

    print(f"[INFO] 스킵 (변경 없음): {skipped}개")
    print(f"[INFO] 인덱싱 대상: {len(to_index)}개")

    if args.dry_run:
        for t, _ in to_index:
            status = "신규" if t["path"] not in indexed else "업데이트"
            print(f"  [{status}] {t['path']}")
        return

    if not to_index:
        print("✅ 인덱스가 최신 상태입니다.")
        return

    # 임베딩 생성
    print("[INFO] 임베딩 생성 중...")
    texts  = [extract_text(t["folder"], t["topic"]) for t, _ in to_index]
    vectors = embed_texts(texts)

    # Qdrant 업서트
    now = time.time()
    points = []
    for (t, mtime), vec in zip(to_index, vectors):
        points.append({
            "id":     folder_uuid(t["path"]),
            "vector": vec,
            "payload": {
                "path":       t["path"],
                "topic":      t["topic"],
                "category":   t["category"],
                "para":       t["para"],
                "indexed_at": now,
                "mtime":      mtime,
            },
        })

    upsert_points(client, points)

    added   = sum(1 for t, _ in to_index if t["path"] not in indexed)
    updated = len(to_index) - added
    print(f"\n✅ 완료!")
    print(f"   신규: {added}개 | 업데이트: {updated}개 | 삭제: {len(deleted)}개 | 스킵: {skipped}개")
    print(f"   총 인덱스: {len(all_topics) - len(deleted)}개 폴더")


if __name__ == "__main__":
    main()
