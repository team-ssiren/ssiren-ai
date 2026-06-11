# 대분류

| 카테고리 이름 | 카테고리 코드 | 역할 |
| --- | --- | --- |
| 교통 | `TRAFFIC` | 차량·주차·교통질서 관련 민원 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 도로, 보도, 교통시설, 공공시설 파손·고장 |
| 생활불편 | `LIVING_INCONVENIENCE` | 쓰레기, 광고물, 소음, 악취, 오염 등 생활환경 민원 |
| 생활안전 | `LIFE_SAFETY` | 침수, 벌집, 동물, 화재·가스·전기 위험 등 안전 제보 |
| 공사장 | `CONSTRUCTION_SITE` | 공사장 안전, 소음, 균열, 통행불편 |
| 치안 | `PUBLIC_ORDER` | 취객, 소란, 범죄의심, 방범불안 등 112 연계형 제보 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 위생, 식품, 장애인 편의시설, 취약계층 위험 |
| 기타 | `ETC` | 이외의 항목 |

## 소분류

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 교통 | `TRAFFIC` | 불법주정차 | `ILLEGAL_PARKING` | 세부 위치별 분류는 제거하고 하나로 통합 |
| 교통 | `TRAFFIC` | 교통위반 | `TRAFFIC_VIOLATION` | 자동차·이륜차 위반을 하나로 통합 |
| 교통 | `TRAFFIC` | 방치차량 | `ABANDONED_VEHICLE` | 장기 방치 차량, 번호판 훼손 차량 등 |
| 교통 | `TRAFFIC` | 주차장 불편 | `PARKING_LOT_ISSUE` | 주차장 운영, 주차질서, 주차공간 불편 |
| 교통 | `TRAFFIC` | 대중교통 운행 불편 | `PUBLIC_TRANSPORT_ISSUE` | 버스·택시·정류장 이용 불편 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 시설물 | `INFRASTRUCTURE_ROAD` | 도로 파손 | `ROAD_DAMAGE` | 포트홀, 균열, 함몰을 하나로 통합 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 도로시설 파손 | `ROAD_FACILITY_DAMAGE` | 난간, 중앙분리대, 방호울타리 등 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 보도블록 파손 | `SIDEWALK_DAMAGE` | 보도블록, 보행로 파손 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 가로등 고장 | `STREETLIGHT_FAILURE` | 보안등 포함 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 교통시설물 고장 | `TRAFFIC_FACILITY_FAILURE` | 신호등, 횡단보도 시설, 표지판을 통합 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 맨홀·배수구 파손 | `MANHOLE_DRAIN_DAMAGE` | 맨홀, 빗물받이 덮개, 배수구 파손 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 공공시설물 파손 | `PUBLIC_FACILITY_DAMAGE` | 벤치, 펜스, 안내판 등 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 다중이용시설 안전 문제 | `PUBLIC_USE_FACILITY_SAFETY` | 다중이용시설 내 안전 위험 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 장애물·통행 방해 | `OBSTRUCTION_ACCESS_BLOCKAGE` | 도로 이용 방해, 낙하물, 적치물 통합 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 노후 시설물 위험 | `AGING_FACILITY_RISK` | 교량, 육교, 옹벽, 노후 구조물 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 공원시설 파손 | `PARK_FACILITY_DAMAGE` | 공원, 놀이터, 체육시설 파손 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 생활불편 | `LIVING_INCONVENIENCE` | 쓰레기·폐기물 | `WASTE_AND_DEBRIS` | 쓰레기 무단투기, 수거 불편, 폐기물 방치를 통합 |
| 생활불편 | `LIVING_INCONVENIENCE` | 불법광고물 | `ILLEGAL_ADVERTISEMENT` | 현수막, 전단지, 불법 게시물 포함 |
| 생활불편 | `LIVING_INCONVENIENCE` | 악취 | `ODOR` | 하수구, 쓰레기, 사업장 악취 등 |
| 생활불편 | `LIVING_INCONVENIENCE` | 소음 | `NOISE` | 일반 생활소음. 공사장 소음은 공사장 대분류로 분리 |
| 생활불편 | `LIVING_INCONVENIENCE` | 대기오염·비산먼지 | `AIR_POLLUTION_DUST` | 대기오염, 비산먼지를 통합 |
| 생활불편 | `LIVING_INCONVENIENCE` | 수질오염·오폐수 | `WATER_POLLUTION_WASTEWATER` | 하천 오염, 배수로 오염, 오폐수 |
| 생활불편 | `LIVING_INCONVENIENCE` | 불법소각 | `ILLEGAL_BURNING` | 악취·대기오염과 겹치지만 행위 기준으로 분리 |
| 생활불편 | `LIVING_INCONVENIENCE` | 빛공해 | `LIGHT_POLLUTION` | 간판, 조명, 야간 빛 불편 |
| 생활불편 | `LIVING_INCONVENIENCE` | 반려동물 불편 | `PET_NUISANCE` | 배설물, 목줄 미착용, 짖음 등 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 생활안전 | `LIFE_SAFETY` | 침수 위험 | `FLOODING_RISK` | 침수, 빗물받이 막힘을 통합 |
| 생활안전 | `LIFE_SAFETY` | 하수도 역류 | `SEWER_BACKFLOW` | 하수 역류, 배수 불량 |
| 생활안전 | `LIFE_SAFETY` | 하천 위험 | `RIVER_FACILITY_RISK` | 하천 범람, 제방 위험 |
| 생활안전 | `LIFE_SAFETY` | 벌집 위험 | `BEEHIVE_RISK` | 119 생활안전 연계 |
| 생활안전 | `LIFE_SAFETY` | 유기동물·위험동물 | `STRAY_OR_DANGEROUS_ANIMAL` | 유기동물, 위협 동물 통합 |
| 생활안전 | `LIFE_SAFETY` | 화재위험 | `FIRE_RISK` | 화재 가능성, 연기, 불씨 등 |
| 생활안전 | `LIFE_SAFETY` | 가스·전기 위험 | `GAS_ELECTRIC_RISK` | 가스 누출, 전기 스파크, 감전 위험 통합 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 공사장 | `CONSTRUCTION_SITE` | 공사장 안전조치 미흡 | `CONSTRUCTION_SAFETY_VIOLATION` | 안전펜스, 표지, 보행자 보호 미흡 |
| 공사장 | `CONSTRUCTION_SITE` | 공사장 소음 | `CONSTRUCTION_NOISE` | 일반 소음과 분리 |
| 공사장 | `CONSTRUCTION_SITE` | 공사로 인한 균열 | `CONSTRUCTION_CRACK_DAMAGE` | 건물 균열, 도로 균열, 피해 주장 |
| 공사장 | `CONSTRUCTION_SITE` | 공사장 통행 불편 | `CONSTRUCTION_ACCESS_BLOCKAGE` | 보행로 점유, 우회 불편, 도로 점용 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 치안 | `PUBLIC_ORDER` | 취객·주취자 불안 | `INTOXICATED_PERSON_CONCERN` | 취객, 주취자 관련 불안 |
| 치안 | `PUBLIC_ORDER` | 행패소란·시비 | `DISORDERLY_CONDUCT_DISPUTE` | 행패소란, 노상다툼, 시비, 소란 통합 |
| 치안 | `PUBLIC_ORDER` | 범죄의심·방범불안 | `SUSPICIOUS_ACTIVITY` | 배회 의심, 방범 불안, 범죄 의심 통합 |
| 치안 | `PUBLIC_ORDER` | 불법촬영 의심 | `ILLEGAL_FILMING_SUSPICION` | 즉시 경찰 안내 필요 가능 |
| 치안 | `PUBLIC_ORDER` | 청소년 비행·집단소란 | `YOUTH_DELINQUENCY_DISTURBANCE` | 청소년 비행, 집단 소란 통합 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 장애인 편의시설 불편 | `ACCESSIBILITY_FACILITY_ISSUE` | 경사로, 점자블록, 접근성 문제 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 공중위생 불량 | `PUBLIC_HYGIENE_ISSUE` | 공중화장실, 업소 위생 등 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 식품위생 신고 | `FOOD_HYGIENE_REPORT` | 음식점, 불량식품, 위생 문제 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 해충 문제 | `PEST_CONTROL_ISSUE` | 모기, 바퀴, 방역 요청 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 노약자 위험 상황 | `VULNERABLE_PERSON_RISK` | 쓰러진 사람, 보호 필요 상황 |
| 보건복지 | `PUBLIC_HEALTH_WELFARE` | 청소년 위험 환경 | `YOUTH_RISK_ENVIRONMENT` | 통학로, 놀이터, 유해환경 |

| 대분류 | 대분류 코드 | 소분류 이름 | 소분류 코드 | 병합/정리 기준 |
| --- | --- | --- | --- | --- |
| 기타 | `ETC` | 기타 | `ETC_OTHER` | 이외의 기타 항목 |
| 기타 | `ETC` | 제보 불성립 | `INSUFFICIENT` | 불충분한 제보 |