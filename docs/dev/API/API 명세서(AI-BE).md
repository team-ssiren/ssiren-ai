# API 명세서 (AI-BE)

Spring 백엔드(BE)가 호출하는 **내부 AI 서버(FastAPI)** 의 API 명세.

## 개요

| 항목 | 내용 |
| --- | --- |
| 호출 방향 | **BE → AI 단방향** (AI 는 BE 를 역호출하지 않음) |
| 노출 범위 | 내부 전용(`/internal/v1`), 외부 미노출 |
| 인증 | **없음** (BE 가 사용자 인증을 이미 처리, AI 는 신뢰된 내부 호출만 수신) |
| 상태 | **Stateless** — DB·세션 저장 없음. 대화/지식 맥락은 매 요청에 BE 가 전달 |
| LLM | OpenAI (모델명 env, 기본 `gpt-5.5`). Structured Outputs(enum 강제)로 결정성 확보 |
| 임베딩 | `BAAI/bge-m3` (1024차원, L2 정규화). AI 는 벡터만 생성, 코사인/저장/임계값은 BE |
| Base URL | `http://{ai-host}:{port}` (예: `http://localhost:8000`) |

### BE ↔ AI 책임 분담

| 항목 | AI | BE |
| --- | --- | --- |
| 멀티모달 분석·생성(제목/육하원칙/요약/키워드) | ✅ | |
| 카테고리 분류(코드), 기관유형 힌트 | ✅ | 코드→ID 매핑 |
| 위험도 점수 | ✅ 산정 | 규칙 보정(선택) |
| 임베딩 벡터 생성 | ✅ | 저장·유사도·임계값 |
| 역지오코딩(좌표→주소) | | ✅ |
| 기관/부서 실인스턴스(관할 조회) | | ✅ |
| 중복 후보 1차 필터(반경/시간) | | ✅ |
| 챗봇 세션·메시지 저장, retrieval | | ✅ |

### 엔드포인트 요약

| 도메인 | 기능 | HTTP 메서드 | API Path | 형식 |
| --- | --- | --- | --- | --- |
| 분석 | ① 구조화 제보 분석 | POST | /internal/v1/reports:analyze | multipart/form-data |
| 임베딩 | ② 텍스트 임베딩(백필/재계산) | POST | /internal/v1/embeddings | application/json |
| 챗봇 | ③ 의도 라우팅(plan) | POST | /internal/v1/chatbot:plan | application/json |
| 챗봇 | ③ 근거 기반 응답(answer) | POST | /internal/v1/chatbot:answer | application/json |
| 메타 | 헬스 체크 | GET | /health | - |
| 메타 | 운영 메트릭 | GET | /metrics | - |

### 공통 enum

**categoryCode** (리프, AI 는 이 중 하나만 선택)

| code | 한글 | 대분류(parent) | 기본 기관유형 | 기본 부서 |
| --- | --- | --- | --- | --- |
| ILLEGAL_PARKING | 불법주정차 | 교통 | 지자체 | 교통행정과 |
| ROAD_DAMAGE | 도로 파손 | 교통 | 지자체 | 도로관리과 |
| TRASH_DUMPING | 쓰레기 무단투기 | 환경 | 지자체 | 청소행정과 |
| ANIMAL_CARCASS | 동물 사체 | 환경 | 지자체 | 청소행정과 |
| NOISE | 소음 | 환경 | 지자체 | 환경과 |
| STREETLIGHT | 가로등 고장 | 시설물 | 지자체 | 도시안전과 |
| DANGEROUS_FACILITY | 위험 시설물 | 시설물 | 지자체 | 시설관리과 |
| FALL_RISK | 낙상 위험 | 생활불편 | 지자체 | 시설관리과 |
| DRUNK_PERSON | 주취자 | 치안 | 경찰 | 관할 지구대 |
| YOUTH_RISK | 청소년 위험 | 치안 | 경찰 | 관할 지구대 |
| SUSPICIOUS | 수상한 상황 | 치안 | 경찰 | 관할 지구대 |
| HOMELESS | 노숙 | 복지 | 지자체 | 복지정책과 |
| FIRE_EMERGENCY | 화재/응급 | 재난안전 | 소방 | 119안전센터 |
| ETC_OTHER | 기타 | 기타 | 지자체 | 민원실 |

**action** (챗봇 plan): `ANSWER_DIRECT` | `SEARCH_NEARBY` | `MY_REPORTS`

> 기관유형·부서는 AI 가 반환하지 않는다. BE 가 위 표의 `categoryCode → 기본 기관유형/기본 부서` 매핑과 위치(관할)로 해소한다.

---

## ① 구조화 제보 분석

