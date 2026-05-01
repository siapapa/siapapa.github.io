# 📘 Day 1 — 개관 · SQL · RAG 파이프라인 + 프로젝트 브리핑 (1~8H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API  
> **준비물**: 노트북(크롬 브라우저), 이메일 계정(Google/Neon/OpenAI)

---

## 📦 공통 부트스트랩 — 모든 실습의 시작점

> 💡 **부트스트랩이란?** 컴퓨터를 켜면 운영체제가 먼저 로드되듯, 우리 실습도 매번 "기본 환경 세팅"을 먼저 실행해야 합니다. 이 코드를 모든 노트북의 첫 번째 셀에 복사·붙여넣기 하세요.

### 이 코드가 하는 일
> 실습에 필요한 라이브러리(도구 모음)를 설치하고, 데이터베이스와 AI에 접속하기 위한 비밀번호를 설정합니다.

```python
# ============================================================
# 📦 패키지 설치 (Colab 환경)
# ============================================================
# !pip install = "이 도구를 설치해줘"라는 명령
# -q = quiet, 설치 과정 메시지를 간략히 보여줌
!pip install -q \
    psycopg2-binary sqlalchemy \
    llama-index llama-index-embeddings-openai llama-index-llms-openai \
    llama-index-vector-stores-chroma \
    chromadb \
    openai \
    tabulate pandas matplotlib

# ============================================================
# 🔑 환경변수 설정 — API 키와 DB 접속 정보
# ============================================================
import os                              # 운영체제 관련 기능
from google.colab import userdata      # Colab에 저장한 비밀키 불러오기

# Colab Secrets에 미리 저장해 둔 키를 환경변수로 등록
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")  # AI(GPT) 사용 키
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")        # DB 접속 주소

# 연결이 잘 되는지 확인
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])     # DB 연결 엔진 생성
with engine.connect() as conn:                      # DB에 접속
    result = conn.execute(text("SELECT version()")).fetchone()  # PostgreSQL 버전 확인
    print(f"✅ PostgreSQL 연결 성공: {result[0][:50]}...")
```

> ⚠️ **자주 발생하는 오류**: "연결 실패" → Neon DSN 끝에 `?sslmode=require`가 빠진 경우가 많습니다.

---

# 1H · OT & Agentic Analytics 전체 데모

## 학습목표
- "에이전틱 분석"이 기존 방식과 어떻게 다른지 설명할 수 있다
- 4일간 만들 최종 산출물의 전체 모습을 미리 체험한다
- Colab + Neon + OpenAI 환경을 설정한다

## 쉬운 비유로 이해하기 — 데이터 분석의 3세대

우리가 식당에서 주문하는 방식에 비유해 봅시다:

| 세대 | 방식 | 식당 비유 | 한계 |
|---|---|---|---|
| **1세대: BI 대시보드** | 분석가가 미리 만들어 둔 보고서 | 정해진 세트 메뉴만 가능 | 새로운 질문은 불가 |
| **2세대: Text-to-SQL** | 자연어로 질문 → SQL 1회 변환 | 메뉴판 보고 단품 주문 | 복잡한 요리는 실패 |
| **3세대: Agentic Analytics** | AI가 계획-실행-검증-재시도 | 셰프에게 "맛있는 거 해주세요" | 우리가 4일간 만들 것! |

### 왜 "에이전트"인가?

**Text-to-SQL의 한계 (2세대)**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

Text-to-SQL: SQL 1회 생성 → 실행 → 끝
  ❌ 잘못된 SQL을 감지하지 못함
  ❌ 복잡한 질문을 분해하지 못함
  ❌ 결과가 이상해도 재시도하지 않음
```

**에이전트의 접근 (3세대)**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

에이전트:
  1단계: 질문 분석 → "매출 상위 5개" + "전년 대비 성장률"로 분해
  2단계: SQL 생성 → 첫 번째 쿼리 작성
  3단계: SQL 실행 → 결과 확인
  4단계: 검증 → "행이 0개? 날짜 조건을 수정하자" → SQL 재작성
  5단계: 재실행 → 성공 → 자연어 답변 생성
```

### 에이전트의 4가지 핵심 요소

