#!/usr/bin/env python3
import os
import argparse
import pathlib
import sys

# common.utils 임포트를 위해 sys.path 설정
_here = pathlib.Path(__file__).resolve()
_skills_dir = _here.parent.parent.parent
if str(_skills_dir) not in sys.path:
    sys.path.insert(0, str(_skills_dir))

from common.utils import load_env

# .env 자동 로드
load_env()

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
    
    # rglob으로 모든 manifest.json을 찾아 토픽 폴더를 식별
    # 단, .obsidian 같은 숨김 폴더나 플러그인 폴더는 제외
    for manifest_path in sorted(agent_dir.rglob("rag/manifest.json")):
        if ".obsidian" in manifest_path.parts:
            continue
            
        # 경로에서 정보 추출: .../Vault/Category/[SubCategory]/.../Topic/rag/manifest.json
        rag_dir = manifest_path.parent
        topic_dir = rag_dir.parent
        src_dir = topic_dir / "sources"
        
        # Vault 루트를 기준으로 한 상대 경로에서 "Category" 와 "Topic" 식별자를 만듦
        try:
            rel_topic_dir = topic_dir.relative_to(agent_dir)
            identifier = str(rel_topic_dir).replace("\\", "/")
        except ValueError:
            continue
            
        src_files = list(src_dir.glob("*.md")) if src_dir.exists() else []
        src_size  = sum(f.stat().st_size for f in src_files)
        has_rag   = True

        src_label  = f"{len(src_files)}파일" if src_files else "없음"
        rag_label  = "✓"

        entries.append(identifier)
        print(f"  {identifier:<40}  {src_label:^8}  {rag_label:^5}  {fmt_size(src_size):>7}")

    print()
    print(f"  총 {len(entries)}개 토픽")
    print("=" * 65)

if __name__ == "__main__":
    main()
