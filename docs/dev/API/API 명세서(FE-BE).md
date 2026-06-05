---

---
!![[API 명세서.base]]


> [!note]+ # API Template
> ### Example request
> 
> `GET /api/`
> 
> ### **Headers**
> 
> | **Header** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> | Authorization | `String` | Yes | `Bearer {accessToken}` |
> 
> ### **Query Parameters**
> 
> | **Parameter** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> |   |   |   |   |
> 
> ### **Path Parameters**
> 
> | **Parameter** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> |   |   |   |   |
> 
> ### Request Body
> 
> ```json
> {
> 	"key1" : "string",
> 	"key2" : number,
>   "key3" : boolean
> }
> ```
> 
> ### Request Fields
> 
> | **Field** | **Type** | **Description** |
> | --- | --- | --- |
> |   |   |   |
> 
> ### Response Body
> 
> ```json
> {
>     "key1" : "string",
>     "key2" : number,
>     "key3" : boolean
> }
> ```
> 
> ### Response Fields
> 
> | **Field** | **Type** | **Description** |
> | --- | --- | --- |
> |   |   |   |

> [!note]+ # Example
> ### Example request
> 
> `POST /api/playlists/open-ply`
> 
> ### **Headers**
> 
> | **Header** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> |   |   |   |   |
> 
> ### **Query Parameters**
> 
> | **Parameter** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> |   |   |   |   |
> 
> ### **Path Parameters**
> 
> | **Parameter** | **Type** | **Required** | **Description** |
> | --- | --- | --- | --- |
> |   |   |   |   |
> 
> ### Request Body
> 
> ```json
> {
>   "title" : "우리 같이 만드는 플리",
>   "description" : "자유롭게 곡을 추가해주세요.",
>   "isCommentPrivate" : false,
>   "password" : "password123"
> }
> ```
> 
> ### Request Fields
> 
> | **Field** | **Type** | **Description** |
> | --- | --- | --- |
> | title | string | 플레이리스트 제목 (필수, 최대 50자) |
> | description | string | 플레이리스트 설명 (최대 300자) |
> | isCommentPrivate | boolean | 코멘트 비공개 여부 |
> | password | string | 복제용 비밀번호 (최대 20자) |
> 
> ### Response Body
> 
> - **회원 (마이 플리)**
> 
> ```json
> {
>     "status": 201,
>     "message": "오픈 플리 생성 성공",
>     "data": {
>         "playlistUid": "1d8b2799-d14a-4c25-9ef4-9b7d40e6a6c6",
>         "title": "테스트 제목1",
>         "description": "테스트 내용1",
>         "coverImageUrl": null,
>         "isCommentPrivate": true,
>         "ownerNickname": null
>     }
> }
> ```
> 
> ### Response Fields
> 
> | **Field** | **Type** | **Description** |
> | --- | --- | --- |
> | playlistUid | string | 플레이리스트 고유 UID (공유용) |
> | title | string | 플레이리스트 제목 |
> | description | string | 플레이리스트 설명 |
> | coverImageUrl | string | 커버 이미지 URL |
> | isCommentPrivate | boolean | 코멘트 비공개 설정 여부 |
> | ownerNickname | string | 생성자 닉네임 (오픈 플리는 null) |
> 

> [!note]+ # 백엔드 Response template
> > [!note]+ 공통 response (BaseResponse<T>)
> > ```json
> > {
> >   "status": 200,
> >   "message": "유저 조회 성공",
> >   "data": {
> >     "userId": 1,
> >     "email": "dev@example.com",
> >     "nickname": "backend_master"
> >   }
> > }
> > ```
> 
> > [!note]+ 페이지네이션 Response (BaseResponse<PageResponse<T>>)
> > ```json
> > {
> >   "status": 201,
> >   "message": "게시글 조회 성공",
> >   "data": {
> >     "content": [
> >       { "id": 1, "title": "첫 번째 게시글" },
> >       { "id": 2, "title": "두 번째 게시글" }
> >     ],
> >     "pageNumber": 0,
> >     "pageSize": 10,
> >     "totalElements": 42,
> >     "totalPages": 5,
> >     "hasNext": true
> >   }
> > }
> > ```





