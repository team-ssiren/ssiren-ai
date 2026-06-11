# 대분류

| 카테고리 이름 | 카테고리 코드 | 역할 |
| --- | --- | --- |
| 교통 | `TRAFFIC` | 차량·주차·교통질서 관련 민원 |
| 시설물 | `INFRASTRUCTURE_ROAD` | 도로, 보도, 교통시설, 공공시설 파손·고장 |
| 생활불편 | `LIVING_INCONVENIENCE` | 쓰레기, 광고물, 소음, 악취, 오염 등 생활환경 민원 |

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