사진·텍스트·위치를 분석해 구조화된 제보 데이터를 생성한다. AI 는 분류/생성/위험도/허위·긴급 판단과 임베딩까지 반환하며, 역지오코딩·기관 실인스턴스·저장은 BE 가 담당한다. **DB에 저장하지 않는다.**

### Example request

`POST /internal/v1/reports:analyze`

### Headers

| Header | Type | Required | Description |
| --- | --- | --- | --- |
| Content-Type | `String` | Yes | `multipart/form-data` |

### Query Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
|   |   |   |   |

### Path Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
|   |   |   |   |

### Request Body

`multipart/form-data`

```json
{
  "content": "맨홀이 깨져있어요",
  "latitude": 36.3519123,
  "longitude": 127.3785214,
  "occurredAt": "2026-06-05T15:30:00",
  "roadAddress": "대전광역시 서구 둔산로 1036",
  "sido": "대전광역시",
  "sigungu": "서구",
  "eupmyeondong": "둔산동",
  "images": ["MultipartFile", "MultipartFile"]
}
```

### Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| content | `String` | Yes | 사용자가 입력한 원본 제보 텍스트 |
| latitude | `Decimal` | Yes | 제보 위치 위도 |
| longitude | `Decimal` | Yes | 제보 위치 경도 |
| occurredAt | `String` | No | 발생 시각(ISO-8601). 미입력 시 서버 현재 시각 사용 |
| roadAddress | `String` | No | BE 가 역지오코딩한 도로명 주소(분석 정확도 향상용) |
| sido | `String` | No | 시/도 |
| sigungu | `String` | No | 시/군/구 |
| eupmyeondong | `String` | No | 읍/면/동 |
| images | `MultipartFile[]` | No | 제보 이미지. 0~5장, 장당 최대 10MB, `image/*` |

### Response Body