| **도메인** | **기능** | **토큰유무** | **HTTP 메서드** | **API Path** |
| --- | --- | --- | --- | --- |
| **인증/사용자 (Auth/User)** | 카카오 로그인 | X | POST | /api/v1/auth/login/kakao |
|   | 토큰 재발급 (Refresh) | X | POST | /api/v1/auth/refresh |
|   | 서비스 로그아웃 | O | POST | /api/v1/auth/logout |
|   | 회원 탈퇴 (데이터 처리) | O | DELETE | /api/v1/users/me |
|   | 내 정보 조회 | O | GET | /api/v1/users/me |
|   | 내 정보 수정 (닉네임 등) | O | PATCH | /api/v1/users/me |
|   | 사용자 약관/민감정보 동의 갱신 | O | PUT | /api/v1/users/me/consents |
|   | 푸시 알림용 FCM 토큰 등록/수정 | O | PUT | /api/v1/users/me/fcm-token |
|   |   |   |   |   |
|   |   |   |   |   |
|   |   |   |   |   |
| **AI (AI Analysis)** | 사진 기반 객체 인식 및 유형 분류 | O | POST | /api/v1/ai/analyze-image |
|   | 제보 내용 자동 요약/초안 생성 | O | POST | /api/v1/ai/generate-draft |
| **제보 (Report)** | 제보용 이미지 업로드 (S3 등) | O | POST | /api/v1/reports/images |
|   | 신규 제보 최종 등록 | O | POST | /api/v1/reports |
|   | 지도 핀/클러스터용 반경 내 제보 조회 | X | GET | /api/v1/reports |
|   | 위험 밀집도(히트맵) 데이터 조회 | X | GET | /api/v1/reports/heatmap |
|   | 제보 상세 정보 조회 | X | GET | /api/v1/reports/{reportId} |
|   | 내 제보 내역 조회 (필터/페이징) | O | GET | /api/v1/users/me/reports |
|   | 등록 전 제보 취소/삭제 | O | DELETE | /api/v1/reports/{reportId} |
| **이슈 그룹 <br>(Issue Group)**<br> | 통합 중복 이슈(클러스터) 목록 조회 | X | GET | /api/v1/issues |
|   | 특정 통합 이슈 상세 정보 조회 | X | GET | /api/v1/issues/{issueId} |
| **공감/확인 (Reaction)** | 제보 상태 확인 투표 (YES/NO/모름) | O | POST | /api/v1/reports/{reportId}/reactions |
|   | 잘못 누른 투표 취소 | O | DELETE | /api/v1/reports/{reportId}/reactions |
| **알림 (Notification)** | 내 푸시 알림 이력 조회 | O | GET | /api/v1/notifications |
|   | 특정 알림 읽음 처리 | O | PATCH | /api/v1/notifications/{notificationId}/read |
|   | 모든 알림 읽음 처리 | O | PATCH | /api/v1/notifications/read-all |
| **챗봇 (Chatbot)** | 새 챗봇 세션(방) 생성 | O | POST | /api/v1/chatbots/sessions |
|   | 내 챗봇 세션 목록 조회 | O | GET | /api/v1/chatbots/sessions |
|   | 특정 세션의 이전 채팅 내역 조회 | O | GET | /api/v1/chatbots/sessions/{sessionId}/messages |
|   | 챗봇 메시지 전송 및 AI 응답 수신 | O | POST | /api/v1/chatbots/sessions/{sessionId}/messages |
| **관리자/공무원 (Admin)** | 관할 구역/부서의 제보 목록 전체 조회 | O | GET | /api/v1/admin/reports |
|   | 관리자용 제보 상세 조회 | O | GET | /api/v1/admin/reports/{reportId} |
|   | 제보 처리 상태 변경 (접수, 완료 등) | O | PATCH | /api/v1/admin/reports/{reportId}/status |
|   | 제보 관할 부서 수동 이관(라우팅) | O | PATCH | /api/v1/admin/reports/{reportId}/department |
|   | 제보 내부 처리 메모 작성 | O | POST | /api/v1/admin/reports/{reportId}/memos |
|   | 허위/무관 제보 반려 및 삭제 처리 | O | DELETE | /api/v1/admin/reports/{reportId} |
|   | 수동 제보 병합 (특정 이슈 그룹으로) | O | POST | /api/v1/admin/issues/{issueId}/merge |
|   | 대시보드 메인 통계 요약 조회 | O | GET | /api/v1/admin/dashboard/statistics |
|   | 지역/기간/카테고리별 차트용 추이 조회 | O | GET | /api/v1/admin/dashboard/trends |
| 카테고리 | 제보 카테고리 목록 조회 (대/소분류) | X | GET | /api/v1/categories |
|   | 처리 기관 목록 조회 | X | GET | /api/v1/agencies |
|   | 소속 부서 목록 조회 | X | GET | /api/v1/departments |