```
┌─────────────────────────────────────────────┐
│               AI 에이전트                      │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │  State   │  │  Tools   │                 │
│  │ (기억력)  │  │ (도구함)  │                 │
│  │ 대화 이력 │  │ SQL 실행  │                 │
│  │ 현재 SQL  │  │ 검색 엔진 │                 │
│  └──────────┘  └──────────┘                 │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │ Planning │  │Validation│                 │
│  │ (계획력)  │  │ (검증력)  │                 │
│  │ 질문 분해 │  │ 결과 확인 │                 │
│  │ 단계 수립 │  │ 재시도    │                 │
│  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────┘
```

1. **State (기억력)** — 이전 대화, 현재 작업 상태를 기억
2. **Tools (도구함)** — SQL 실행, 벡터 검색, AI 호출 등 사용 가능한 도구
3. **Planning (계획력)** — 복잡한 질문을 단계별로 분해
4. **Validation (검증력)** — 결과 확인, 오류 시 재시도

### 4일 학습 여정

```
┌──────────┬──────────────────────────────────────────────┐
│  Day 1   │ SQL 기초 + RAG 파이프라인 + 프로젝트 브리핑   │
│ (1~8H)   │ 🎯 "재료 준비" — DB, 검색, Text-to-SQL 기초  │
├──────────┼──────────────────────────────────────────────┤
│  Day 2   │ Text-to-SQL 심화 + 상담사 에이전트            │
│ (9~12H)  │ 🎯 "조리 시작" — 프롬프트 튜닝, Gradio UI    │
├──────────┼──────────────────────────────────────────────┤
│  Day 3   │ Vanna + LangChain + LangGraph 에이전트       │
│ (13~20H) │ 🎯 "완성" — 본인 프로젝트 에이전트 빌드      │
├──────────┼──────────────────────────────────────────────┤
│  Day 4   │ LangSmith + Ragas 평가 + 최종 발표           │
│ (21~24H) │ 🎯 "검증 & 발표" — 정량 평가, 라이브 데모    │
└──────────┴──────────────────────────────────────────────┘
```

## 🎯 실습 — 완성형 에이전트 데모 시연 (강사 진행)

> 이 코드는 강사가 시연합니다. 학생들은 4일 후에 이 에이전트를 직접 만들게 됩니다!

### 이 코드가 하는 일
> LangGraph라는 프레임워크로 SQL 분석 에이전트를 만듭니다. 질문을 받으면 SQL을 생성하고, 실행하고, 검증하고, 자연어로 답변합니다.

```python
# ============================================================
# 🎯 완성형 SQL 분석 에이전트 데모
# ============================================================
!pip install -q langchain langchain-openai langgraph sqlalchemy psycopg2-binary tabulate

import os, re
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text, inspect
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

engine = create_engine(os.environ["NEON_DSN"])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- 상태 정의: 에이전트가 기억할 정보 ---
class AgentState(TypedDict):
    question: str     # 사용자 질문
    sql: str          # 생성된 SQL
    result: str       # 실행 결과
    error: str        # 에러 메시지
    answer: str       # 최종 답변
    attempts: int     # 재시도 횟수

# --- (생략: 스키마 수집 + 노드 함수들은 강사 시연용) ---
# 4일 후에 여러분이 직접 구현합니다!
```

```python
# 시연 질문 예시
# ask("현재 등록된 환자 수는 몇 명인가요?")
# ask("진료과별 의사 수를 보여주세요.")
# ask("지난 3개월간 가장 많이 방문한 환자 Top 5는?")
```

## 🎯 실습 — 환경 셋업 (직접 따라하기)

### Step 1: Google Colab 접속
1. 브라우저에서 `colab.research.google.com` 접속
2. Google 계정으로 로그인
3. "새 노트" 클릭하여 빈 노트북 생성

### Step 2: Neon PostgreSQL 가입
1. `neon.tech` 접속 → "Sign Up" 클릭
2. Google 계정 또는 GitHub으로 가입
3. "New Project" → 프로젝트 이름: `sql-agent-course`
4. Region: `Asia Pacific (Singapore)` 선택
5. 생성 완료 후 **Connection String** 복사
   - 형식: `postgresql://user:pass@host/dbname?sslmode=require`

> ⚠️ **반드시 `?sslmode=require`가 포함되어야 합니다!**

### Step 3: Colab Secrets 등록
1. Colab 왼쪽 사이드바의 🔑 아이콘(Secrets) 클릭
2. "Add a new secret" 클릭
3. 두 개의 키 등록:
   - 이름: `OPENAI_API_KEY` → 값: OpenAI API 키 붙여넣기
   - 이름: `NEON_DSN` → 값: Neon Connection String 붙여넣기
