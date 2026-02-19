---
description: knowledge_tutor로 수집된 RAG manifest를 기반으로 기존 자료에서 즉시 질문-답변하는 워크플로우
trigger: /knowledge_query
---

# Knowledge Query Workflow

`knowledge_tutor`로 수집·생성된 `/rag/{topic}/manifest.json`을 조회하여
BM25 RAG 검색으로 사용자 질문에 즉시 답변합니다.

- 새로운 웹 검색 없이 기존 수집 자료만 활용 (빠름)
- 질문마다 관련 청크만 추출 → 토큰 절감 (~94%)
- 여러 토픽을 동시에 또는 선택적으로 검색 가능
- RAG manifest가 없으면 자동으로 `knowledge_tutor` 수집 흐름 실행

---

## Phase 1: RAG Manifest 조회 및 토픽 선택

### Step 1-1: 기존 RAG 목록 확인

```powershell
$RAG_ROOT = "$env:OBSIDIAN_VAULT_PATH\rag"

# 등록된 RAG manifest 목록 출력
Get-ChildItem "$RAG_ROOT" -Directory | ForEach-Object {
    $manifest = Get-Content "$($_.FullName)\manifest.json" | ConvertFrom-Json
    [PSCustomObject]@{
        Topic      = $manifest.topic
        Files      = $manifest.file_count
        Size_KB    = [math]::Round($manifest.total_bytes / 1024)
        Updated    = $manifest.updated
        SafeTopic  = $manifest.safe_topic
    }
} | Format-Table -AutoSize
```

> **예시 출력:**
> ```
> Topic                            Files  Size_KB  Updated              SafeTopic
> -----                            -----  -------  -------              ---------
> Mamba SSM architecture           6      185      2026-02-19T15:48:00  Mamba_SSM_architecture...
> NVIDIA 자율주행 기술 특징과 동향    6      142      2026-02-19T16:15:00  NVIDIA__________
> ```

---

### Step 1-2: 사용자 토픽 선택

사용자에게 질문합니다:

> **"어떤 주제를 검색하시겠습니까?**
> 위 목록에서 토픽명을 입력하거나, `전체`로 모든 자료를 검색합니다."

#### 입력 유형별 처리

| 입력 | 처리 |
|------|------|
| 목록의 토픽명과 **일치** | 해당 manifest 로드 → Step 1-3 |
| 목록에 **없는** 새 주제 | Step 1-4 (RAG 생성 흐름 실행) |
| `전체` 또는 `all` | 모든 manifest의 source_dirs 합산 |
| 복수 토픽 (쉼표 구분) | 해당 manifest들 병합 |

---

### Step 1-3: Manifest에서 소스 경로 로드

```powershell
$SAFE_TOPIC = "{선택한_safe_topic}"
$manifest = Get-Content "$RAG_ROOT\$SAFE_TOPIC\manifest.json" | ConvertFrom-Json

# source_dirs를 배열로 추출
$SOURCE_DIRS = $manifest.source_dirs
Write-Host "📂 소스 경로: $SOURCE_DIRS"
Write-Host "📄 파일 수: $($manifest.file_count)개 ($([math]::Round($manifest.total_bytes/1024)) KB)"
```

소스 경로가 존재하지 않으면 (파일이 이동/삭제된 경우):
```
⚠️ 소스 디렉토리를 찾을 수 없습니다: {path}
   knowledge_tutor로 재수집하시겠습니까? (y/n)
```

→ `y` 입력 시 Step 1-4로 이동

---

### Step 1-4: RAG 없음 — 자동 수집 흐름 실행 ⭐

조회한 주제의 manifest가 없거나 소스가 손상된 경우,
**`knowledge_tutor` Phase 1 + manifest 생성**을 자동으로 실행합니다.

```
🔍 '{TOPIC}'에 대한 RAG manifest가 없습니다.
   지금 자료를 수집하고 RAG를 생성하시겠습니까? (y/n)
```

**`y` 입력 시 순서대로 실행:**

