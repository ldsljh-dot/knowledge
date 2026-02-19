---
name: obsidian-integration
description: "학습 대화 내용(Q&A)과 핵심 요약을 Obsidian vault에 표준 형식의 노트로 저장하는 스킬입니다. Use when the user wants to save learning conversations, Q&A records, or summaries to an Obsidian vault as formatted markdown notes."
---

# Obsidian Integration Skill

학습 대화 내용(Q&A)과 핵심 요약을 Obsidian vault에 표준 형식의 노트로 저장하는 스킬입니다.

## 사용법

```bash
cd <project_root>/.agent/skills/obsidian-integration

python scripts/save_to_obsidian.py \
  --topic "학습 주제" \
  --content "## 💬 학습 기록\n### Q1: ...\n**A**: ..." \
  --summary "- 핵심 포인트 1\n- 핵심 포인트 2" \
  --category "AI_Study" \
  --vault-path "/path/to/obsidian/vault" \
  --sources "file1.md,file2.md"
```

## 파라미터

| 파라미터 | 필수 | 기본값 | 설명 |
|----------|------|--------|------|
| `--topic` | ✅ | — | 학습 주제명 |
| `--content` | ✅ | — | 학습 대화 전체 기록 (Q&A) |
| `--summary` | ❌ | `""` | 핵심 요약 (bullet points) |
| `--category` | ✅ | — | 카테고리 태그 (예: `AI_Study`) |
| `--vault-path` | ✅ | — | Obsidian vault 절대경로 |
| `--sources` | ❌ | `""` | 소스 파일 경로 (comma-separated) |
| `--status` | ❌ | `🌿 seed` | `🌿 seed` \| `🌱 sprout` \| `🌳 tree` |

## 환경변수

- `OBSIDIAN_VAULT_PATH`: vault 경로를 환경변수로 지정할 수도 있음

## 출력 파일 형식

vault 루트에 다음 파일이 생성됩니다:

```
{vault-path}/
└── {YYYY-MM-DD}_{topic}.md
```

파일 구조:
```markdown
---
created: ...
tags: [AI_Study, {category}]
sources: [wikilinks...]
---

# 📚 {topic}

## 📖 원본 자료
## 💬 학습 기록
## 🎯 핵심 요약
## 🔗 관련 개념
## 📝 추가 노트
```

동일 이름 파일이 존재하면 자동으로 `_2`, `_3` suffix가 붙습니다.

## 의존성

```
python-dotenv  (선택)
```
