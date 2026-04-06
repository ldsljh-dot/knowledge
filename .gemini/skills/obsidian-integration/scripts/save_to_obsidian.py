#!/usr/bin/env python3
"""
Obsidian Integration Skill
학습 내용을 Obsidian vault에 표준 형식으로 저장.

Usage:
    # 새 파일 생성 (기존 동작)
    python scripts/save_to_obsidian.py \
      --topic "PyTorch FX Graph" \
      --content "Q&A 기록..." \
      --summary "핵심 요약..." \
      --category "AI_Study" \
      --vault-path "/path/to/vault" \
      --sources "file1.md,file2.md"

    # 기존 노트에 세션 누적 추가
    python scripts/save_to_obsidian.py \
      --topic "PyTorch FX Graph" \
      --content "Q&A 기록..." \
      --summary "핵심 요약..." \
      --category "AI_Study" \
      --vault-path "/path/to/vault" \
      --append
"""

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# common.utils 임포트를 위해 sys.path 설정
_here = Path(__file__).resolve()
_skills_dir = _here.parent.parent.parent
if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

from common.utils import load_env, safe_filename

# .env 자동 로드
load_env()


# ────────────────────────── 유틸 ──────────────────────────

def extract_title(filepath: str) -> str:
    """md 파일에서 frontmatter title 또는 첫 번째 H1 추출"""
    try:
        lines = Path(filepath).read_text(encoding="utf-8").splitlines()
        in_fm = False
        for line in lines:
            s = line.strip()
            if s == "---":
                in_fm = not in_fm
                continue
            if in_fm and s.startswith("title:"):
                return s.split(":", 1)[1].strip().strip("'\"")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return Path(filepath).stem


def unique_path(base: Path) -> Path:
    """같은 이름 파일이 있으면 _2, _3 ... suffix 추가"""
    if not base.exists():
        return base
    stem, suffix = base.stem, base.suffix
    parent = base.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# ────────────────────────── 노트 생성 ──────────────────────

def build_note(
    topic: str,
    content: str,
    summary: str,
    category: str,
    sources: Optional[List[str]],
    status: str,
) -> str:
    """Obsidian 노트 텍스트 생성 (기존 단일 세션 형식)"""
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

    # wikilinks
    wikilinks_yaml  = "  []"
    source_section  = "_없음_"

    if sources:
        yaml_lines = [f'  - "[[{Path(s).stem}]]"' for s in sources]
        wikilinks_yaml = "\n".join(yaml_lines)

        md_lines = []
        for s in sources:
            stem  = Path(s).stem
            title = extract_title(s) if Path(s).exists() else stem
            md_lines.append(f"- [[{stem}]] - {title}")
        source_section = "\n".join(md_lines)

    frontmatter = f"""---
created: {now_str}
updated: {now_str}
tags: [AI_Study, {category}]
category: {category}
status: {status}
sources:
{wikilinks_yaml}
---"""

    note = f"""{frontmatter}

# 📚 {topic}

## 📖 원본 자료
{source_section}

{content.strip()}

## 🎯 핵심 요약
{summary.strip()}

## 🔗 관련 개념
<!-- 나중에 채워주세요 -->

## 📝 추가 노트
<!-- 나중에 채워주세요 -->
"""
    return note


def save_note(
    topic: str,
    content: str,
    category: str,
    vault_path: str,
    sources: Optional[List[str]] = None,
    summary: str = "",
    status: str = "🌿 seed",
) -> str:
    """
    Obsidian 통합 노트 저장.

    Returns:
        저장된 파일의 절대경로 문자열
    """
    vault = Path(vault_path)
    vault.mkdir(parents=True, exist_ok=True)

    date_str   = datetime.now().strftime("%Y-%m-%d")
    note_title = re.sub(r'[\\/*?:"<>|]', '_', topic)[:60].strip()
    category_dir = vault / category
    category_dir.mkdir(parents=True, exist_ok=True)
    filepath   = unique_path(category_dir / f"{date_str}_{note_title}.md")

    note_text = build_note(
        topic=topic,
        content=content,
        summary=summary,
        category=category,
        sources=sources,
        status=status,
    )

    filepath.write_text(note_text, encoding="utf-8")
    return str(filepath)


# ────────────────────── 위키 페이지 저장 ──────────────────────

def build_wiki_note(
    topic: str,
    content: str,
    category: str,
    sources: Optional[List[str]] = None,
    related_topics: Optional[List[str]] = None,
    status: str = "🌿 seed",
) -> str:
    """위키 페이지용 마크다운 생성. content는 Claude가 이미 구조화한 상태."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # sources wikilinks
    sources_yaml = "  []"
    if sources:
        yaml_lines = [f'  - "[[{Path(s).stem}]]"' for s in sources]
        sources_yaml = "\n".join(yaml_lines)

    # related topics wikilinks
    related_yaml = "  []"
    if related_topics:
        yaml_lines = [f'  - "[[{t.strip()}]]"' for t in related_topics]
        related_yaml = "\n".join(yaml_lines)

    frontmatter = f"""---
