"""카테고리 택소노미 — 단일 진실 소스(SSOT).

AI는 **리프 코드 1개만** 선택하고(enum 강제), 상위 카테고리·기본 부서·기관유형은
이 테이블에서 결정론적으로 역산한다. 분류 스키마(② report)·프롬프트 few-shot·
챗봇 SEARCH_NEARBY 의 categoryCode 가 모두 이 파일을 단일 소스로 사용한다.

⚠️ 코드셋 변경 시 BE 의 카테고리 ID 매핑과 반드시 동기화할 것.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgencyType(StrEnum):
    """기관 유형 (suggestedAgencyType 의 허용값)."""

    LOCAL_GOV = "지자체"
    POLICE = "경찰"
    FIRE = "소방"


class ParentCategory(StrEnum):
    """대분류 (PRD AI-002)."""

    PUBLIC_SAFETY = "치안"
    TRAFFIC = "교통"
    ENVIRONMENT = "환경"
    FACILITY = "시설물"
    LIVING = "생활불편"
    DISASTER = "재난안전"
    WELFARE = "복지"
    ETC = "기타"


@dataclass(frozen=True)
class CategoryLeaf:
    code: str
    ko: str
    parent: ParentCategory
    default_agency_type: AgencyType
    default_department: str
    definition: str
    includes: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)


# --- 리프 정의 (14종) ---------------------------------------------------------
_LEAVES: list[CategoryLeaf] = [
    CategoryLeaf(
        code="ILLEGAL_PARKING",
        ko="불법주정차",
        parent=ParentCategory.TRAFFIC,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="교통행정과",
        definition="주정차 금지구역·소화전·횡단보도 앞 등에 정차/주차된 차량.",
        includes=["횡단보도 앞 차량", "소화전 앞 주차", "이중주차로 통행 방해"],
        excludes=["사고로 멈춘 차량은 SUSPICIOUS/긴급", "도로 자체 손상은 ROAD_DAMAGE"],
    ),
    CategoryLeaf(
        code="ROAD_DAMAGE",
        ko="도로 파손",
        parent=ParentCategory.TRAFFIC,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="도로관리과",
        definition="포트홀·도로/인도 균열·보도블록 파손 등 노면 손상.",
        includes=["포트홀", "보도블록 깨짐", "맨홀 뚜껑 파손"],
        excludes=["가로등 손상은 STREETLIGHT", "낙상 유발 빙판/계단은 FALL_RISK"],
    ),
    CategoryLeaf(
        code="TRASH_DUMPING",
        ko="쓰레기 무단투기",
        parent=ParentCategory.ENVIRONMENT,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="청소행정과",
        definition="생활폐기물·대형폐기물의 무단 투기 및 적치.",
        includes=["봉투 미사용 쓰레기 더미", "대형 폐가구 무단 배출"],
        excludes=["동물 사체는 ANIMAL_CARCASS", "건축 적치물 위험은 DANGEROUS_FACILITY"],
    ),
    CategoryLeaf(
        code="ANIMAL_CARCASS",
        ko="동물 사체",
        parent=ParentCategory.ENVIRONMENT,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="청소행정과",
        definition="도로·보도 등에 방치된 동물 사체(로드킬 포함).",
        includes=["도로 위 로드킬", "보도 옆 죽은 동물"],
        excludes=["도로 위에 있어도 교통 아님 → 환경으로 분류", "살아있는 유기동물은 ETC_OTHER"],
    ),
    CategoryLeaf(
        code="NOISE",
        ko="소음",
        parent=ParentCategory.ENVIRONMENT,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="환경과",
        definition="공사·업소·차량 등으로 인한 생활 소음.",
        includes=["야간 공사 소음", "상가 확성기 소음"],
        excludes=["주취 소란 동반은 DRUNK_PERSON"],
    ),
    CategoryLeaf(
        code="STREETLIGHT",
        ko="가로등 고장",
        parent=ParentCategory.FACILITY,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="도시안전과",
        definition="가로등·보안등 소등·점멸·파손.",
        includes=["가로등 꺼짐", "보안등 깜빡임"],
        excludes=["조명 어두워 불안한 치안 우려는 SUSPICIOUS"],
    ),
    CategoryLeaf(
        code="DANGEROUS_FACILITY",
        ko="위험 시설물",
        parent=ParentCategory.FACILITY,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="시설관리과",
        definition="붕괴/추락/누전 우려가 있는 시설물·구조물·적치물.",
        includes=["기울어진 옹벽", "떨어질 듯한 간판", "노출된 전선"],
        excludes=["노면 파손은 ROAD_DAMAGE", "화재 진행 중은 FIRE_EMERGENCY"],
    ),
    CategoryLeaf(
        code="FALL_RISK",
        ko="낙상 위험",
        parent=ParentCategory.LIVING,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="시설관리과",
        definition="빙판·미끄럼·계단 등 보행자 낙상 유발 환경.",
        includes=["결빙된 보도", "난간 없는 계단"],
        excludes=["보도블록 파손 자체는 ROAD_DAMAGE"],
    ),
    CategoryLeaf(
        code="DRUNK_PERSON",
        ko="주취자",
        parent=ParentCategory.PUBLIC_SAFETY,
        default_agency_type=AgencyType.POLICE,
        default_department="관할 지구대",
        definition="음주 후 소란·노상 방치·위협 행위.",
        includes=["길에 쓰러진 취객", "취중 시비"],
        excludes=["단순 노숙은 HOMELESS", "복지 대상 판단은 HOMELESS"],
    ),
    CategoryLeaf(
        code="YOUTH_RISK",
        ko="청소년 위험",
        parent=ParentCategory.PUBLIC_SAFETY,
        default_agency_type=AgencyType.POLICE,
        default_department="관할 지구대",
        definition="청소년 비행·탈선·유해환경 노출 우려.",
        includes=["심야 배회", "유해업소 출입 정황"],
        excludes=["성인 주취는 DRUNK_PERSON"],
    ),
    CategoryLeaf(
        code="SUSPICIOUS",
        ko="수상한 상황",
        parent=ParentCategory.PUBLIC_SAFETY,
        default_agency_type=AgencyType.POLICE,
        default_department="관할 지구대",
        definition="신고 애매하나 불안한 정황(미행·은신·어두운 골목 등).",
        includes=["골목에 숨은 사람 같음", "야간 우범 불안"],
        excludes=["실제 범죄 진행 중은 emergencyGuide(112)로 안내"],
    ),
    CategoryLeaf(
        code="HOMELESS",
        ko="노숙",
        parent=ParentCategory.WELFARE,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="복지정책과",
        definition="노숙인 보호·복지 지원이 필요한 상황.",
        includes=["역사/지하도 노숙", "한파 속 노상 취침"],
        excludes=["음주 소란 동반은 DRUNK_PERSON"],
    ),
    CategoryLeaf(
        code="FIRE_EMERGENCY",
        ko="화재/응급",
        parent=ParentCategory.DISASTER,
        default_agency_type=AgencyType.FIRE,
        default_department="119안전센터",
        definition="화재·연기·붕괴·응급환자 등 즉시 대응이 필요한 상황.",
        includes=["건물 연기", "쓰러진 사람", "가스 누출 냄새"],
        excludes=["대부분 emergencyGuide(119) 우선 안내 대상"],
    ),
    CategoryLeaf(
        code="ETC_OTHER",
        ko="기타",
        parent=ParentCategory.ETC,
        default_agency_type=AgencyType.LOCAL_GOV,
        default_department="민원실",
        definition="위 유형에 해당하지 않거나 분류가 모호한 제보.",
        includes=["분류 애매", "이미지/텍스트 불충분"],
        excludes=["억지로 끼워맞추지 말고 여기로 분류"],
    ),
]

# --- 인덱스 & 파생 ------------------------------------------------------------
CATEGORIES: dict[str, CategoryLeaf] = {leaf.code: leaf for leaf in _LEAVES}

# enum 강제용 (pydantic 스키마 / OpenAI Structured Outputs 의 enum 제약에 사용)
CategoryCode = StrEnum("CategoryCode", {code: code for code in CATEGORIES})

# 경계 케이스 타이브레이크 규칙 (프롬프트에 명시) — 일관 분류의 핵심.
TIE_BREAK_RULES: list[str] = [
    "도로 위 동물 사체 → 교통이 아니라 ANIMAL_CARCASS(환경).",
    "성인 주취 소란 → 복지가 아니라 DRUNK_PERSON(치안).",
    "가로등/조명 고장 → 교통이 아니라 STREETLIGHT(시설물).",
    "조명이 어두워 '불안'한 치안 우려 → STREETLIGHT 가 아니라 SUSPICIOUS(치안).",
    "보도블록 파손 자체 → ROAD_DAMAGE, 그로 인한 빙판/미끄럼 → FALL_RISK.",
    "분류가 모호하거나 이미지/텍스트가 무관·불충분 → 억지 분류 금지, ETC_OTHER.",
]


def leaf_codes() -> list[str]:
    """허용 리프 코드 목록."""
    return list(CATEGORIES.keys())


def get_leaf(code: str) -> CategoryLeaf:
    try:
        return CATEGORIES[code]
    except KeyError as exc:
        raise KeyError(f"unknown category code: {code!r}") from exc


def parent_of(code: str) -> ParentCategory:
    return get_leaf(code).parent


def department_of(code: str) -> str:
    return get_leaf(code).default_department


def agency_type_of(code: str) -> AgencyType:
    return get_leaf(code).default_agency_type


def few_shot_block() -> str:
    """프롬프트 주입용 카테고리 설명 블록 (코드/한글/정의/포함·제외)."""
    lines: list[str] = []
    for leaf in _LEAVES:
        lines.append(
            f"- {leaf.code} ({leaf.ko}, 대분류={leaf.parent.value}): {leaf.definition}"
        )
        if leaf.includes:
            lines.append(f"    · 포함: {', '.join(leaf.includes)}")
        if leaf.excludes:
            lines.append(f"    · 제외: {'; '.join(leaf.excludes)}")
    lines.append("")
    lines.append("[타이브레이크 규칙]")
    lines.extend(f"- {rule}" for rule in TIE_BREAK_RULES)
    return "\n".join(lines)
