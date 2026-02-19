"""
create_manifest.py — RAG 토픽 manifest 생성/업데이트

사용법:
    python create_manifest.py \
      --topic "NVIDIA 자율주행 기술 특징과 동향" \
      --sources-dir "C:/path/to/sources/nvidia_autonomous_driving" \
      --rag-root "C:/path/to/rag"

    # 복수 sources-dir
    python create_manifest.py \
      --topic "AI 아키텍처 비교" \
      --sources-dir "C:/vault/sources/mamba_ssm_tech" "C:/vault/sources/nvidia_gpu_h100" \
      --rag-root "C:/path/to/rag"

출력:
    {rag_root}/{safe_topic}/manifest.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def safe_filename(text: str) -> str:
    """공백/특수문자를 밑줄로 변환"""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text).strip("_")


def scan_sources(source_dirs: list[str]) -> dict:
    """소스 디렉토리의 .md 파일 목록과 통계를 수집"""
    files = []
    total_bytes = 0
    for src_dir in source_dirs:
        p = Path(src_dir)
        if not p.exists():
            print(f"  [warn] 소스 디렉토리 없음: {src_dir}", file=sys.stderr)
            continue
        for md in sorted(p.glob("*.md")):
            size = md.stat().st_size
            files.append({
                "path": str(md.resolve()),
                "name": md.name,
                "size_bytes": size,
            })
            total_bytes += size
    return {"files": files, "file_count": len(files), "total_bytes": total_bytes}


def load_existing(manifest_path: Path) -> dict:
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG manifest 생성/업데이트")
    parser.add_argument("--topic",       required=True,           help="토픽 이름 (자연어)")
    parser.add_argument("--sources-dir", required=True, nargs="+",help="소스 .md 파일 디렉토리 (복수 가능)")
    parser.add_argument("--rag-root",    required=True,           help="RAG 루트 폴더 (예: {vault}/rag)")
    parser.add_argument("--tags",        nargs="*", default=[],   help="추가 태그")
    args = parser.parse_args()

    safe_topic = safe_filename(args.topic)
    rag_dir = Path(args.rag_root) / safe_topic
    rag_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = rag_dir / "manifest.json"

    now = datetime.now().isoformat(timespec="seconds")
    existing = load_existing(manifest_path)

    scan = scan_sources(args.sources_dir)

    manifest = {
        "topic":        args.topic,
        "safe_topic":   safe_topic,
        "source_dirs":  [str(Path(d).resolve()) for d in args.sources_dir],
        "files":        scan["files"],
        "file_count":   scan["file_count"],
        "total_bytes":  scan["total_bytes"],
        "tags":         args.tags or existing.get("tags", []),
        "created":      existing.get("created", now),
        "updated":      now,
    }

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ manifest 저장: {manifest_path}")
    print(f"   topic      : {manifest['topic']}")
    print(f"   source_dirs: {manifest['source_dirs']}")
    print(f"   files      : {manifest['file_count']}개 ({manifest['total_bytes']:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
