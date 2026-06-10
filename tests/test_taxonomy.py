"""Phase 0-3: taxonomy SSOT integrity and reverse-lookups."""

from app.core.taxonomy import (
    CATEGORIES,
    AgencyType,
    CategoryCode,
    ParentCategory,
    agency_type_of,
    department_of,
    few_shot_block,
    get_leaf,
    leaf_codes,
    parent_of,
)

EXPECTED_LEAVES = {
    "ILLEGAL_PARKING",
    "ROAD_DAMAGE",
    "TRASH_DUMPING",
    "ANIMAL_CARCASS",
    "NOISE",
    "STREETLIGHT",
    "DANGEROUS_FACILITY",
    "FALL_RISK",
    "DRUNK_PERSON",
    "YOUTH_RISK",
    "SUSPICIOUS",
    "HOMELESS",
    "FIRE_EMERGENCY",
    "ETC_OTHER",
    "INSUFFICIENT",
}


def test_leaf_set_is_exact():
    assert set(leaf_codes()) == EXPECTED_LEAVES
    assert len(CATEGORIES) == 15


def test_enum_matches_categories():
    assert {c.value for c in CategoryCode} == set(CATEGORIES.keys())


def test_every_leaf_well_formed():
    for code, leaf in CATEGORIES.items():
        assert leaf.code == code
        assert leaf.ko
        assert leaf.definition
        assert isinstance(leaf.parent, ParentCategory)
        assert isinstance(leaf.default_agency_type, AgencyType)
        assert leaf.default_department


def test_reverse_lookups():
    assert parent_of("ROAD_DAMAGE") is ParentCategory.TRAFFIC
    assert agency_type_of("DRUNK_PERSON") is AgencyType.POLICE
    assert agency_type_of("FIRE_EMERGENCY") is AgencyType.FIRE
    assert department_of("ANIMAL_CARCASS") == "청소행정과"


def test_tie_break_mappings():
    # 도로 위 동물 사체 → 환경
    assert parent_of("ANIMAL_CARCASS") is ParentCategory.ENVIRONMENT
    # 주취자 → 치안
    assert parent_of("DRUNK_PERSON") is ParentCategory.PUBLIC_SAFETY
    # 가로등 → 시설물
    assert parent_of("STREETLIGHT") is ParentCategory.FACILITY


def test_etc_and_insufficient_are_distinct_under_etc():
    # 유효 기타 vs 제보 불성립 — 둘 다 '기타' 하위지만 별개 코드
    assert parent_of("ETC_OTHER") is ParentCategory.ETC
    assert parent_of("INSUFFICIENT") is ParentCategory.ETC
    assert "INSUFFICIENT" in leaf_codes()
    # 타이브레이크 규칙에 둘의 구분이 명시되어 있어야 함
    block = few_shot_block()
    assert "INSUFFICIENT" in block and "ETC_OTHER" in block


def test_unknown_code_raises():
    import pytest

    with pytest.raises(KeyError):
        get_leaf("NOPE")


def test_few_shot_block_lists_all_codes():
    block = few_shot_block()
    for code in EXPECTED_LEAVES:
        assert code in block
    assert "타이브레이크" in block
