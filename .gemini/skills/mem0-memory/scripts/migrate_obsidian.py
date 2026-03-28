#!/usr/bin/env python3
"""
Mem0 Migration - Obsidian Vault → Mem0
기존 Obsidian 볼트에 축적된 학습 정보를 Mem0에 구축합니다.
노트는 Inbox → 1-Projects → 2-Areas 등으로 이동할 수 있으므로
경로 기반 탐색 없이 전체 볼트를 재귀 탐색합니다.

Usage:
    # 드라이런 (미리보기, 저장 없음)
    python migrate_obsidian.py --dry-run --type manifests

    # 단일 카테고리 테스트
    python migrate_obsidian.py --type manifests --limit 3

    # 세션 요약만
    python migrate_obsidian.py --type summaries --limit 5

    # 전체 마이그레이션
    python migrate_obsidian.py --type both
"""

import os
import sys
import re
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


def _get_vault_path() -> Path:
    vault = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault:
        print("[ERROR] OBSIDIAN_VAULT_PATH 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    p = Path(vault)
    if not p.exists():
        print(f"[ERROR] 볼트 경로가 존재하지 않습니다: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def _extract_current_category(manifest_path: Path, vault_root: Path) -> str:
    """현재 manifest 파일 위치에서 카테고리를 동적으로 추출한다.
    노트가 이동되었을 수 있으므로 manifest에 저장된 category 대신 실제 경로 사용.

    예: /Obsidian/1-Projects/NVBit/rag/manifest.json → "1-Projects"
        /Obsidian/Inbox/Mamba/rag/manifest.json → "Inbox"
    """
    try:
        rel = manifest_path.relative_to(vault_root)
        # 첫 번째 경로 컴포넌트가 카테고리
        return rel.parts[0]
    except (ValueError, IndexError):
        return "unknown"


def _collect_manifests(vault_root: Path) -> list[dict]:
    """볼트 전체를 재귀 탐색해 manifest.json 파일을 모두 수집한다."""
    results = []
    # **/rag/manifest.json 패턴으로 탐색
    for manifest_path in sorted(vault_root.rglob("rag/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] manifest 읽기 실패: {manifest_path} — {e}", file=sys.stderr)
            continue

        current_category = _extract_current_category(manifest_path, vault_root)
        results.append({
            "manifest_path": manifest_path,
            "topic": data.get("topic", ""),
            "safe_topic": data.get("safe_topic", ""),
            "category_stored": data.get("category", ""),
            "category_current": current_category,
            "file_count": data.get("file_count", 0),
            "updated": data.get("updated", ""),
            "created": data.get("created", ""),
        })
    return results


def _collect_session_summaries(vault_root: Path) -> list[dict]:
    """볼트 전체에서 '📝 세션 총괄 요약 리포트' 섹션을 가진 MD 파일을 탐색한다.
    노트 이동을 고려해 경로와 무관하게 전체 재귀 탐색.
    """
    SUMMARY_MARKER = "### 📝 세션 총괄 요약 리포트"
    results = []

    for md_path in sorted(vault_root.rglob("*.md")):
        # rag 폴더 내부, sources 폴더 내부는 skip
        if "rag" in md_path.parts or "sources" in md_path.parts:
            continue

        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            continue

        if SUMMARY_MARKER not in text:
            continue

        current_category = _extract_current_category(md_path, vault_root)

        # 파일명에서 날짜 추출 (YYYY-MM-DD_xxx.md 패턴)
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_path.stem)
        date_str = date_match.group(1) if date_match else ""

        # 토픽명 추출: 날짜 접두사 제거
        stem = md_path.stem
        if date_str:
            stem = stem[len(date_str):].lstrip("_- ")

        # 모든 세션 요약 섹션 추출 (파일 내 여러 개 있을 수 있음)
        sections = _extract_summary_sections(text, SUMMARY_MARKER)

        results.append({
            "md_path": md_path,
            "topic": stem,
            "category": current_category,
            "date": date_str,
            "sections": sections,
        })

    return results


def _extract_summary_sections(text: str, marker: str) -> list[str]:
    """마커 이후 다음 동급 헤딩(###)까지의 텍스트를 추출한다."""
    sections = []
    parts = text.split(marker)

    for part in parts[1:]:  # 첫 번째는 마커 이전
        # 다음 ### 헤딩에서 자름 (같은 레벨)
        next_heading = re.search(r"\n###\s", part)
        if next_heading:
            section = part[:next_heading.start()].strip()
        else:
            section = part.strip()

        if section:
            sections.append(section)

    return sections


def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    """긴 텍스트를 max_chars 단위로 분할한다. 단락 경계 우선."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # max_chars 이전의 마지막 \n\n 위치를 찾아 자름
        cut = text.rfind("\n\n", 0, max_chars)
        if cut < 100:  # 단락 경계가 너무 앞이면 강제 자름
            cut = max_chars
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()

    return [c for c in chunks if c]


def migrate_manifests(m, user_id: str, manifests: list[dict], dry_run: bool) -> tuple[int, int]:
    """토픽 인벤토리를 Mem0에 저장한다."""
    saved = 0
    skipped = 0

    for item in manifests:
        topic = item["topic"]
        if not topic:
            skipped += 1
            continue

        category = item["category_current"]
        file_count = item["file_count"]
        updated = item["updated"][:10] if item["updated"] else ""
        created = item["created"][:10] if item["created"] else ""

        content = (
            f"토픽 '{topic}'이 {category} 카테고리에 수집됨. "
            f"소스 {file_count}개"
            + (f", 최초 수집: {created}" if created else "")
            + (f", 마지막 업데이트: {updated}" if updated else "")
            + "."
        )

        metadata = {
            "agent": "migrate",
            "workflow": "migration",
            "topic": topic,
            "category": category,
            "type": "topic_inventory",
        }

        if dry_run:
            print(f"  [DRY-RUN] {content}")
        else:
            try:
                m.add(content, user_id=user_id, metadata=metadata)
                saved += 1
            except Exception as e:
                print(f"  [WARN] 저장 실패 ({topic}): {e}", file=sys.stderr)
                skipped += 1
                continue

        if not dry_run:
            print(f"  ✓ {topic} ({category})")

    return saved, skipped


def migrate_summaries(m, user_id: str, summaries: list[dict], dry_run: bool) -> tuple[int, int]:
    """세션 요약을 Mem0에 저장한다."""
    saved = 0
    skipped = 0

    for item in summaries:
        topic = item["topic"]
        category = item["category"]
        date = item["date"]

        for i, section in enumerate(item["sections"]):
            chunks = _chunk_text(section)

            for j, chunk in enumerate(chunks):
                chunk_label = f" (파트 {j+1}/{len(chunks)})" if len(chunks) > 1 else ""
                content = f"[{topic}] 세션 요약{chunk_label}: {chunk}"

                metadata = {
                    "agent": "migrate",
                    "workflow": "migration",
                    "topic": topic,
                    "category": category,
                    "type": "session_summary",
                }
                if date:
                    metadata["date"] = date

                if dry_run:
                    preview = content[:120] + ("..." if len(content) > 120 else "")
                    print(f"  [DRY-RUN] {preview}")
                else:
                    try:
                        m.add(content, user_id=user_id, metadata=metadata)
                        saved += 1
                    except Exception as e:
                        print(f"  [WARN] 저장 실패 ({topic}): {e}", file=sys.stderr)
                        skipped += 1
                        continue
                    print(f"  ✓ {topic}{chunk_label} ({date or category})")

    return saved, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Obsidian 볼트 → Mem0 마이그레이션",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type", choices=["both", "manifests", "summaries"], default="both",
        help="마이그레이션 유형: manifests(토픽 목록), summaries(세션 요약), both(전체)"
    )
    parser.add_argument("--limit", type=int, default=0, help="처리 상한 (0 = 무제한)")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만 하고 저장하지 않음")
    args = parser.parse_args()

    vault_root = _get_vault_path()
    print(f"볼트 경로: {vault_root}")

    # SQLite 스레드 제한 우회
    import sqlite3 as _sqlite3
    _orig_connect = _sqlite3.connect
    def _patched_connect(*a, **kw):
        kw['check_same_thread'] = False
        return _orig_connect(*a, **kw)
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
    config = _get_mem0_config()

    if not args.dry_run:
        m = Memory.from_config(config)
    else:
        m = None

    total_saved = 0
    total_skipped = 0

    # ── Type A: 토픽 인벤토리 ──
    if args.type in ("both", "manifests"):
        print("\n=== 토픽 인벤토리 마이그레이션 (manifest.json) ===\n")
        manifests = _collect_manifests(vault_root)
        print(f"  발견된 manifest: {len(manifests)}개")

        if args.limit:
            manifests = manifests[:args.limit]
            print(f"  제한 적용: 최대 {args.limit}개")

        if args.dry_run:
            print()
            for item in manifests:
                category = item["category_current"]
                topic = item["topic"]
                file_count = item["file_count"]
                updated = item["updated"][:10] if item["updated"] else ""
                print(f"  [DRY-RUN] '{topic}' ({category}) — 소스 {file_count}개, 업데이트: {updated}")
            saved, skipped = 0, 0
        else:
            saved, skipped = migrate_manifests(m, user_id, manifests, dry_run=False)
            total_saved += saved
            total_skipped += skipped
            print(f"\n  → 저장: {saved}건, 건너뜀: {skipped}건")

    # ── Type B: 세션 요약 ──
    if args.type in ("both", "summaries"):
        print("\n=== 세션 요약 마이그레이션 (📝 세션 총괄 요약 리포트) ===\n")
        summaries = _collect_session_summaries(vault_root)
        total_sections = sum(len(s["sections"]) for s in summaries)
        print(f"  발견된 파일: {len(summaries)}개, 총 섹션: {total_sections}개")

        if args.limit:
            summaries = summaries[:args.limit]
            print(f"  제한 적용: 최대 {args.limit}개 파일")

        if args.dry_run:
            print()
            for item in summaries:
                for section in item["sections"]:
                    chunks = _chunk_text(section)
                    for j, chunk in enumerate(chunks):
                        chunk_label = f" (파트 {j+1}/{len(chunks)})" if len(chunks) > 1 else ""
                        preview = chunk[:100].replace("\n", " ")
                        print(f"  [DRY-RUN] [{item['topic']}]{chunk_label}: {preview}...")
            saved, skipped = 0, 0
        else:
            saved, skipped = migrate_summaries(m, user_id, summaries, dry_run=False)
            total_saved += saved
            total_skipped += skipped
            print(f"\n  → 저장: {saved}건, 건너뜀: {skipped}건")

    # ── 최종 결과 ──
    if not args.dry_run:
        print(f"\n{'='*40}")
        print(f"마이그레이션 완료: 총 저장 {total_saved}건, 건너뜀 {total_skipped}건")
    else:
        print("\n[DRY-RUN 완료] 위 내용이 저장될 예정입니다. --dry-run 없이 실행하면 실제 저장됩니다.")


if __name__ == "__main__":
    main()
