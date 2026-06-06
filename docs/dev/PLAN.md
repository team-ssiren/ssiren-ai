# Phase 0 — 공통 기반 (Foundation)

모든 기능이 의존. 여기서 막히면 전부 막힘.

### 0-1. 프로젝트 스캐폴드 & 설정
- **목표**: FastAPI 앱 부팅, `config.py`(env 로딩: OpenAI 키/모델, bge-m3, 임계값), `GET /health` 동작.
- **성공 기준**: `uvicorn` 기동 후 `/health`가 200 + 모델/버전 메타 반환. env 누락 시 기동 단계에서 명확한 에러.
- **영향 범위**: `app/main.py`, `app/config.py`, `requirements.txt`, `.env.example`. (신규, 격리)

### 0-2. 공통 인프라 (LLM 클라이언트 · 구조화 출력 · 에러 규약)
- **목표**: OpenAI wrapper(`core/llm.py`) + Structured Output 헬퍼(JSON Schema→파싱·재시도) + 공통 에러/응답 포맷 + 요청ID 로깅.
- **성공 기준**: 임의 Pydantic 스키마를 주면 enum 위반·필드 누락 없이 검증된 객체 반환. LLM 5xx/타임아웃 시 1회 재시도 후 표준 에러 JSON.
- **영향 범위**: `core/llm.py`, `core/structured.py`, `api/errors.py`, `app/main.py`(미들웨어). **→ 이후 ①③ 전부가 이 모듈에 의존.**

### 0-3. 택소노미 SSOT
- **목표**: `core/taxonomy.py`에 리프 14종(code/ko/parent/agency_type/department/정의/포함·제외예) 확정, enum·역산 함수 제공.
- **성공 기준**: `code→parent/department/agency_type` 역산 단위테스트 통과. enum 리스트가 ① 스키마와 프롬프트 few-shot에 단일 소스로 주입됨.
- **영향 범위**: `core/taxonomy.py`, `tests/test_taxonomy.py`. **→ ①의 분류·기관힌트, ③ SEARCH_NEARBY의 categoryCode가 의존.** BE와 공유할 코드셋이라 변경 시 BE 매핑 동기화 필요(외부 영향).

---

# Phase 1 — ② 임베딩 (가장 격리, 무거운 의존성 선검증)

먼저 만들어 bge-m3 로딩 리스크를 일찍 제거. ①이 이 모듈을 재사용.

### 1-1. bge-m3 임베더 로딩
- **목표**: `services/embedder.py` — 기동 시 모델 싱글톤 로드, `embed(texts)→L2정규화 1024벡터`.
- **성공 기준**: 콜드스타트 후 첫 임베딩 < 목표시간(CPU 기준 합의값), 동일 입력 재현성 100%, `‖v‖≈1`. 임베딩 대상 텍스트 결합규칙(`title+summary+keywords`)이 ①과 동일.
- **영향 범위**: `services/embedder.py`, `config.py`(모델명/디바이스), `requirements.txt`(FlagEmbedding or sentence-transformers). **메모리/콜드스타트** 영향 큼 → 배포 인스턴스 사양에 직결.

### 1-2. 임베딩 엔드포인트
- **목표**: `POST /internal/v1/embeddings` — batch texts→vectors.
- **성공 기준**: 명세대로 `{model,dimension,embeddings}` 반환. 빈 배열·과대 배치 입력 검증. 차원=1024 고정.
- **영향 범위**: `api/routes/embeddings.py`, `schemas/embedding.py`. (외부: BE 백필 잡이 호출)

---

# Phase 2 — ① 구조화 분석 (핵심·최대 표면적)

### 2-1. 분석 스키마 정의
- **목표**: `schemas/report.py`에 요청(multipart)·응답(title/contents/category/analysis/embedding) Pydantic + JSON Schema(enum=categoryCode, agencyType).
- **성공 기준**: 응답 스키마가 `API 명세서(AI-BE).md`와 1:1. enum 강제가 스키마 레벨에서 동작.
- **영향 범위**: `schemas/report.py`. **→ BE 파싱 계약의 원본.** 필드 변경 시 BE DTO 영향(외부).

