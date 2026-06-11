"""택소노미 SSOT 무결성 — 새 8 대분류 / 47 소분류 (+가상 2)."""

from pathlib import Path

import pytest

from app.core.taxonomy import (
    CATEGORIES,
    ETC_OTHER,
    INSUFFICIENT,
    AgencyType,
    CategoryCode,
    MajorCategory,
    agency_type_of,
    candidate_agency_types,
    department_of,
    get_leaf,
    is_virtual,
    leaf_codes,
    major_block,
    minor_block,
    minors_of,
    parent_of,
)

RULEBOOK_DIR = Path(__file__).resolve().parent.parent / "docs" / "rules" / "database"
NON_VIRTUAL = {c for c in leaf_codes() if not is_virtual(c)}


def test_counts():
    assert len(CATEGORIES) == 49  # 47 leaves + ETC_OTHER + INSUFFICIENT
    assert len(NON_VIRTUAL) == 47
    assert len(list(MajorCategory)) == 8


def test_enum_matches_categories():
    assert {c.value for c in CategoryCode} == set(CATEGORIES.keys())


def test_folder_set_matches_taxonomy():
    """폴더(룰북) 셋 == 비가상 택소노미 셋 — 드리프트 가드."""
    folder_codes = {p.stem for p in RULEBOOK_DIR.glob("*/*.md")}
    assert folder_codes == NON_VIRTUAL


def test_every_leaf_well_formed():
    for code, leaf in CATEGORIES.items():
        assert leaf.code == code
        assert leaf.ko and leaf.definition
        assert isinstance(leaf.major, MajorCategory)
        assert isinstance(leaf.default_agency_type, AgencyType)
        assert leaf.default_department


def test_minors_partition_majors():
    """모든 비가상 리프가 정확히 한 대분류에 속하고, minors_of 로 복원된다."""
    seen: set[str] = set()
    for major in MajorCategory:
        for leaf in minors_of(major):
            assert leaf.major is major
            seen.add(leaf.code)
    assert seen == set(leaf_codes())


def test_reverse_lookups():
    assert parent_of("MANHOLE_DRAIN_DAMAGE") is MajorCategory.INFRASTRUCTURE_ROAD
    assert agency_type_of("FIRE_RISK") is AgencyType.FIRE
    assert agency_type_of("SUSPICIOUS_ACTIVITY") is AgencyType.POLICE
    assert department_of("MANHOLE_DRAIN_DAMAGE")  # non-empty fallback


def test_virtual_codes():
    assert is_virtual(ETC_OTHER) and is_virtual(INSUFFICIENT)
    assert parent_of(ETC_OTHER) is MajorCategory.ETC
    assert not is_virtual("MANHOLE_DRAIN_DAMAGE")


def test_candidate_agency_types():
    assert AgencyType.POLICE in candidate_agency_types(MajorCategory.PUBLIC_ORDER)
    assert AgencyType.FIRE in candidate_agency_types(MajorCategory.LIFE_SAFETY)
    assert candidate_agency_types(MajorCategory.INFRASTRUCTURE_ROAD) == (AgencyType.LOCAL_GOV,)


def test_blocks_render():
    mb = major_block()
    for major in MajorCategory:
        assert major.value in mb
    block = minor_block(MajorCategory.INFRASTRUCTURE_ROAD)
    assert "MANHOLE_DRAIN_DAMAGE" in block
    assert "ILLEGAL_PARKING" not in block  # other major's leaf excluded


def test_unknown_code_raises():
    with pytest.raises(KeyError):
        get_leaf("NOPE")
