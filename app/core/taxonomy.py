"""카테고리 택소노미 — 단일 진실 소스(SSOT).

대분류(8) · 소분류(47) + 가상코드(ETC_OTHER, INSUFFICIENT) 2종.
코드/한글/정의는 `docs/rules/database/<MAJOR>/<MINOR>.md` 폴더 구조를 권위 소스로 하며,
한글 라벨·정리 기준은 `docs/rules/index.md` 표를 참고해 정리했다.

다단계 분석 파이프라인이 이 파일을 단일 소스로 사용한다:
- 1차 LLM: 대분류 선택(`MajorCategory` enum)
- 2차 LLM: 소분류 선택(대분류별 동적 enum, `minors_of`)
- 3차 LLM: 기관종류(`AgencyType`) 결정 — 후보 부서는 SQLite 조직표에서 공급
`default_agency_type`/`default_department` 는 이제 **fallback** 이다(실값은 LLM+SQLite).

⚠️ 코드셋 변경 시 BE 의 카테고리 ID 매핑과 반드시 동기화할 것.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgencyType(StrEnum):
    """기관 유형 (suggestedAgencyType 의 허용값)."""

    LOCAL_GOV = "지자체"
    POLICE = "경찰"
    FIRE = "소방"
    HEALTH = "보건"


class MajorCategory(StrEnum):
    """대분류 (코드값). 한글 라벨은 MAJOR_KO 참조."""

    TRAFFIC = "TRAFFIC"
    INFRASTRUCTURE_ROAD = "INFRASTRUCTURE_ROAD"
    LIVING_INCONVENIENCE = "LIVING_INCONVENIENCE"
    LIFE_SAFETY = "LIFE_SAFETY"
    CONSTRUCTION_SITE = "CONSTRUCTION_SITE"
    PUBLIC_ORDER = "PUBLIC_ORDER"
    PUBLIC_HEALTH_WELFARE = "PUBLIC_HEALTH_WELFARE"
    ETC = "ETC"


MAJOR_KO: dict[MajorCategory, str] = {
    MajorCategory.TRAFFIC: "교통",
    MajorCategory.INFRASTRUCTURE_ROAD: "시설물",
    MajorCategory.LIVING_INCONVENIENCE: "생활불편",
    MajorCategory.LIFE_SAFETY: "생활안전",
    MajorCategory.CONSTRUCTION_SITE: "공사장",
    MajorCategory.PUBLIC_ORDER: "치안",
    MajorCategory.PUBLIC_HEALTH_WELFARE: "보건복지",
    MajorCategory.ETC: "기타",
}

MAJOR_ROLE: dict[MajorCategory, str] = {
    MajorCategory.TRAFFIC: "차량·주차·교통질서 관련 민원",
    MajorCategory.INFRASTRUCTURE_ROAD: "도로·보도·교통시설·공공시설 파손·고장",
    MajorCategory.LIVING_INCONVENIENCE: "쓰레기·광고물·소음·악취·오염 등 생활환경 민원",
    MajorCategory.LIFE_SAFETY: "침수·벌집·동물·화재·가스·전기 위험 등 안전 제보",
    MajorCategory.CONSTRUCTION_SITE: "공사장 안전·소음·균열·통행불편",
    MajorCategory.PUBLIC_ORDER: "취객·소란·범죄의심·방범불안 등 112 연계형 제보",
    MajorCategory.PUBLIC_HEALTH_WELFARE: "위생·식품·장애인 편의시설·취약계층 위험",
    MajorCategory.ETC: "위 대분류에 맞지 않는 기타·제보 불성립",
}

# 대분류별 후보 기관유형 — 3차 단계에서 조직표 후보 부서를 가져올 때의 union 휴리스틱.
_CANDIDATE_AGENCY_TYPES: dict[MajorCategory, tuple[AgencyType, ...]] = {
    MajorCategory.TRAFFIC: (AgencyType.LOCAL_GOV, AgencyType.POLICE),
    MajorCategory.INFRASTRUCTURE_ROAD: (AgencyType.LOCAL_GOV,),
    MajorCategory.LIVING_INCONVENIENCE: (AgencyType.LOCAL_GOV, AgencyType.HEALTH),
    MajorCategory.LIFE_SAFETY: (AgencyType.LOCAL_GOV, AgencyType.FIRE),
    MajorCategory.CONSTRUCTION_SITE: (AgencyType.LOCAL_GOV,),
    MajorCategory.PUBLIC_ORDER: (AgencyType.POLICE,),
    MajorCategory.PUBLIC_HEALTH_WELFARE: (AgencyType.HEALTH, AgencyType.LOCAL_GOV),
    MajorCategory.ETC: (AgencyType.LOCAL_GOV,),
}

# 가상 코드 — 폴더(룰북) 없음. INSUFFICIENT 는 라우팅 안 함(BE 반려 큐).
ETC_OTHER = "ETC_OTHER"
INSUFFICIENT = "INSUFFICIENT"
_VIRTUAL_CODES = frozenset({ETC_OTHER, INSUFFICIENT})


@dataclass(frozen=True)
class CategoryLeaf:
    code: str
    ko: str
    major: MajorCategory
    default_agency_type: AgencyType
    default_department: str  # fallback only — 실 부서는 LLM+SQLite
    definition: str


# --- 리프 정의 (47 + 가상 2) ---------------------------------------------------
# (code, ko, major, default_agency_type, default_department, definition)
_T, _I, _L, _S, _C, _P, _H, _E = (
    MajorCategory.TRAFFIC,
    MajorCategory.INFRASTRUCTURE_ROAD,
    MajorCategory.LIVING_INCONVENIENCE,
    MajorCategory.LIFE_SAFETY,
    MajorCategory.CONSTRUCTION_SITE,
    MajorCategory.PUBLIC_ORDER,
    MajorCategory.PUBLIC_HEALTH_WELFARE,
    MajorCategory.ETC,
)
_GOV, _POL, _FIRE, _HLT = (
    AgencyType.LOCAL_GOV,
    AgencyType.POLICE,
    AgencyType.FIRE,
    AgencyType.HEALTH,
)

_LEAF_SPECS: list[tuple[str, str, MajorCategory, AgencyType, str, str]] = [
    # 교통
    ("ILLEGAL_PARKING", "불법주정차", _T, _GOV, "경제교통과",
     "주정차 금지구역 등 불법 주정차(세부 위치별 분류는 하나로 통합)."),
    ("TRAFFIC_VIOLATION", "교통위반", _T, _POL, "경비교통과",
     "자동차·이륜차의 교통법규 위반."),
    ("ABANDONED_VEHICLE", "방치차량", _T, _GOV, "경제교통과",
     "장기 방치 차량, 번호판 훼손 차량 등."),
    ("PARKING_LOT_ISSUE", "주차장 불편", _T, _GOV, "경제교통과",
     "주차장 운영·주차질서·주차공간 불편."),
    ("PUBLIC_TRANSPORT_ISSUE", "대중교통 운행 불편", _T, _GOV, "경제교통과",
     "버스·택시·정류장 이용 불편."),
    # 시설물
    ("ROAD_DAMAGE", "도로 파손", _I, _GOV, "건설과",
     "포트홀·균열·함몰 등 노면 손상."),
    ("ROAD_FACILITY_DAMAGE", "도로시설 파손", _I, _GOV, "건설과",
     "난간·중앙분리대·방호울타리 등 도로 부속물 파손."),
    ("SIDEWALK_DAMAGE", "보도블록 파손", _I, _GOV, "건설과",
     "보도블록·보행로 파손·침하·들뜸·단차."),
    ("STREETLIGHT_FAILURE", "가로등 고장", _I, _GOV, "건설과",
     "가로등·보안등 소등·점멸·파손."),
    ("TRAFFIC_FACILITY_FAILURE", "교통시설물 고장", _I, _GOV, "경제교통과",
     "신호등·횡단보도 시설·표지판 고장."),
    ("MANHOLE_DRAIN_DAMAGE", "맨홀·배수구 파손", _I, _GOV, "건설과",
     "맨홀 뚜껑·빗물받이 덮개·배수구 파손·이탈·함몰·막힘."),
    ("PUBLIC_FACILITY_DAMAGE", "공공시설물 파손", _I, _GOV, "구조물관리과",
     "벤치·펜스·안내판 등 공공시설물 파손."),
    ("PUBLIC_USE_FACILITY_SAFETY", "다중이용시설 안전 문제", _I, _GOV, "구조물관리과",
     "다중이용시설 내 안전 위험."),
    ("OBSTRUCTION_ACCESS_BLOCKAGE", "장애물·통행 방해", _I, _GOV, "건설과",
     "도로 이용 방해·낙하물·적치물."),
    ("AGING_FACILITY_RISK", "노후 시설물 위험", _I, _GOV, "구조물관리과",
     "교량·육교·옹벽 등 노후 구조물 위험."),
    ("PARK_FACILITY_DAMAGE", "공원시설 파손", _I, _GOV, "녹지공원과",
     "공원·놀이터·체육시설 내 시설물 파손."),
    # 생활불편
    ("WASTE_AND_DEBRIS", "쓰레기·폐기물", _L, _GOV, "환경자원과",
     "쓰레기 무단투기·수거 불편·폐기물 방치."),
    ("ILLEGAL_ADVERTISEMENT", "불법광고물", _L, _GOV, "도시미관과",
     "현수막·전단지·불법 게시물."),
    ("ODOR", "악취", _L, _GOV, "환경자원과",
     "하수구·쓰레기·사업장 악취."),
    ("NOISE", "소음", _L, _GOV, "환경자원과",
     "일반 생활소음(공사장 소음은 공사장 대분류)."),
    ("AIR_POLLUTION_DUST", "대기오염·비산먼지", _L, _GOV, "환경자원과",
     "대기오염·비산먼지."),
    ("WATER_POLLUTION_WASTEWATER", "수질오염·오폐수", _L, _GOV, "환경자원과",
     "하천 오염·배수로 오염·오폐수."),
    ("ILLEGAL_BURNING", "불법소각", _L, _GOV, "환경자원과",
     "불법 소각(행위 기준 분리)."),
    ("LIGHT_POLLUTION", "빛공해", _L, _GOV, "환경자원과",
     "간판·조명·야간 빛 불편."),
    ("PET_NUISANCE", "반려동물 불편", _L, _GOV, "위생안전과",
     "배설물·목줄 미착용·짖음 등."),
    # 생활안전
    ("FLOODING_RISK", "침수 위험", _S, _GOV, "건설과",
     "침수·빗물받이 막힘."),
    ("SEWER_BACKFLOW", "하수도 역류", _S, _GOV, "건설과",
     "하수 역류·배수 불량."),
    ("RIVER_FACILITY_RISK", "하천 위험", _S, _GOV, "건설과",
     "하천 범람·제방 위험."),
    ("BEEHIVE_RISK", "벌집 위험", _S, _FIRE, "재난대응과",
     "벌집 제거 등 119 생활안전 연계."),
    ("STRAY_OR_DANGEROUS_ANIMAL", "유기동물·위험동물", _S, _GOV, "위생안전과",
     "유기동물·위협 동물."),
    ("FIRE_RISK", "화재위험", _S, _FIRE, "화재예방과",
     "화재 가능성·연기·불씨 등."),
    ("GAS_ELECTRIC_RISK", "가스·전기 위험", _S, _FIRE, "재난대응과",
     "가스 누출·전기 스파크·감전 위험."),
    # 공사장
    ("CONSTRUCTION_SAFETY_VIOLATION", "공사장 안전조치 미흡", _C, _GOV, "건축과",
     "안전펜스·표지·보행자 보호 미흡."),
    ("CONSTRUCTION_NOISE", "공사장 소음", _C, _GOV, "환경자원과",
     "공사장 소음(일반 소음과 분리)."),
    ("CONSTRUCTION_CRACK_DAMAGE", "공사로 인한 균열", _C, _GOV, "건축과",
     "건물·도로 균열, 피해 주장."),
    ("CONSTRUCTION_ACCESS_BLOCKAGE", "공사장 통행 불편", _C, _GOV, "건축과",
     "보행로 점유·우회 불편·도로 점용."),
    # 치안
    ("INTOXICATED_PERSON_CONCERN", "취객·주취자 불안", _P, _POL, "범죄예방대응과",
     "취객·주취자 관련 불안."),
    ("DISORDERLY_CONDUCT_DISPUTE", "행패소란·시비", _P, _POL, "범죄예방대응과",
     "행패소란·노상다툼·시비·소란."),
    ("SUSPICIOUS_ACTIVITY", "범죄의심·방범불안", _P, _POL, "범죄예방대응과",
     "배회 의심·방범 불안·범죄 의심."),
    ("ILLEGAL_FILMING_SUSPICION", "불법촬영 의심", _P, _POL, "여성청소년과",
     "불법촬영 의심(즉시 경찰 안내 가능)."),
    ("YOUTH_DELINQUENCY_DISTURBANCE", "청소년 비행·집단소란", _P, _POL, "여성청소년과",
     "청소년 비행·집단 소란."),
    # 보건복지
    ("ACCESSIBILITY_FACILITY_ISSUE", "장애인 편의시설 불편", _H, _GOV, "사회복지과",
     "경사로·점자블록·접근성 문제."),
    ("PUBLIC_HYGIENE_ISSUE", "공중위생 불량", _H, _HLT, "보건행정과",
     "공중화장실·업소 위생 등."),
    ("FOOD_HYGIENE_REPORT", "식품위생 신고", _H, _HLT, "보건행정과",
     "음식점·불량식품·위생 문제."),
    ("PEST_CONTROL_ISSUE", "해충 문제", _H, _HLT, "감염병관리센터",
     "모기·바퀴·방역 요청."),
    ("VULNERABLE_PERSON_RISK", "노약자 위험 상황", _H, _GOV, "사회복지과",
     "쓰러진 사람·보호 필요 상황."),
    ("YOUTH_RISK_ENVIRONMENT", "청소년 위험 환경", _H, _GOV, "가정복지과",
     "통학로·놀이터·유해환경."),
    # 기타 (가상)
    (ETC_OTHER, "기타", _E, _GOV, "시민봉사과",
     "유효하나 위 유형에 맞지 않는 기타 제보(억지 분류 금지)."),
    (INSUFFICIENT, "제보 불성립", _E, _GOV, "시민봉사과",
     "내용·이미지 불충분/무관/확인불가하여 제보로 성립하지 않음."),
]

_LEAVES: list[CategoryLeaf] = [
    CategoryLeaf(code=c, ko=k, major=m, default_agency_type=a, default_department=d, definition=df)
    for (c, k, m, a, d, df) in _LEAF_SPECS
]

# --- 인덱스 & 파생 ------------------------------------------------------------
CATEGORIES: dict[str, CategoryLeaf] = {leaf.code: leaf for leaf in _LEAVES}

# enum 강제용 (pydantic 스키마 / OpenAI Structured Outputs 의 enum 제약).
CategoryCode = StrEnum("CategoryCode", {code: code for code in CATEGORIES})

_MAJOR_TO_LEAVES: dict[MajorCategory, list[CategoryLeaf]] = {}
for _leaf in _LEAVES:
    _MAJOR_TO_LEAVES.setdefault(_leaf.major, []).append(_leaf)


def leaf_codes() -> list[str]:
    """허용 리프 코드 목록(가상 코드 포함)."""
    return list(CATEGORIES.keys())


def major_codes() -> list[MajorCategory]:
    return list(MajorCategory)


def get_leaf(code: str) -> CategoryLeaf:
    try:
        return CATEGORIES[code]
    except KeyError as exc:
        raise KeyError(f"unknown category code: {code!r}") from exc


def parent_of(code: str) -> MajorCategory:
    return get_leaf(code).major


def minors_of(major: MajorCategory) -> list[CategoryLeaf]:
    """대분류에 속한 소분류 리프 목록(정의 순서 유지)."""
    return list(_MAJOR_TO_LEAVES.get(major, []))


def is_virtual(code: str) -> bool:
    return code in _VIRTUAL_CODES


def agency_type_of(code: str) -> AgencyType:
    return get_leaf(code).default_agency_type


def department_of(code: str) -> str:
    return get_leaf(code).default_department


def candidate_agency_types(major: MajorCategory) -> tuple[AgencyType, ...]:
    """3차 단계에서 후보 부서를 조회할 기관유형 union."""
    return _CANDIDATE_AGENCY_TYPES.get(major, (AgencyType.LOCAL_GOV,))


def major_block() -> str:
    """1차(대분류) 프롬프트용 블록."""
    lines = [f"- {m.value} ({MAJOR_KO[m]}): {MAJOR_ROLE[m]}" for m in MajorCategory]
    return "\n".join(lines)


def minor_block(major: MajorCategory) -> str:
    """2차(소분류) 프롬프트용 블록 — 해당 대분류의 소분류만."""
    lines = [f"- {leaf.code} ({leaf.ko}): {leaf.definition}" for leaf in minors_of(major)]
    return "\n".join(lines)