4. 각 키의 "Notebook access" 토글을 **ON**으로 설정

### Step 4: 부트스트랩 실행
- 공통 부트스트랩 코드를 복사 → 첫 번째 셀에 붙여넣기 → 실행(▶)
- `✅ PostgreSQL 연결 성공:` 메시지가 나오면 성공!

> 🎯 **실습 체크리스트**
> - [ ] Colab 노트북 생성 완료
> - [ ] Neon 인스턴스 생성 + DSN 복사 완료
> - [ ] Colab Secrets에 2개 키 등록 완료
> - [ ] 부트스트랩 실행 → 연결 성공 확인

## 📌 1H 핵심 정리
- **에이전틱 분석** = AI가 계획→실행→검증→재시도를 자율적으로 수행
- 4일 후 여러분은 **본인 도메인**의 SQL 분석 에이전트를 만들어 발표합니다
- 오늘은 "재료 준비" — SQL, 검색, Text-to-SQL의 기초를 배웁니다

---

# 2H · PostgreSQL 기초

## 학습목표
- Colab에서 Neon PostgreSQL에 접속하고 데이터를 조회할 수 있다
- `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`을 사용할 수 있다
- `EXPLAIN`으로 쿼리 실행 계획을 읽을 수 있다

## 쉬운 비유 — 데이터베이스란?

> 💡 **데이터베이스 = 체계적인 엑셀 파일 모음**
> - 엑셀의 "시트" = 데이터베이스의 "테이블"
> - 엑셀의 "열" = 데이터베이스의 "컬럼"
> - 엑셀의 "행" = 데이터베이스의 "로우(레코드)"
> - 엑셀의 "필터" = SQL의 `WHERE`
> - 엑셀의 "정렬" = SQL의 `ORDER BY`

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

> **AI 가독성**: `COMMENT ON`으로 테이블/컬럼에 설명을 달 수 있어서 AI가 스키마를 이해하기 쉽습니다. 이것이 PostgreSQL을 선택한 핵심 이유입니다.

## 🎯 실습 — 병원 데이터베이스 만들기

### 이 코드가 하는 일
> 5개 테이블(진료과, 의사, 환자, 방문, 진단)로 구성된 병원 DB를 만들고 샘플 데이터를 넣습니다.

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

-- 1️⃣ 진료과 테이블
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

> 💡 **테이블 간 관계**: 환자(patients) → 방문(visits) → 진단(diagnoses), 의사(doctors) → 방문(visits), 진료과(departments) → 의사(doctors)

### 시드 데이터 삽입

### 이 코드가 하는 일
> 진료과 8개, 의사 20명, 환자 30명, 방문 50건, 진단 20건의 샘플 데이터를 넣습니다.

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

### 이 코드가 하는 일
> SQL 쿼리를 실행하고 결과를 보기 좋게 출력하는 도우미 함수입니다.

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

> 💡 `EXTRACT(YEAR FROM AGE(birth_date))` = 생년월일로부터 현재 나이를 계산하는 PostgreSQL 함수

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

### EXPLAIN 맛보기

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

> 💡 EXPLAIN은 지금 깊이 이해하지 않아도 됩니다. "SQL이 빠른지 느린지 확인하는 도구"라고만 알아두세요.

### 🎯 실습 과제
1. `doctors` 테이블에서 2020년 이후 입사한 의사 목록을 급여 내림차순으로 조회하세요
2. `visits` 테이블에서 응급(`emergency`) 방문 기록만 찾아 날짜순으로 정렬하세요
3. 혈액형이 `O`인 남성 환자의 이름과 주소를 조회하세요

## 📌 2H 핵심 정리
- **데이터베이스** = 체계적인 엑셀, AI 연동 가능
- `SELECT` = 조회, `WHERE` = 필터, `ORDER BY` = 정렬, `LIMIT` = 상위 N개
- `COMMENT ON`으로 AI가 이해할 수 있는 설명을 달 수 있음

---

# 3H · 집계 · 조인 · CTE · 윈도우 함수

## 학습목표
- `GROUP BY` / `HAVING`으로 데이터를 요약할 수 있다
- `JOIN`으로 여러 테이블을 결합할 수 있다
- `CTE`와 윈도우 함수를 사용할 수 있다

## GROUP BY — 엑셀의 "피벗 테이블"

