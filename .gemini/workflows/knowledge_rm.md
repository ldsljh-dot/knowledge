---
description: 수집된 RAG 토픽의 sources/manifest/노트를 선택적으로 삭제합니다
trigger: /knowledge_rm
---

# Knowledge Remove Workflow

수집된 지식(sources, RAG manifest, Obsidian 노트)을 토픽 단위로 삭제합니다.

모든 bash 명령은 프로젝트 루트(`/home/jh/projects/knowledge`)에서 실행합니다.

---

## Phase 1: 삭제 가능한 토픽 목록 표시

### Step 1-1: 환경변수 로드 및 목록 출력

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

AGENT_DIR="$OBSIDIAN_VAULT_PATH/Agent"

python3 << 'PYEOF'
import json, os, pathlib

VAULT = pathlib.Path(os.environ["OBSIDIAN_VAULT_PATH"])
AGENT = VAULT / "Agent"

def fmt_size(b):
    if b >= 1_048_576: return f"{b/1_048_576:.1f}MB"
    if b >= 1024:      return f"{b/1024:.0f}KB"
    return f"{b}B"

print("=" * 65)
print("  🗑  Knowledge Remove — 삭제할 토픽을 선택하세요")
print("=" * 65)
print(f"  {'식별자 (Category/SafeTopic)':<40} {'sources':^8} {'rag':^5} {'크기':>7}")
print(f"  {'-'*40}  {'-'*8}  {'-'*5}  {'-'*7}")

entries = []
for cat_dir in sorted(AGENT.iterdir()):
    if not cat_dir.is_dir():
        continue
    cat = cat_dir.name

    # sources 목록
    sources_root = cat_dir / "sources"
    rag_root     = cat_dir / "rag"

    # sources와 rag 토픽 합집합
    topic_set = set()
    if sources_root.exists():
        topic_set |= {d.name for d in sources_root.iterdir() if d.is_dir()}
    if rag_root.exists():
        topic_set |= {d.name for d in rag_root.iterdir() if d.is_dir()}

    for topic in sorted(topic_set):
        src_dir = sources_root / topic
        rag_dir = rag_root / topic

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
PYEOF
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

python -c "
import json, os, pathlib
VAULT = pathlib.Path(os.environ['OBSIDIAN_VAULT_PATH'])
AGENT = VAULT / 'Agent'
def fmt_size(b):
    if b >= 1_048_576: return f'{b/1_048_576:.1f}MB'
    if b >= 1024:      return f'{b/1024:.0f}KB'
    return f'{b}B'
print('=' * 65)
print('  Knowledge Remove — 삭제할 토픽을 선택하세요')
print('=' * 65)
for cat_dir in sorted(AGENT.iterdir()):
    if not cat_dir.is_dir(): continue
    cat = cat_dir.name
    sources_root = cat_dir / 'sources'
    rag_root = cat_dir / 'rag'
    topic_set = set()
    if sources_root.exists(): topic_set |= {d.name for d in sources_root.iterdir() if d.is_dir()}
    if rag_root.exists():     topic_set |= {d.name for d in rag_root.iterdir() if d.is_dir()}
    for topic in sorted(topic_set):
        src_dir = sources_root / topic
        rag_dir = rag_root / topic
        src_files = list(src_dir.glob('*.md')) if src_dir.exists() else []
        src_size = sum(f.stat().st_size for f in src_files)
        has_rag = (rag_dir / 'manifest.json').exists()
        identifier = f'{cat}/{topic}'
        print(f'  {identifier:<40}  {len(src_files)}파일  {\"V\" if has_rag else \"X\"}  {fmt_size(src_size)}')
