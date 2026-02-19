#!/usr/bin/env python3
"""
Obsidian Integration Skill
학습 내용을 Obsidian vault에 표준 형식으로 저장.

Usage:
    python scripts/save_to_obsidian.py \
      --topic "PyTorch FX Graph" \
      --content "Q&A 기록..." \
      --summary "핵심 요약..." \
      --category "AI_Study" \
      --vault-path "/path/to/vault" \
      --sources "file1.md,file2.md"
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# .env 지원
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in [_here.parent, _here.parent.parent.parent.parent]:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(_env)
            break
except ImportError:
    pass


# ────────────────────────── 유틸 ──────────────────────────

def safe_filename(text: str) -> str:
    """특수문자 → 언더바 (Obsidian 안전 파일명)"""
    return "".join(c if (c.isalnum() or c in " -") else "_" for c in text).strip()


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
    """Obsidian 노트 텍스트 생성"""
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
    safe_topic = safe_filename(topic)
    filepath   = unique_path(vault / f"{date_str}_{safe_topic}.md")

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
    args = parser.parse_args()

    sources = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources else None
    )

    try:
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
