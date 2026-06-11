# 싸이렌 AI 서버 (ssairen-ai)

싸이렌의 핵심 AI 기능을 제공하는 **stateless FastAPI 서버**. Spring 백엔드(BE)에서만 내부 호출하며 외부에 노출되지 않는다.

- 호출 방향: **BE → AI 단방향** (AI는 BE를 역호출하지 않음)
- 상태 없음: DB·세션 저장 없음. 대화/지식 맥락은 매 요청에 BE가 실어 보냄.
- 계약 문서: [`docs/dev/API/API 명세서(AI-BE).md`](docs/dev/API/API%20명세서(AI-BE).md) · 로드맵: [`docs/dev/PLAN.md`](docs/dev/PLAN.md)

## 기능

| 기능 | 엔드포인트 | 비고 |
|---|---|---|
| ① 구조화된 제보 생성 | `POST /internal/v1/reports:analyze` | 멀티모달 → **다단계 분류(대→소) + 가이드/유사사례 보강 → 기관·부서 배정** + 임베딩 |
| ② 유사 제보 임베딩 | `POST /internal/v1/embeddings` | text-embedding-3-small 벡터 (백필/재계산) |
| ③ 챗봇 | `POST /internal/v1/chatbot:plan` · `:answer` · `:title` | BE 주도 2-스텝 RAG + 세션 제목 생성 |

## 스택

- Python 3.12, FastAPI, OpenAI SDK — LLM(구조화 분석/챗봇) + `text-embedding-3-small`(임베딩). GPU·로컬 모델 불필요
- 패키지/환경 관리: **uv**

## 개발 시작

```bash
# 의존성 설치 (.venv 생성)
uv sync

# 환경 변수 준비
cp .env.example .env   # OPENAI_API_KEY 입력

# 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# 헬스 체크
curl http://localhost:8000/health
```

## 운영

- **헬스/메트릭**: `GET /health`(모델·버전), `GET /metrics`(LLM 호출수·토큰·평균지연·오류).
- **동시성 제한**: `LLM_MAX_CONCURRENCY`(기본 8), `EMBEDDING_MAX_CONCURRENCY`(기본 8). 기동 시 세마포어 초기화.
- **타임아웃/재시도**: `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`(SDK 전송 재시도), `STRUCTURED_OUTPUT_MAX_RETRIES`(구조화 출력 스키마/JSON 검증 실패 시 앱 레벨 재시도, 기본 2).
- **에러 규약**: 모든 오류는 `{"error":{"code","message","requestId"}}` 형태. LLM 장애는 502(`llm_upstream_error`)로 무중단 응답.
- **⚠️ GPT-5 계열 주의**: `gpt-5.5` 는 기본 temperature(1)만 지원하므로 `LLM_SEND_TEMPERATURE=false`(기본) 로 둔다. 결정성은 Structured Outputs 가 담당.

## 라이브 스모크 (실 OpenAI 호출, 비용 발생)

```bash
uv run python scripts/live_smoke.py   # ① 분석 골든셋 + ③ 챗봇 검증
```

## 프로젝트 구조

```
app/
  main.py        # FastAPI 엔트리포인트, /health, lifespan(run_schema)
  config.py      # 환경설정 (pydantic-settings)
  api/           # 라우트
  core/          # llm, structured-output, taxonomy(8 대분류/47 소분류 SSOT)
  db/            # AI 전용 SQLite — schema.sql, connection, repository
  schemas/       # 요청/응답 + 단계별(pipeline) Pydantic 모델
  services/      # analyzer(다단계), embedder, chatbot
  prompts/       # classify(대/소분류) · enrich(보강) · common
data/
  seed/          # 분당기관부서.xlsx (조직표 시드)
  ssiren.db      # 생성물 — 룰북 가이드 + 조직표 (커밋)
scripts/
  ingest_rulebook_and_org.py   # docs/rules + 시드 xlsx → SQLite 적재(멱등)
tests/
```

> **DB 빌드**: `uv run python scripts/ingest_rulebook_and_org.py` — `docs/rules/database/*.md`(소분류 가이드 평문)와 `data/seed/분당기관부서.xlsx`(조직표)를 `data/ssiren.db`로 적재한다.