> 💡 **GROUP BY = 엑셀 피벗 테이블**: 데이터를 그룹별로 묶어서 합계, 평균, 개수 등을 계산합니다.

| 집계 함수 | 의미 | 엑셀 비유 |
|---|---|---|
| `COUNT(*)` | 행 수 | COUNTA |
| `SUM(col)` | 합계 | SUM |
| `AVG(col)` | 평균 | AVERAGE |
| `MAX(col)` | 최대값 | MAX |
| `MIN(col)` | 최소값 | MIN |

```python
# 진료과별 의사 수 (피벗: 진료과 기준으로 의사 수 합산)
run_query("""
    SELECT d.name AS department, COUNT(*) AS doctor_count
    FROM doctors doc
    JOIN departments d ON d.department_id = doc.department_id
    GROUP BY d.name
    ORDER BY doctor_count DESC
""", "진료과별 의사 수")
```

```python
# HAVING: 그룹화 후 조건 필터 (3회 이상 방문한 환자만)
run_query("""
    SELECT p.name, COUNT(*) AS visit_count,
           SUM(COALESCE(v.cost, 0)) AS total_cost
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE v.status = 'completed'
    GROUP BY p.name
    HAVING COUNT(*) >= 3
    ORDER BY visit_count DESC
""", "3회 이상 방문한 환자")
```

> 💡 **WHERE vs HAVING**: WHERE는 그룹화 **전**에, HAVING은 그룹화 **후**에 필터링합니다.

## JOIN — 테이블 합치기

> 💡 **JOIN = 엑셀의 VLOOKUP**: 두 시트를 공통 열로 연결하여 하나의 표로 만듭니다.

```
INNER JOIN: 양쪽 모두에 있는 것만 (교집합)
  환자 ∩ 방문 → 방문 기록이 있는 환자만

LEFT JOIN: 왼쪽 전체 + 오른쪽 매칭 (왼쪽 시트 기준 VLOOKUP)
  환자 전체 + 방문 기록 → 방문 없는 환자도 포함 (NULL 표시)
```

```python
# INNER JOIN: 완료된 진료 기록 (환자명 + 의사명 함께 보기)
run_query("""
    SELECT p.name AS patient_name, d.name AS doctor_name,
           v.visit_date, v.chief_complaint
    FROM visits v
    INNER JOIN patients p ON p.patient_id = v.patient_id
    INNER JOIN doctors d ON d.doctor_id = v.doctor_id
    WHERE v.status = 'completed'
    ORDER BY v.visit_date DESC LIMIT 10
""", "INNER JOIN — 최근 완료 진료 10건")
```

```python
# LEFT JOIN: 모든 환자의 방문 횟수 (한번도 안 온 환자도 포함)
run_query("""
    SELECT p.name, COUNT(v.visit_id) AS visit_count
    FROM patients p
    LEFT JOIN visits v ON v.patient_id = p.patient_id
    GROUP BY p.patient_id, p.name
    ORDER BY visit_count, p.name
""", "LEFT JOIN — 모든 환자의 방문 횟수 (0건 포함)")
```

## CTE — "단계별 레시피"

> 💡 **CTE(Common Table Expression) = 요리 레시피**: 복잡한 요리를 단계별로 나누어 만드는 것처럼, 복잡한 SQL을 단계별로 나눕니다.

```python
# 월별 방문 수가 전체 평균 이상/미만인지 비교
run_query("""
    WITH monthly_visits AS (
        -- 1단계: 월별 방문 수 집계 (재료 준비)
        SELECT TO_CHAR(visit_date, 'YYYY-MM') AS month,
               COUNT(*) AS cnt
        FROM visits WHERE status = 'completed'
        GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ),
    avg_visits AS (
        -- 2단계: 전체 월 평균 계산 (소스 만들기)
        SELECT AVG(cnt) AS avg_cnt FROM monthly_visits
    )
    -- 3단계: 비교 (완성!)
    SELECT mv.month, mv.cnt AS visits,
           ROUND(av.avg_cnt, 1) AS overall_avg,
           CASE WHEN mv.cnt > av.avg_cnt THEN '평균 이상' ELSE '평균 미만' END AS status
    FROM monthly_visits mv, avg_visits av
    ORDER BY mv.month
""", "CTE — 월별 방문 vs 평균 비교")
```

## 윈도우 함수 — "모든 행에 메모 추가하기"

