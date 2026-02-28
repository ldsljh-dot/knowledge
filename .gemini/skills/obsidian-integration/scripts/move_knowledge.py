#!/usr/bin/env python3
"""
Move Knowledge Script
Moves a knowledge topic (sources, rag, and note) to a new category or renames it.

Usage:
    python move_knowledge.py \
      --source "Category/Topic" \
      --dest-category "NewCategory" \
      --dest-topic "NewTopicName" \
      --vault-path "/path/to/vault"
"""

import os
import sys
import shutil
import argparse
import json
import re
from pathlib import Path
from typing import Optional

# common.utils 임포트를 위해 sys.path 설정
_here = Path(__file__).resolve()
_skills_dir = _here.parent.parent.parent
if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

from common.utils import load_env, safe_filename

# .env 자동 로드
load_env()

def find_note(category_dir: Path, topic: str) -> Optional[Path]:
    """Find the note file, handling potential date prefixes."""
    if not category_dir.exists():
        return None

    # 1. Try exact match (safe_filename applied)
    safe = safe_filename(topic, max_length=60)
    exact = category_dir / f"{safe}.md"
    if exact.exists():
        return exact

    # 2. Try date-prefixed match (YYYY-MM-DD_safe_topic.md)
    # The topic in the filename is already safe_filename'd
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_" + re.escape(safe) + r"\.md$")
    
    for f in category_dir.iterdir():
        if f.is_file() and pattern.match(f.name):
            return f
            
    return None

def update_manifest(rag_dir: Path, old_cat: str, old_topic: str, 
                   new_cat: str, new_topic: str, vault_path: Path):
    """Update paths and metadata in manifest.json"""
    manifest_path = rag_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"⚠️  Manifest not found at {manifest_path}")
        return

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to read manifest: {e}")
        return

    # Helper to replace path prefixes
    # Paths in manifest are relative to vault_path (e.g., Agent/OldCat/OldTopic/sources)
    old_safe_topic = safe_filename(old_topic, max_length=60)
    new_safe_topic = safe_filename(new_topic, max_length=60)
    
    old_rel_base = f"Agent/{old_cat}/{old_safe_topic}"
    new_rel_base = f"Agent/{new_cat}/{new_safe_topic}"
    
    # Update Metadata
    data['topic'] = new_topic
    data['safe_topic'] = new_safe_topic
    data['category'] = new_cat
    data['updated'] = get_now_str()

    # Update source_dirs
    if 'source_dirs' in data:
        new_source_dirs = []
        for p in data['source_dirs']:
            if p.startswith(old_rel_base):
                new_source_dirs.append(p.replace(old_rel_base, new_rel_base, 1))
            else:
                new_source_dirs.append(p)
        data['source_dirs'] = new_source_dirs

    # Update files paths
    if 'files' in data:
        for file_info in data['files']:
            if 'path' in file_info and file_info['path'].startswith(old_rel_base):
                file_info['path'] = file_info['path'].replace(old_rel_base, new_rel_base, 1)

    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ Manifest updated.")

def update_note_content(note_path: Path, new_cat: str, new_topic: str):
    """Update frontmatter category and title in the markdown note."""
    if not note_path.exists():
        return

    content = note_path.read_text(encoding="utf-8")
    
    # Update Category in Frontmatter
    # category: OldCat -> category: NewCat
    # Use \g<1> for backreference in re.sub replacement string
    content = re.sub(r"^(category:\s*).*$", f"\\g<1>{new_cat}", content, flags=re.MULTILINE)
    
    # Update Title if changed
    # # 📚 OldTopic -> # 📚 NewTopic
    if new_topic:
        content = re.sub(r"^# 📚 .*$", f"# 📚 {new_topic}", content, flags=re.MULTILINE)

    note_path.write_text(content, encoding="utf-8")
    print("✅ Note content updated.")

def get_now_str():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")

def main():
    parser = argparse.ArgumentParser(description="Move Knowledge Topic")
    parser.add_argument("--source", required=True, help="Source 'Category/Topic'")
    parser.add_argument("--dest-category", required=True, help="Destination Category")
    parser.add_argument("--dest-topic", help="Destination Topic Name (optional, defaults to source name)")
    parser.add_argument("--vault-path", help="Obsidian Vault Root")
    parser.add_argument("--agent-dir", help="Agent Directory (optional override)")

    args = parser.parse_args()

    # Setup Paths
    vault_path = Path(args.vault_path or os.environ.get("OBSIDIAN_VAULT_PATH", ""))
    if not vault_path.exists():
        print(f"❌ Vault path not found: {vault_path}", file=sys.stderr)
        return 1
        
    agent_dir = Path(args.agent_dir) if args.agent_dir else vault_path / "Agent"
    
    # Parse Source
    try:
        src_cat, src_topic = args.source.split("/", 1)
    except ValueError:
        print("❌ Source must be in 'Category/Topic' format", file=sys.stderr)
        return 1
        
    dest_cat = args.dest_category
    dest_topic = args.dest_topic if args.dest_topic else src_topic
    
    src_safe = safe_filename(src_topic, max_length=60)
    dest_safe = safe_filename(dest_topic, max_length=60)
    
    # Define Source Locations
    src_folder = agent_dir / src_cat / src_safe
    src_note = find_note(agent_dir / src_cat, src_topic)
    
    # Define Dest Locations
    dest_folder_parent = agent_dir / dest_cat
    dest_folder = dest_folder_parent / dest_safe
    
    # Determine Dest Note Path
    dest_note = None
    if src_note:
        if src_note.name.startswith(src_safe + ".md"):
             dest_note = dest_folder_parent / f"{dest_safe}.md"
        else:
            # Handle date prefix
            prefix = src_note.name.split(src_safe)[0] 
            dest_note = dest_folder_parent / f"{prefix}{dest_safe}.md"

    # Validation
    if not src_folder.exists() and not src_note:
        print(f"❌ Source not found: {args.source}", file=sys.stderr)
        return 1
        
    if dest_folder.exists():
        print(f"❌ Destination folder already exists: {dest_folder}", file=sys.stderr)
        return 1
        
    if dest_note and dest_note.exists():
        print(f"❌ Destination note already exists: {dest_note}", file=sys.stderr)
        return 1

    print(f"🚀 Moving '{src_cat}/{src_topic}' -> '{dest_cat}/{dest_topic}'")

    # Create Dest Category if needed
    dest_folder_parent.mkdir(parents=True, exist_ok=True)

    # 1. Move Folder (sources + rag)
    if src_folder.exists():
        shutil.move(str(src_folder), str(dest_folder))
        print(f"✅ Moved folder: {src_folder.name} -> {dest_folder}")
        
        # Update Manifest
        update_manifest(dest_folder / "rag", src_cat, src_topic, dest_cat, dest_topic, vault_path)

    # 2. Move Note
    if src_note:
        shutil.move(str(src_note), str(dest_note))
        print(f"✅ Moved note: {src_note.name} -> {dest_note.name}")
        
        # Update Note Content
        update_note_content(dest_note, dest_cat, dest_topic)

    print("\n✨ Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
