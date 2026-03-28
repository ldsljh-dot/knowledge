---
name: personal-db
description: "일정(events)과 메모(memos)를 SQLite DB에 정확하게 저장·조회합니다. LLM이 직접 텍스트를 읽는 대신 스크립트를 통해 결정론적인 결과를 반환합니다. ZeroClaw/OpenClaw/Claude/Gemini 모두 공유. Use when you need to store, retrieve, update, or delete schedules or memos with 100% accuracy."
---

# Personal DB Skill

일정과 메모를 SQLite에 저장하여 LLM의 텍스트 해석 오류를 제거합니다.

**DB 위치**: `$OBSIDIAN_VAULT_PATH/Agent/personal.db` (모든 에이전트 공유)

## 일정 관리 (manage_events.py)

```bash
# 일정 추가
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" add \
  --title "팀 미팅" \
  --start "2026-03-28T14:00" \
  --end "2026-03-28T15:00" \
  --location "회의실 A" \
  --tags '["work","meeting"]' \
  --source "user"

# 특정 날짜 조회
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --date "2026-03-28"

# 기간 조회
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --from "2026-03-28" --to "2026-03-31"

# 키워드 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" query \
  --keyword "미팅" --format json

# 수정
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" update \
  --id "abc-123" --location "온라인"

# 삭제
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" delete \
  --id "abc-123"

# 배치 추가 (JSON 파일)
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_events.py" add \
  --input-json "/path/to/events.json"
```

### 파라미터 (add)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `--title` | ✅ | 일정 제목 |
| `--start` | ✅ | 시작 일시 ISO 8601 (e.g. `2026-03-28T14:00`) |
| `--end` | ❌ | 종료 일시 |
| `--location` | ❌ | 장소 |
| `--tags` | ❌ | JSON 배열 (e.g. `'["work","meeting"]'`) |
| `--source` | ❌ | 출처 (`user`/`zeroclaw`/`openclaw`, 기본: `user`) |
| `--input-json` | ❌ | 배치 추가용 JSON 파일 경로 |

### 파라미터 (query)

| 파라미터 | 설명 |
|----------|------|
| `--date` | 특정 날짜 (e.g. `2026-03-28`) |
| `--from` | 시작 날짜 범위 |
| `--to` | 종료 날짜 범위 |
| `--keyword` | 제목/장소 키워드 |
| `--tag` | 태그 필터 |
| `--limit` | 최대 결과 수 (기본: 50) |
| `--format` | `text` (기본) 또는 `json` |

---

## 메모 관리 (manage_memos.py)

```bash
# 메모 추가
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" add \
  --title "회의록 2026-03-28" \
  --content "결정사항: 다음 스프린트 목표는..." \
  --tags '["work","meeting-notes"]'

# 키워드 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" search \
  --keyword "회의록"

# 태그로 검색
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" search \
  --tag "todo" --format json

# 수정
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" update \
  --id "abc-123" --content "수정된 내용"

# 삭제
python "$AGENT_ROOT/.gemini/skills/personal-db/scripts/manage_memos.py" delete \
  --id "abc-123"
```

### 파라미터 (add)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `--title` | ✅ | 메모 제목 |
| `--content` | ✅ | 메모 내용 |
| `--tags` | ❌ | JSON 배열 |
| `--source` | ❌ | 출처 (기본: `user`) |

---

## DB 스키마

```sql
-- 일정
events (id, title, start_dt, end_dt, location, tags, source, created_at, updated_at)

-- 메모
memos (id, title, content, tags, source, created_at, updated_at)
```

- `start_dt`, `end_dt`: ISO 8601 형식 (`2026-03-28T14:00:00`)
- `tags`: JSON 배열 문자열 (`["work","meeting"]`)
- `id`: UUID v4 자동 생성
- 동시 접근 안전: WAL 모드 + 5초 busy timeout

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `OBSIDIAN_VAULT_PATH` | ✅ | DB 자동 위치 결정 (`{vault}/Agent/personal.db`) |

또는 `--db-path` 인자로 직접 지정 가능.

## 의존성

- `sqlite3` (Python 표준 라이브러리, 추가 설치 불필요)
- `python-dotenv` (선택)
