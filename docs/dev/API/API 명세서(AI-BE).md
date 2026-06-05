# 공통 기반

## 아키텍처 원칙
- **AI 서버 = FastAPI, stateless 연산 서버.** DB 없음, 세션 저장 없음.
- **호출 방향: BE(Spring) → AI 단방향.** AI는 BE를 역호출하지 않음. 외부 미노출(`/internal/v1`), 토큰 검증은 BE가 이미 처리.
- **LLM = OpenAI** (GPT-5.5, 모델명 env로 분리). `temperature=0` + structured output으로 결정성 확보.
- **임베딩 = `BAAI/bge-m3`** (1024차원), AI 서버가 벡터만 생성. 코사인/저장/임계값은 BE(pgvector).

## BE ↔ AI 책임 분담
| 항목 | AI | BE |
|---|---|---|
| 멀티모달 분석·생성(제목/육하원칙/요약/키워드) | ✅ | |
| 카테고리 분류(코드), agencyType 힌트 | ✅ | ID 매핑 |
| 위험도 점수 | ✅ 산정 | 규칙 보정(선택) |
| 임베딩 벡터 생성 | ✅ | 저장·유사도·임계값 |
| 역지오코딩(좌표→주소) | | ✅ |
| 기관/부서 실인스턴스(관할 조회) | | ✅ |
| 중복 후보 1차 필터(반경/시간) | | ✅ |
| 챗봇 세션·메시지 저장, retrieval | | ✅ |

## 택소노미 (SSOT: `core/taxonomy.py`)
- **2단계, 코드 기반.** AI는 **리프 코드 1개만** enum으로 선택, 상위·부서·기관유형은 테이블에서 파생.
- 각 리프 보유 필드: `code / ko / parent / default_agency_type / default_department / 정의 / 포함예 / 제외예`
- 리프 세트(초안): `ILLEGAL_PARKING, ROAD_DAMAGE, TRASH_DUMPING, ANIMAL_CARCASS, NOISE, STREETLIGHT, DANGEROUS_FACILITY, FALL_RISK, DRUNK_PERSON, YOUTH_RISK, SUSPICIOUS, HOMELESS, FIRE_EMERGENCY, ETC_OTHER`
- **위험도 스케일 0~100.**

## 공통 응답 규약
- 모든 LLM 호출은 **OpenAI Structured Outputs(JSON Schema, enum 강제)** 사용 → 표기 흔들림·리스트 밖 값·필드 누락 차단.

---

# ① 구조화된 제보 생성 (Analyze)

### 구현 방법
멀티모달 1콜: 이미지(들) + 원문 텍스트 + BE가 준 주소 컨텍스트 → OpenAI Vision + Structured Output → 구조화 JSON. 임베딩은 같은 요청에서 함께 생성해 반환(왕복 절약).

### 구현 세부
- **입력 가공**: multipart 이미지 → base64 data URL로 OpenAI에 전달. `roadAddress/sido/sigungu/dong`을 프롬프트에 주입해 `where` 정확도↑.
- **분류**: 리프 `categoryCode` enum 강제 + `confidence`. 타이브레이크 규칙(동물사체→환경, 주취자→치안, 가로등→시설물)을 프롬프트에 명시. 애매 시 `ETC_OTHER`.
- **기관 힌트**: `suggestedAgencyType`은 택소노미 default에서 도출, 다부서 걸칠 때만 `agencyTypeReason`으로 override.
- **위험도**: LLM이 0~100 산정(카테고리 위험성·이미지 심각도·긴급성 반영). (선택) BE가 제보수·공감수·최근성으로 후보정.
- **허위/장난 탐지**: `falseReport{isSuspicious, score, reason}` — 이미지-텍스트 불일치/욕설/무관 이미지.
- **긴급 가드**: `emergencyGuide{isEmergency, message}` — 실제 화재/범죄/응급이면 앱 접수보다 112/119 우선 안내.
- **이미지 객체 인식**: `detectedObjects[]`.
- **결정성**: `temperature=0`, 동일 스키마.

### API 계약 — `POST /internal/v1/reports:analyze`
**요청** (`multipart/form-data`)
| field | type | 설명 |
|---|---|---|
| content | string | 원문 텍스트 |
| latitude / longitude | float | 좌표 |
| occurredAt | string? | 미입력 시 서버시각 |
| roadAddress, sido, sigungu, eupmyeondong | string? | BE 역지오코딩 결과 |
| images | file[] | 제보 이미지 |

