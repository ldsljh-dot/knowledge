#!/usr/bin/env python3
import os
import argparse
import pathlib
import shutil
import sys

def main():
    parser = argparse.ArgumentParser(description="Delete knowledge topics")
    parser.add_argument("--agent-dir", required=True, help="Path to Agent directory")
    parser.add_argument("--targets", required=True, help="Comma-separated list of Category/Topic")
    parser.add_argument("--preview", action="store_true", help="Show what will be deleted")
    parser.add_argument("--delete", action="store_true", help="Execute deletion (folders)")
    parser.add_argument("--find-notes", action="store_true", help="Find related notes")
    parser.add_argument("--delete-notes", action="store_true", help="Delete related Obsidian notes")
    parser.add_argument("--vault-path", help="Path to vault root (required for relative path display)")
    args = parser.parse_args()

    agent_dir = pathlib.Path(args.agent_dir)
    if not agent_dir.exists():
        print(f"Error: Agent directory not found at {agent_dir}", file=sys.stderr)
        return

    vault_path = pathlib.Path(args.vault_path) if args.vault_path else agent_dir.parent
    
    selections = [s.strip() for s in args.targets.split(",") if s.strip()]
    
    # Identify items to process
    items_to_process = [] # List of path objects

    if args.find_notes or args.delete_notes:
        # Notes deletion logic
        keywords = []
        for sel in selections:
            parts = sel.split("/", 1)
            if len(parts) == 2:
                topic = parts[1]
                # Add topic keywords
                keywords.append(topic.lower())
                keywords.append(topic.replace("_", " ").lower())
            else:
                # Category only selection -> Maybe skip finding notes unless we scan all topics in category?
                # For safety, let's skip unless specific topic is targeted or implement category scanning later.
                pass
        
        candidates = []
        if keywords:
             for md in agent_dir.rglob("*.md"):
                # Exclude sources and rag folders
                if "sources" in md.parts or "rag" in md.parts:
                    continue
                name_lower = md.stem.lower()
                if any(kw in name_lower for kw in keywords):
                    candidates.append(md)
        
        items_to_process = candidates

    else:
        # Folder deletion logic (Phase 2-1, 3-1)
        for sel in selections:
            parts = sel.split("/", 1)
            if len(parts) == 1:
                # Category
                cat = parts[0]
                cat_dir = agent_dir / cat
                if cat_dir.exists():
                    for topic_dir in cat_dir.iterdir():
                        if topic_dir.is_dir():
                            for sub in ["sources", "rag"]:
                                p = topic_dir / sub
                                if p.exists():
                                    items_to_process.append(p)
            else:
                cat, topic = parts
                for sub in ["sources", "rag"]:
                    p = agent_dir / cat / topic / sub
                    if p.exists():
                        items_to_process.append(p)

    # Action
    if args.preview:
        if not items_to_process:
            if args.find_notes:
                print("  관련 노트를 찾지 못했습니다.")
            else:
                print("  삭제 대상이 없습니다.")
            return

        total_bytes = 0
        if not args.find_notes:
            print("\n⚠️  다음 항목이 삭제됩니다:\n")
        else:
            print("  발견된 관련 노트:")

        for p in items_to_process:
            try:
                rel = p.relative_to(vault_path)
            except ValueError:
                rel = p
            
            if p.is_dir():
                size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                count = sum(1 for f in p.rglob("*") if f.is_file())
                total_bytes += size
                print(f"  🗂  {rel}  ({count}개 파일, {size//1024}KB)")
            else:
                size = p.stat().st_size
                total_bytes += size
                print(f"  📄 {rel}")
        
        if not args.find_notes:
            print(f"\n  총 삭제 용량: {total_bytes//1024}KB")

    elif args.delete: # execute delete folders
        deleted_count = 0
        for p in items_to_process:
            if p.exists():
                try:
                    try:
                        rel = p.relative_to(vault_path)
                    except ValueError:
                        rel = p
                    shutil.rmtree(p)
                    print(f"  ✅ 삭제: {rel}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ 실패: {p} ({e})")
        print(f"\n  총 {deleted_count}개 폴더 삭제 완료")

    elif args.delete_notes: # execute delete notes
        deleted_count = 0
        for p in items_to_process:
            if p.exists():
                try:
                    try:
                        rel = p.relative_to(vault_path)
                    except ValueError:
                        rel = p
                    p.unlink()
                    print(f"  ✅ 삭제: {rel}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ 실패: {p} ({e})")
        if deleted_count > 0:
            print(f"\n  총 {deleted_count}개 노트 삭제 완료")
        else:
            print("  삭제된 노트 없음.")

if __name__ == "__main__":
    main()