```json
{
  "title": "보도 위 맨홀 뚜껑 파손",
  "contents": {
    "who": "확인되지 않음",
    "when": "2026-06-05T15:30:00",
    "where": "대전광역시 서구 둔산로 1036",
    "what": "맨홀 뚜껑 파손 및 보도 안전 위험",
    "how": "맨홀 뚜껑이 파손되어 구멍이 노출됨",
    "why": "보행자 추락·부상 위험이 있어 보수가 필요함",
    "summary": "대전광역시 서구 둔산로 1036 인근 보도에 맨홀 뚜껑이 파손되어 보행자 안전 위험이 있습니다."
  },
  "keywords": ["맨홀 파손", "도로 파손", "보도 위험", "추락 위험"],
  "category": {
    "categoryCode": "ROAD_DAMAGE",
    "confidence": 0.96
  },
  "riskScore": 72.0,
  "analysis": {
    "detectedObjects": ["파손된 맨홀 뚜껑", "보도블록", "균열", "구멍"],
    "falseReport": {
      "isSuspicious": false,
      "score": 5.0,
      "reason": "이미지와 텍스트의 연관성이 높습니다."
    },
    "emergencyGuide": {
      "isEmergency": false,
      "message": null
    }
  },
  "occurredAt": "2026-06-05T15:30:00",
  "embedding": [0.013, -0.024, "...(총 1024개)"]
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| title | `String` | AI 가 생성한 제보 제목(한 줄) |
| contents | `Object` | 육하원칙 기반 제보 본문 |
| contents.who | `String` | 문제와 관련된 주체. 불명 시 "확인되지 않음" |
| contents.when | `String` | 문제 발생/확인 시각 |
| contents.where | `String` | 발생 위치 설명(제공된 주소 활용) |
| contents.what | `String` | 발생한 문제 유형/내용 |
| contents.how | `String` | 문제가 발생한 방식 또는 현재 상태 |
| contents.why | `String` | 위험하거나 조치가 필요한 이유 |
| contents.summary | `String` | 상황을 한 문장으로 요약 |
| keywords | `String[]` | 핵심 키워드(3~6개) |
| category | `Object` | 분류 결과 |
| category.categoryCode | `String(enum)` | 리프 카테고리 코드(공통 enum 참조) |
| category.confidence | `Decimal` | 분류 확신도(0.0~1.0) |
| riskScore | `Decimal` | 위험 점수(0~100) |
| analysis | `Object` | AI 분석 부가 결과 |
| analysis.detectedObjects | `String[]` | 이미지에서 감지된 객체. 이미지 없으면 `[]` |
| analysis.falseReport | `Object` | 허위·장난 제보 의심 결과 |
| analysis.falseReport.isSuspicious | `Boolean` | 허위·장난 제보 의심 여부 |
| analysis.falseReport.score | `Decimal` | 허위 의심 점수(0~100, 높을수록 의심) |
| analysis.falseReport.reason | `String` | 판단 사유 |
| analysis.emergencyGuide | `Object` | 긴급 신고 안내 |
| analysis.emergencyGuide.isEmergency | `Boolean` | 긴급 상황 여부 |
| analysis.emergencyGuide.message | `String` | 긴급 시 112/119 안내 문구. 아니면 `null` |
| occurredAt | `String` | 서버가 해소한 발생 시각(요청값 또는 서버 기본값). `contents.when` 과 동일 출처이므로 BE 는 이 값을 `reportDraft.occurredAt` 으로 그대로 사용 |
| embedding | `Decimal[]` | bge-m3 임베딩 벡터(1024차원, L2 정규화). BE 가 중복판단·저장에 사용 |

> BE 처리: `categoryCode` 로 `categoryId`·`parentCategory`·`departmentName`·실기관을 매핑하고, 주소(`roadAddress` 등)는 자체 역지오코딩 값을 사용한다. `embedding` 은 별도 임베딩 호출 없이 중복판단/저장에 바로 활용한다.

---

## ② 텍스트 임베딩

`title + summary + keywords` 결합 규칙으로 만든 텍스트를 bge-m3 벡터로 변환한다. ① 분석 응답에 이미 임베딩이 포함되므로, 이 엔드포인트는 **기존 제보 백필·재계산용**이다.

### Example request

`POST /internal/v1/embeddings`

### Headers

| Header | Type | Required | Description |
| --- | --- | --- | --- |
| Content-Type | `String` | Yes | `application/json` |

### Request Body

```json
{
  "texts": [
    "둔산동 인도 파손으로 낙상 위험\n둔산동 갤러리아 앞 인도 파손\n인도 파손 보행 위험",
    "도로 위 동물 사체 방치\n로드킬 사체로 통행 위험\n동물 사체 환경"
  ]
}
```

### Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| texts | `String[]` | Yes | 임베딩할 텍스트 목록(1~128개) |

### Response Body

```json
{
  "model": "bge-m3",
  "dimension": 1024,
  "embeddings": [
    [0.011, -0.022, "...(1024)"],
    [0.034, 0.005, "...(1024)"]
  ]
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| model | `String` | 임베딩 모델명(`bge-m3`) |
| dimension | `Integer` | 벡터 차원(1024) |
| embeddings | `Decimal[][]` | 입력 순서대로의 L2 정규화 임베딩 벡터 목록 |

---

## ③ 챗봇 — Step 1 (plan)

질문과 대화 맥락을 보고 `action` 을 라우팅한다. `ANSWER_DIRECT` 면 검색 없이 `answer` 를 직접 반환(1콜 종료), 그 외에는 BE 가 수행할 검색 `params` 를 반환한다.

### Example request

`POST /internal/v1/chatbot:plan`

### Headers

| Header | Type | Required | Description |
| --- | --- | --- | --- |
| Content-Type | `String` | Yes | `application/json` |

### Request Body

```json
{
  "question": "이 근처에 위험한 제보 있어?",
  "history": [
    { "role": "user", "content": "안녕" },
    { "role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?" }
  ],
  "userLocation": { "lat": 36.36, "lng": 127.34 }
}
```

### Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| question | `String` | Yes | 사용자 질문 |
| history | `Object[]` | No | 대화 이력. BE 가 최근 N턴만 전달 |
| history[].role | `String` | Yes | `user` 또는 `assistant` |
| history[].content | `String` | Yes | 메시지 내용 |
| userLocation | `Object` | No | 사용자 위치 |
| userLocation.lat | `Decimal` | Yes | 위도 |
| userLocation.lng | `Decimal` | Yes | 경도 |

### Response Body

```json
{
  "action": "SEARCH_NEARBY",
  "params": {
    "categoryCode": null,
    "radiusMeters": 500
  },
  "answer": null
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| action | `String(enum)` | `ANSWER_DIRECT` / `SEARCH_NEARBY` / `MY_REPORTS` |
| params | `Object` | SEARCH_NEARBY 검색 파라미터(그 외 action 은 모두 `null`) |
| params.categoryCode | `String(enum)` | 유형 필터(공통 enum) 또는 `null` |
| params.radiusMeters | `Integer` | SEARCH_NEARBY 검색 반경(기본 500) 또는 `null` |
| answer | `String` | `ANSWER_DIRECT` 일 때만 채워지는 응답 문구. 그 외 `null` |

> BE 처리: `ANSWER_DIRECT` 면 `answer` 를 그대로 사용하고 종료. `SEARCH_NEARBY`/`MY_REPORTS` 면 `params` 로 자체 검색 후 Step 2(answer) 호출.

---

## ③ 챗봇 — Step 2 (answer)

BE 가 검색한 `context.reports` 를 근거로 답변을 생성한다. 제공된 사실만 사용하며, 비면 솔직하게 "없음" 으로 답한다(환각 금지).

### Example request

`POST /internal/v1/chatbot:answer`

### Headers

| Header | Type | Required | Description |
| --- | --- | --- | --- |
| Content-Type | `String` | Yes | `application/json` |

### Request Body

```json
{
  "question": "이 근처 위험한 제보 있어?",
  "history": [],
  "context": {
    "scope": "SEARCH_NEARBY",
    "reports": [
      {
        "reportId": 15,
        "title": "궁동 도로 파손",
        "summary": "도로 파손으로 통행 위험",
        "category": "도로 파손",
        "address": "유성구 궁동",
        "riskScore": 66.0,
        "distanceMeters": 120.0,
        "recentReportedAt": "2026-06-05T15:35:00"
      }
    ],
    "userLocation": { "lat": 36.36, "lng": 127.34 }
  }
}
```

### Request Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| question | `String` | Yes | 사용자 질문 |
| history | `Object[]` | No | 대화 이력(role/content) |
| context | `Object` | Yes | BE 가 검색한 근거 |
| context.scope | `String` | Yes | 검색 범위(예: `SEARCH_NEARBY`, `MY_REPORTS`) |
| context.reports | `Object[]` | No | 근거 제보 목록(비어 있을 수 있음) |
| context.reports[].reportId | `Integer` | Yes | 제보/이슈 ID |
| context.reports[].title | `String` | Yes | 제목 |
| context.reports[].summary | `String` | Yes | 요약 |
| context.reports[].category | `String` | No | 카테고리명 |
| context.reports[].address | `String` | No | 위치 |
| context.reports[].riskScore | `Decimal` | No | 위험 점수 |
| context.reports[].distanceMeters | `Decimal` | No | 사용자 위치로부터의 거리(m) |
| context.reports[].recentReportedAt | `String` | No | 최근 제보 시각 |
| context.userLocation | `Object` | No | 사용자 위치(lat/lng) |

### Response Body

```json
{
  "answer": "네, 약 120m 거리에 '궁동 도로 파손' 이슈가 있어요. 위험도 66으로 통행 시 주의가 필요해요.",
  "usedReportIds": [15]
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| answer | `String` | 근거 기반 응답(한국어) |
| usedReportIds | `Integer[]` | 답변에 실제 활용한 reportId 목록. 없으면 `[]` |

---

## 메타 — 헬스 체크

### Example request

`GET /health`

### Response Body

```json
{
  "status": "ok",
  "app": "ssairen-ai",
  "version": "0.1.0",
  "environment": "local",
  "models": {
    "llm": "gpt-5.5",
    "embedding": "BAAI/bge-m3",
    "embedding_device": "cuda",
    "embedding_dimension": 1024
  }
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| status | `String` | `ok` |
| app | `String` | 앱 이름 |
| version | `String` | 앱 버전 |
| environment | `String` | 실행 환경 |
| models.llm | `String` | LLM 모델 ID |
| models.embedding | `String` | 임베딩 모델명 |
| models.embedding_device | `String` | 임베딩 디바이스(cuda/cpu) |
| models.embedding_dimension | `Integer` | 임베딩 차원 |

---

## 메타 — 운영 메트릭

### Example request

`GET /metrics`

### Response Body

```json
{
  "llm_calls": 42,
  "llm_errors": 1,
  "prompt_tokens": 28840,
  "completion_tokens": 5120,
  "total_tokens": 33960,
  "avg_latency_ms": 3608.7
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| llm_calls | `Integer` | 누적 LLM 호출 수 |
| llm_errors | `Integer` | 누적 LLM 오류 수 |
| prompt_tokens | `Integer` | 누적 프롬프트 토큰 |
| completion_tokens | `Integer` | 누적 응답 토큰 |
| total_tokens | `Integer` | 누적 총 토큰 |
| avg_latency_ms | `Decimal` | 평균 LLM 지연(ms) |

---

## 공통 에러 응답

모든 오류는 다음 형태로 반환한다.

```json
{
  "error": {
    "code": "llm_upstream_error",
    "message": "OpenAI request failed: ...",
    "requestId": "ae0c61bd80584ddd9ad233f6f643a173"
  }
}
```

### Error Codes

| code | HTTP | 설명 |
| --- | --- | --- |
| validation_error | 422 | 요청 검증 실패(필드 누락/형식 오류, 이미지 개수·MIME 위반, 임베딩 배치 초과) |
| payload_too_large | 413 | 이미지 용량 초과(장당 최대 10MB) |
| llm_upstream_error | 502 | OpenAI 호출 실패(타임아웃/5xx/레이트리밋, 재시도 후) |
| llm_refusal | 422 | LLM 이 구조화 응답을 거부 |
| embedding_error | 500 | 임베딩 계산 실패 |
| internal_error | 500 | 처리되지 않은 서버 오류 |

> 라우트 가드 오류(이미지 개수·용량·MIME, 배치 초과 등)도 위 표준 봉투로 통일되어 반환된다.