**응답**
```json
{
  "title": "둔산동 갤러리아 앞 인도 파손으로 인한 보행 안전 위험",
  "contents": {
    "who":"보행 중인 시민","when":"2026-05-28T07:40:00",
    "where":"둔산동 갤러리아 앞 인도","what":"인도 블록 파손으로 낙상 위험",
    "how":"우천 물고임+보도블록 파손","why":"낙상·부상 가능성","summary":"..."
  },
  "keywords": ["인도 파손","보행 위험","낙상 위험"],
  "category": { "categoryCode":"ROAD_DAMAGE", "confidence":0.92 },
  "suggestedAgencyType": "지자체",
  "agencyTypeReason": null,
  "riskScore": 62.5,
  "analysis": {
    "detectedObjects": ["보도블록","균열","물고임"],
    "falseReport": { "isSuspicious":false, "score":8.2, "reason":"이미지-텍스트 연관성 높음" },
    "emergencyGuide": { "isEmergency":false, "message":null }
  },
  "embedding": [/* bge-m3 1024차원 */]
}
```
→ BE가 `categoryCode`로 `categoryId/parentCategory/departmentName`·실기관 매핑, `roadAddress` 등은 자기 값 사용, `embedding`은 중복판단·저장에 사용.

---

# ② 유사 제보 병합 (Embeddings)

### 구현 방법
AI는 **벡터 생성만**. 병합 판단 파이프라인은 BE가 소유. ①에서 신규 제보 임베딩은 이미 받으므로, 이 엔드포인트는 **백필·재계산용**.

### 구현 세부
- **모델**: `BAAI/bge-m3`, 1024차원. AI 서버 기동 시 1회 로드(싱글톤).
- **임베딩 대상 텍스트**: `title + summary + keywords` 결합(또는 정책 합의값) — ①과 ② 동일 규칙 사용해야 벡터 공간 일치.
- **정규화**: L2 normalize 후 반환 → BE는 내적=코사인.
- **BE 측 병합 로직(참고)**: ⓐ 반경 100m + 7일 + 동일 parent 카테고리로 후보 필터 → ⓑ 코사인 ≥ 임계값(예 0.80)이면 기존 이슈그룹 합류, 아니면 신규 → ⓒ 합류 시 reportCount/recentReportedAt 갱신. (DP-001/007/011, 10.3)

### API 계약 — `POST /internal/v1/embeddings`
**요청**
```json
{ "texts": ["둔산동 인도 파손으로 낙상 위험 ...", "..."] }
```
**응답**
```json
{ "model":"bge-m3", "dimension":1024, "embeddings": [[/* ... */],[/* ... */]] }
```

---

# ③ 챗봇 (2-스텝)

### 구현 방법
BE 주도 2-스텝 루프. AI는 stateless 생성기. 대화 맥락(`history`)·지식 맥락(`context`)은 **매 요청에 BE가 실어 보냄**.

### 구현 세부
- **Step 1 (plan)**: 질문+이력 → `action` enum 라우팅. `ANSWER_DIRECT`면 answer까지 반환해 1콜 종료(잡담·일반질문). 검색 필요 시 `params`만 반환.
- **Step 2 (answer)**: BE가 검색한 `context.reports` 기반 생성. **grounding 고정** — 주어진 사실만 사용, 없으면 "주변 제보 없음"으로 답하고 환각 금지. `usedReportIds` 반환.
- **history 윈도우**: BE가 최근 6~10턴만 전달.
- **긴급 가드**: 대화 중 응급 묘사 시 112/119 우선 안내.
- **결정성**: plan은 `temperature=0`+enum, answer는 자연스러움 위해 낮은 temperature(예 0.3).

### API 계약 — Step 1 `POST /internal/v1/chatbot:plan`
**요청**
```json
{ "question":"이 근처 위험한 제보 있어?",
  "history":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}],
  "userLocation":{"lat":36.36,"lng":127.34} }
```
**응답**
```json
{ "action":"SEARCH_NEARBY", "params":{"categoryCode":null,"radiusMeters":500}, "answer":null }
```
| action | params | BE 동작 |
|---|---|---|
| `ANSWER_DIRECT` | — | 검색 없음, `answer` 사용 후 종료 |
| `SEARCH_NEARBY` | categoryCode?, radiusMeters? | 반경 내 이슈 검색 |
| `MY_REPORTS` | status? | 유저 제보 조회 |

### API 계약 — Step 2 `POST /internal/v1/chatbot:answer`
**요청**
```json
{ "question":"이 근처 위험한 제보 있어?",
  "history":[/* ... */],
  "context":{ "scope":"SEARCH_NEARBY",
    "reports":[{"reportId":15,"title":"궁동 도로 파손","summary":"...","category":"도로 파손",
                "address":"유성구 궁동","riskScore":66.0,"distanceMeters":120,"recentReportedAt":"2026-06-05T15:35:00"}] } }
```
**응답**
```json
{ "answer":"네, 약 120m 거리에 '궁동 도로 파손' 이슈가 있어요. 위험도 66으로 주의가 필요해요.",
  "usedReportIds":[15] }
```

---

# 엔드포인트 총괄
| 기능 | 메서드 · 경로 | 형식 |
|---|---|---|
| ① 구조화 분석 | `POST /internal/v1/reports:analyze` | multipart |
| ② 임베딩 | `POST /internal/v1/embeddings` | json |
| ③ 챗봇 의도 | `POST /internal/v1/chatbot:plan` | json |
| ③ 챗봇 응답 | `POST /internal/v1/chatbot:answer` | json |
| 헬스체크 | `GET /health` | — |