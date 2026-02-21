#!/usr/bin/env python3
"""
generate_dashboard.py — Knowledge Agent 전체 현황 대시보드 생성

폴더 구조 가정:
    {agent_dir}/{Category}/rag/{safe_topic}/manifest.json

사용법:
    python generate_dashboard.py \
      --agent-dir "$OBSIDIAN_VAULT_PATH/Agent" \
      --output "$OBSIDIAN_VAULT_PATH/Agent/_Dashboard.md"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# common.utils 임포트를 위해 sys.path 설정
_here = Path(__file__).resolve()
_skills_dir = _here.parent.parent.parent
if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

from common.utils import load_env

# .env 자동 로드
load_env()

def load_manifests(agent_dir: Path) -> dict[str, list[dict]]:
    """agent_dir/{Category}/rag/{topic}/manifest.json 을 카테고리별로 수집"""
    categories: dict[str, list[dict]] = {}

    for manifest_path in sorted(agent_dir.glob("*/*/rag/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # 경로에서 카테고리 추출: parts[0] = Category
        rel = manifest_path.relative_to(agent_dir)
        category = rel.parts[0]

        manifest["_category"] = category
        categories.setdefault(category, []).append(manifest)

    return categories


def generate_dashboard(agent_dir: Path) -> str:
    categories = load_manifests(agent_dir)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    now_iso = datetime.now().isoformat(timespec="seconds")

    total_topics = sum(len(v) for v in categories.values())
    total_files  = sum(m.get("file_count", 0) for v in categories.values() for m in v)
    total_bytes  = sum(m.get("total_bytes", 0) for v in categories.values() for m in v)

    lines = [
        "---",
        "tags: [dashboard, agent]",
        f"updated: {now_iso}",
        "---",
        "",
        "# 🧠 Knowledge Agent Dashboard",
        "",
        f"> 마지막 업데이트: {now_str}",
        "",
        "## 📊 전체 통계",
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| 카테고리 | {len(categories)}개 |",
        f"| 토픽 | {total_topics}개 |",
        f"| 수집 파일 | {total_files}개 |",
        f"| 총 용량 | {total_bytes // 1024:,} KB |",
        "",
        "---",
        "",
    ]

    if not categories:
        lines.append("> ℹ️ 수집된 데이터가 없습니다. `/knowledge_tutor`로 학습을 시작하세요.")
        lines.append("")
        return "\n".join(lines)

    for category in sorted(categories.keys()):
        manifests = sorted(
            categories[category],
            key=lambda m: m.get("updated", ""),
            reverse=True,
        )
        cat_files = sum(m.get("file_count", 0) for m in manifests)
        cat_kb    = sum(m.get("total_bytes", 0) for m in manifests) // 1024

        lines.append(
            f"## 📁 {category}"
            f"  `{len(manifests)}토픽 · {cat_files}파일 · {cat_kb} KB`"
        )
        lines.append("")
        lines.append("| 토픽 | 식별자 | 파일 | 용량 | 업데이트 |")
        lines.append("|------|--------|------|------|---------|")

        for m in manifests:
            topic      = m.get("topic", "")
            safe_topic = m.get("safe_topic", "")
            identifier = f"{category}/{safe_topic}"
            fc         = m.get("file_count", 0)
            kb         = m.get("total_bytes", 0) // 1024
            updated    = m.get("updated", "")[:10]
            lines.append(
                f"| {topic} | `{identifier}` | {fc} | {kb} KB | {updated} |"
            )

        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Knowledge Agent 대시보드 생성")
    parser.add_argument("--agent-dir", required=True, help="Agent 폴더 절대경로")
    parser.add_argument(
        "--output", default=None,
        help="출력 파일 경로 (기본: {agent_dir}/_Dashboard.md)",
    )
    args = parser.parse_args()

    agent_dir = Path(args.agent_dir)
    if not agent_dir.exists():
        print(f"[ERROR] Agent 폴더 없음: {agent_dir}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else agent_dir / "_Dashboard.md"
    content = generate_dashboard(agent_dir)
    output_path.write_text(content, encoding="utf-8")

    print(f"✅ 대시보드 저장: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
