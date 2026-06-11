-- AI-only SQLite schema. Idempotent (CREATE IF NOT EXISTS).
-- Populated by scripts/ingest_rulebook_and_org.py.

-- 소분류별 기관·부서 배정 가이드 (룰북 .md 전체를 평문으로 저장).
CREATE TABLE IF NOT EXISTS assignment_guide (
  major_code TEXT NOT NULL,
  minor_code TEXT NOT NULL,
  guide_text TEXT NOT NULL,
  PRIMARY KEY (major_code, minor_code)
);

-- 기관 (전체기관명 단위). region_code 로 관할 구분(행정동코드 미사용).
CREATE TABLE IF NOT EXISTS agency (
  id          INTEGER PRIMARY KEY,
  region_code TEXT NOT NULL,            -- 'BUNDANG' (multi-region ready)
  agency_type TEXT NOT NULL,            -- 지자체 | 경찰 | 소방 | 보건
  name        TEXT NOT NULL,            -- 전체기관명 e.g. 분당구청
  phone       TEXT,
  UNIQUE (region_code, name)
);

-- 부서 (최하위기관명 단위).
CREATE TABLE IF NOT EXISTS department (
  id          INTEGER PRIMARY KEY,
  agency_id   INTEGER NOT NULL REFERENCES agency(id),
  region_code TEXT NOT NULL,
  agency_type TEXT NOT NULL,            -- denormalized for direct candidate query
  name        TEXT NOT NULL,            -- 최하위기관명 e.g. 건설과
  phone       TEXT,
  UNIQUE (region_code, agency_id, name)
);

CREATE INDEX IF NOT EXISTS idx_dept_lookup ON department(region_code, agency_type);
