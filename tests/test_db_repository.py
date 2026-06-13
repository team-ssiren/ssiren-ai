"""SQLite repository — 임시 DB로 가이드/후보/해소 동작 검증."""

import pytest

from app.config import get_settings
from app.db import connection, repository


@pytest.fixture
def temp_db(tmp_path):
    settings = get_settings()
    original = settings.sqlite_db_path
    settings.sqlite_db_path = str(tmp_path / "test.db")
    connection.reset_connection_for_tests()
    conn = connection.get_connection()  # runs schema

    conn.execute(
        "INSERT INTO assignment_guide(major_code, minor_code, guide_text) VALUES (?,?,?)",
        ("INFRASTRUCTURE_ROAD", "MANHOLE_DRAIN_DAMAGE", "맨홀 가이드 평문"),
    )
    for aid, atype, name, phone in [
        (1, "지자체", "수지구청", "031-1"),
        (2, "소방", "용인서부소방서", "119"),
    ]:
        conn.execute(
            "INSERT INTO agency(id, region_code, agency_type, name, phone) "
            "VALUES (?,'SUJI',?,?,?)",
            (aid, atype, name, phone),
        )
    for did, aid, atype, name, phone in [
        (1, 1, "지자체", "건설도로과", "031-2"),
        (2, 1, "지자체", "산업환경과", None),
        (3, 2, "소방", "화재예방과", None),
    ]:
        conn.execute(
            "INSERT INTO department(id, agency_id, region_code, agency_type, name, phone) "
            "VALUES (?,?,'SUJI',?,?,?)",
            (did, aid, atype, name, phone),
        )
    conn.commit()
    yield
    connection.reset_connection_for_tests()
    settings.sqlite_db_path = original


def test_get_assignment_guide(temp_db):
    guide = repository.get_assignment_guide("INFRASTRUCTURE_ROAD", "MANHOLE_DRAIN_DAMAGE")
    assert guide == "맨홀 가이드 평문"
    assert repository.get_assignment_guide("X", "Y") is None


def test_list_departments_filters_by_type(temp_db):
    gov = repository.list_departments(["지자체"], "SUJI")
    assert {d.department for d in gov} == {"건설도로과", "산업환경과"}
    both = repository.list_departments(["지자체", "소방"], "SUJI")
    assert {d.department for d in both} == {"건설도로과", "산업환경과", "화재예방과"}
    assert repository.list_departments([], "SUJI") == []


def test_resolve_org_exact_and_fallback(temp_db):
    # 부서명만으로 해소, 기관유형은 행에서 도출
    exact = repository.resolve_org("SUJI", "건설도로과")
    assert exact.name == "수지구청" and exact.phone == "031-2" and exact.agency_type == "지자체"

    # 부서 전화가 없으면 기관 전화로 폴백 + 다른 기관유형도 부서명만으로 해소
    fire = repository.resolve_org("SUJI", "화재예방과")
    assert fire.phone == "119" and fire.agency_type == "소방"

    # contains 폴백: 존재하지 않는 정확명이지만 부분일치
    contains = repository.resolve_org("SUJI", "건설")
    assert contains is not None and contains.department == "건설도로과"

    # 매칭 실패 → None
    assert repository.resolve_org("SUJI", "존재하지않는과") is None
    # 빈 부서명 → None
    assert repository.resolve_org("SUJI", "") is None