created: {now_str}
updated: {now_str}
tags: [{category}, wiki]
category: {category}
type: wiki
status: {status}
session_count: 1
sources:
{sources_yaml}
related:
{related_yaml}
---"""

    return f"{frontmatter}\n\n{content.strip()}\n"


def save_wiki_page(
    topic: str,
    content: str,
    category: str,
    vault_path: str,
    sources: Optional[List[str]] = None,
    related_topics: Optional[List[str]] = None,
    status: str = "🌿 seed",
) -> str:
    """
    위키 페이지 저장. 기존 파일이 있으면 content를 교체하고 메타데이터 갱신.

    Returns:
        저장된 파일의 절대경로 문자열
    """
    vault = Path(vault_path)
    vault.mkdir(parents=True, exist_ok=True)

    note_title = re.sub(r'[\\/*?:"<>|]', '_', topic)[:60].strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    existing = find_existing_note(vault, note_title)

    if existing:
        old_text = existing.read_text(encoding="utf-8")

        # session_count 추출 및 증가
        m = re.search(r"^session_count:\s*(\d+)", old_text, re.MULTILINE)
        session_count = int(m.group(1)) + 1 if m else 2

        # 상태 자동 승격
        if session_count >= 3:
            status = "🌳 tree"
        elif session_count >= 2:
            status = "🌱 sprout"

        # frontmatter 갱신: updated, session_count, status
        new_text = re.sub(
            r"^(updated:\s*).*$", f"\\g<1>{now_str}",
            old_text, flags=re.MULTILINE,
        )
        new_text = re.sub(
            r"^(session_count:\s*).*$", f"\\g<1>{session_count}",
            new_text, flags=re.MULTILINE,
        )
        new_text = re.sub(
            r"^(status:\s*).*$", f"\\g<1>{status}",
            new_text, flags=re.MULTILINE,
        )

        # frontmatter 이후 content 교체
        fm_end = 0
        fm_count = 0
        for i, line in enumerate(new_text.splitlines()):
            if line.strip() == "---":
                fm_count += 1
                if fm_count == 2:
                    fm_end = sum(len(l) + 1 for l in new_text.splitlines()[:i+1])
                    break

        new_text = new_text[:fm_end] + "\n" + content.strip() + "\n"
        existing.write_text(new_text, encoding="utf-8")
        print(f"📝 위키 페이지 업데이트됨 (세션 {session_count}회차)")
        return str(existing)
    else:
        filepath = vault / f"{note_title}.md"
        note_text = build_wiki_note(
            topic=topic,
            content=content,
            category=category,
            sources=sources,
            related_topics=related_topics,
            status=status,
        )
        filepath.write_text(note_text, encoding="utf-8")
        print("📝 새 위키 페이지 생성됨")
        return str(filepath)


# ────────────────────── 누적 세션 저장 ──────────────────────

def find_existing_note(vault: Path, safe_topic: str) -> Optional[Path]:
    """기존 누적 노트 파일 찾기 (날짜 없는 파일명 우선)"""
    candidate = vault / f"{safe_topic}.md"
    if candidate.exists():
        return candidate
    return None


def count_sessions(text: str) -> int:
    """노트 내 세션 블록 개수 계산"""
    return len(re.findall(r"^## 🗓️ 세션 \d+", text, re.MULTILINE))


def build_accumulated_note(
    topic: str,
    content: str,
    summary: str,
    category: str,
    sources: Optional[List[str]],
    status: str,
    now_str: str,
) -> str:
    """누적 노트 초기 생성 (세션 1 포함)"""
    wikilinks_yaml = "  []"
    source_section = "_없음_"

    if sources:
        yaml_lines = [f'  - "[[{Path(s).stem}]]"' for s in sources]
        wikilinks_yaml = "\n".join(yaml_lines)

        md_lines = []
        for s in sources:
            stem  = Path(s).stem
            title = extract_title(s) if Path(s).exists() else stem
            md_lines.append(f"- [[{stem}]] - {title}")
        source_section = "\n".join(md_lines)

    frontmatter = f"""---
created: {now_str}
updated: {now_str}
tags: [AI_Study, {category}]
category: {category}
status: {status}
sources:
{wikilinks_yaml}
---"""

    session_block = f"""---

## 🗓️ 세션 1 — {now_str}

{content.strip()}"""

    if summary.strip():
        session_block += f"\n\n### 🎯 핵심 요약\n{summary.strip()}"

    note = f"""{frontmatter}

# 📚 {topic}

## 📖 원본 자료
{source_section}

## 🔗 관련 개념
<!-- 나중에 채워주세요 -->