> 💡 **윈도우 함수 vs GROUP BY 차이**:
> - GROUP BY: 그룹별로 **한 행으로 요약** (10행 → 3행)
> - 윈도우 함수: 원래 행을 유지하면서 **추가 정보를 옆에 붙임** (10행 → 10행 + 추가 열)

```python
# ROW_NUMBER: 순위 매기기 (전체 + 부서별)
run_query("""
    SELECT name, salary, department_id,
           ROW_NUMBER() OVER (ORDER BY salary DESC) AS overall_rank,
           ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dept_rank
    FROM doctors
""", "ROW_NUMBER — 전체 순위 vs 진료과별 순위")
```

```python
# LAG: 전월 대비 방문 증감 ("전 행의 값"을 참조)
run_query("""
    SELECT TO_CHAR(visit_date, 'YYYY-MM') AS month,
           COUNT(*) AS visits,
           LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS prev_month,
           COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS diff
    FROM visits WHERE status = 'completed'
    GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ORDER BY month
""", "LAG — 전월 대비 방문 증감")
```

## 📌 3H 핵심 정리
- **GROUP BY** = 피벗 테이블 (그룹화 + 집계)
- **JOIN** = VLOOKUP (테이블 결합). INNER는 교집합, LEFT는 왼쪽 전체
- **CTE** = 단계별 레시피 (복잡한 쿼리를 읽기 쉽게)
- **윈도우 함수** = 행을 줄이지 않고 순위/누적/비교 추가

---

# 4H · Schema Intelligence — AI가 읽기 좋은 스키마

## 학습목표
- AI(LLM)이 스키마를 어떻게 읽는지 이해한다
- AI 가독성 스키마의 5가지 원칙을 적용할 수 있다
- ERD를 Mermaid로 작성할 수 있다

## 핵심 인사이트 — AI는 스키마를 "텍스트"로 읽는다

AI에게 SQL을 만들어달라고 하면, AI는 테이블 구조를 **텍스트**로 받아봅니다:

```
❌ 나쁜 스키마 (AI가 추측해야 함):
CREATE TABLE p (p_id INT, nm VARCHAR, gen CHAR, bd DATE, bt VARCHAR);

✅ 좋은 스키마 (AI가 즉시 이해):
CREATE TABLE patients (patient_id INT, name VARCHAR, gender CHAR, birth_date DATE, blood_type VARCHAR);
COMMENT ON COLUMN patients.gender IS '성별: M=남성, F=여성';
```

### 5가지 설계 원칙

| # | 원칙 | 나쁜 예 | 좋은 예 |
|---|---|---|---|
| 1 | **명시적 네이밍** | `p_id`, `nm`, `gen` | `patient_id`, `name`, `gender` |
| 2 | **COMMENT ON** | (설명 없음) | `COMMENT ON COLUMN gender IS '성별: M=남성'` |
| 3 | **FK 명시** | `pid INT` (무슨 테이블?) | `patient_id INT REFERENCES patients` |
| 4 | **ENUM → 룩업 테이블** | `CHECK (status IN (...))` | 별도 status 테이블 |
| 5 | **리포팅 뷰** | 3단계 JOIN 필요 | `vw_visit_details` 뷰로 미리 결합 |

### 이 코드가 하는 일
> 여러 테이블을 미리 결합한 "리포팅 뷰"를 만듭니다. AI가 JOIN 없이 간단하게 조회할 수 있습니다.

```python
with engine.begin() as conn:
    conn.execute(text("""
        CREATE OR REPLACE VIEW vw_visit_details AS
        SELECT
            v.visit_id, v.visit_date, v.visit_type, v.status,
            v.chief_complaint, v.cost,
            p.name AS patient_name, p.gender AS patient_gender,
            EXTRACT(YEAR FROM AGE(p.birth_date)) AS patient_age,
            d.name AS doctor_name, d.specialty AS doctor_specialty,
            dept.name AS department_name
        FROM visits v
        JOIN patients p ON p.patient_id = v.patient_id
        JOIN doctors d ON d.doctor_id = v.doctor_id
        JOIN departments dept ON dept.department_id = d.department_id
    """))
print("✅ vw_visit_details 뷰 생성 완료!")

# 뷰를 사용하면 복잡한 JOIN 없이 간단히 조회
run_query("""
    SELECT patient_name, doctor_name, department_name, visit_date, cost
    FROM vw_visit_details
    WHERE status = 'completed'
    ORDER BY visit_date DESC LIMIT 10
""", "뷰를 활용한 간편 조회")
```