### 2-2. 멀티모달 분석 파이프라인
- **목표**: `services/analyzer.py` — 이미지 base64 변환 + 주소 컨텍스트 주입 + 프롬프트(타이브레이크 규칙) + Structured Output 호출 → 구조화 JSON. 임베딩(Phase1) 합성.
- **성공 기준**: 골든셋 케이스(불법주정차/도로파손/동물사체/주취자/허위/긴급)에서 categoryCode·suggestedAgencyType·emergency/false 플래그가 기대값과 일치(목표 정확도 합의). `temperature=0` 재현성.
- **영향 범위**: `services/analyzer.py`, `prompts/analyze.py`, `core/llm`·`taxonomy`·`embedder` 사용. 비용/지연(Vision 콜)에 가장 큰 기여.

### 2-3. 분석 엔드포인트 + 가드
- **목표**: `POST /internal/v1/reports:analyze`(multipart) 라우트, 이미지 0~N장·용량·MIME 검증, occurredAt 기본값.
- **성공 기준**: 이미지 없는 텍스트-only 제보도 동작. 잘못된 파일/과대 용량은 4xx. p95 지연 목표 내.
- **영향 범위**: `api/routes/reports.py`, `schemas/report.py`. **→ BE 초안생성(`/reports/drafts`) 흐름이 직접 의존.**

---

# Phase 3 — ③ 챗봇 (2-스텝)

### 3-1. Plan (의도 라우팅)
- **목표**: `POST /internal/v1/chatbot:plan` — 질문+history→`action` enum(+ANSWER_DIRECT 단락회로 answer).
- **성공 기준**: 의도 분류 골든셋(잡담/근처질문/내제보)에서 action 정확. `ANSWER_DIRECT`는 1콜 종료. enum 외 값 0건.
- **영향 범위**: `api/routes/chatbot.py`, `schemas/chatbot.py`, `services/chatbot.py`, `prompts/chatbot_plan.py`. taxonomy(categoryCode 추출) 의존.

### 3-2. Answer (근거 기반 생성)
- **목표**: `POST /internal/v1/chatbot:answer` — context.reports 기반 응답 + `usedReportIds`, grounding 고정.
- **성공 기준**: context 비면 환각 없이 "주변 제보 없음" 응답. 답변이 인용한 reportId만 `usedReportIds`에 포함. 응급 묘사 시 112/119 안내.
- **영향 범위**: `services/chatbot.py`, `prompts/chatbot_answer.py`, `schemas/chatbot.py`. **→ BE 챗봇 retrieval 결과 포맷과 결합.**

---

# Phase 4 — 통합 · 하드닝

### 4-1. 운영 가드
- **목표**: 타임아웃/재시도/동시성 제한, 구조화 로깅, 비용·지연 메트릭, OpenAPI 문서 자동노출(`/docs` 내부용).
- **성공 기준**: LLM 지연/실패 주입 시 서버 무중단·표준 에러. 부하 시 동시성 상한 동작.
- **영향 범위**: `app/main.py`, `core/llm`, 미들웨어. 전 기능 횡단.

### 4-2. BE 연동 계약 검증
- **목표**: 4개 엔드포인트 mock/실 호출 e2e, 샘플 페이로드로 BE팀과 round-trip 확인.
- **성공 기준**: `API 명세서(AI-BE).md` 예시 페이로드가 그대로 통과. categoryCode↔BE ID 매핑 합의 완료.
- **영향 범위**: `tests/e2e`, 문서. **외부: BE 통합** 직접 영향.

---

## 빌드 순서 요약 (의존성 DAG)
```
0-1 → 0-2 → 0-3
        └─→ 1-1 → 1-2
              └─→ 2-1 → 2-2 → 2-3
        └────────────→ 3-1 → 3-2
                              └─→ 4-1 → 4-2
```
- **크리티컬 패스**: 0 → 1-1 → 2-2 (멀티모달 분석이 가장 무겁고 표면적 큼).
- **외부(BE) 영향 큰 지점**: 0-3 택소노미 코드셋, 2-1 응답 스키마, 4-2 연동 — 이 셋은 **BE와 합의 락**이 필요.
- **리스크 선제거**: 1-1 bge-m3 로딩(메모리/콜드스타트)을 일찍 검증.