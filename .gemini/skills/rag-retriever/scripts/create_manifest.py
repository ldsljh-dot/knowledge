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

# common.utils 임포트를 위해 sys.path 설정
_here = Path(__file__).resolve()
_skills_dir = _here.parent.parent.parent
if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

from common.utils import load_env, safe_filename

# .env 자동 로드
load_env()


def to_relative(path: Path, vault_path: Path) -> str:
    """vault_path 기준 상대경로로 변환. 실패 시 절대경로 반환."""
    try:
        return str(path.resolve().relative_to(vault_path.resolve()))
    except ValueError:
        return str(path.resolve())


def scan_sources(source_dirs: list[str], vault_path: Path) -> dict:
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
                "path": to_relative(md, vault_path),
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
    parser.add_argument("--rag-root",    default="",              help="RAG 루트 폴더 (예: {vault}/rag). --output-dir 미지정 시 사용.")
    parser.add_argument("--output-dir",  default="",              help="manifest.json이 저장될 정확한 폴더 경로 (topic 하위폴더 생성 안 함)")
    parser.add_argument("--vault-path",  default=None,            help="Obsidian vault 루트 경로 (미지정 시 OBSIDIAN_VAULT_PATH 환경변수 사용)")
    parser.add_argument("--category",   default="",              help="주제 카테고리 (예: NVBit, PyTorch)")
    parser.add_argument("--tags",        nargs="*", default=[],   help="추가 태그")
    args = parser.parse_args()

    vault_str = args.vault_path or os.environ.get("OBSIDIAN_VAULT_PATH", "")
    if not vault_str:
        print("[ERROR] --vault-path 또는 OBSIDIAN_VAULT_PATH 환경변수가 필요합니다.", file=sys.stderr)
        return 1
    vault_path = Path(vault_str)

    safe_topic = safe_filename(args.topic, max_length=60)
    
    if args.output_dir:
        rag_dir = Path(args.output_dir)
    elif args.rag_root:
        rag_dir = Path(args.rag_root) / safe_topic
    else:
        print("[ERROR] --rag-root 또는 --output-dir 중 하나는 필수입니다.", file=sys.stderr)
        return 1

    rag_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = rag_dir / "manifest.json"

    now = datetime.now().isoformat(timespec="seconds")
    existing = load_existing(manifest_path)

    scan = scan_sources(args.sources_dir, vault_path)

    manifest = {
        "topic":        args.topic,
        "safe_topic":   safe_topic,
        "category":     args.category,
        "vault_path":   str(vault_path.resolve()),
        "source_dirs":  [to_relative(Path(d), vault_path) for d in args.sources_dir],
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