### ERD (Entity-Relationship Diagram) — Mermaid 문법

```mermaid
erDiagram
    departments ||--o{ doctors : "has"
    doctors ||--o{ visits : "conducts"
    patients ||--o{ visits : "makes"
    visits ||--o{ diagnoses : "results_in"
```

> 💡 `mermaid.live`에 접속하면 위 코드를 붙여넣어 ERD 이미지를 만들 수 있습니다.

## 📌 4H 핵심 정리
- AI는 스키마를 **텍스트**로 읽으므로, 명시적 네이밍 + COMMENT ON이 핵심
- **리포팅 뷰**: 복잡한 JOIN을 미리 해두면 AI의 SQL 정확도가 올라감
- 프로젝트에서도 이 5원칙을 반드시 적용할 것

---

# 5H · LlamaIndex 파이프라인 개론

## 학습목표
- RAG의 개념을 이해한다
- LlamaIndex의 5단계 파이프라인을 실습한다
- 문서 로딩, 청킹, 인덱싱, 질의를 수행할 수 있다

## RAG란? — "오픈북 시험"

> 💡 **RAG(Retrieval-Augmented Generation) = 오픈북 시험**
> - AI(LLM)은 학습 데이터에 없는 정보를 모릅니다 (회사 내부 데이터, 최신 정보)
> - RAG는 "관련 자료를 찾아서(Retrieval) AI에게 건네주는(Augmented) 방식"
> - AI는 건네받은 자료를 참고하여 답변을 생성(Generation)합니다

```
질문: "내과에 어떤 의사가 있나요?"
  ↓
[검색] 관련 문서 찾기 → "내과에는 김철수, 이영희, 신민아 전문의가..."
  ↓
[증강] 찾은 문서 + 질문을 AI에게 전달
  ↓
[생성] AI: "내과에는 심장내과 김철수, 호흡기내과 이영희, 소화기내과 신민아 전문의가 있습니다."
```

### LlamaIndex 5단계 파이프라인

```
Documents → Nodes(Chunks) → Embeddings → Index → QueryEngine
 (원본 문서)  (작은 조각)     (숫자 벡터)   (검색 가능한 저장소)  (질의-응답)
```

### 이 코드가 하는 일
> 병원 안내 문서를 로딩하고, 작은 조각으로 나누고, 벡터로 변환하여 검색 가능하게 만듭니다.

```python
!pip install -q llama-index llama-index-llms-openai llama-index-embeddings-openai

from llama_index.core import Settings, Document, VectorStoreIndex
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter

# 1️⃣ AI 모델 설정
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 2️⃣ 문서 로딩 (병원 안내서)
hospital_docs = [
    Document(text="내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기) 전문의가 있습니다.",
             metadata={"section": "진료과"}),
    Document(text="진료 시간: 평일 09:00-18:00, 토요일 09:00-13:00. 응급실 24시간.",
             metadata={"section": "진료안내"}),
    Document(text="입원 병실: 1인실 250,000원/일, 2인실 150,000원/일, 4인실 80,000원/일.",
             metadata={"section": "입원안내"}),
    Document(text="외래 환자 주차 3시간 무료, 이후 30분당 1,000원.",
             metadata={"section": "주차"}),
]

# 3️⃣ 청킹 (문서를 작은 조각으로 나누기)
splitter = SentenceSplitter(chunk_size=256, chunk_overlap=30)

# 4️⃣ 인덱싱 (벡터 변환 + 저장)
index = VectorStoreIndex.from_documents(hospital_docs, transformations=[splitter])

# 5️⃣ 질의
query_engine = index.as_query_engine(similarity_top_k=3)
response = query_engine.query("내과에는 어떤 의사가 있나요?")
print(f"💬 답변: {response.response}")
```

## 📌 5H 핵심 정리
- **RAG** = AI에게 참고 자료를 건네주는 방식 ("오픈북 시험")
- **5단계**: 문서 로딩 → 청킹 → 임베딩 → 인덱싱 → 질의
- LlamaIndex가 이 전체 과정을 쉽게 구현하게 해줌

---

# 6H · 임베딩 + ChromaDB 영속화

## 학습목표
- 임베딩(벡터 변환)의 원리를 이해한다
- ChromaDB로 벡터를 영구 저장한다

## 임베딩이란? — "단어의 좌표"

