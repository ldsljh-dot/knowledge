---
description: 수집된 RAG 토픽 현황을 카테고리별로 한눈에 보여줍니다
trigger: /knowledge_dashboard
---

# Knowledge Dashboard Workflow

수집된 RAG 토픽 현황을 카테고리별로 한눈에 보여줍니다.

모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.

---

## Step 1: 환경변수 로드

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*[^#\s]+=.*$") {
            $name, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
        }
    }
}
if (-not $env:AGENT_ROOT) { $env:AGENT_ROOT = Get-Location }
```

</tab>
</tabs>

## Step 2: 대시보드 출력

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 << 'PYEOF'
import json, pathlib, datetime, os

VAULT = pathlib.Path(os.environ["OBSIDIAN_VAULT_PATH"])
AGENT = VAULT / "Agent"

def fmt_size(b):
    if b >= 1_048_576:
        return f"{b/1_048_576:.1f}MB"
    elif b >= 1024:
        return f"{b/1024:.0f}KB"
    return f"{b}B"

def count_sources(source_dirs):
    """source_dirs 목록에서 실제 .md 파일 수와 총 크기를 반환"""
    total_files, total_bytes = 0, 0
    for d in source_dirs:
        p = VAULT / d if not d.startswith("/") else pathlib.Path(d)
        if p.exists():
            for f in p.glob("*.md"):
                total_files += 1
                total_bytes += f.stat().st_size
    return total_files, total_bytes

# 카테고리별 manifest 수집
categories = {}
manifests = sorted(AGENT.glob("*/rag/*/manifest.json"))

for mpath in manifests:
    cat = mpath.parts[-4]   # Agent/{cat}/rag/{topic}/manifest.json
    data = json.loads(mpath.read_text())
    topic = data.get("topic", mpath.parent.name)
    updated = data.get("updated", data.get("created", ""))[:10]
    source_dirs = data.get("source_dirs", [])
    file_count, total_bytes = count_sources(source_dirs)

    if cat not in categories:
        categories[cat] = []
    categories[cat].append({
        "topic": topic,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "updated": updated,
        "has_sources": file_count > 0,
    })

# 전체 합계
all_topics = [t for topics in categories.values() for t in topics]
grand_files = sum(t["file_count"] for t in all_topics)
grand_bytes = sum(t["total_bytes"] for t in all_topics)

print("=" * 60)
print("  📚 Knowledge Dashboard")
print(f"  {datetime.date.today()}  |  카테고리 {len(categories)}개  |  토픽 {len(all_topics)}개  |  {fmt_size(grand_bytes)}")
print("=" * 60)

if not categories:
    print("\n  등록된 RAG가 없습니다. /knowledge_tutor를 먼저 실행하세요.")
else:
    for cat in sorted(categories):
        topics = categories[cat]
        cat_bytes = sum(t["total_bytes"] for t in topics)
        print(f"\n  🗂  {cat}  ({len(topics)}개 토픽 / {fmt_size(cat_bytes)})")
        for t in sorted(topics, key=lambda x: x["topic"]):
            status = "✓" if t["has_sources"] else "⚠"
            print(f"    {status} {t['topic']}")
            print(f"       파일 {t['file_count']}개  /  {fmt_size(t['total_bytes'])}  /  {t['updated']}")

print()
print("=" * 60)
print(f"  합계: 파일 {grand_files}개  /  {fmt_size(grand_bytes)}")
print("=" * 60)
print()
print("  [명령어]")
print("  /knowledge_query   → 기존 자료로 Q&A")
print("  /knowledge_tutor   → 새 주제 수집 및 튜터링")
print()
print("  ⚠  표시 토픽: sources 파일 없음 (rag manifest만 존재)")
PYEOF
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python -c "
import json, pathlib, datetime, os

VAULT = pathlib.Path(os.environ['OBSIDIAN_VAULT_PATH'])
AGENT = VAULT / 'Agent'

def fmt_size(b):
    if b >= 1_048_576:
        return f'{b/1_048_576:.1f}MB'
    elif b >= 1024:
        return f'{b/1024:.0f}KB'
    return f'{b}B'

def count_sources(source_dirs):
    total_files, total_bytes = 0, 0
    for d in source_dirs:
        p = VAULT / d if not d.startswith('/') else pathlib.Path(d)
        if p.exists():
            for f in p.glob('*.md'):
                total_files += 1
                total_bytes += f.stat().st_size
    return total_files, total_bytes

categories = {}
manifests = sorted(AGENT.glob('*/rag/*/manifest.json'))
for mpath in manifests:
    cat = mpath.parts[-4]
    data = json.loads(mpath.read_text())
    topic = data.get('topic', mpath.parent.name)
    updated = data.get('updated', data.get('created', ''))[:10]
    source_dirs = data.get('source_dirs', [])
    file_count, total_bytes = count_sources(source_dirs)
    if cat not in categories:
        categories[cat] = []
    categories[cat].append({'topic': topic, 'file_count': file_count, 'total_bytes': total_bytes, 'updated': updated, 'has_sources': file_count > 0})

all_topics = [t for topics in categories.values() for t in topics]
grand_files = sum(t['file_count'] for t in all_topics)
grand_bytes = sum(t['total_bytes'] for t in all_topics)
print('=' * 60)
print('  Knowledge Dashboard')
print(f'  {datetime.date.today()}  |  카테고리 {len(categories)}개  |  토픽 {len(all_topics)}개  |  {fmt_size(grand_bytes)}')
print('=' * 60)
for cat in sorted(categories):
    topics = categories[cat]
    cat_bytes = sum(t['total_bytes'] for t in topics)
    print(f'  {cat}  ({len(topics)}개 토픽 / {fmt_size(cat_bytes)})')
    for t in sorted(topics, key=lambda x: x['topic']):
        status = 'V' if t['has_sources'] else '!'
        print(f'    {status} {t[\"topic\"]}')
        print(f'       파일 {t[\"file_count\"]}개  /  {fmt_size(t[\"total_bytes\"])}  /  {t[\"updated\"]}')
print(f'  합계: 파일 {grand_files}개  /  {fmt_size(grand_bytes)}')
"
```

</tab>
</tabs>

출력 예시:
```
============================================================
  📚 Knowledge Dashboard
  2026-02-21  |  카테고리 3개  |  토픽 5개  |  2.2MB
============================================================

  🗂  AI_Study  (3개 토픽 / 1.8MB)
    ✓ MemoryLLM Research
       파일 3개  /  124KB  /  2026-02-21
    ✓ NVBit H100 DSM TMA profiling and address detection
       파일 14개  /  1.3MB  /  2026-02-19
    ✓ NVIDIA H100 GPU Cache structure and principles
       파일 9개  /  297KB  /  2026-02-19

  🗂  DB_Research  (1개 토픽 / 354KB)
    ✓ PolarStore Research
       파일 6개  /  354KB  /  2026-02-21
  ...
```