#### 1-4-a: Tavily 검색 수집

```powershell
$AGENT_ROOT = "C:\Users\ldslj\OneDrive\문서\work\claude\knowledge_collector"
$SAFE_TOPIC = "{TOPIC}" -replace '[ /]','_'
$OUTPUT_DIR = "$env:OBSIDIAN_VAULT_PATH\sources\$SAFE_TOPIC"

python "$AGENT_ROOT\.agent\skills\tavily-search\scripts\search_tavily.py" `
  --query "{TOPIC}" `
  --output-dir "$OUTPUT_DIR" `
  --max-results 5 `
  --search-depth advanced `
  --use-jina `
  --exclude-domains "reddit.com,youtube.com,amazon.com,ebay.com" `
  --min-content-length 300
```

> ⚠️ 수집 결과 품질이 낮으면 `knowledge_tutor` Step 1-5 (Garbage 정리 + 재검색) 절차를 따릅니다.

#### 1-4-b: RAG Manifest 생성

```powershell
python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\create_manifest.py" `
  --topic "{TOPIC}" `
  --sources-dir "$OUTPUT_DIR" `
  --rag-root "$RAG_ROOT"
```

#### 1-4-c: manifest 로드 후 Step 2로 진행

```powershell
$manifest = Get-Content "$RAG_ROOT\$SAFE_TOPIC\manifest.json" | ConvertFrom-Json
$SOURCE_DIRS = $manifest.source_dirs
```

---

## Phase 2: RAG Q&A 루프

### Step 2-1: 질문 입력받기

사용자에게 질문합니다:

> **"어떤 내용이 궁금하신가요?"**
> 예: `DRIVE Hyperion 10의 센서 구성은?`, `Mamba의 Selection Mechanism이란?`

---

### Step 2-2: RAG 청크 검색 실행

```powershell
$AGENT_ROOT = "C:\Users\ldslj\OneDrive\문서\work\claude\knowledge_collector"

# 단일 소스 디렉토리
python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\retrieve_chunks.py" `
  --query "{QUESTION}" `
  --sources-dir $SOURCE_DIRS[0] `
  --top-k 5 `
  --chunk-size 800 `
  --show-stats