> 💡 **임베딩 = 텍스트를 지도 위의 좌표로 바꾸는 것**
> - "두통" → 좌표 (3, 5)
> - "머리가 아파요" → 좌표 (3.1, 4.9) ← 가까움! (의미가 비슷하니까)
> - "오늘 날씨" → 좌표 (8, 1) ← 멀리 떨어져 있음 (의미가 다르니까)

### 코사인 유사도 — "화살표 방향이 비슷한가?"
- 두 벡터(화살표)의 방향이 같으면 유사도 = 1 (완전 같은 의미)
- 방향이 직각이면 유사도 = 0 (관련 없음)
- 방향이 반대면 유사도 = -1 (반대 의미)

### 이 코드가 하는 일
> 문장들을 벡터(숫자 배열)로 변환하고, 서로 얼마나 비슷한지 유사도를 계산합니다.

```python
from openai import OpenAI
import numpy as np

client = OpenAI()

def get_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 유사도 테스트
sentences = ["환자가 두통을 호소합니다", "머리가 아파요", "오늘 날씨가 맑습니다"]
embeddings = [get_embedding(s) for s in sentences]

for i in range(len(sentences)):
    for j in range(i+1, len(sentences)):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        print(f"  '{sentences[i]}' vs '{sentences[j]}' → 유사도: {sim:.4f}")
```

### ChromaDB — "영구 보관함"

> 💡 5H에서 만든 인덱스는 Colab을 닫으면 사라집니다. ChromaDB를 사용하면 벡터를 **영구 저장**할 수 있습니다.

```python
!pip install -q llama-index-vector-stores-chroma chromadb

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext, VectorStoreIndex

# ChromaDB 저장소 생성
chroma_client = chromadb.Client()
chroma_collection = chroma_client.get_or_create_collection("hospital_docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 문서 인덱싱 (ChromaDB에 저장)
index = VectorStoreIndex.from_documents(
    hospital_docs, storage_context=storage_context
)

# 검색 테스트
query_engine = index.as_query_engine(similarity_top_k=3)
print(query_engine.query("주차 요금이 어떻게 되나요?").response)
```

## 📌 6H 핵심 정리
- **임베딩** = 텍스트를 숫자 벡터(좌표)로 변환하는 것
- **코사인 유사도** = 두 벡터의 방향이 비슷하면 의미가 비슷
- **ChromaDB** = 벡터를 영구 저장하는 "보관함"

---

# 7H · Text-to-SQL 맛보기

## 학습목표
- 자연어 질문을 SQL로 자동 변환하는 과정을 체험한다
- 스키마 정보가 정확도에 미치는 영향을 이해한다

## Text-to-SQL이란?

> 💡 **Text-to-SQL = "한국어로 질문하면 AI가 SQL을 만들어줌"**

```
사용자: "남성 환자 수는?"
  ↓ AI가 변환
SQL: SELECT COUNT(*) FROM patients WHERE gender = 'M';
  ↓ 실행
결과: 15명
```

### 이 코드가 하는 일
> LlamaIndex의 NLSQLTableQueryEngine으로 자연어 질문을 SQL로 자동 변환하고 실행합니다.

```python
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

# DB 래퍼 생성 (어떤 테이블을 사용할지 지정)
sql_db = SQLDatabase(engine,
    include_tables=["patients", "doctors", "visits", "diagnoses", "departments"])

# 질의 엔진 생성
nlq = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)

# 테스트 질문들
test_questions = [
    "전체 환자 수는?",            # Easy
    "남성 환자 수는?",            # Easy
    "진료과별 의사 수를 보여줘",   # Medium
    "지난달 방문 환자 수는?",      # Medium
    "최근에 많이 온 사람은?",      # Hard (모호한 질문)
]

for q in test_questions:
    try:
        resp = nlq.query(q)
        print(f"✅ Q: {q}")
        print(f"   SQL: {resp.metadata['sql_query']}")
        print(f"   A: {resp.response[:100]}\n")
    except Exception as e:
        print(f"❌ Q: {q}")
        print(f"   오류: {str(e)[:80]}\n")
```

> ⚠️ **일부 질문은 실패할 수 있습니다!** 이것이 정상입니다. Day 2에서 정확도를 높이는 방법을 배웁니다.

## 📌 7H 핵심 정리
- **Text-to-SQL**: 자연어 → SQL 자동 변환. 기본 설정으로도 간단한 질문은 가능
- **한계**: 모호한 질문, 도메인 용어, 복잡한 JOIN에서 실패
- Day 2에서 프롬프트 튜닝, few-shot 등으로 개선 예정

