# 싸이렌 AI 서버 (ssairen-ai)

싸이렌의 핵심 AI 기능을 제공하는 **stateless FastAPI 서버**. Spring 백엔드(BE)에서만 내부 호출하며 외부에 노출되지 않는다.

- 호출 방향: **BE → AI 단방향** (AI는 BE를 역호출하지 않음)
- 상태 없음: DB·세션 저장 없음. 대화/지식 맥락은 매 요청에 BE가 실어 보냄.
- 계약 문서: [`docs/dev/API/API 명세서(AI-BE).md`](docs/dev/API/API%20명세서(AI-BE).md) · 로드맵: [`docs/dev/PLAN.md`](docs/dev/PLAN.md)

## 기능

| 기능 | 엔드포인트 | 비고 |
|---|---|---|
| ① 구조화된 제보 생성 | `POST /internal/v1/reports:analyze` | 멀티모달(이미지+텍스트) → 구조화 JSON + 임베딩 |
| ② 유사 제보 임베딩 | `POST /internal/v1/embeddings` | bge-m3 벡터 (백필/재계산) |
| ③ 챗봇 | `POST /internal/v1/chatbot:plan` · `:answer` | BE 주도 2-스텝 RAG |

## 스택

- Python 3.12, FastAPI, OpenAI SDK (LLM), `sentence-transformers` + `BAAI/bge-m3` (임베딩, GPU)
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
- **동시성 제한**: `LLM_MAX_CONCURRENCY`(기본 8), `EMBEDDING_MAX_CONCURRENCY`(기본 2, 단일 GPU 경합 방지). 기동 시 세마포어 초기화.
- **타임아웃/재시도**: `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`(OpenAI SDK 내장 재시도).
- **에러 규약**: 모든 오류는 `{"error":{"code","message","requestId"}}` 형태. LLM 장애는 502(`llm_upstream_error`)로 무중단 응답.
- **⚠️ GPT-5 계열 주의**: `gpt-5.5` 는 기본 temperature(1)만 지원하므로 `LLM_SEND_TEMPERATURE=false`(기본) 로 둔다. 결정성은 Structured Outputs 가 담당.

## 라이브 스모크 (실 OpenAI 호출, 비용 발생)

```bash
uv run python scripts/live_smoke.py   # ① 분석 골든셋 + ③ 챗봇 검증
```

## 프로젝트 구조

```
app/
  main.py        # FastAPI 엔트리포인트, /health
  config.py      # 환경설정 (pydantic-settings)
  api/           # 라우트 (phase 1+)
  core/          # llm, structured-output, taxonomy (phase 0-2/0-3)
  schemas/       # 요청/응답 Pydantic 모델
  services/      # analyzer, embedder, chatbot
  prompts/       # LLM 프롬프트
tests/
```
