# 2H · PostgreSQL 기초

## 학습목표

- Colab에서 Neon PostgreSQL에 접속하고 데이터를 조회할 수 있다
- `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`을 사용할 수 있다
- `EXPLAIN`으로 쿼리 실행 계획을 읽을 수 있다

!!! tip "🧭 이 시간을 이렇게 읽으세요 (비개발자용)"
    - **한 줄 핵심**: 데이터베이스를 **"엑셀의 큰 형"** 으로 받아들이고, `SELECT ... WHERE ... ORDER BY` 한 줄을 직접 쳐 보는 시간입니다.
    - **꼭 이해**: 테이블 = 엑셀 시트, 컬럼 = 엑셀 열, 행 = 엑셀 행. `WHERE` 는 엑셀의 "필터", `ORDER BY` 는 "정렬", `LIMIT` 은 "위쪽 N개만 보기" 라는 비유.
    - **지금은 몰라도 OK**: `EXPLAIN` 결과의 세부 항목, `CHECK / SERIAL` 같은 제약조건의 내부 동작. "이런 게 있구나" 정도면 됩니다.
    - **막히면**: [용어 사전 — 데이터·SQL·DB 섹션](../appendix/glossary.md#b-sqldb) 에 테이블·스키마·DSN·`text()` 등이 모두 정리되어 있습니다.

<div class="colab-link" data-notebook="01_postgres_basics"></div>

## 쉬운 비유 — 데이터베이스란?

!!! tip "데이터베이스 = 체계적인 엑셀 파일 모음"
    - 엑셀의 "시트" = 데이터베이스의 "테이블"
    - 엑셀의 "열" = 데이터베이스의 "컬럼"
    - 엑셀의 "행" = 데이터베이스의 "로우(레코드)"
    - 엑셀의 "필터" = SQL의 `WHERE`
    - 엑셀의 "정렬" = SQL의 `ORDER BY`

### 왜 엑셀 대신 데이터베이스를 쓸까?

| 기능 | 엑셀 | PostgreSQL |
|---|---|---|
| 데이터 100만행 이상 | 느려짐 | 문제 없음 |
| 여러 사람이 동시 사용 | 충돌 | 안전 |
| 자동화 (프로그램에서 호출) | 어려움 | 쉬움 |
| AI와 연동 | 불가 | 가능! ← **이것이 핵심** |

### 왜 PostgreSQL인가?

| 특성 | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| SQL 표준 준수 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| `COMMENT ON` (AI 가독성) | ✅ | ❌ | ❌ |
| 윈도우 함수 | ✅ 완전 지원 | ✅ (8.0+) | 제한적 |

!!! tip "팁"
    **AI 가독성**: `COMMENT ON`으로 테이블/컬럼에 설명을 달 수 있어서 AI가 스키마를 이해하기 쉽습니다. 이것이 PostgreSQL을 선택한 핵심 이유입니다.

## 실습 — 병원 데이터베이스 만들기

5개 테이블(진료과, 의사, 환자, 방문, 진단)로 구성된 병원 DB를 만들고 샘플 데이터를 넣습니다.

### 병원 DDL (스키마 생성)

```python
# ============================================================
# 병원 데이터베이스 스키마 생성
# ============================================================
hospital_ddl = """
-- 기존 테이블이 있으면 삭제 (처음 실행 시 무시됨)
DROP TABLE IF EXISTS diagnoses CASCADE;
DROP TABLE IF EXISTS visits CASCADE;
DROP TABLE IF EXISTS doctors CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS departments CASCADE;

-- 📌 아래 DDL에서 계속 나오는 제약조건을 먼저 한 번에 정리합니다.
--    (표는 DDL 아래 !!! note "DDL 제약조건 치트시트" 참고)
--
-- 1️⃣ 진료과 테이블
-- 주의: 학습용으로 SERIAL 을 씁니다(문법이 짧음).
-- 본인 프로젝트/프로덕션에서는 PostgreSQL 표준인
-- `GENERATED ALWAYS AS IDENTITY` 가 모범 사례입니다.
-- 예) department_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
CREATE TABLE departments (
    department_id   SERIAL PRIMARY KEY,    -- 자동 증가 번호 (고유 ID)
    name            VARCHAR(50) NOT NULL,  -- 진료과명 (예: 내과, 외과)
    floor           INT,                   -- 위치 층수
    phone           VARCHAR(20)            -- 대표 전화번호
);
-- AI가 이 테이블을 이해할 수 있도록 설명을 달아줍니다
COMMENT ON TABLE departments IS '병원의 진료과 정보';
COMMENT ON COLUMN departments.name IS '진료과명 (예: 내과, 외과, 소아과)';
COMMENT ON COLUMN departments.floor IS '진료과 위치 층수';

-- 2️⃣ 의사 테이블
CREATE TABLE doctors (
    doctor_id       SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    department_id   INT NOT NULL REFERENCES departments(department_id),
    -- ↑ REFERENCES = "이 값은 departments 테이블에 있는 값이어야 함"
    specialty       VARCHAR(100),          -- 세부 전공
    hire_date       DATE NOT NULL,         -- 입사일
    salary          NUMERIC(12,2)          -- 월급 (원)
);
COMMENT ON TABLE doctors IS '의사 정보';
COMMENT ON COLUMN doctors.department_id IS '소속 진료과 (departments 테이블 참조)';
COMMENT ON COLUMN doctors.specialty IS '세부 전공 (예: 심장내과, 정형외과)';
COMMENT ON COLUMN doctors.salary IS '월급 (원)';

-- 3️⃣ 환자 테이블
CREATE TABLE patients (
    patient_id      SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    birth_date      DATE NOT NULL,
    gender          CHAR(1) NOT NULL CHECK (gender IN ('M','F')),
    -- ↑ CHECK = "M 또는 F만 입력 가능"
    phone           VARCHAR(20),
    address         VARCHAR(200),
    blood_type      VARCHAR(3) CHECK (blood_type IN ('A','B','O','AB')),
    created_at      TIMESTAMP DEFAULT NOW()  -- 등록 시 자동으로 현재 시간
);
COMMENT ON TABLE patients IS '환자 기본 정보';
COMMENT ON COLUMN patients.gender IS '성별: M=남성, F=여성';
COMMENT ON COLUMN patients.blood_type IS '혈액형: A, B, O, AB';

-- 4️⃣ 방문(진료) 테이블
CREATE TABLE visits (
    visit_id        SERIAL PRIMARY KEY,
    patient_id      INT NOT NULL REFERENCES patients(patient_id),
    doctor_id       INT NOT NULL REFERENCES doctors(doctor_id),
    visit_date      DATE NOT NULL,
    visit_type      VARCHAR(20) NOT NULL CHECK (visit_type IN ('outpatient','inpatient','emergency')),
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                    CHECK (status IN ('scheduled','completed','cancelled','no_show')),
    chief_complaint TEXT,                  -- 주요 증상
    cost            NUMERIC(10,2)          -- 진료비 (원)
);
COMMENT ON TABLE visits IS '환자 진료 방문 기록';
COMMENT ON COLUMN visits.visit_type IS '진료 유형: outpatient=외래, inpatient=입원, emergency=응급';
COMMENT ON COLUMN visits.status IS '진료 상태: completed=완료, cancelled=취소, no_show=미방문';
COMMENT ON COLUMN visits.cost IS '진료비 (원)';

-- 5️⃣ 진단 테이블
CREATE TABLE diagnoses (
    diagnosis_id    SERIAL PRIMARY KEY,
    visit_id        INT NOT NULL REFERENCES visits(visit_id),
    icd_code        VARCHAR(10) NOT NULL,  -- 국제 질병 분류 코드
    description     VARCHAR(200) NOT NULL, -- 진단명 (한국어)
    severity        VARCHAR(10) CHECK (severity IN ('mild','moderate','severe'))
);
COMMENT ON TABLE diagnoses IS '진료 시 내려진 진단 기록';
COMMENT ON COLUMN diagnoses.severity IS '중증도: mild=경증, moderate=중등, severe=중증';
""";

with engine.begin() as conn:
    conn.execute(text(hospital_ddl))
print("✅ 병원 DB 스키마 생성 완료!")
```

!!! tip "테이블 간 관계"
    환자(patients) → 방문(visits) → 진단(diagnoses), 의사(doctors) → 방문(visits), 진료과(departments) → 의사(doctors)

!!! note "DDL 제약조건 치트시트 -- 위 스키마에서 쓴 키워드 5가지"
    위 스키마에서 계속 등장한 문법을 한 번에 정리합니다. SQL 이 처음이라면 **이 5개만 알면** Day 1~4 강의 전반에서 헷갈리지 않습니다.

    | 키워드 | 의미 | 예시 | 안 쓰면? |
    |---|---|---|---|
    | `SERIAL` | "자동 증가 정수 컬럼"의 단축 표현. `INT GENERATED ... AS IDENTITY` 와 비슷 | `doctor_id SERIAL PRIMARY KEY` | INSERT 마다 ID를 직접 계산해 넣어야 함 |
    | `PRIMARY KEY` | "이 행을 고유하게 식별하는 컬럼". NOT NULL + UNIQUE 를 동시에 강제 | `PRIMARY KEY (doctor_id)` | 중복 행이 쌓이고, JOIN 대상 컬럼 특정이 어려움 |
    | `REFERENCES` (외래키, FK) | "이 값은 반드시 다른 테이블 X 에 존재해야 한다" | `department_id INT REFERENCES departments(department_id)` | 존재하지 않는 진료과 번호로 의사 등록됨 (orphan 데이터) |
    | `NOT NULL` | "빈 값(NULL) 금지" | `name VARCHAR(100) NOT NULL` | 이름 없는 환자가 들어올 수 있음 |
    | `CHECK (...)` | "값이 이 조건을 만족해야 한다" | `CHECK (gender IN ('M','F'))` | 'X', 'Male', 공백 등 쓰레기 값 유입 |

    **추가**: `ON DELETE CASCADE` / `ON DELETE SET NULL` 은 FK 에 붙이는 옵션으로, 부모 행이 삭제될 때 자식을 같이 지울지/NULL 처리할지 정합니다. 본 강의 스키마는 **실수 삭제 방지**를 위해 CASCADE 를 DDL 에 붙이지 않고, DROP TABLE 시에만 `CASCADE` 를 사용합니다.

### 시드 데이터 삽입

진료과 8개, 의사 20명, 환자 30명, 방문 50건, 진단 20건의 샘플 데이터를 넣습니다.

```python
seed_data = """
-- 진료과 8개
INSERT INTO departments (name, floor, phone) VALUES
('내과', 3, '02-1234-1001'), ('외과', 4, '02-1234-1002'),
('소아과', 2, '02-1234-1003'), ('정형외과', 4, '02-1234-1004'),
('피부과', 2, '02-1234-1005'), ('신경과', 5, '02-1234-1006'),
('산부인과', 3, '02-1234-1007'), ('안과', 2, '02-1234-1008');

-- 의사 20명
INSERT INTO doctors (name, department_id, specialty, hire_date, salary) VALUES
('김철수', 1, '심장내과', '2015-03-01', 8500000),
('이영희', 1, '호흡기내과', '2018-07-15', 7200000),
('박민수', 2, '일반외과', '2012-01-10', 9000000),
('정수진', 2, '흉부외과', '2019-06-01', 7800000),
('최동현', 3, '소아청소년과', '2016-09-20', 7500000),
('강미래', 3, '신생아과', '2020-03-01', 6800000),
('윤성호', 4, '척추외과', '2014-05-15', 8800000),
('한지은', 4, '관절외과', '2017-11-01', 7600000),
('서준혁', 5, '일반피부과', '2021-01-15', 6500000),
('임하늘', 5, '미용피부과', '2022-03-01', 6200000),
('조태영', 6, '뇌신경과', '2013-08-20', 9200000),
('배수현', 6, '말초신경과', '2019-12-01', 7100000),
('노진우', 7, '산과', '2015-06-15', 8000000),
('유다정', 7, '부인과', '2018-09-01', 7400000),
('장세림', 8, '망막', '2016-04-10', 7900000),
('오현우', 8, '녹내장', '2020-07-01', 6900000),
('신민아', 1, '소화기내과', '2017-02-15', 7800000),
('권혁준', 2, '혈관외과', '2021-05-01', 6600000),
('문서영', 3, '소아알레르기', '2023-01-10', 6000000),
('황태윤', 6, '두통클리닉', '2022-06-15', 6300000);

-- 환자 30명
INSERT INTO patients (name, birth_date, gender, phone, address, blood_type) VALUES
('홍길동', '1985-05-15', 'M', '010-1111-0001', '서울시 강남구', 'A'),
('김미영', '1990-08-22', 'F', '010-1111-0002', '서울시 서초구', 'B'),
('이준석', '1978-12-03', 'M', '010-1111-0003', '서울시 송파구', 'O'),
('박서연', '1995-03-17', 'F', '010-1111-0004', '서울시 마포구', 'AB'),
('정태호', '1982-07-30', 'M', '010-1111-0005', '경기도 성남시', 'A'),
('최유진', '2000-01-25', 'F', '010-1111-0006', '서울시 강동구', 'B'),
('강현우', '1975-11-08', 'M', '010-1111-0007', '서울시 중구', 'O'),
('윤서현', '1998-04-12', 'F', '010-1111-0008', '경기도 고양시', 'A'),
('임도윤', '1988-09-05', 'M', '010-1111-0009', '서울시 노원구', 'AB'),
('한소희', '1992-06-18', 'F', '010-1111-0010', '서울시 양천구', 'B'),
('조민기', '1970-02-28', 'M', '010-1111-0011', '서울시 용산구', 'A'),
('배지현', '2003-10-07', 'F', '010-1111-0012', '경기도 수원시', 'O'),
('서영준', '1980-08-14', 'M', '010-1111-0013', '서울시 동작구', 'B'),
('노혜린', '1996-12-25', 'F', '010-1111-0014', '서울시 관악구', 'A'),
('유재석', '1972-08-14', 'M', '010-1111-0015', '경기도 용인시', 'O'),
('장미란', '1983-11-09', 'F', '010-1111-0016', '서울시 영등포구', 'AB'),
('오승환', '1991-07-22', 'M', '010-1111-0017', '서울시 구로구', 'A'),
('신세경', '1999-02-03', 'F', '010-1111-0018', '경기도 안양시', 'B'),
('권상우', '1976-06-05', 'M', '010-1111-0019', '서울시 종로구', 'O'),
('문채원', '1987-11-13', 'F', '010-1111-0020', '서울시 성동구', 'A'),
('황정민', '1969-09-01', 'M', '010-1111-0021', '경기도 부천시', 'AB'),
('이나영', '1993-04-17', 'F', '010-1111-0022', '서울시 은평구', 'B'),
('김수현', '2001-12-08', 'M', '010-1111-0023', '서울시 광진구', 'O'),
('전지현', '1981-10-30', 'F', '010-1111-0024', '경기도 파주시', 'A'),
('송중기', '1986-09-19', 'M', '010-1111-0025', '서울시 강서구', 'B'),
('한가인', '1994-07-06', 'F', '010-1111-0026', '서울시 도봉구', 'O'),
('공유진', '1979-04-23', 'M', '010-1111-0027', '경기도 하남시', 'AB'),
('수지은', '1997-03-11', 'F', '010-1111-0028', '서울시 서대문구', 'A'),
('이병헌', '1970-07-12', 'M', '010-1111-0029', '경기도 광명시', 'B'),
('김태희', '1980-03-29', 'F', '010-1111-0030', '서울시 강북구', 'O');

-- 방문 기록 50건 (최근 6개월)
INSERT INTO visits (patient_id, doctor_id, visit_date, visit_type, status, chief_complaint, cost) VALUES
(1,  1,  '2025-11-05', 'outpatient', 'completed', '가슴 통증, 호흡 곤란', 85000),
(2,  5,  '2025-11-08', 'outpatient', 'completed', '자녀 예방접종', 45000),
(3,  7,  '2025-11-10', 'outpatient', 'completed', '허리 통증', 120000),
(4,  9,  '2025-11-12', 'outpatient', 'completed', '여드름 상담', 35000),
(5,  3,  '2025-11-15', 'emergency',  'completed', '복부 통증, 구토', 250000),
(6,  2,  '2025-11-18', 'outpatient', 'cancelled', '기침, 가래', 0),
(7,  11, '2025-11-20', 'outpatient', 'completed', '두통, 어지럼증', 95000),
(8,  15, '2025-11-22', 'outpatient', 'completed', '시력 저하', 75000),
(9,  1,  '2025-11-25', 'outpatient', 'completed', '고혈압 정기검진', 55000),
(10, 13, '2025-11-28', 'outpatient', 'completed', '임신 검진', 65000),
(1,  1,  '2025-12-03', 'outpatient', 'completed', '고혈압 추적검사', 55000),
(11, 3,  '2025-12-05', 'inpatient',  'completed', '담낭 수술', 1500000),
(12, 5,  '2025-12-08', 'outpatient', 'completed', '성장 검진', 40000),
(13, 8,  '2025-12-10', 'outpatient', 'completed', '무릎 통증', 110000),
(14, 17, '2025-12-12', 'outpatient', 'no_show',   '위장 불편', 0),
(15, 11, '2025-12-15', 'outpatient', 'completed', '만성 두통', 95000),
(3,  7,  '2025-12-18', 'outpatient', 'completed', '허리 재진', 80000),
(16, 14, '2025-12-20', 'outpatient', 'completed', '정기 검진', 55000),
(17, 4,  '2025-12-22', 'emergency',  'completed', '교통사고 외상', 350000),
(18, 9,  '2025-12-25', 'outpatient', 'completed', '아토피 상담', 45000),
(19, 11, '2026-01-05', 'outpatient', 'completed', '편두통', 95000),
(20, 2,  '2026-01-08', 'outpatient', 'completed', '감기, 발열', 35000),
(1,  1,  '2026-01-10', 'outpatient', 'completed', '혈압 추적', 55000),
(21, 3,  '2026-01-12', 'inpatient',  'completed', '탈장 수술', 1200000),
(22, 6,  '2026-01-15', 'outpatient', 'completed', '신생아 검진', 50000),
(5,  3,  '2026-01-18', 'outpatient', 'completed', '수술 후 추적검사', 65000),
(23, 15, '2026-01-20', 'outpatient', 'completed', '콘택트렌즈 검사', 45000),
(24, 13, '2026-01-22', 'outpatient', 'completed', '산전 검사', 80000),
(25, 17, '2026-01-25', 'outpatient', 'completed', '소화불량', 45000),
(7,  11, '2026-01-28', 'outpatient', 'completed', '어지럼증 재진', 85000),
(26, 8,  '2026-02-01', 'outpatient', 'completed', '발목 염좌', 95000),
(27, 4,  '2026-02-03', 'outpatient', 'completed', '어깨 통증', 110000),
(28, 10, '2026-02-05', 'outpatient', 'completed', '피부 트러블', 40000),
(29, 12, '2026-02-08', 'outpatient', 'completed', '손 저림', 75000),
(30, 16, '2026-02-10', 'outpatient', 'completed', '안압 검사', 65000),
(2,  6,  '2026-02-12', 'outpatient', 'completed', '영유아 건강검진', 50000),
(4,  10, '2026-02-15', 'outpatient', 'cancelled', '여드름 재진', 0),
(8,  15, '2026-02-18', 'outpatient', 'completed', '시력 재검', 75000),
(10, 14, '2026-02-20', 'outpatient', 'completed', '산후 검진', 60000),
(3,  7,  '2026-02-22', 'outpatient', 'completed', '허리 3차 재진', 80000),
(15, 20, '2026-03-01', 'outpatient', 'completed', '긴장성 두통', 55000),
(9,  17, '2026-03-05', 'outpatient', 'completed', '역류성 식도염', 65000),
(11, 3,  '2026-03-08', 'outpatient', 'completed', '수술 후 6개월 검진', 55000),
(20, 2,  '2026-03-10', 'outpatient', 'completed', '천식 관리', 45000),
(13, 7,  '2026-03-12', 'outpatient', 'completed', '무릎 재활', 90000),
(6,  2,  '2026-03-15', 'outpatient', 'completed', '기관지염', 55000),
(19, 11, '2026-03-18', 'outpatient', 'completed', '두통 추적', 85000),
(25, 1,  '2026-03-20', 'outpatient', 'completed', '건강검진', 120000),
(14, 17, '2026-03-22', 'outpatient', 'completed', '위내시경', 150000),
(1,  1,  '2026-04-01', 'outpatient', 'scheduled', '정기검진 예약', NULL);

-- 진단 기록
INSERT INTO diagnoses (visit_id, icd_code, description, severity) VALUES
(1,  'I20.0', '불안정 협심증', 'moderate'),
(1,  'R06.0', '호흡곤란', 'mild'),
(2,  'Z23',   '예방접종', 'mild'),
(3,  'M54.5', '요통', 'moderate'),
(4,  'L70.0', '심상성 여드름', 'mild'),
(5,  'K35.8', '급성 충수염', 'severe'),
(7,  'G43.9', '편두통', 'moderate'),
(8,  'H52.1', '근시', 'mild'),
(9,  'I10',   '본태성 고혈압', 'mild'),
(10, 'Z34.0', '정상 첫 임신 감독', 'mild'),
(11, 'I10',   '본태성 고혈압', 'mild'),
(12, 'K80.2', '담낭결석', 'severe'),
(13, 'Z00.1', '영유아 건강검진', 'mild'),
(14, 'M17.1', '무릎 골관절염', 'moderate'),
(16, 'G43.0', '전조 없는 편두통', 'moderate'),
(17, 'M54.5', '요통', 'mild'),
(18, 'Z01.4', '부인과 정기검진', 'mild'),
(19, 'S06.0', '뇌진탕', 'severe'),
(19, 'S80.0', '무릎 타박상', 'moderate'),
(20, 'L20.8', '아토피 피부염', 'mild');
""";

with engine.begin() as conn:
    conn.execute(text(seed_data))
print("✅ 시드 데이터 삽입 완료!")
```

## SELECT 기본 문법 — 데이터 조회

### run_query 도우미 함수

SQL 쿼리를 실행하고 결과를 보기 좋게 출력하는 도우미 함수입니다.

```python
import pandas as pd

def run_query(sql: str, title: str = ""):
    """SQL을 실행하고 결과를 표로 출력"""
    if title:
        print(f"\n📌 {title}")
    print(f"SQL: {sql.strip()}\n")
    df = pd.read_sql(sql, engine)     # SQL 실행 → 결과를 표(DataFrame)로 변환
    print(df.to_string(index=False))  # 표를 화면에 출력
    print(f"({len(df)}행)")            # 결과 행 수 표시
    return df
```

### 기본 조회 (엑셀의 "시트 열기")

```python
# 환자 테이블의 처음 5행 보기 (엑셀에서 시트를 여는 것과 같음)
run_query("SELECT * FROM patients LIMIT 5", "환자 테이블 미리보기")
```

### 원하는 열만 선택 (엑셀의 "열 숨기기")

```python
run_query("""
    SELECT patient_id, name, gender, blood_type
    FROM patients
    LIMIT 10
""", "환자 이름과 혈액형만 보기")
```

### WHERE 조건 (엑셀의 "필터")

```python
# 여성 환자만 필터링 (엑셀에서 성별 열에 필터 '여성'을 거는 것과 같음)
run_query("""
    SELECT name, birth_date, gender
    FROM patients
    WHERE gender = 'F'
    ORDER BY birth_date
""", "여성 환자 (생년월일순)")
```

### 나이 계산 + 조건

```python
# 40세 이상 환자 (엑셀에서 나이 열을 만들고 40 이상을 필터하는 것과 같음)
run_query("""
    SELECT name, birth_date,
           EXTRACT(YEAR FROM AGE(birth_date)) AS age
    FROM patients
    WHERE EXTRACT(YEAR FROM AGE(birth_date)) >= 40
    ORDER BY birth_date
""", "40세 이상 환자")
```

!!! tip "팁"
    `EXTRACT(YEAR FROM AGE(birth_date))` = 생년월일로부터 현재 나이를 계산하는 PostgreSQL 함수

### ORDER BY + LIMIT (정렬 + 상위 N개)

```python
# 진료비가 가장 비싼 5건 (엑셀에서 비용 열을 내림차순 정렬 후 위 5개만 보는 것)
run_query("""
    SELECT v.visit_id, p.name, v.visit_date, v.cost
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE v.cost IS NOT NULL AND v.cost > 0
    ORDER BY v.cost DESC
    LIMIT 5
""", "진료비 상위 5건")
```

## EXPLAIN 맛보기

```python
# SQL이 "어떻게" 실행되는지 확인 (성능 분석 도구)
explain_sql = """
EXPLAIN (FORMAT TEXT)
SELECT p.name, v.visit_date
FROM visits v
JOIN patients p ON p.patient_id = v.patient_id
WHERE v.visit_date >= '2026-01-01'
"""
with engine.connect() as conn:
    plan = conn.execute(text(explain_sql)).fetchall()
    print("📋 실행 계획:")
    for row in plan:
        print(row[0])
```

!!! tip "팁"
    EXPLAIN은 지금 깊이 이해하지 않아도 됩니다. "SQL이 빠른지 느린지 확인하는 도구"라고만 알아두세요.

## 실습 과제

1. `doctors` 테이블에서 2020년 이후 입사한 의사 목록을 급여 내림차순으로 조회하세요
2. `visits` 테이블에서 응급(`emergency`) 방문 기록만 찾아 날짜순으로 정렬하세요
3. 혈액형이 `O`인 남성 환자의 이름과 주소를 조회하세요

!!! note "핵심 정리"
    - **데이터베이스** = 체계적인 엑셀, AI 연동 가능
    - `SELECT` = 조회, `WHERE` = 필터, `ORDER BY` = 정렬, `LIMIT` = 상위 N개
    - `COMMENT ON`으로 AI가 이해할 수 있는 설명을 달 수 있음
