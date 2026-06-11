"""Read-only queries over the AI SQLite DB (assignment guide + org directory).

All functions are blocking (sqlite) — call them via ``run_in_threadpool`` from
async code. Returns plain dataclasses so callers don't depend on sqlite3.Row.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.connection import get_connection


@dataclass(frozen=True)
class DepartmentRow:
    agency_type: str
    agency_name: str
    department: str
    phone: str | None
    agency_phone: str | None = None  # 부서 전화가 없을 때 폴백


@dataclass(frozen=True)
class OrgRow:
    name: str  # 전체기관명 (agency)
    department: str  # 최하위기관명
    phone: str | None
    agency_type: str


def get_assignment_guide(major_code: str, minor_code: str) -> str | None:
    cur = get_connection().execute(
        "SELECT guide_text FROM assignment_guide WHERE major_code = ? AND minor_code = ?",
        (major_code, minor_code),
    )
    row = cur.fetchone()
    return row["guide_text"] if row else None


def list_departments(agency_types: list[str], region_code: str) -> list[DepartmentRow]:
    """Candidate departments for the given agency types within a region (for step-3 enum)."""
    if not agency_types:
        return []
    placeholders = ",".join("?" for _ in agency_types)
    cur = get_connection().execute(
        f"""
        SELECT d.agency_type, a.name AS agency_name, d.name AS department,
               d.phone AS dept_phone, a.phone AS agency_phone
        FROM department d JOIN agency a ON d.agency_id = a.id
        WHERE d.region_code = ? AND d.agency_type IN ({placeholders})
        ORDER BY d.agency_type, a.name, d.name
        """,
        (region_code, *agency_types),
    )
    return [
        DepartmentRow(
            agency_type=r["agency_type"],
            agency_name=r["agency_name"],
            department=r["department"],
            phone=r["dept_phone"],
            agency_phone=r["agency_phone"],
        )
        for r in cur.fetchall()
    ]


def resolve_org(region_code: str, department_name: str) -> OrgRow | None:
    """Resolve a concrete org row by department name within a region.

    Agency type is derived from the matched row (not an input filter), so a
    department name unambiguously determines its agency. exact → contains → None.
    """
    if not department_name:
        return None
    conn = get_connection()
    base = """
        SELECT a.name AS agency_name, d.name AS department, d.phone AS dept_phone,
               a.phone AS agency_phone, d.agency_type AS agency_type
        FROM department d JOIN agency a ON d.agency_id = a.id
        WHERE d.region_code = ?
    """
    row = conn.execute(
        base + " AND d.name = ? LIMIT 1", (region_code, department_name)
    ).fetchone()
    if row is None:
        # contains fallback (either direction): handles name drift vs org table
        row = conn.execute(
            base + " AND (d.name LIKE ? OR ? LIKE '%' || d.name || '%') LIMIT 1",
            (region_code, f"%{department_name}%", department_name),
        ).fetchone()
    if row is None:
        return None
    return OrgRow(
        name=row["agency_name"],
        department=row["department"],
        phone=row["dept_phone"] or row["agency_phone"],
        agency_type=row["agency_type"],
    )


def list_agency_types() -> list[str]:
    cur = get_connection().execute("SELECT DISTINCT agency_type FROM agency ORDER BY agency_type")
    return [r["agency_type"] for r in cur.fetchall()]