# 복수 소스 디렉토리 (전체 / 다중 토픽 선택 시)
foreach ($dir in $SOURCE_DIRS) {
    python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\retrieve_chunks.py" `
      --query "{QUESTION}" `
      --sources-dir $dir `
      --top-k 3 `
      --chunk-size 800
}
```

> 💡 **top-k 조정 가이드:**
> - 간단한 사실 확인 → `--top-k 3`
> - 개념 설명 / 비교 분석 → `--top-k 5` (기본)
> - 복잡한 종합 질문 → `--top-k 8`

---

### Step 2-3: 청크 기반 답변 생성

검색된 청크를 내부 컨텍스트로 활용하여 다음 규칙으로 답변합니다:

1. **근거 기반 답변**: 검색된 청크에 있는 내용을 인용하여 답변
2. **출처 명시**: 답변 마지막에 `📄 출처: {파일명} (chunk #{n}, score={s})` 형식으로 표기
3. **범위 초과 처리**: 청크에 관련 내용이 없으면:
   - `"수집된 자료에 해당 내용이 없습니다."`
   - `→ 다른 토픽 추가 검색 or knowledge_tutor로 신규 수집` 제안
4. **한국어 답변 + 기술 용어 병기**

---

### Step 2-4: 후속 안내

답변 후 항상 안내합니다:

```
[계속]  다른 질문을 입력하세요.
[범위]  다른 토픽도 추가로 검색할까요? (현재: {topic})
[신규]  이 주제로 웹 검색(knowledge_tutor)을 추가 실행할까요?
[종료]  'exit' 또는 '종료'
```

---

### Step 2-5: 다중 토픽 동시 검색

사용자가 `[범위]`를 요청하거나 처음에 복수 토픽을 지정한 경우:

```powershell
# 선택한 복수 manifest에서 source_dirs 합산
$ALL_DIRS = @()
foreach ($safe in @("{topic1_safe}", "{topic2_safe}")) {
    $m = Get-Content "$RAG_ROOT\$safe\manifest.json" | ConvertFrom-Json
    $ALL_DIRS += $m.source_dirs
}

# 각 dir에 대해 retrieve_chunks 실행 후 결과 합산
foreach ($dir in $ALL_DIRS) {
    Write-Host "=== [$dir] 검색 중 ==="
    python "$AGENT_ROOT\.agent\skills\rag-retriever\scripts\retrieve_chunks.py" `
      --query "{QUESTION}" `
      --sources-dir $dir `
      --top-k 3 `
      --chunk-size 800
}
```

---

### Step 2-6: 종료 감지

사용자가 다음 중 하나를 입력하면 Phase 3으로 이동:
- `종료`, `exit`, `quit`, `그만`, `끝`, `done`

---

## Phase 3: 세션 Q&A Obsidian 저장 (선택)

세션 Q&A를 저장하려면:

```powershell
python "$AGENT_ROOT\.agent\skills\obsidian-integration\scripts\save_to_obsidian.py" `
  --topic "{검색_주제}_조회" `
  --content "{Q&A_기록}" `
  --summary "{핵심_포인트}" `
  --category "Knowledge_Query" `
  --vault-path "$env:OBSIDIAN_VAULT_PATH"
```

---

## 예시 세션

```
USER: /knowledge_query

AI: 등록된 RAG 목록:
    1. Mamba SSM architecture deep learning explanation (6파일, 185KB, 2026-02-19)
    2. NVIDIA 자율주행 기술 특징과 동향 (6파일, 142KB, 2026-02-19)

    어떤 주제를 검색하시겠습니까?

USER: NVIDIA 자율주행

AI: manifest 로드 완료.
    📂 소스: .../sources/NVIDIA__________
    📄 파일: 6개 (142 KB)

    어떤 내용이 궁금하신가요?

USER: DRIVE Hyperion 10의 센서 구성은?

AI: [RAG 검색 → chunk #9, score=5.769 발견]

    DRIVE AGX Hyperion 10은 다음 멀티모달 센서를 탑재합니다:
    - HD 카메라 14대 / 레이더 9개 / 라이다 1개 / 초음파 12개

    📄 출처: ...DRIVE_platform_features_..._5_2026-02-19.md (chunk #9, score=5.77)

    [계속] 다른 질문을 입력하세요.
    [범위] 다른 토픽도 추가 검색 가능합니다.
    [종료] 'exit'

USER: Mamba SSM과 어떤 차이가 있어?

AI: 현재 토픽(NVIDIA 자율주행)에서 Mamba 관련 내용이 없습니다.
    'Mamba SSM architecture' 토픽도 함께 검색할까요?

USER: 응

AI: [두 토픽 동시 검색 실행...]
    ...

USER: 종료

AI: 세션을 Obsidian에 저장하시겠습니까? (y/n)
```

---

## Notes

- **전제 조건**: `knowledge_tutor`로 수집 + manifest 생성이 먼저 필요
- **manifest 경로**: `{OBSIDIAN_VAULT_PATH}/rag/{safe_topic}/manifest.json`
- **소스 경로 이동 시**: manifest의 `source_dirs`를 수동 수정하거나 재수집
- **의존성**: `rank-bm25` (`pip install rank-bm25`)
- **knowledge_tutor와의 차이**:

| | `knowledge_tutor` | `knowledge_query` |
|---|---|---|
| 웹 검색 | ✅ Tavily + Jina | ❌ (기존 자료만) |
| 속도 | 느림 (수집 포함) | ⚡ 빠름 (로컬 BM25) |
| 용도 | 새 주제 학습 | 기존 자료 즉시 조회 |
| RAG 생성 | ✅ (Step 1-6) | ❌ 없으면 자동 연동 |
