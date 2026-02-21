#!/usr/bin/env python3
import os
import argparse
import pathlib
import sys

def fmt_size(b):
    if b >= 1_048_576: return f"{b/1_048_576:.1f}MB"
    if b >= 1024:      return f"{b/1024:.0f}KB"
    return f"{b}B"

def main():
    parser = argparse.ArgumentParser(description="List topics for knowledge removal")
    parser.add_argument("--agent-dir", required=True, help="Path to Agent directory")
    args = parser.parse_args()
    
    agent_dir = pathlib.Path(args.agent_dir)
    if not agent_dir.exists():
        print(f"Error: Agent directory not found at {agent_dir}", file=sys.stderr)
        return

    print("=" * 65)
    print("  🗑  Knowledge Remove — 삭제할 토픽을 선택하세요")
    print("=" * 65)
    print(f"  {'식별자 (Category/SafeTopic)':<40} {'sources':^8} {'rag':^5} {'크기':>7}")
    print(f"  {'-'*40}  {'-'*8}  {'-'*5}  {'-'*7}")

    entries = []
    for cat_dir in sorted(agent_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name

        topic_set = set()
        for item in cat_dir.iterdir():
            if item.is_dir():
                if (item / "sources").exists() or (item / "rag").exists():
                    topic_set.add(item.name)

        for topic in sorted(topic_set):
            src_dir = cat_dir / topic / "sources"
            rag_dir = cat_dir / topic / "rag"

            src_files = list(src_dir.glob("*.md")) if src_dir.exists() else []
            src_size  = sum(f.stat().st_size for f in src_files)
            has_rag   = (rag_dir / "manifest.json").exists()

            identifier = f"{cat}/{topic}"
            src_label  = f"{len(src_files)}파일" if src_files else "없음"
            rag_label  = "✓" if has_rag else "✗"

            entries.append(identifier)
            print(f"  {identifier:<40}  {src_label:^8}  {rag_label:^5}  {fmt_size(src_size):>7}")

    print()
    print(f"  총 {len(entries)}개 토픽")
    print("=" * 65)

if __name__ == "__main__":
    main()
