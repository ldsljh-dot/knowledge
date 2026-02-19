---
name: tavily-search
description: "웹에서 최신 정보를 검색하고 각 소스를 개별 Obsidian .md 파일로 저장하는 스킬입니다. Tavily로 URL을 발굴하고 Jina Reader로 전체 페이지를 수집하는 2단계 파이프라인을 지원합니다."
---

# Tavily Search Skill (v2)

Tavily로 URL을 발굴하고, **Jina Reader로 전체 페이지**를 수집하는 2단계 파이프라인 스킬입니다.

## 파이프라인 구조

```
[Stage 1] Tavily API
  → 쿼리 검색
  → URL 목록 + AI 요약 + 스니펫 수집
  → include_domains 필터링으로 노이즈 소스 제거

[Stage 2] Jina Reader (--use-jina 옵션)
  → 각 URL의 전체 페이지를 Markdown으로 수집
  → 실패/너무 짧은 경우 Tavily 스니펫으로 자동 fallback
  → min_content_length로 쇼핑몰/네비게이션 잔재 필터링
```

## 사용법

### 기본 (기존과 동일)
```bash
cd <project_root>/.agent/skills/tavily-search

python scripts/search_tavily.py \
  --query "검색할 주제" \
  --output-dir "/path/to/obsidian/vault/sources/주제명"
```

### 권장: Jina Reader + 도메인 필터 적용
```bash
python scripts/search_tavily.py \
  --query "nvidia H100 hopper architecture" \
  --output-dir "/path/to/vault/sources/h100" \
  --use-jina \
  --include-domains "nvidia.com,docs.nvidia.com,arxiv.org,anandtech.com" \
  --exclude-domains "reddit.com,youtube.com,amazon.com" \
  --min-content-length 300
```

### 다중 쿼리 (주제를 세분화하여 품질 향상)
```bash
python scripts/search_tavily.py \
  --queries "H100 transformer engine FP8,H100 MIG multi-instance GPU,H100 NVLink HBM3 specs" \
  --output-dir "/path/to/vault/sources/h100" \
  --use-jina \
  --include-domains "nvidia.com,arxiv.org,developer.nvidia.com"
```

## 파라미터

| 파라미터 | 필수 | 기본값 | 설명 |
|----------|------|--------|------|
| `--query` | ✅* | — | 단일 검색 쿼리 (`--queries`와 택1) |
| `--queries` | ✅* | — | 다중 쿼리, 쉼표 구분 (`--query`와 택1) |
| `--output-dir` | ✅ | — | 결과 파일 저장 디렉토리 |
| `--max-results` | ❌ | `5` | 쿼리당 최대 검색 결과 수 |
| `--search-depth` | ❌ | `advanced` | `basic` \| `advanced` |
| `--include-domains` | ❌ | — | 허용 도메인, 쉼표 구분 (예: `nvidia.com,arxiv.org`) |
| `--exclude-domains` | ❌ | — | 제외 도메인, 쉼표 구분 (예: `reddit.com,youtube.com`) |
| `--use-jina` | ❌ | `False` | Jina Reader로 전체 페이지 수집 활성화 |
| `--min-content-length` | ❌ | `200` | 이 길이 미만 콘텐츠는 노이즈로 필터링 |
| `--jina-timeout` | ❌ | `15` | Jina 요청 타임아웃(초) |

## 환경변수

- `TAVILY_API_KEY` (필수): [app.tavily.com](https://app.tavily.com) 에서 발급
  - `.env` 파일 또는 `export TAVILY_API_KEY=tvly-...` 로 설정
- Jina Reader는 **API 키 불필요** (무료, `r.jina.ai` 공개 서비스)

## 출력 파일 형식

```
{output-dir}/
├── {query}_summary_{date}.md        ← Tavily AI 요약
├── {query}_1_{date}.md              ← 소스 1 (jina_enhanced or tavily_snippet)
├── {query}_2_{date}.md              ← 소스 2
└── ...
```

각 소스 파일의 frontmatter에 수집 방식이 기록됩니다:
```yaml
content_source: jina_enhanced   # 전체 페이지 수집 성공
content_source: tavily_snippet  # 스니펫 fallback
```

## 도메인 추천 목록

### 기술/AI 학습
```
nvidia.com,docs.nvidia.com,developer.nvidia.com,
arxiv.org,proceedings.mlsys.org,dl.acm.org,
anandtech.com,techpowerup.com,semianalysis.com
```

### 공식 문서 중심
```
docs.nvidia.com,developer.nvidia.com,
pytorch.org,huggingface.co,
kubernetes.io,docs.aws.amazon.com
```

## 의존성

```
tavily-python       # pip install tavily-python
python-dotenv       # pip install python-dotenv (선택)
urllib (표준 라이브러리)  # Jina Reader 요청용, 추가 설치 불필요
```