"
```

</tab>
</tabs>

---

### Step 1-2: 삭제 대상 선택

사용자에게 질문합니다:

> **"어떤 토픽을 삭제하시겠습니까?**
> 식별자(`Category/SafeTopic`)를 입력하세요. 쉼표로 구분하면 복수 선택 가능합니다."

| 입력 예시 | 처리 |
|-----------|------|
| `Security/동형암호기술` | 해당 토픽 단건 삭제 |
| `AI_Study/MemoryLLM_Research, DB_Research/PolarStore_Research` | 복수 토픽 삭제 |
| `AI_Study` | 해당 카테고리 전체 삭제 |

---

## Phase 2: 삭제 범위 확인 및 사용자 확인

### Step 2-1: 삭제될 항목 미리보기

선택한 토픽에 대해 실제 삭제될 항목을 나열합니다:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 << 'PYEOF'
import os, pathlib, json

VAULT = pathlib.Path(os.environ["OBSIDIAN_VAULT_PATH"])
AGENT = VAULT / "Agent"

# {선택한_식별자_목록} 을 실제 식별자 리스트로 교체
selections = "{선택한_식별자_목록}".split(",")

total_bytes = 0
items_to_delete = []

for sel in selections:
    sel = sel.strip()
    parts = sel.split("/", 1)
    if len(parts) == 1:
        # 카테고리 전체
        cat = parts[0]
        cat_dir = AGENT / cat
        for sub in ["sources", "rag"]:
            p = cat_dir / sub
            if p.exists():
                items_to_delete.append(("dir", p))
    else:
        cat, topic = parts
        src_dir = AGENT / cat / "sources" / topic
        rag_dir = AGENT / cat / "rag" / topic
        if src_dir.exists(): items_to_delete.append(("dir", src_dir))
        if rag_dir.exists(): items_to_delete.append(("dir", rag_dir))

print("\n⚠️  다음 항목이 삭제됩니다:\n")
for kind, p in items_to_delete:
    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    total_bytes += size
    count = sum(1 for f in p.rglob("*") if f.is_file())
    rel = p.relative_to(VAULT)
    print(f"  🗂  {rel}  ({count}개 파일, {size//1024}KB)")

print(f"\n  총 삭제 용량: {total_bytes//1024}KB")
PYEOF
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python -c "
import os, pathlib
VAULT = pathlib.Path(os.environ['OBSIDIAN_VAULT_PATH'])
AGENT = VAULT / 'Agent'
selections = '{선택한_식별자_목록}'.split(',')
total_bytes = 0
items = []
for sel in selections:
    sel = sel.strip()
    parts = sel.split('/', 1)
    if len(parts) == 1:
        cat_dir = AGENT / parts[0]
        for sub in ['sources', 'rag']:
            p = cat_dir / sub
            if p.exists(): items.append(p)
    else:
        cat, topic = parts
        for sub in ['sources', 'rag']:
            p = AGENT / cat / sub / topic
            if p.exists(): items.append(p)
print('다음 항목이 삭제됩니다:')
for p in items:
    size = sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
    count = sum(1 for f in p.rglob('*') if f.is_file())
    total_bytes += size
    print(f'  {p.relative_to(VAULT)}  ({count}파일, {size//1024}KB)')
print(f'총 삭제 용량: {total_bytes//1024}KB')
"
```

</tab>
</tabs>

### Step 2-2: 삭제 전 최종 확인

사용자에게 질문합니다:

> **"위 항목을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.**
> `y` 입력 시 삭제 진행 / `n` 입력 시 취소"

`n` 또는 입력 없으면 → 취소 메시지 출력 후 종료

---

## Phase 3: 삭제 실행

### Step 3-1: sources 및 RAG manifest 삭제

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 << 'PYEOF'
import os, pathlib, shutil, json

VAULT = pathlib.Path(os.environ["OBSIDIAN_VAULT_PATH"])
AGENT = VAULT / "Agent"

selections = "{선택한_식별자_목록}".split(",")

deleted = []

for sel in selections:
    sel = sel.strip()
    parts = sel.split("/", 1)

    if len(parts) == 1:
        # 카테고리 전체
        cat = parts[0]
        for sub in ["sources", "rag"]:
            p = AGENT / cat / sub
            if p.exists():
                shutil.rmtree(p)
                deleted.append(str(p.relative_to(VAULT)))
                print(f"  ✅ 삭제: {p.relative_to(VAULT)}")
    else:
        cat, topic = parts
        for sub in ["sources", "rag"]:
            p = AGENT / cat / sub / topic
            if p.exists():
                shutil.rmtree(p)
                deleted.append(str(p.relative_to(VAULT)))
                print(f"  ✅ 삭제: {p.relative_to(VAULT)}")

