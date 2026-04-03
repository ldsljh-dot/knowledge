---
created: 2026-04-01
updated: 2026-04-01
description: Obsidian vault 의미 검색 인덱스를 증분 갱신합니다
trigger: /vault_reindex
---

# Vault Reindex Workflow

Obsidian vault의 토픽 폴더(`sources/` 또는 `rag/` 포함 폴더)를 스캔하여
Qdrant 벡터 인덱스(`obsidian_vault_index` 컬렉션)를 갱신합니다.

**동작 방식:**
- **기본 (인수 없음):** incremental — sources/ 파일 mtime이 indexed_at보다 최신인 폴더만 재임베딩
- **`--full`:** 전체 재빌드 — 모든 폴더 재임베딩
- **`--dry-run`:** 실행 없이 인덱싱 대상 폴더 목록만 출력

> 💡 `/vault_reindex`만 입력 시 기본(incremental)으로 실행합니다.
> `/vault_reindex --full` 또는 `/vault_reindex --dry-run`으로 옵션 지정 가능합니다.
> 사용자가 옵션을 지정하지 않았으면 인수 없이 기본 실행합니다.

---

## Step 1: 환경 확인

<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi

echo "OBSIDIAN_VAULT_PATH: $OBSIDIAN_VAULT_PATH"
if [ -z "$OBSIDIAN_VAULT_PATH" ]; then
  echo "❌ OBSIDIAN_VAULT_PATH가 설정되지 않았습니다. .env 파일을 확인하세요."
  exit 1
fi
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
if (-not $env:OBSIDIAN_VAULT_PATH) {
    Write-Host "❌ OBSIDIAN_VAULT_PATH가 설정되지 않았습니다. .env 파일을 확인하세요."
    exit 1
}
```

</tab>
</tabs>

---

## Step 2: 인덱스 갱신

사용자가 지정한 옵션에 따라 아래 중 하나를 실행합니다.

**기본 (incremental):** 옵션 없이 실행
<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py"
```

</tab>
</tabs>

**전체 재빌드:** 사용자가 `--full` 지정 시
<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py" --full
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py" --full
```

</tab>
</tabs>

**대상 미리 확인:** 사용자가 `--dry-run` 지정 시
<tabs>
<tab label="Linux/macOS (Bash)">

```bash
if [ -f .env ]; then set -a; source .env; set +a; fi
if [ -z "$AGENT_ROOT" ]; then export AGENT_ROOT=$(pwd); fi
python3 "$AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py" --dry-run
```

</tab>
<tab label="Windows (PowerShell)">

```powershell
python "$env:AGENT_ROOT/.gemini/skills/vault-index/scripts/vault_index.py" --dry-run
```

</tab>
</tabs>

결과 예시:
```
[INFO] Vault: /Users/xxx/Obsidian
[INFO] 발견된 토픽 폴더: 32개
[INFO] 스킵 (변경 없음): 28개
[INFO] 인덱싱 대상: 4개

✅ 완료!
   신규: 3개 | 업데이트: 1개 | 삭제: 0개 | 스킵: 28개
   총 인덱스: 32개 폴더
```

스크립트 실패 시(`exit code != 0`):
- `qdrant-client` 또는 `sentence-transformers` 미설치 → `pip3 install qdrant-client sentence-transformers` 실행 후 재시도
- `OBSIDIAN_VAULT_PATH` 미설정 → Step 1 재확인

---

## Step 3: 완료 메시지

인덱스 갱신 결과를 사용자에게 보고합니다.

**인덱스 효과:**
- `/knowledge_tutor` Step 1-1: 주제 입력 후 vault_search.py가 이 인덱스로 유사 폴더를 찾아 저장 위치를 추천합니다
- `/knowledge_query` Step 0-1: 질문 전 관련 기존 지식 폴더를 이 인덱스에서 탐색합니다
- 새 토픽이 추가될 때마다 `/vault_reindex` 또는 knowledge_tutor Phase 3의 자동 갱신으로 인덱스를 최신 상태로 유지합니다