{session_block}
"""
    return note


def append_session(
    topic: str,
    content: str,
    summary: str,
    category: str,
    vault_path: str,
    sources: Optional[List[str]] = None,
    status: str = "🌿 seed",
    realtime: bool = False,
) -> str:
    """
    기존 누적 노트에 새 세션 추가. 없으면 새 파일 생성.

    Returns:
        저장된 파일의 절대경로 문자열
    """
    vault = Path(vault_path)
    vault.mkdir(parents=True, exist_ok=True)

    note_title = re.sub(r'[\\/*?:"<>|]', '_', topic)[:60].strip()
    now_str    = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 종합파일은 vault 루트에 저장 — 카테고리 서브폴더 없음
    existing = find_existing_note(vault, note_title)

    if existing:
        old_text = existing.read_text(encoding="utf-8")

        # frontmatter updated 필드 갱신
        new_text = re.sub(
            r"^(updated:\s*).*$",
            f"\\g<1>{now_str}",
            old_text,
            flags=re.MULTILINE,
        )

        if realtime and count_sessions(old_text) > 0:
            append_block = f"\n\n{content.strip()}"
            if summary.strip():
                append_block += f"\n\n**[추가 요약]**\n{summary.strip()}"
            new_text = new_text.rstrip() + append_block + "\n"
            existing.write_text(new_text, encoding="utf-8")
            print(f"📎 마지막 세션에 실시간 내용 추가됨")
            return str(existing)

        # 세션 번호 계산
        session_num = count_sessions(old_text) + 1

        # 세션 블록 구성
        session_block = f"\n---\n\n## 🗓️ 세션 {session_num} — {now_str}\n\n{content.strip()}"
        if summary.strip():
            session_block += f"\n\n### 🎯 핵심 요약\n{summary.strip()}"
        session_block += "\n"

        new_text = new_text.rstrip() + "\n" + session_block
        existing.write_text(new_text, encoding="utf-8")
        print(f"📎 세션 {session_num} 추가됨")
        return str(existing)
    else:
        # 새 누적 파일 생성 (날짜 없는 파일명)
        filepath = vault / f"{note_title}.md"
        note_text = build_accumulated_note(
            topic=topic,
            content=content,
            summary=summary,
            category=category,
            sources=sources,
            status=status,
            now_str=now_str,
        )
        filepath.write_text(note_text, encoding="utf-8")
        print("📄 새 누적 노트 생성됨 (세션 1)")
        return str(filepath)


# ────────────────────────── CLI ──────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obsidian Integration Skill — 학습 내용 저장"
    )
    parser.add_argument("--topic",      required=True, help="학습 주제")
    parser.add_argument("--content",    required=True, help="학습 대화 기록 (Q&A)")
    parser.add_argument("--summary",    default="",    help="핵심 요약 (bullet points)")
    parser.add_argument("--category",   required=True, help="카테고리 (예: AI_Study)")
    parser.add_argument("--vault-path", required=True, help="Obsidian vault 경로")
    parser.add_argument(
        "--sources", default="",
        help="소스 파일 경로 목록 (comma-separated)",
    )
    parser.add_argument(
        "--status",
        default="🌿 seed",
        choices=["🌿 seed", "🌱 sprout", "🌳 tree"],
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="기존 노트에 세션을 누적 추가 (없으면 새로 생성)",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="기존 노트의 마지막 세션에 내용을 실시간으로 이어서 추가",
    )
    parser.add_argument(
        "--wiki",
        action="store_true",
        help="위키 페이지 모드 — 정제된 백과사전 스타일 페이지 저장",
    )
    parser.add_argument(
        "--related-topics",
        default="",
        help="관련 토픽 목록 (comma-separated, 위키링크용)",
    )
    args = parser.parse_args()

    sources = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources else None
    )
    related_topics = (
        [t.strip() for t in args.related_topics.split(",") if t.strip()]
        if args.related_topics else None
    )

    try:
        if args.wiki:
            filepath = save_wiki_page(
                topic=args.topic,
                content=args.content,
                category=args.category,
                vault_path=args.vault_path,
                sources=sources,
                related_topics=related_topics,
                status=args.status,
            )
        elif args.append or args.realtime:
            filepath = append_session(
                topic=args.topic,
                content=args.content,
                summary=args.summary,
                category=args.category,
                vault_path=args.vault_path,
                sources=sources,
                status=args.status,
                realtime=args.realtime,
            )
        else:
            filepath = save_note(
                topic=args.topic,
                content=args.content,
                summary=args.summary,
                category=args.category,
                vault_path=args.vault_path,
                sources=sources,
                status=args.status,
            )
        print(f"✅ 저장 완료!")
        print(f"📁 {filepath}")
        return 0
    except Exception as e:
        print(f"❌ 저장 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