print(f"\n  총 {len(deleted)}개 폴더 삭제 완료")
PYEOF
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python -c "
import os, pathlib, shutil
VAULT = pathlib.Path(os.environ['OBSIDIAN_VAULT_PATH'])
AGENT = VAULT / 'Agent'
selections = '{선택한_식별자_목록}'.split(',')
deleted = []
for sel in selections:
    sel = sel.strip()
    parts = sel.split('/', 1)
    if len(parts) == 1:
        for sub in ['sources', 'rag']:
            p = AGENT / parts[0] / sub
            if p.exists():
                shutil.rmtree(p)
                deleted.append(str(p.relative_to(VAULT)))
                print(f'  삭제: {p.relative_to(VAULT)}')
    else:
        cat, topic = parts
        for sub in ['sources', 'rag']:
            p = AGENT / cat / sub / topic
            if p.exists():
                shutil.rmtree(p)
                deleted.append(str(p.relative_to(VAULT)))
                print(f'  삭제: {p.relative_to(VAULT)}')
print(f'총 {len(deleted)}개 폴더 삭제 완료')
"
```

</tab>
</tabs>

### Step 3-2: 관련 Obsidian 노트 삭제 (선택)

삭제 후 사용자에게 추가로 질문합니다:

> **"관련 Obsidian 노트도 삭제하시겠습니까?**
> 토픽명을 포함하는 `.md` 파일을 검색합니다. (`y` / `n`)"

`y` 입력 시:

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
python3 << 'PYEOF'
import os, pathlib

VAULT  = pathlib.Path(os.environ["OBSIDIAN_VAULT_PATH"])
AGENT  = VAULT / "Agent"

# 토픽명 키워드 추출
selections = "{선택한_식별자_목록}".split(",")
keywords = []
for sel in selections:
    sel = sel.strip()
    topic = sel.split("/", 1)[-1]          # Category/Topic → Topic
    keywords.append(topic.replace("_", " ").lower())
    keywords.append(topic.lower())

# Agent/ 루트의 .md 파일 중 키워드 포함 파일 탐색
candidates = []
for md in AGENT.glob("*.md"):
    name_lower = md.stem.lower()
    if any(kw in name_lower for kw in keywords):
        candidates.append(md)

# 카테고리 하위 노트도 탐색
for md in AGENT.glob("*/*.md"):
    if md.parent.name in ("sources", "rag"):
        continue
    name_lower = md.stem.lower()
    if any(kw in name_lower for kw in keywords):
        candidates.append(md)

if not candidates:
    print("  관련 노트를 찾지 못했습니다.")
else:
    print("  발견된 관련 노트:")
    for md in candidates:
        print(f"    - {md.relative_to(VAULT)}")
    print()
    # 실제 삭제는 사용자 재확인 후 진행
    # (워크플로우 실행 중 사용자에게 한 번 더 확인)
    confirm = input("  위 노트를 삭제하시겠습니까? (y/n): ").strip().lower()
    if confirm == "y":
        for md in candidates:
            md.unlink()
            print(f"  ✅ 삭제: {md.relative_to(VAULT)}")
    else:
        print("  노트 삭제를 취소했습니다.")
PYEOF
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
# 관련 노트는 수동 확인 후 삭제
# Agent/ 폴더에서 토픽명 포함 .md 파일 검색
$keyword = "{토픽명_키워드}"
Get-ChildItem -Path "$env:OBSIDIAN_VAULT_PATH/Agent" -Filter "*.md" -Recurse |
  Where-Object { $_.Name -like "*$keyword*" } |
  Select-Object FullName
```

</tab>
</tabs>

---

## Phase 4: 완료 메시지

```
✅ 삭제 완료!

🗑  삭제된 항목:
  - Agent/{Category}/sources/{topic}/  (N개 파일)
  - Agent/{Category}/rag/{topic}/      (manifest.json)

💡 같은 주제를 다시 수집하려면:
   /knowledge_tutor → '{topic}' 입력

💡 현재 남은 토픽 목록:
   /knowledge_dashboard
```

---

## Notes

- **sources와 rag 둘 다 삭제**: 토픽을 완전히 제거할 때
- **rag만 삭제 후 재생성**: `create_manifest.py --topic ... --sources-dir ...` 재실행
- **카테고리 폴더 자체는 삭제하지 않음**: sources/rag 하위만 삭제
- **Obsidian 노트**: 별도 확인 후 선택 삭제 (자동 삭제 안 함)