---

# 8H · 최종 프로젝트 브리핑

## 학습목표
- 4일간의 프로젝트 구조와 마일스톤을 이해한다
- 과제 #1(제안서) 작성 방법을 익힌다
- 본인 프로젝트 도메인을 선정한다

## 프로젝트 개요

```
🎯 최종 목표: 본인이 선택한 도메인의 SQL 분석 에이전트를 만들어 발표!

4단계 마일스톤:
Day 1 끝 → 과제 #1: 프로젝트 제안서 (도메인, 스키마, 질문 10개)
Day 2 끝 → 과제 #2: 스키마 + 시드 데이터 (Neon에 배포)
Day 3 끝 → 과제 #3: 에이전트 v1 (LangGraph)
Day 4    → 최종 발표 (5~7분, Ragas 평가 포함)
```

## 과제 #1 — 프로젝트 제안서

### 제안서에 포함할 내용

| 항목 | 설명 | 예시 |
|---|---|---|
| 도메인 | 분석 대상 | 음식점 예약 시스템 |
| 테이블 | 3~5개 | restaurants, reservations, reviews, menus |
| 질문 10개 | Easy 3~4, Medium 3~4, Hard 2~3 | "이번 달 예약 수는?" |
| 기대 SQL | 각 질문에 대한 정답 SQL | `SELECT COUNT(*) ...` |
| ERD | 테이블 간 관계 | Mermaid 다이어그램 |

### 도메인 선정 팁

```
✅ 좋은 도메인 (3~5 테이블로 충분):
  - 음식점/카페 관리 시스템
  - 온라인 쇼핑몰 (상품-주문-고객)
  - 도서관/서점 (도서-대출-회원)
  - 피트니스 센터 (회원-수업-예약)
  - 영화관 (영화-상영-예매)

❌ 피해야 할 도메인:
  - 테이블이 10개 이상 필요한 것
  - 데이터 구하기가 어려운 것
  - 업무 지식이 너무 전문적인 것
```

### 제안서 양식

```markdown
# 프로젝트 제안서

## 1. 도메인: ________________
## 2. 대상 사용자: ________________
## 3. 해결할 문제: ________________

## 4. 테이블 설계

### 테이블 1: ________________
CREATE TABLE ... (
    ...
);
COMMENT ON TABLE ...;
COMMENT ON COLUMN ...;

## 5. 질문 10개

[Easy] Q1: "________________"
SQL: ...

[Medium] Q5: "________________"
SQL: ...

[Hard] Q9: "________________"
SQL: ...

## 6. ERD (Mermaid)
```

> 🎯 **실습 체크리스트 — 과제 #1**
> - [ ] 도메인 선정 완료
> - [ ] 테이블 3~5개 설계 (CREATE TABLE + COMMENT ON)
> - [ ] 질문 10개 작성 (Easy/Medium/Hard 분포)
> - [ ] 각 질문에 기대 SQL 작성
> - [ ] ERD 초안 작성

## 📌 8H 핵심 정리
- **과제 #1** = Day 2 시작 시 제출하는 프로젝트 제안서
- 도메인은 **3~5개 테이블**로 표현 가능한 것을 선택
- **COMMENT ON**을 모든 컬럼에 달아야 AI가 잘 이해함
- 질문 난이도를 **Easy/Medium/Hard로 분산**시키기

---

## 📌 Day 1 전체 정리

| 시간 | 주제 | 핵심 키워드 |
|---|---|---|
| 1H | OT & 데모 | Agentic Analytics, 환경 셋업 |
| 2H | PostgreSQL 기초 | SELECT, WHERE, ORDER BY, LIMIT |
| 3H | 집계·조인 | GROUP BY, JOIN, CTE, 윈도우 함수 |
| 4H | Schema Intelligence | COMMENT ON, FK, 리포팅 뷰, ERD |
| 5H | LlamaIndex | RAG, Documents → Index → Query |
| 6H | 임베딩 + ChromaDB | 벡터, 코사인 유사도, 영속 저장 |
| 7H | Text-to-SQL | NLSQLTableQueryEngine, 성공과 실패 |
| 8H | 프로젝트 브리핑 | 과제 #1: 제안서 작성 |

> **내일(Day 2) 예고**: 제안서 피어리뷰 → Text-to-SQL 정확도 높이기 → 병원 상담사 만들기 → Gradio UI!
