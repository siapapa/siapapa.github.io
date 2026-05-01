# Day 1 — 개관 · SQL · RAG 파이프라인 + 프로젝트 브리핑 (1~8H)

> 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> 실행 환경: Google Colab + Neon PostgreSQL + OpenAI API

---

## 공통 부트스트랩 (모든 노트북 첫 셀)

```python
# ============================================================
# 📦 패키지 설치 (Colab 환경)
# ============================================================
!pip install -q \
    psycopg2-binary sqlalchemy \
    llama-index llama-index-embeddings-openai llama-index-llms-openai \
    llama-index-vector-stores-chroma \
    chromadb \
    openai \
    tabulate pandas matplotlib

# ============================================================
# 🔑 환경변수 설정
# ============================================================
import os
from google.colab import userdata

os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

# 연결 확인
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()")).fetchone()
    print(f"✅ PostgreSQL 연결 성공: {result[0][:50]}...")
```

---

# 1H · OT & Agentic Analytics 전체 데모

## 학습목표

- "에이전틱 분석(Agentic Analytics)"이 기존 BI/Text-to-SQL과 어떻게 다른지 설명할 수 있다.
- 4일간 만들어 갈 최종 산출물의 전체 모습을 이해한다.
- Colab + Neon + OpenAI API 환경을 설정할 수 있다.

## 이론 — Analytics의 진화

### 3단계 진화 모델

데이터 분석 방식은 크게 세 단계로 진화해 왔습니다.

| 단계 | 방식 | 사용자 경험 | 한계 |
|---|---|---|---|
| **1세대: Traditional BI** | 분석가가 대시보드·SQL 수작업 | 정적 보고서 | 질문이 미리 정해져야 함 |
| **2세대: Text-to-SQL** | LLM이 자연어 → SQL 1회 변환 | 단발성 질의 | 복잡한 추론·검증 불가 |
| **3세대: Agentic Analytics** | LLM이 상태를 갖고 다단계 계획·실행·검증·재시도 | 대화형·자율 분석 | 신뢰성 관리 필요 |

### 왜 Agentic인가?

**Text-to-SQL의 한계:**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

Text-to-SQL → SQL 1회 생성 → 실행 → 끝
  ❌ 잘못된 SQL을 감지하지 못함
  ❌ 복잡한 질문을 분해하지 못함
  ❌ 결과가 이상해도 재시도하지 않음
```

**Agentic Analytics의 접근:**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

에이전트:
  1단계: 질문 분석 → "매출 상위 5개" + "전년 대비 성장률" 두 하위 질문으로 분해
  2단계: SQL 생성 → 첫 번째 쿼리 작성
  3단계: SQL 실행 → 결과 확인
  4단계: 검증 → "행이 0개? 날짜 조건을 확인하자" → SQL 수정
  5단계: 재실행 → 성공 → 자연어 답변 생성
```

### 에이전트의 4요소

```
┌─────────────────────────────────────────────┐
│               AI Agent                       │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │  State   │  │  Tools   │                 │
│  │ 대화 이력 │  │ SQL 실행  │                 │
│  │ 현재 SQL  │  │ 검색 엔진 │                 │
│  │ 실행 결과 │  │ LLM 호출  │                 │
│  └──────────┘  └──────────┘                 │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │ Planning │  │Validation│                 │
│  │ 질문 분해 │  │ 결과 검증 │                 │
│  │ 단계 계획 │  │ 재시도    │                 │
│  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────┘
```

1. **State (상태)** — 에이전트가 "기억"하는 것. 대화 히스토리, 현재 작업 중인 SQL, 이전 실행 결과 등.
2. **Tools (도구)** — 에이전트가 "사용"하는 것. SQL 실행기, 벡터 검색, LLM 호출 등.
3. **Planning (계획)** — 에이전트가 "생각"하는 것. 복잡한 질문을 하위 단계로 분해.
4. **Validation (검증)** — 에이전트가 "확인"하는 것. 결과가 맞는지, SQL에 오류가 없는지.

## 핵심 코드 — `00_demo_agent.ipynb` (완성형 에이전트 시연)

> 아래 코드는 강사가 시연하는 완성본입니다. 학생들은 4일에 걸쳐 이 에이전트를 직접 구축합니다.

```python
# ============================================================
# 🎯 완성형 SQL 분석 에이전트 데모
# ============================================================
# 이 노트북은 강의 첫 시간에 시연합니다.
# 학생들이 4일 후 완성할 에이전트의 최종 모습을 보여줍니다.

!pip install -q langchain langchain-openai langgraph sqlalchemy psycopg2-binary tabulate

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
```

```python
# ============================================================
# 1. 데이터베이스 연결
# ============================================================
from sqlalchemy import create_engine, text, inspect

engine = create_engine(os.environ["NEON_DSN"])

# 테이블 목록 확인
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"📋 사용 가능한 테이블: {tables}")
```

```python
# ============================================================
# 2. 스키마 정보 수집 (에이전트가 참고할 컨텍스트)
# ============================================================
def get_schema_info(engine, table_names: list[str]) -> str:
    """테이블 스키마 정보를 LLM이 읽을 수 있는 텍스트로 변환"""
    inspector = inspect(engine)
    schema_parts = []
    
    for table in table_names:
        columns = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        fks = inspector.get_foreign_keys(table)
        
        col_defs = []
        for col in columns:
            nullable = "" if col["nullable"] else " NOT NULL"
            col_defs.append(f"  {col['name']} {col['type']}{nullable}")
        
        # COMMENT ON 정보 가져오기
        with engine.connect() as conn:
            comments = conn.execute(text(f"""
                SELECT column_name, col_description('{table}'::regclass, ordinal_position)
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)).fetchall()
        
        comment_lines = []
        for col_name, comment in comments:
            if comment:
                comment_lines.append(f"  -- {col_name}: {comment}")
        
        fk_lines = []
        for fk in fks:
            fk_lines.append(
                f"  FOREIGN KEY ({', '.join(fk['constrained_columns'])}) "
                f"REFERENCES {fk['referred_table']}({', '.join(fk['referred_columns'])})"
            )
        
        part = f"CREATE TABLE {table} (\n"
        part += ",\n".join(col_defs)
        if pk and pk["constrained_columns"]:
            part += f",\n  PRIMARY KEY ({', '.join(pk['constrained_columns'])})"
        if fk_lines:
            part += ",\n" + ",\n".join(fk_lines)
        part += "\n);\n"
        if comment_lines:
            part += "-- Column descriptions:\n" + "\n".join(comment_lines)
        
        schema_parts.append(part)
    
    return "\n\n".join(schema_parts)

schema_info = get_schema_info(engine, tables)
print(schema_info)
```

```python
# ============================================================
# 3. LangGraph 에이전트 정의
# ============================================================
import re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- 상태 정의 ---
class AgentState(TypedDict):
    question: str          # 사용자 질문
    sql: str               # 생성된 SQL
    result: str            # 실행 결과
    error: str             # 에러 메시지
    answer: str            # 최종 답변
    attempts: int          # 재시도 횟수

# --- 보안 가드레일 ---
BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

def check_sql_safety(sql: str) -> str | None:
    """위험한 SQL 키워드를 감지하면 에러 메시지를 반환"""
    match = BLOCKED_KEYWORDS.search(sql)
    if match:
        return f"🚫 보안 위반: '{match.group()}' 명령은 허용되지 않습니다."
    return None

def inject_limit(sql: str, limit: int = 1000) -> str:
    """LIMIT 절이 없으면 자동으로 추가"""
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";")
        sql += f"\nLIMIT {limit};"
    return sql

# --- 노드 함수들 ---
def generate_sql(state: AgentState) -> dict:
    """자연어 질문을 SQL로 변환"""
    error_context = ""
    if state.get("error"):
        error_context = f"\n\n이전 시도에서 발생한 오류:\n{state['error']}\n이 오류를 피해서 SQL을 다시 작성하세요."
    
    prompt = f"""당신은 PostgreSQL 전문가입니다. 아래 스키마를 참고하여 질문에 답하는 SQL을 작성하세요.

## 데이터베이스 스키마
{schema_info}

## 규칙
- SELECT 문만 작성하세요.
- 테이블명과 컬럼명을 정확히 사용하세요.
- 한국어 질문에 대해 SQL만 반환하세요 (설명 없이).
- 날짜 관련 함수는 PostgreSQL 문법을 사용하세요.
{error_context}

## 질문
{state['question']}

## SQL
"""
    response = llm.invoke(prompt)
    sql = response.content.strip()
    # 마크다운 코드 블록 제거
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    
    return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

def run_sql(state: AgentState) -> dict:
    """SQL을 실행하고 결과를 반환"""
    sql = state["sql"]
    
    # 보안 검사
    safety_error = check_sql_safety(sql)
    if safety_error:
        return {"error": safety_error, "result": ""}
    
    # LIMIT 주입
    sql = inject_limit(sql)
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
            if not rows:
                return {"result": "(결과 없음)", "error": ""}
            
            # 결과를 읽기 좋은 텍스트로 변환
            from tabulate import tabulate
            headers = rows[0]._fields if hasattr(rows[0], '_fields') else range(len(rows[0]))
            result_text = tabulate(rows, headers=headers, tablefmt="grid")
            return {"result": result_text, "error": ""}
    except Exception as e:
        return {"error": f"SQL 실행 오류: {str(e)}", "result": ""}

def validate(state: AgentState) -> dict:
    """결과를 검증하고 재시도 여부를 결정"""
    if state.get("error"):
        return state  # 에러가 있으면 그대로 전달
    return {"error": ""}  # 성공

def answer(state: AgentState) -> dict:
    """실행 결과를 자연어로 요약"""
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"❌ 죄송합니다. 질문에 답변하지 못했습니다.\n오류: {state['error']}"}
    
    prompt = f"""아래 SQL 쿼리 결과를 한국어로 자연스럽게 요약해주세요.

## 원래 질문
{state['question']}

## 실행된 SQL
{state['sql']}

## 쿼리 결과
{state['result']}

## 지시사항
- 숫자는 천 단위 구분자를 사용하세요.
- 결과가 표 형태라면 핵심만 요약하세요.
- 가능하면 인사이트도 한 줄 추가하세요.
"""
    response = llm.invoke(prompt)
    return {"answer": response.content}

def should_retry(state: AgentState) -> str:
    """재시도 여부를 판단"""
    if not state.get("error"):
        return "answer"
    if state.get("attempts", 0) >= 3:
        return "answer"
    return "generate_sql"

# --- 그래프 조립 ---
graph = StateGraph(AgentState)

graph.add_node("generate_sql", generate_sql)
graph.add_node("run_sql", run_sql)
graph.add_node("validate", validate)
graph.add_node("answer", answer)

graph.set_entry_point("generate_sql")
graph.add_edge("generate_sql", "run_sql")
graph.add_edge("run_sql", "validate")
graph.add_conditional_edges("validate", should_retry)
graph.add_edge("answer", END)

agent = graph.compile()
```

```python
# ============================================================
# 4. 에이전트 실행 시연
# ============================================================
def ask(question: str):
    """에이전트에 질문하고 결과를 출력"""
    print(f"\n{'='*60}")
    print(f"❓ 질문: {question}")
    print(f"{'='*60}")
    
    result = agent.invoke({"question": question, "attempts": 0})
    
    print(f"\n📝 생성된 SQL:\n{result['sql']}")
    print(f"\n📊 실행 결과:\n{result['result']}")
    print(f"\n💬 답변:\n{result['answer']}")
    print(f"\n🔄 시도 횟수: {result['attempts']}")
    return result

# 시연 질문들
ask("현재 등록된 환자 수는 몇 명인가요?")
ask("진료과별 의사 수를 보여주세요.")
ask("지난 3개월간 가장 많이 방문한 환자 Top 5는?")
```

```python
# ============================================================
# 5. 에이전트 그래프 시각화
# ============================================================
from IPython.display import Image, display

try:
    display(Image(agent.get_graph().draw_mermaid_png()))
except Exception:
    print(agent.get_graph().draw_mermaid())
```

## 4일 로드맵

```
┌─────────────────────────────────────────────────────────┐
│                    4일 학습 여정                          │
├──────────┬──────────────────────────────────────────────┤
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

## 실습 과제 — 환경 셋업

1. Google Colab에서 새 노트북 생성
2. Neon (https://neon.tech) 가입 → 무료 인스턴스 생성 → Connection String 복사
3. Colab Secrets에 다음 키 등록:
   - `OPENAI_API_KEY` — OpenAI API 키
   - `NEON_DSN` — `postgresql://user:pass@host/dbname?sslmode=require`
4. 부트스트랩 셀 실행 → `SELECT version()` 결과 확인

## 강사 노트

- **시간 배분**: 이론 20분 (3단계 진화 + 에이전트 4요소) → 시연 20분 (완성 에이전트 실행) → 셋업 10분
- 시연 시 LangSmith 트레이스를 열어 에이전트 내부 동작을 함께 보여주면 효과적
- Neon 가입에서 막히는 학생이 반드시 있음 → 사전에 스크린샷 가이드 준비
- **핵심 메시지**: "오늘 본 이 에이전트를, 4일 후에는 여러분이 직접 만듭니다"

---

# 2H · PostgreSQL 기초 (Colab + Neon)

## 학습목표

- Neon PostgreSQL 인스턴스를 생성하고 Colab에서 접속할 수 있다.
- `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`을 사용하여 데이터를 조회할 수 있다.
- PostgreSQL의 주요 데이터 타입을 이해한다.
- `EXPLAIN`으로 쿼리 실행 계획을 읽을 수 있다.

## 이론 — 왜 PostgreSQL인가?

### RDBMS 비교

| 특성 | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| 라이선스 | 완전 무료(BSD) | 이중 라이선스 | 퍼블릭 도메인 |
| 표준 SQL 준수 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 윈도우 함수 | ✅ 완전 지원 | ✅ (8.0+) | ✅ 제한적 |
| JSON 지원 | ✅ JSONB | ✅ JSON | ✅ JSON |
| CTE (WITH) | ✅ 재귀 포함 | ✅ (8.0+) | ✅ |
| COMMENT ON | ✅ | ❌ | ❌ |
| 확장성 | 매우 높음 | 보통 | 임베디드용 |

> PostgreSQL은 SQL 표준을 가장 충실히 따르며, `COMMENT ON` 지원으로 **AI 가독성 스키마** 구축에 이상적입니다.

### 왜 Neon인가?

- **설치 불필요** — 브라우저에서 30초면 인스턴스 생성
- **무료 티어** — 개인 프로젝트에 충분한 0.5GB 스토리지
- **어디서나 동일한 DSN** — Colab, 로컬, IDE 상관없이 같은 Connection String
- **학생별 독립 인스턴스** — DDL 실험해도 서로 간섭 없음

## 핵심 코드 — `01_postgres_basics.ipynb`

### Neon 접속 및 기본 설정

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q psycopg2-binary sqlalchemy pandas tabulate

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
```

```python
# ============================================================
# 1. SQLAlchemy로 Neon 접속
# ============================================================
from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine(os.environ["NEON_DSN"])

# 연결 테스트
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).fetchone()[0]
    print(f"✅ PostgreSQL 버전: {version}")
    
    # 현재 시간 확인
    now = conn.execute(text("SELECT NOW()")).fetchone()[0]
    print(f"🕐 서버 시간: {now}")
```

```python
# ============================================================
# 2. psycopg2로 직접 접속 (로우레벨)
# ============================================================
import psycopg2

conn_pg = psycopg2.connect(os.environ["NEON_DSN"])
cur = conn_pg.cursor()

cur.execute("SELECT current_database(), current_user")
db_name, user_name = cur.fetchone()
print(f"📁 데이터베이스: {db_name}, 👤 사용자: {user_name}")

cur.close()
conn_pg.close()

# 💡 일반적으로 SQLAlchemy를 사용하는 것이 더 편리합니다.
# psycopg2는 저수준 제어가 필요할 때만 사용합니다.
```

### 샘플 DB 임포트

```python
# ============================================================
# 3. 병원 데이터베이스 생성
# ============================================================
hospital_ddl = """
-- 기존 테이블 제거 (순서 중요: FK 의존성)
DROP TABLE IF EXISTS diagnoses CASCADE;
DROP TABLE IF EXISTS visits CASCADE;
DROP TABLE IF EXISTS doctors CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS departments CASCADE;

-- 진료과 테이블
CREATE TABLE departments (
    department_id   SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL,
    floor           INT,
    phone           VARCHAR(20)
);
COMMENT ON TABLE departments IS '병원의 진료과 정보';
COMMENT ON COLUMN departments.department_id IS '진료과 고유 식별자';
COMMENT ON COLUMN departments.name IS '진료과명 (예: 내과, 외과, 소아과)';
COMMENT ON COLUMN departments.floor IS '진료과 위치 층수';
COMMENT ON COLUMN departments.phone IS '진료과 대표 전화번호';

-- 의사 테이블
CREATE TABLE doctors (
    doctor_id       SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    department_id   INT NOT NULL REFERENCES departments(department_id),
    specialty       VARCHAR(100),
    hire_date       DATE NOT NULL,
    salary          NUMERIC(12,2)
);
COMMENT ON TABLE doctors IS '의사 정보';
COMMENT ON COLUMN doctors.doctor_id IS '의사 고유 식별자';
COMMENT ON COLUMN doctors.name IS '의사 이름';
COMMENT ON COLUMN doctors.department_id IS '소속 진료과 (departments 테이블 참조)';
COMMENT ON COLUMN doctors.specialty IS '세부 전공 (예: 심장내과, 정형외과)';
COMMENT ON COLUMN doctors.hire_date IS '입사일';
COMMENT ON COLUMN doctors.salary IS '월급 (원)';

-- 환자 테이블
CREATE TABLE patients (
    patient_id      SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    birth_date      DATE NOT NULL,
    gender          CHAR(1) NOT NULL CHECK (gender IN ('M','F')),
    phone           VARCHAR(20),
    address         VARCHAR(200),
    blood_type      VARCHAR(3) CHECK (blood_type IN ('A','B','O','AB')),
    created_at      TIMESTAMP DEFAULT NOW()
);
COMMENT ON TABLE patients IS '환자 기본 정보';
COMMENT ON COLUMN patients.patient_id IS '환자 고유 식별자';
COMMENT ON COLUMN patients.name IS '환자 이름';
COMMENT ON COLUMN patients.birth_date IS '생년월일';
COMMENT ON COLUMN patients.gender IS '성별: M=남성, F=여성';
COMMENT ON COLUMN patients.phone IS '연락처';
COMMENT ON COLUMN patients.address IS '주소';
COMMENT ON COLUMN patients.blood_type IS '혈액형: A, B, O, AB';
COMMENT ON COLUMN patients.created_at IS '환자 등록 일시';

-- 방문(진료) 테이블
CREATE TABLE visits (
    visit_id        SERIAL PRIMARY KEY,
    patient_id      INT NOT NULL REFERENCES patients(patient_id),
    doctor_id       INT NOT NULL REFERENCES doctors(doctor_id),
    visit_date      DATE NOT NULL,
    visit_type      VARCHAR(20) NOT NULL CHECK (visit_type IN ('outpatient','inpatient','emergency')),
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                    CHECK (status IN ('scheduled','completed','cancelled','no_show')),
    chief_complaint TEXT,
    cost            NUMERIC(10,2)
);
COMMENT ON TABLE visits IS '환자 진료 방문 기록';
COMMENT ON COLUMN visits.visit_id IS '방문 고유 식별자';
COMMENT ON COLUMN visits.patient_id IS '방문 환자 (patients 테이블 참조)';
COMMENT ON COLUMN visits.doctor_id IS '담당 의사 (doctors 테이블 참조)';
COMMENT ON COLUMN visits.visit_date IS '진료 날짜';
COMMENT ON COLUMN visits.visit_type IS '진료 유형: outpatient=외래, inpatient=입원, emergency=응급';
COMMENT ON COLUMN visits.status IS '진료 상태: scheduled=예약, completed=완료, cancelled=취소, no_show=미방문';
COMMENT ON COLUMN visits.chief_complaint IS '주요 증상/호소 내용';
COMMENT ON COLUMN visits.cost IS '진료비 (원)';

-- 진단 테이블
CREATE TABLE diagnoses (
    diagnosis_id    SERIAL PRIMARY KEY,
    visit_id        INT NOT NULL REFERENCES visits(visit_id),
    icd_code        VARCHAR(10) NOT NULL,
    description     VARCHAR(200) NOT NULL,
    severity        VARCHAR(10) CHECK (severity IN ('mild','moderate','severe'))
);
COMMENT ON TABLE diagnoses IS '진료 시 내려진 진단 기록';
COMMENT ON COLUMN diagnoses.diagnosis_id IS '진단 고유 식별자';
COMMENT ON COLUMN diagnoses.visit_id IS '관련 방문 (visits 테이블 참조)';
COMMENT ON COLUMN diagnoses.icd_code IS 'ICD-10 질병 분류 코드';
COMMENT ON COLUMN diagnoses.description IS '진단명 (한국어)';
COMMENT ON COLUMN diagnoses.severity IS '중증도: mild=경증, moderate=중등, severe=중증';
""";

with engine.begin() as conn:
    conn.execute(text(hospital_ddl))
print("✅ 병원 DB 스키마 생성 완료!")
```

```python
# ============================================================
# 4. 시드 데이터 삽입
# ============================================================
seed_data = """
-- 진료과
INSERT INTO departments (name, floor, phone) VALUES
('내과', 3, '02-1234-1001'),
('외과', 4, '02-1234-1002'),
('소아과', 2, '02-1234-1003'),
('정형외과', 4, '02-1234-1004'),
('피부과', 2, '02-1234-1005'),
('신경과', 5, '02-1234-1006'),
('산부인과', 3, '02-1234-1007'),
('안과', 2, '02-1234-1008');

-- 의사 (20명)
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

-- 환자 (30명)
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

-- 방문 기록 (50건, 최근 6개월)
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

-- 진단 (각 completed 방문에 1~2개)
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

### SELECT 기본 문법

```python
# ============================================================
# 5. SELECT 기본 — 데이터 조회의 시작
# ============================================================

def run_query(sql: str, title: str = ""):
    """SQL을 실행하고 결과를 DataFrame으로 반환"""
    if title:
        print(f"\n📌 {title}")
    print(f"SQL: {sql.strip()}\n")
    df = pd.read_sql(sql, engine)
    print(df.to_string(index=False))
    print(f"({len(df)}행)")
    return df
```

```python
# --- 전체 조회 ---
run_query("SELECT * FROM patients LIMIT 5", "환자 테이블 미리보기")
```

```python
# --- 특정 컬럼 선택 ---
run_query("""
    SELECT patient_id, name, gender, blood_type
    FROM patients
    LIMIT 10
""", "환자 이름과 혈액형")
```

```python
# --- WHERE 조건 ---
run_query("""
    SELECT name, birth_date, gender
    FROM patients
    WHERE gender = 'F'
    ORDER BY birth_date
""", "여성 환자 (생년월일순)")
```

```python
# --- 비교 연산자 ---
run_query("""
    SELECT name, birth_date,
           EXTRACT(YEAR FROM AGE(birth_date)) AS age
    FROM patients
    WHERE EXTRACT(YEAR FROM AGE(birth_date)) >= 40
    ORDER BY birth_date
""", "40세 이상 환자")
```

```python
# --- BETWEEN ---
run_query("""
    SELECT visit_id, patient_id, visit_date, cost
    FROM visits
    WHERE visit_date BETWEEN '2026-01-01' AND '2026-01-31'
    ORDER BY visit_date
""", "2026년 1월 방문 기록")
```

```python
# --- IN ---
run_query("""
    SELECT name, blood_type
    FROM patients
    WHERE blood_type IN ('A', 'AB')
    ORDER BY name
""", "혈액형이 A 또는 AB인 환자")
```

```python
# --- LIKE 패턴 매칭 ---
run_query("""
    SELECT name, address
    FROM patients
    WHERE address LIKE '서울시 강%'
""", "서울시 강~구 거주 환자")
```

```python
# --- IS NULL / IS NOT NULL ---
run_query("""
    SELECT visit_id, patient_id, visit_date, cost
    FROM visits
    WHERE cost IS NULL OR cost = 0
""", "진료비가 없는 방문 (취소/미방문)")
```

```python
# --- ORDER BY + LIMIT ---
run_query("""
    SELECT v.visit_id, p.name, v.visit_date, v.cost
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE v.cost IS NOT NULL AND v.cost > 0
    ORDER BY v.cost DESC
    LIMIT 5
""", "진료비 상위 5건")
```

```python
# --- 별칭(Alias) + 계산 컬럼 ---
run_query("""
    SELECT 
        name AS 이름,
        birth_date AS 생년월일,
        EXTRACT(YEAR FROM AGE(birth_date)) AS 나이,
        CASE gender WHEN 'M' THEN '남' WHEN 'F' THEN '여' END AS 성별
    FROM patients
    ORDER BY 나이 DESC
    LIMIT 10
""", "환자 정보 (한국어 별칭)")
```

### EXPLAIN 맛보기

```python
# ============================================================
# 6. EXPLAIN — 쿼리 실행 계획 읽기
# ============================================================

# 쿼리가 어떻게 실행되는지 확인
explain_sql = """
EXPLAIN (FORMAT TEXT)
SELECT p.name, v.visit_date, d.name AS doctor_name
FROM visits v
JOIN patients p ON p.patient_id = v.patient_id
JOIN doctors d ON d.doctor_id = v.doctor_id
WHERE v.visit_date >= '2026-01-01'
ORDER BY v.visit_date DESC
"""

with engine.connect() as conn:
    plan = conn.execute(text(explain_sql)).fetchall()
    print("📋 실행 계획:")
    for row in plan:
        print(row[0])
```

```
# 실행 계획 읽는 법:
# - Seq Scan: 테이블 전체를 순차적으로 읽음 (느릴 수 있음)
# - Index Scan: 인덱스를 사용해 빠르게 찾음
# - Hash Join / Nested Loop: 테이블 조인 방식
# - Sort: 정렬 작업
# - cost=초기비용..총비용: 비용 추정값
# - rows: 예상 행 수
```

### PostgreSQL 주요 데이터 타입

```
┌──────────────┬─────────────────────────────────────────┐
│    타입       │  설명 및 예시                             │
├──────────────┼─────────────────────────────────────────┤
│ INTEGER/INT  │ 정수 (-2^31 ~ 2^31-1)                    │
│ SERIAL       │ 자동 증가 정수 (PK에 사용)                │
│ BIGINT       │ 큰 정수 (-2^63 ~ 2^63-1)                │
│ NUMERIC(p,s) │ 정밀 소수 (예: NUMERIC(10,2) → 99999999.99) │
│ VARCHAR(n)   │ 가변 길이 문자열 (최대 n자)               │
│ TEXT         │ 무제한 문자열                             │
│ CHAR(n)      │ 고정 길이 문자열                          │
│ DATE         │ 날짜 (YYYY-MM-DD)                        │
│ TIMESTAMP    │ 날짜+시간                                │
│ BOOLEAN      │ TRUE/FALSE                               │
│ JSONB        │ JSON 데이터 (인덱싱 가능)                 │
└──────────────┴─────────────────────────────────────────┘
```

## 실습 과제

1. `doctors` 테이블에서 2020년 이후 입사한 의사 목록을 급여 내림차순으로 조회하세요.
2. `visits` 테이블에서 응급(`emergency`) 방문 기록만 찾아 날짜순으로 정렬하세요.
3. 혈액형이 `O`인 남성 환자의 이름과 주소를 조회하세요.
4. 진료비가 10만원 이상인 방문에서 환자명, 진료일, 비용을 조회하세요. (`JOIN` 사용)
5. `EXPLAIN`을 사용하여 위 쿼리 4번의 실행 계획을 확인하세요.

## 강사 노트

- **시간 배분**: Neon 셋업 확인 5분 → 이론(왜 PostgreSQL/Neon) 5분 → DB 임포트 5분 → SELECT 실습 25분 → EXPLAIN 5분 → 과제 5분
- 학생들이 Neon DSN을 잘못 입력하는 경우가 많음 — `?sslmode=require` 빠뜨리면 연결 실패
- `psycopg2` vs `SQLAlchemy` 차이를 묻는 학생이 있을 것 — "psycopg2는 드라이버, SQLAlchemy는 ORM/래퍼"로 간단히 설명
- `pd.read_sql()`을 일찍 소개하면 이후 실습이 편해짐

---

# 3H · 집계·조인·CTE·윈도우 함수

## 학습목표

- `GROUP BY` / `HAVING`으로 데이터를 그룹화하고 필터링할 수 있다.
- 다양한 `JOIN` 유형의 차이를 이해하고 적재적소에 사용할 수 있다.
- `CTE`로 복잡한 쿼리를 가독성 있게 구조화할 수 있다.
- 윈도우 함수(`ROW_NUMBER`, `RANK`, `LAG` 등)의 기본 사용법을 익힌다.

## 이론 — 집계 함수와 GROUP BY

### 집계 함수 (Aggregate Functions)

| 함수 | 설명 | 예시 |
|---|---|---|
| `COUNT(*)` | 행 수 | 전체 환자 수 |
| `COUNT(col)` | NULL이 아닌 값 수 | 전화번호가 있는 환자 수 |
| `SUM(col)` | 합계 | 총 진료비 |
| `AVG(col)` | 평균 | 평균 진료비 |
| `MAX(col)` | 최대값 | 최고 진료비 |
| `MIN(col)` | 최소값 | 최저 진료비 |

### GROUP BY + HAVING 흐름

```
전체 데이터  →  WHERE (행 필터)  →  GROUP BY (그룹화)  →  HAVING (그룹 필터)  →  SELECT  →  ORDER BY
```

> **WHERE vs HAVING**: WHERE는 그룹화 **전**에, HAVING은 그룹화 **후**에 필터링합니다.

## 핵심 코드

### GROUP BY 예제

```python
# ============================================================
# 1. GROUP BY — 데이터 그룹화
# ============================================================

# 진료과별 의사 수
run_query("""
    SELECT d.name AS department, COUNT(*) AS doctor_count
    FROM doctors doc
    JOIN departments d ON d.department_id = doc.department_id
    GROUP BY d.name
    ORDER BY doctor_count DESC
""", "진료과별 의사 수")
```

```python
# 월별 방문 건수
run_query("""
    SELECT 
        TO_CHAR(visit_date, 'YYYY-MM') AS month,
        COUNT(*) AS visit_count,
        SUM(COALESCE(cost, 0)) AS total_cost,
        ROUND(AVG(cost), 0) AS avg_cost
    FROM visits
    WHERE status = 'completed'
    GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ORDER BY month
""", "월별 방문 통계")
```

```python
# 혈액형별 환자 분포
run_query("""
    SELECT 
        blood_type,
        COUNT(*) AS count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
    FROM patients
    GROUP BY blood_type
    ORDER BY count DESC
""", "혈액형별 환자 분포 (%)")
```

```python
# HAVING — 5건 이상 방문한 환자만
run_query("""
    SELECT 
        p.name,
        COUNT(*) AS visit_count,
        SUM(COALESCE(v.cost, 0)) AS total_cost
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE v.status = 'completed'
    GROUP BY p.name
    HAVING COUNT(*) >= 3
    ORDER BY visit_count DESC
""", "3회 이상 방문한 환자")
```

```python
# 진료과별 평균 급여가 750만원 이상인 곳
run_query("""
    SELECT 
        d.name AS department,
        COUNT(*) AS doctors,
        ROUND(AVG(doc.salary), 0) AS avg_salary,
        MAX(doc.salary) AS max_salary
    FROM doctors doc
    JOIN departments d ON d.department_id = doc.department_id
    GROUP BY d.name
    HAVING AVG(doc.salary) >= 7500000
    ORDER BY avg_salary DESC
""", "평균 급여 750만원 이상 진료과")
```

### JOIN 유형별 예제

```python
# ============================================================
# 2. JOIN — 테이블 결합
# ============================================================

# INNER JOIN: 양쪽 모두 매칭되는 행만
run_query("""
    SELECT 
        p.name AS patient_name,
        d.name AS doctor_name,
        v.visit_date,
        v.chief_complaint
    FROM visits v
    INNER JOIN patients p ON p.patient_id = v.patient_id
    INNER JOIN doctors d ON d.doctor_id = v.doctor_id
    WHERE v.status = 'completed'
    ORDER BY v.visit_date DESC
    LIMIT 10
""", "INNER JOIN — 완료된 진료 기록 (최근 10건)")
```

```python
# LEFT JOIN: 왼쪽 테이블의 모든 행 + 매칭되는 오른쪽 행
# "방문 기록이 없는 환자도 포함"하고 싶을 때
run_query("""
    SELECT 
        p.name,
        COUNT(v.visit_id) AS visit_count
    FROM patients p
    LEFT JOIN visits v ON v.patient_id = p.patient_id
    GROUP BY p.patient_id, p.name
    ORDER BY visit_count, p.name
""", "LEFT JOIN — 모든 환자의 방문 횟수 (0건 포함)")
```

```python
# LEFT JOIN + IS NULL: "한 번도 방문하지 않은 환자"
run_query("""
    SELECT p.name, p.phone
    FROM patients p
    LEFT JOIN visits v ON v.patient_id = p.patient_id
    WHERE v.visit_id IS NULL
""", "LEFT JOIN + IS NULL — 미방문 환자")
```

```python
# SELF JOIN: 같은 테이블끼리 조인
# "같은 진료과 소속 의사 쌍"
run_query("""
    SELECT 
        a.name AS doctor_a,
        b.name AS doctor_b,
        d.name AS department
    FROM doctors a
    JOIN doctors b ON a.department_id = b.department_id AND a.doctor_id < b.doctor_id
    JOIN departments d ON d.department_id = a.department_id
    ORDER BY department, doctor_a
""", "SELF JOIN — 같은 진료과 의사 쌍")
```

### 서브쿼리

```python
# ============================================================
# 3. 서브쿼리 (Subquery)
# ============================================================

# WHERE절 서브쿼리: 평균보다 급여가 높은 의사
run_query("""
    SELECT name, salary
    FROM doctors
    WHERE salary > (SELECT AVG(salary) FROM doctors)
    ORDER BY salary DESC
""", "평균 급여 이상인 의사")
```

```python
# FROM절 서브쿼리: 진료과별 최고 급여 의사
run_query("""
    SELECT sub.department, sub.doctor_name, sub.salary
    FROM (
        SELECT 
            d.name AS department,
            doc.name AS doctor_name,
            doc.salary,
            ROW_NUMBER() OVER (PARTITION BY d.department_id ORDER BY doc.salary DESC) AS rn
        FROM doctors doc
        JOIN departments d ON d.department_id = doc.department_id
    ) sub
    WHERE sub.rn = 1
    ORDER BY sub.salary DESC
""", "진료과별 최고 급여 의사")
```

```python
# EXISTS 서브쿼리: 진단 기록이 있는 방문만
run_query("""
    SELECT v.visit_id, p.name, v.visit_date
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE EXISTS (
        SELECT 1 FROM diagnoses dg WHERE dg.visit_id = v.visit_id
    )
    ORDER BY v.visit_date DESC
    LIMIT 10
""", "진단 기록이 존재하는 방문")
```

### CTE (Common Table Expressions)

```python
# ============================================================
# 4. CTE — 가독성 높은 쿼리 구조화
# ============================================================

# CTE 없이 → 읽기 어려운 중첩 쿼리
# CTE 사용 → 단계별로 명확하게

run_query("""
    WITH monthly_visits AS (
        -- 1단계: 월별 방문 집계
        SELECT
            TO_CHAR(visit_date, 'YYYY-MM') AS month,
            COUNT(*) AS cnt
        FROM visits
        WHERE status = 'completed'
        GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ),
    avg_visits AS (
        -- 2단계: 전체 월 평균
        SELECT AVG(cnt) AS avg_cnt FROM monthly_visits
    )
    -- 3단계: 평균 이상인 달만 선택
    SELECT 
        mv.month,
        mv.cnt AS visits,
        ROUND(av.avg_cnt, 1) AS overall_avg,
        CASE WHEN mv.cnt > av.avg_cnt THEN '📈 평균 이상' ELSE '📉 평균 미만' END AS status
    FROM monthly_visits mv, avg_visits av
    ORDER BY mv.month
""", "CTE — 월별 방문 vs 평균 비교")
```

### 윈도우 함수

```python
# ============================================================
# 5. 윈도우 함수 — 그룹 내 순위/누적/비교
# ============================================================

# 기본 구문: 함수() OVER (PARTITION BY ... ORDER BY ...)
# GROUP BY와 달리 행을 줄이지 않고 각 행에 계산값을 추가

# ROW_NUMBER: 순번 부여
run_query("""
    SELECT
        name, salary,
        department_id,
        ROW_NUMBER() OVER (ORDER BY salary DESC) AS overall_rank,
        ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dept_rank
    FROM doctors
""", "ROW_NUMBER — 전체 순위 vs 진료과별 순위")
```

```python
# RANK vs DENSE_RANK: 동점 처리 차이
run_query("""
    SELECT
        name, salary,
        RANK() OVER (ORDER BY salary DESC) AS rank,
        DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
    FROM doctors
    ORDER BY salary DESC
""", "RANK vs DENSE_RANK 비교")
# RANK: 공동 1위 2명 → 다음은 3위 (2위 건너뜀)
# DENSE_RANK: 공동 1위 2명 → 다음은 2위 (건너뛰지 않음)
```

```python
# LAG / LEAD: 이전/다음 행 참조
run_query("""
    SELECT
        TO_CHAR(visit_date, 'YYYY-MM') AS month,
        COUNT(*) AS visits,
        LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS prev_month,
        COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS diff
    FROM visits
    WHERE status = 'completed'
    GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ORDER BY month
""", "LAG — 전월 대비 방문 증감")
```

```python
# SUM OVER: 누적 합계
run_query("""
    SELECT
        visit_date,
        cost,
        SUM(cost) OVER (ORDER BY visit_date) AS running_total,
        AVG(cost) OVER (ORDER BY visit_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3
    FROM visits
    WHERE status = 'completed' AND cost > 0
    ORDER BY visit_date
    LIMIT 15
""", "SUM OVER — 누적 진료비 + 3건 이동평균")
```

## 실습 과제

```
문제: "각 의사별로 가장 최근에 진료한 환자 3명을 추출하세요."

힌트: 윈도우 함수 + CTE 조합
- CTE에서 ROW_NUMBER()로 의사별 최근 방문에 순번 부여
- 외부 쿼리에서 rn <= 3 필터
- 의사 이름, 환자 이름, 방문일 출력

기대 결과:
doctor_name | patient_name | visit_date | visit_rank
김철수       | 홍길동        | 2026-04-01 | 1
김철수       | 홍길동        | 2026-01-10 | 2
...
```

**정답:**
```sql
WITH ranked AS (
    SELECT
        d.name AS doctor_name,
        p.name AS patient_name,
        v.visit_date,
        ROW_NUMBER() OVER (PARTITION BY v.doctor_id ORDER BY v.visit_date DESC) AS rn
    FROM visits v
    JOIN doctors d ON d.doctor_id = v.doctor_id
    JOIN patients p ON p.patient_id = v.patient_id
)
SELECT doctor_name, patient_name, visit_date, rn AS visit_rank
FROM ranked
WHERE rn <= 3
ORDER BY doctor_name, visit_rank;
```

## 강사 노트

- **시간 배분**: GROUP BY 10분 → JOIN 15분 → 서브쿼리 5분 → CTE 5분 → 윈도우 함수 10분 → 실습 과제 5분
- JOIN을 시각적으로 설명할 때 벤 다이어그램을 칠판에 그리면 효과적
- 윈도우 함수가 처음인 학생이 많음 — `PARTITION BY`를 "그룹 안에서"로 설명
- CTE의 장점을 강조: "서브쿼리를 이름 붙여서 위에 꺼내놓은 것. 디버깅이 쉬워짐"

---

# 4H · Schema Intelligence — AI가 읽기 좋은 스키마

## 학습목표

- LLM이 스키마를 어떻게 읽는지 이해한다.
- AI 가독성 스키마의 5가지 설계 원칙을 적용할 수 있다.
- 정규화 vs 비정규화 트레이드오프를 AI 관점에서 판단할 수 있다.
- ERD를 Mermaid 문법으로 작성할 수 있다.

## 이론 — LLM은 스키마를 어떻게 읽는가?

### 핵심 인사이트

Text-to-SQL 시스템에서 LLM은 데이터베이스 스키마를 **프롬프트의 일부 텍스트**로 받습니다.

```
# LLM에 전달되는 프롬프트 (실제 예시)

Given the following database schema:

CREATE TABLE p (
    p_id INT PRIMARY KEY,
    nm VARCHAR(100),
    gen CHAR(1),
    bd DATE,
    bt VARCHAR(3)
);

Write a SQL query to answer: "30대 여성 환자 수는?"
```

위의 스키마를 보고 LLM은:
- `p`가 무슨 테이블인지 **추측**해야 합니다
- `nm`이 이름인지, `gen`이 성별인지 **짐작**해야 합니다
- `bt`가 혈액형인지 **알 수 없습니다**

→ 추측이 많아질수록 **오답 확률이 높아집니다**.

### 개선된 스키마

```sql
CREATE TABLE patients (
    patient_id   SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    gender       CHAR(1) NOT NULL CHECK (gender IN ('M','F')),
    birth_date   DATE NOT NULL,
    blood_type   VARCHAR(3) CHECK (blood_type IN ('A','B','O','AB'))
);

COMMENT ON TABLE patients IS '환자 기본 정보';
COMMENT ON COLUMN patients.gender IS '성별: M=남성, F=여성';
COMMENT ON COLUMN patients.blood_type IS '혈액형: A, B, O, AB';
```

→ LLM이 **즉시 이해**합니다. 추측 0%.

### 5가지 설계 원칙

#### 원칙 1: 명시적 네이밍

```
❌ 나쁜 예                    ✅ 좋은 예
─────────────────────────    ─────────────────────────
p_id                         patient_id
nm                           name
gen                          gender
v_dt                         visit_date
sal                          salary
dept_cd                      department_code
stat                         status
amt                          amount
```

> **규칙**: 축약 금지. 컬럼명만 보고 의미를 알 수 있어야 합니다.

#### 원칙 2: COMMENT ON — 모든 컬럼에 자연어 설명

```python
# COMMENT ON이 프롬프트에 반영되는 과정 확인
from sqlalchemy import inspect

inspector = inspect(engine)

# 테이블별 COMMENT 확인
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            c.table_name,
            c.column_name,
            pgd.description AS comment
        FROM information_schema.columns c
        LEFT JOIN pg_catalog.pg_stattio_all_tables st
            ON c.table_name = st.relname
        LEFT JOIN pg_catalog.pg_description pgd
            ON pgd.objoid = st.relid
            AND pgd.objsubid = c.ordinal_position
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position
    """))
    
    current_table = ""
    for row in result:
        if row[0] != current_table:
            current_table = row[0]
            print(f"\n📋 {current_table}")
        comment = row[2] or "(COMMENT 없음)"
        print(f"  {row[1]}: {comment}")
```

#### 원칙 3: FK 명시적 선언

```sql
-- ❌ FK 없이 → LLM이 JOIN 경로를 추론할 수 없음
CREATE TABLE visits (
    visit_id INT PRIMARY KEY,
    pid INT,          -- 어떤 테이블의 어떤 컬럼?
    did INT           -- doctor_id인지 department_id인지?
);

-- ✅ FK 명시 → LLM이 자동으로 JOIN 가능
CREATE TABLE visits (
    visit_id    INT PRIMARY KEY,
    patient_id  INT NOT NULL REFERENCES patients(patient_id),
    doctor_id   INT NOT NULL REFERENCES doctors(doctor_id)
);
```

#### 원칙 4: ENUM보다 룩업 테이블

```sql
-- ❌ CHECK 제약 → LLM이 허용된 값을 알려면 DDL을 정독해야 함
CREATE TABLE visits (
    status VARCHAR(20) CHECK (status IN ('scheduled','completed','cancelled','no_show'))
);

-- ✅ 룩업 테이블 → LLM이 SELECT로 값 목록을 직접 조회 가능
CREATE TABLE visit_status (
    code    VARCHAR(20) PRIMARY KEY,
    label   VARCHAR(50) NOT NULL,
    description TEXT
);
INSERT INTO visit_status VALUES
('scheduled',  '예약',   '진료 예약 상태'),
('completed',  '완료',   '진료 완료'),
('cancelled',  '취소',   '환자 또는 병원에 의해 취소'),
('no_show',    '미방문', '예약했으나 방문하지 않음');
```

#### 원칙 5: 적정 비정규화 — 리포팅 뷰

```sql
-- JOIN 깊이가 3단계 이상이면 LLM이 실수할 확률이 높아짐
-- → 리포팅 뷰로 "미리 JOIN해둔 테이블"을 제공

CREATE VIEW vw_visit_details AS
SELECT
    v.visit_id,
    v.visit_date,
    v.visit_type,
    v.status,
    v.chief_complaint,
    v.cost,
    p.name          AS patient_name,
    p.gender        AS patient_gender,
    EXTRACT(YEAR FROM AGE(p.birth_date)) AS patient_age,
    d.name          AS doctor_name,
    d.specialty     AS doctor_specialty,
    dept.name       AS department_name
FROM visits v
JOIN patients p    ON p.patient_id = v.patient_id
JOIN doctors d     ON d.doctor_id = v.doctor_id
JOIN departments dept ON dept.department_id = d.department_id;

COMMENT ON VIEW vw_visit_details IS '진료 상세 정보 (환자/의사/진료과 JOIN 완료)';
```

```python
# 뷰 생성
with engine.begin() as conn:
    conn.execute(text("""
        CREATE OR REPLACE VIEW vw_visit_details AS
        SELECT
            v.visit_id,
            v.visit_date,
            v.visit_type,
            v.status,
            v.chief_complaint,
            v.cost,
            p.name          AS patient_name,
            p.gender        AS patient_gender,
            EXTRACT(YEAR FROM AGE(p.birth_date)) AS patient_age,
            d.name          AS doctor_name,
            d.specialty     AS doctor_specialty,
            dept.name       AS department_name
        FROM visits v
        JOIN patients p    ON p.patient_id = v.patient_id
        JOIN doctors d     ON d.doctor_id = v.doctor_id
        JOIN departments dept ON dept.department_id = d.department_id
    """))
print("✅ vw_visit_details 뷰 생성 완료!")

# 뷰를 사용하면 복잡한 JOIN 없이 간단히 조회
run_query("""
    SELECT patient_name, doctor_name, department_name, visit_date, cost
    FROM vw_visit_details
    WHERE status = 'completed'
    ORDER BY visit_date DESC
    LIMIT 10
""", "뷰를 활용한 간편 조회")
```

### 정규화 vs 비정규화 트레이드오프

```
정규화 (Normalized)                  비정규화 (Denormalized)
────────────────────                 ────────────────────────
✅ 데이터 무결성                      ✅ 쿼리 단순화
✅ 업데이트 시 일관성                  ✅ LLM이 이해하기 쉬움
✅ 저장 공간 효율                      ✅ JOIN 없이 조회 가능
❌ JOIN이 많아 LLM이 실수             ❌ 데이터 중복 가능성
❌ 복잡한 쿼리 필요                    ❌ 업데이트 시 여러 곳 수정

AI 관점 권장: 원본은 정규화 유지 + 리포팅 뷰(vw_*)로 비정규화 제공
```

### ERD 작성 — Mermaid 문법

```python
# Mermaid ERD 문법 가이드
mermaid_erd = """
```mermaid
erDiagram
    departments ||--o{ doctors : "has"
    doctors ||--o{ visits : "conducts"
    patients ||--o{ visits : "makes"
    visits ||--o{ diagnoses : "results_in"

    departments {
        int department_id PK
        varchar name
        int floor
        varchar phone
    }
    
    doctors {
        int doctor_id PK
        varchar name
        int department_id FK
        varchar specialty
        date hire_date
        numeric salary
    }
    
    patients {
        int patient_id PK
        varchar name
        date birth_date
        char gender
        varchar phone
        varchar address
        varchar blood_type
    }
    
    visits {
        int visit_id PK
        int patient_id FK
        int doctor_id FK
        date visit_date
        varchar visit_type
        varchar status
        text chief_complaint
        numeric cost
    }
    
    diagnoses {
        int diagnosis_id PK
        int visit_id FK
        varchar icd_code
        varchar description
        varchar severity
    }
```
"""
print(mermaid_erd)
# 이 코드를 Mermaid Live Editor (mermaid.live)에 붙여넣으면 ERD 이미지 생성
```

## 실습 과제

1. 병원 DB의 `COMMENT ON` 목록을 전부 조회하여, 빠진 것이 없는지 확인하세요.
2. `vw_visit_details` 뷰를 사용하여 "2026년 내과 외래 진료 건수"를 조회하세요.
3. 본인 프로젝트 도메인을 떠올리며 ERD 초안(3테이블 이상)을 Mermaid로 작성하세요.

## 강사 노트

- **시간 배분**: 이론(LLM이 스키마를 읽는 방식) 15분 → 5원칙 설명 15분 → 뷰 생성 실습 10분 → ERD 실습 10분
- "왜 COMMENT ON이 중요한가?"를 7H에서 다시 확인시킴 — 여기서 심어둔 복선
- ERD 초안은 프로젝트 제안서의 기초가 됨 → "오늘 대충이라도 그려두면 8H 숙제가 수월"

---

# 5H · LlamaIndex 파이프라인 개론

## 학습목표

- RAG(Retrieval-Augmented Generation)의 개념과 필요성을 설명할 수 있다.
- LlamaIndex의 5단계 파이프라인(Documents → Nodes → Embeddings → Index → Query Engine)을 이해한다.
- `Settings` 객체를 통해 LLM과 임베딩 모델을 설정할 수 있다.
- 다양한 Data Loader를 사용하여 문서를 로드할 수 있다.

## 이론 — RAG란 무엇인가?

### LLM의 한계

LLM은 학습 데이터에 포함된 정보만 알고 있습니다:
- ❌ 회사 내부 데이터를 모름
- ❌ 최신 정보를 모름 (학습 시점 이후)
- ❌ 할루시네이션 (없는 정보를 만들어냄)

### RAG의 해결 방식

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  질문     │ →  │  검색     │ →  │ 컨텍스트  │ →  │  LLM     │
│ "매출은?" │    │ 관련문서   │    │ + 질문    │    │ 답변 생성 │
└──────────┘    │ 상위 K개  │    └──────────┘    └──────────┘
                └──────────┘
                  벡터 DB
```

1. **Retrieval (검색)**: 질문과 관련된 문서를 벡터 DB에서 찾아옴
2. **Augmented (증강)**: 찾은 문서를 LLM 프롬프트에 추가
3. **Generation (생성)**: LLM이 제공된 컨텍스트 기반으로 답변 생성

> RAG = "LLM에게 오픈북 시험을 보게 하는 것"

### LlamaIndex 아키텍처 5단계

```
Documents  →  Nodes(Chunks)  →  Embeddings  →  Index  →  QueryEngine
 (원본 문서)    (청크 분할)      (벡터 변환)    (저장/검색)   (질의 응답)

  📄 PDF       📝 512자씩      🔢 [0.1,      🗄️ 벡터     ❓ "매출은?"
  📄 CSV        분할            0.3, ...]      DB에        💬 "답변..."
  📄 SQL                                       인덱싱
```

## 핵심 코드 — `04_llamaindex_intro.ipynb`

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q \
    llama-index \
    llama-index-llms-openai \
    llama-index-embeddings-openai \
    llama-index-readers-database

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
```

### Settings 객체 — 전역 설정

```python
# ============================================================
# 1. Settings — LLM과 임베딩 모델 설정
# ============================================================
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# 전역 LLM 설정 (모든 쿼리에서 사용)
Settings.llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0,          # 결정적 출력 (일관된 결과)
    max_tokens=1024,
)

# 전역 임베딩 모델 설정 (모든 인덱싱/검색에서 사용)
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # 빠르고 저렴
    # model="text-embedding-3-large",  # 더 정확하지만 비용 ↑
)

print(f"✅ LLM: {Settings.llm.model}")
print(f"✅ Embedding: {Settings.embed_model.model_name}")
```

### Document 로딩

```python
# ============================================================
# 2. Document 로딩 — 다양한 소스에서 문서 가져오기
# ============================================================

# --- 방법 1: 텍스트에서 직접 생성 ---
from llama_index.core import Document

# 병원 관련 문서를 직접 생성 (실습용)
hospital_docs = [
    Document(
        text="""
        서울중앙병원 진료 안내
        
        진료 시간: 평일 09:00-18:00, 토요일 09:00-13:00
        점심 시간: 12:30-13:30
        응급실: 24시간 운영
        
        외래 진료 예약은 전화(02-1234-5678) 또는 온라인으로 가능합니다.
        초진 환자는 신분증을 지참해 주세요.
        """,
        metadata={"source": "hospital_guide", "section": "진료안내", "doc_type": "guide"}
    ),
    Document(
        text="""
        진료과 소개
        
        내과: 심장, 호흡기, 소화기 질환을 전문으로 합니다. 김철수, 이영희, 신민아 전문의가 진료합니다.
        외과: 일반외과, 흉부외과, 혈관외과를 운영합니다. 박민수, 정수진, 권혁준 전문의가 근무합니다.
        소아과: 소아청소년과와 신생아과로 구성되어 있으며, 최동현, 강미래, 문서영 전문의가 있습니다.
        정형외과: 척추, 관절 질환을 전문으로 하며, 윤성호, 한지은 전문의가 진료합니다.
        """,
        metadata={"source": "hospital_guide", "section": "진료과소개", "doc_type": "guide"}
    ),
    Document(
        text="""
        입원 안내
        
        입원 절차:
        1. 담당 의사의 입원 결정
        2. 원무과에서 입원 수속 (보험증, 신분증 필요)
        3. 병동 배정 및 입실
        
        병실 종류:
        - 1인실: 250,000원/일
        - 2인실: 150,000원/일  
        - 4인실: 80,000원/일
        - 다인실: 건강보험 적용
        
        면회 시간: 매일 18:00-20:00
        """,
        metadata={"source": "hospital_guide", "section": "입원안내", "doc_type": "guide"}
    ),
    Document(
        text="""
        자주 묻는 질문 (FAQ)
        
        Q: 진료비 수납은 어떻게 하나요?
        A: 진료 후 1층 수납 창구 또는 무인 수납기를 이용해 주세요. 카드, 현금, 계좌이체 가능합니다.
        
        Q: 진단서 발급은 어떻게 하나요?
        A: 1층 제증명 창구에서 신청하실 수 있습니다. 신분증 지참 필수이며, 발급 소요 시간은 약 30분입니다.
        
        Q: 주차 요금은 얼마인가요?
        A: 외래 환자 3시간 무료, 이후 30분당 1,000원입니다. 입원 환자 보호자는 1일 5,000원입니다.
        """,
        metadata={"source": "hospital_guide", "section": "FAQ", "doc_type": "faq"}
    ),
]

print(f"✅ 로드된 문서 수: {len(hospital_docs)}")
for doc in hospital_docs:
    print(f"  - [{doc.metadata['section']}] {doc.text[:50].strip()}...")
```

### 청킹 (Node 생성)

```python
# ============================================================
# 3. 청킹 — 문서를 작은 단위(Node)로 분할
# ============================================================
from llama_index.core.node_parser import SentenceSplitter

# SentenceSplitter: 문장 경계를 존중하면서 청킹
splitter = SentenceSplitter(
    chunk_size=256,        # 청크 최대 크기 (토큰 기준)
    chunk_overlap=30,      # 청크 간 겹침 (문맥 연결성 유지)
)

nodes = splitter.get_nodes_from_documents(hospital_docs)

print(f"✅ 생성된 노드(청크) 수: {len(nodes)}")
print(f"\n{'='*50}")
for i, node in enumerate(nodes):
    print(f"\n--- 노드 {i+1} ---")
    print(f"  텍스트: {node.text[:100].strip()}...")
    print(f"  메타데이터: {node.metadata}")
    print(f"  길이: {len(node.text)} 자")
```

```python
# 청킹 전략 비교
from llama_index.core.node_parser import TokenTextSplitter

# TokenTextSplitter: 토큰 단위로 정확히 분할
token_splitter = TokenTextSplitter(chunk_size=256, chunk_overlap=30)
token_nodes = token_splitter.get_nodes_from_documents(hospital_docs)

print(f"\n📊 청킹 전략 비교:")
print(f"  SentenceSplitter: {len(nodes)}개 노드")
print(f"  TokenTextSplitter: {len(token_nodes)}개 노드")
```

### 인덱싱 + 질의

```python
# ============================================================
# 4. 인덱싱 + 질의 — VectorStoreIndex
# ============================================================
from llama_index.core import VectorStoreIndex

# 문서를 임베딩 → 인메모리 벡터 인덱스에 저장
index = VectorStoreIndex.from_documents(
    hospital_docs,
    transformations=[splitter],  # 청킹 전략 지정
    show_progress=True,
)

# Query Engine 생성
query_engine = index.as_query_engine(
    similarity_top_k=3,     # 상위 3개 관련 문서 검색
)

# 질의
response = query_engine.query("내과에는 어떤 의사가 있나요?")
print(f"💬 답변: {response.response}")
print(f"\n📚 참조한 소스:")
for node in response.source_nodes:
    print(f"  - [{node.metadata.get('section', '?')}] score={node.score:.3f}")
    print(f"    {node.text[:80].strip()}...")
```

```python
# 추가 질의 예제
questions = [
    "입원 1인실 비용은 얼마인가요?",
    "주차 요금에 대해 알려주세요.",
    "응급실은 언제 이용할 수 있나요?",
]

for q in questions:
    resp = query_engine.query(q)
    print(f"\n❓ {q}")
    print(f"💬 {resp.response}")
    print(f"   (참조 {len(resp.source_nodes)}개, 최고 유사도: {resp.source_nodes[0].score:.3f})")
```

### Retriever로 검색만 수행

```python
# ============================================================
# 5. Retriever — 검색만 수행 (LLM 호출 없이)
# ============================================================
retriever = index.as_retriever(similarity_top_k=3)

nodes_found = retriever.retrieve("외래 진료 시간이 어떻게 되나요?")

print(f"🔍 검색 결과 ({len(nodes_found)}개):")
for i, node in enumerate(nodes_found):
    print(f"\n--- 결과 {i+1} (유사도: {node.score:.4f}) ---")
    print(f"  섹션: {node.metadata.get('section', '?')}")
    print(f"  내용: {node.text[:200].strip()}")
```

## 실습 과제

1. `hospital_docs`에 "비급여 항목 안내" 문서를 하나 추가하고 인덱스를 재구성하세요.
2. `chunk_size`를 128, 256, 512로 바꿔가며 노드 수 변화를 관찰하세요.
3. "정형외과 의사의 전문 분야가 뭔가요?"를 질의하고 참조 소스를 확인하세요.

## 강사 노트

- **시간 배분**: RAG 개념 10분 → LlamaIndex 아키텍처 5분 → Settings 5분 → Document 로딩 5분 → 청킹 5분 → 인덱싱+질의 15분 → 실습 5분
- "RAG = 오픈북 시험"이라는 비유가 학생들에게 잘 와닿음
- 이 시간에는 인메모리 인덱스 사용 → 6H에서 ChromaDB 영속화로 확장
- `show_progress=True` 옵션으로 임베딩 진행 상황을 보여주면 "벡터 변환"이 실제로 일어나는 걸 체감

---

# 6H · 임베딩 + ChromaDB 영속화

## 학습목표

- 텍스트 임베딩의 개념과 코사인 유사도를 이해한다.
- OpenAI와 HuggingFace 임베딩 모델의 차이를 안다.
- ChromaDB를 사용하여 벡터를 영속적으로 저장·검색할 수 있다.
- LlamaIndex와 ChromaDB를 연동할 수 있다.

## 이론 — 임베딩이란?

### 텍스트 → 벡터

임베딩(Embedding)은 텍스트를 **숫자 벡터**로 변환하는 과정입니다.

```
"환자가 두통을 호소합니다" → [0.12, -0.34, 0.56, 0.08, ..., -0.21]  (1536차원)
"머리가 아파요"           → [0.11, -0.32, 0.55, 0.09, ..., -0.20]  (1536차원)
"오늘 날씨가 좋습니다"     → [0.78, 0.45, -0.12, 0.33, ..., 0.67]  (1536차원)
```

- "두통을 호소"와 "머리가 아파요"는 벡터가 **가까움** → 의미적으로 유사
- "오늘 날씨가 좋습니다"는 벡터가 **멀리 떨어져 있음** → 의미적으로 다름

### 코사인 유사도

두 벡터의 유사도를 측정하는 가장 일반적인 방법:

```
cos(A, B) = (A · B) / (||A|| × ||B||)

결과 범위: -1 ~ 1
  1에 가까움 = 매우 유사
  0에 가까움 = 관련 없음
 -1에 가까움 = 반대 의미
```

## 핵심 코드 — `05_embedding_chromadb.ipynb`

### 임베딩 직접 체험

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q \
    llama-index llama-index-embeddings-openai llama-index-llms-openai \
    llama-index-vector-stores-chroma \
    chromadb \
    numpy matplotlib scikit-learn

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
```

```python
# ============================================================
# 1. 임베딩 직접 생성 + 유사도 계산
# ============================================================
from openai import OpenAI
import numpy as np

client = OpenAI()

def get_embedding(text: str) -> list[float]:
    """텍스트를 임베딩 벡터로 변환"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def cosine_similarity(a: list, b: list) -> float:
    """두 벡터의 코사인 유사도"""
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 테스트 문장
sentences = [
    "환자가 심한 두통을 호소합니다",
    "머리가 깨질 듯이 아파요",
    "복부에 통증이 있습니다",
    "오늘 서울 날씨가 맑습니다",
    "내일 비가 올 예정입니다",
]

# 임베딩 생성
embeddings = [get_embedding(s) for s in sentences]

print(f"임베딩 차원: {len(embeddings[0])}")
print(f"\n📊 유사도 행렬:")
print(f"{'':>5}", end="")
for i in range(len(sentences)):
    print(f"  [{i}]", end="")
print()

for i in range(len(sentences)):
    print(f"[{i}]", end="")
    for j in range(len(sentences)):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        print(f"  {sim:.2f}", end="")
    print(f"  ← {sentences[i][:20]}")
```

```python
# ============================================================
# 2. 유사도 히트맵 시각화
# ============================================================
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

# 유사도 행렬 계산
n = len(sentences)
sim_matrix = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        sim_matrix[i][j] = cosine_similarity(embeddings[i], embeddings[j])

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(sim_matrix, cmap='YlOrRd', vmin=0, vmax=1)
plt.colorbar(im)

labels = [s[:15] + "..." for s in sentences]
ax.set_xticks(range(n))
ax.set_yticks(range(n))
ax.set_xticklabels(range(n))
ax.set_yticklabels(labels)

for i in range(n):
    for j in range(n):
        ax.text(j, i, f"{sim_matrix[i][j]:.2f}", ha="center", va="center", fontsize=10)

plt.title("Cosine Similarity Matrix")
plt.tight_layout()
plt.show()
```

### ChromaDB 영속 저장

```python
# ============================================================
# 3. ChromaDB — 벡터 영속 저장소
# ============================================================
import chromadb

# PersistentClient: 데이터가 디스크에 저장됨
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# 컬렉션 생성 (또는 기존 컬렉션 로드)
collection = chroma_client.get_or_create_collection(
    name="hospital_docs",
    metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
)

print(f"✅ ChromaDB 컬렉션 생성: {collection.name}")
print(f"   기존 문서 수: {collection.count()}")
```

```python
# ============================================================
# 4. ChromaDB에 문서 추가
# ============================================================

# 병원 문서들을 ChromaDB에 직접 저장
documents = [
    "서울중앙병원 내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기) 전문의가 있습니다.",
    "외과는 박민수(일반외과), 정수진(흉부외과), 권혁준(혈관외과)이 근무합니다.",
    "진료 시간은 평일 09:00-18:00, 토요일 09:00-13:00입니다.",
    "응급실은 24시간 운영되며, 야간 당직의가 상주합니다.",
    "입원 병실은 1인실(25만원/일), 2인실(15만원/일), 4인실(8만원/일)입니다.",
    "외래 환자 주차는 3시간 무료이며, 이후 30분당 1,000원입니다.",
    "진단서 발급은 1층 제증명 창구에서 가능하며, 소요 시간은 약 30분입니다.",
    "소아과에는 최동현, 강미래, 문서영 전문의가 소아청소년 질환을 진료합니다.",
]

metadatas = [
    {"section": "내과", "doc_type": "department"},
    {"section": "외과", "doc_type": "department"},
    {"section": "진료시간", "doc_type": "guide"},
    {"section": "응급실", "doc_type": "guide"},
    {"section": "입원", "doc_type": "guide"},
    {"section": "주차", "doc_type": "guide"},
    {"section": "제증명", "doc_type": "guide"},
    {"section": "소아과", "doc_type": "department"},
]

# Upsert (있으면 업데이트, 없으면 추가)
collection.upsert(
    ids=[f"doc_{i}" for i in range(len(documents))],
    documents=documents,
    metadatas=metadatas,
)

print(f"✅ {len(documents)}개 문서 저장 완료 (총 {collection.count()}개)")
```

```python
# ============================================================
# 5. ChromaDB 검색
# ============================================================

# 유사도 검색
results = collection.query(
    query_texts=["내과 의사가 누구인가요?"],
    n_results=3,
)

print("🔍 검색: '내과 의사가 누구인가요?'\n")
for i, (doc, meta, dist) in enumerate(zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
)):
    similarity = 1 - dist  # ChromaDB는 distance를 반환 → similarity로 변환
    print(f"  [{i+1}] 유사도={similarity:.3f} | 섹션={meta['section']}")
    print(f"      {doc}")
```

```python
# 메타데이터 필터링 검색
results_filtered = collection.query(
    query_texts=["의사 정보를 알려주세요"],
    n_results=5,
    where={"doc_type": "department"},  # department 타입만 검색
)

print("\n🔍 필터 검색: doc_type='department'\n")
for doc, meta in zip(results_filtered["documents"][0], results_filtered["metadatas"][0]):
    print(f"  [{meta['section']}] {doc}")
```

### LlamaIndex + ChromaDB 연동

```python
# ============================================================
# 6. LlamaIndex + ChromaDB 통합
# ============================================================
from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# ChromaDB 컬렉션을 LlamaIndex 벡터스토어로 래핑
chroma_collection = chroma_client.get_or_create_collection("hospital_llamaindex")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# LlamaIndex 문서 → ChromaDB에 인덱싱
li_docs = [
    Document(text=doc, metadata=meta)
    for doc, meta in zip(documents, metadatas)
]

index = VectorStoreIndex.from_documents(
    li_docs,
    storage_context=storage_context,
    show_progress=True,
)

print(f"✅ LlamaIndex + ChromaDB 인덱싱 완료!")
```

```python
# Query Engine으로 질의
query_engine = index.as_query_engine(similarity_top_k=3)

response = query_engine.query("응급실 이용 가능한 시간은?")
print(f"💬 답변: {response.response}")
print(f"\n📚 참조:")
for node in response.source_nodes:
    print(f"  - score={node.score:.3f}: {node.text[:60]}...")
```

```python
# ============================================================
# 7. 영속성 확인 — 세션 재시작 후에도 데이터 유지
# ============================================================

# 새로운 ChromaDB 클라이언트로 같은 경로에 접속
chroma_client2 = chromadb.PersistentClient(path="./chroma_db")
collection2 = chroma_client2.get_collection("hospital_docs")

print(f"✅ 재접속 후 문서 수: {collection2.count()}")
# → 세션이 끊겨도 ./chroma_db 폴더에 데이터가 남아있음!
```

### 임베딩 모델 비교

```
┌──────────────────────────┬────────────┬──────────┬──────────┐
│ 모델                      │ 차원       │ 비용     │ 특징     │
├──────────────────────────┼────────────┼──────────┼──────────┤
│ text-embedding-3-small   │ 1,536      │ 저렴     │ 빠르고 경제적 │
│ text-embedding-3-large   │ 3,072      │ 보통     │ 더 높은 정확도 │
│ BAAI/bge-small-ko        │ 384        │ 무료(HF) │ 한국어 특화   │
│ sentence-transformers/   │ 768        │ 무료(HF) │ 다국어 지원   │
│   paraphrase-multilingual│            │          │              │
└──────────────────────────┴────────────┴──────────┴──────────┘
```

## 실습 과제

1. "비급여 항목 안내" 문서를 ChromaDB에 추가하고 검색되는지 확인하세요.
2. 같은 질문을 `text-embedding-3-small`과 `text-embedding-3-large`로 검색하여 결과를 비교하세요.
3. ChromaDB의 `where` 필터를 사용하여 특정 `doc_type`만 검색하세요.

## 강사 노트

- **시간 배분**: 임베딩 이론 10분 → 코사인 유사도 시각화 10분 → ChromaDB 기본 15분 → LlamaIndex 연동 10분 → 실습 5분
- 유사도 히트맵이 시각적으로 임팩트가 큼 — "두통"과 "머리 아파요"가 높은 유사도를 보이는 것에 학생들이 놀라는 순간이 학습 포인트
- Colab에서 한국어 폰트가 안 나올 수 있음 → `DejaVu Sans`로 대체하거나 영어 레이블 사용
- ChromaDB `PersistentClient`는 Colab 런타임이 끊기면 사라짐 — Google Drive 마운트로 해결 가능하다고 언급만

---

# 7H · Text-to-SQL 맛보기

## 학습목표

- LlamaIndex의 `SQLDatabase` 래퍼를 사용하여 데이터베이스를 LLM에 연결할 수 있다.
- `NLSQLTableQueryEngine`으로 자연어 질문을 SQL로 변환·실행할 수 있다.
- LLM에 전달되는 `table_info`의 내용을 확인하고 Schema Intelligence의 중요성을 체감한다.

## 이론 — Text-to-SQL 작동 원리

```
자연어 질문                    NLSQLTableQueryEngine
"지난달 방문 환자 수는?"  →  ┌─────────────────────────────┐
                            │ 1. 스키마 수집               │
                            │    (table_info 생성)         │
                            │ 2. 프롬프트 조립              │
                            │    스키마 + 질문 + 규칙       │
                            │ 3. LLM 호출                  │
                            │    → SQL 생성                │
                            │ 4. SQL 실행                   │
                            │ 5. 결과 → 자연어 답변         │
                            └─────────────────────────────┘
                                    ↓
SQL: SELECT COUNT(*) FROM visits WHERE visit_date >= '2026-03-01'
답변: "지난달에는 총 8명의 환자가 방문했습니다."
```

### 핵심: `table_info`란?

LLM에 전달되는 스키마 텍스트입니다. `CREATE TABLE` + `COMMENT` + 샘플 행이 합쳐진 형태로, LLM이 테이블 구조를 이해하는 **유일한 정보원**입니다.

## 핵심 코드 — `06_text_to_sql.ipynb`

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q \
    llama-index llama-index-llms-openai llama-index-embeddings-openai \
    sqlalchemy psycopg2-binary pandas

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine
engine = create_engine(os.environ["NEON_DSN"])
```

```python
# ============================================================
# 1. SQLDatabase 래퍼 생성
# ============================================================
from llama_index.core import SQLDatabase, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 사용할 테이블 지정
sql_db = SQLDatabase(
    engine,
    include_tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)

# 어떤 테이블이 연결되었는지 확인
print(f"✅ 연결된 테이블: {sql_db.get_usable_table_names()}")
```

```python
# ============================================================
# 2. table_info 확인 — LLM에 전달되는 스키마 텍스트
# ============================================================

# 각 테이블의 table_info 확인
for table in sql_db.get_usable_table_names():
    info = sql_db.get_single_table_info(table)
    print(f"\n{'='*60}")
    print(f"📋 {table}")
    print(f"{'='*60}")
    print(info)

# 💡 여기서 COMMENT ON이 어떻게 반영되는지 확인!
# COMMENT ON이 없으면 LLM은 컬럼 이름만 보고 추측해야 합니다.
```

```python
# ============================================================
# 3. NLSQLTableQueryEngine 생성
# ============================================================
from llama_index.core.query_engine import NLSQLTableQueryEngine

nlq = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)

# 간단한 질문
response = nlq.query("현재 등록된 환자 수는 몇 명인가요?")
print(f"💬 답변: {response.response}")
print(f"📝 생성된 SQL: {response.metadata['sql_query']}")
```

```python
# ============================================================
# 4. 다양한 난이도의 질문 테스트
# ============================================================

test_questions = [
    # Easy
    ("🟢 Easy", "남성 환자는 몇 명인가요?"),
    ("🟢 Easy", "내과에 소속된 의사 목록을 보여주세요."),
    ("🟢 Easy", "2026년 1월에 방문한 환자의 이름을 알려주세요."),
    
    # Medium
    ("🟡 Medium", "진료과별 의사 수를 알려주세요."),
    ("🟡 Medium", "완료된 진료 중 진료비가 가장 높은 상위 5건은?"),
    ("🟡 Medium", "2번 이상 방문한 환자의 이름과 방문 횟수를 보여주세요."),
    
    # Hard
    ("🔴 Hard", "각 진료과별로 가장 최근에 진료한 의사의 이름은?"),
    ("🔴 Hard", "월별 방문 추이를 전월 대비 증감과 함께 보여주세요."),
]

results = []
for level, question in test_questions:
    print(f"\n{'='*60}")
    print(f"{level}: {question}")
    try:
        resp = nlq.query(question)
        print(f"💬 답변: {resp.response}")
        print(f"📝 SQL: {resp.metadata['sql_query']}")
        results.append({"level": level, "question": question, "status": "✅", "sql": resp.metadata['sql_query']})
    except Exception as e:
        print(f"❌ 에러: {str(e)[:100]}")
        results.append({"level": level, "question": question, "status": "❌", "sql": str(e)[:100]})
```

```python
# ============================================================
# 5. 결과 요약 — 성공/실패 분석
# ============================================================
import pandas as pd

df = pd.DataFrame(results)
print("\n📊 결과 요약:")
print(df[["level", "question", "status"]].to_string(index=False))
print(f"\n성공: {len(df[df['status']=='✅'])} / {len(df)}")
```

```python
# ============================================================
# 6. Schema Intelligence가 왜 중요한지 실험
# ============================================================

# 실험: COMMENT가 없는 테이블 vs 있는 테이블

# COMMENT 없는 버전의 table_info를 시뮬레이션
print("\n🔬 실험: COMMENT 유무에 따른 table_info 비교\n")

# COMMENT ON이 포함된 table_info
info_with_comment = sql_db.get_single_table_info("visits")
print("✅ COMMENT ON 포함:")
print(info_with_comment[:500])
print("...")

print("\n💡 COMMENT ON이 있으면 LLM은:")
print("   - visit_type이 'outpatient/inpatient/emergency'임을 알 수 있음")
print("   - status가 'scheduled/completed/cancelled/no_show'임을 알 수 있음")
print("   - cost가 진료비(원)임을 명확히 알 수 있음")
print("\n❌ COMMENT ON이 없으면 LLM은:")
print("   - visit_type에 어떤 값이 들어가는지 추측해야 함")
print("   - status에 'active/inactive'를 잘못 추측할 수 있음")
print("   - cost의 단위를 알 수 없음")
```

```python
# ============================================================
# 7. 실패 사례 분석 — Day 2에서 개선할 포인트
# ============================================================

# 모호한 질문 — LLM이 혼란을 겪는 케이스
ambiguous_questions = [
    "최근에 많이 온 사람은?",           # "최근"이 언제?, "많이"가 몇 번?
    "비싼 진료를 받은 환자는?",          # "비싼"의 기준은?
    "젊은 환자가 주로 가는 과는?",       # "젊은"의 기준은?
]

print("🔍 모호한 질문 테스트 (Day 2에서 개선 예정)\n")
for q in ambiguous_questions:
    print(f"❓ {q}")
    try:
        resp = nlq.query(q)
        print(f"   SQL: {resp.metadata['sql_query']}")
        print(f"   → LLM이 자의적으로 해석했을 가능성 높음 ⚠️")
    except Exception as e:
        print(f"   ❌ 실패: {str(e)[:80]}")
    print()

print("📌 다음 시간(Day 2 10H)에 프롬프트 튜닝으로 이 문제를 해결합니다.")
```

## 실습 과제

1. `NLSQLTableQueryEngine`에 본인이 생각한 질문 5개를 테스트하세요.
2. 성공/실패를 기록하고, 실패한 질문의 원인을 분석하세요 (스키마 부족? 모호한 질문?).
3. `sql_db.get_single_table_info("테이블명")`으로 각 테이블의 table_info를 확인하세요.

## 강사 노트

- **시간 배분**: Text-to-SQL 개념 5분 → SQLDatabase 셋업 5분 → table_info 분석 10분 → 질문 테스트 15분 → 실패 사례 분석 10분 → 실습 5분
- **핵심 복선**: 4H의 Schema Intelligence가 여기서 효과를 발휘 → "COMMENT ON 덕분에 LLM이 정확히 이해"
- 실패 사례를 **일부러** 보여주는 것이 중요 — "완벽하지 않다"는 걸 인식시키고, Day 2에서 개선 방법을 배울 동기 부여
- 학생들이 자기 질문으로 테스트하는 시간을 꼭 확보할 것

---

# 8H · 🎯 최종 프로젝트 브리핑

## 학습목표

- 최종 프로젝트의 전체 구조와 4단계 마일스톤을 이해한다.
- 평가 루브릭을 파악하고 과제 #1(제안서) 작성 방법을 안다.
- 본인 프로젝트 도메인을 선정하고 초기 스키마를 구상한다.

## 이론 — 프로젝트 전체 그림

### 최종 목표

> 자신이 선택한 도메인에서, **자연어 질문 → SQL 생성 → 실행 → 검증 → 답변**을 자동으로 수행하는 AI SQL 분석 에이전트를 구축한다.

### 4단계 마일스톤

```
Day 1 (오늘)                Day 2                Day 3                Day 4
┌──────────┐            ┌──────────┐        ┌──────────┐        ┌──────────┐
│ 프로젝트   │            │ 과제 #1   │        │ 과제 #2   │        │ 과제 #3   │
│ 브리핑 수령 │ ────────→ │ 제안서    │ ───→   │ DB 구축   │ ───→   │ 에이전트  │
│            │           │ 제출      │        │ 완료      │        │ v1 제출   │
└──────────┘            └──────────┘        └──────────┘        └──────────┘
                                                                      │
                                                                      ▼
                                                                ┌──────────┐
                                                                │ 최종 발표 │
                                                                │ 5~7분    │
                                                                └──────────┘
```

### 평가 비중

| 항목 | 비중 | 핵심 |
|---|---|---|
| 기능·동작 | 30% | 10개 질문 중 7개 이상 정답 |
| Ragas 평가 | 25% | Faithfulness, Relevancy 등 정량 점수 |
| LangGraph 설계 | 20% | 상태 관리, 분기/루프, 에러 처리 |
| 최종 발표 | 15% | 명확성, 데모, 회고의 깊이 |
| 과제 성실도 | 10% | 3건 기한 내 제출 |

### 도메인 선택 가이드

```
추천 도메인 (3~5 테이블로 구현 가능한 것):

📊 전자상거래    — products, orders, customers, order_items
👥 인사 관리    — employees, departments, salaries, projects  
🏥 병원 (샘플)  — patients, doctors, visits, diagnoses
🎓 학사 관리    — students, courses, enrollments, grades
🏋️ 피트니스    — members, workouts, trainers, plans
🎮 게임 로그    — players, matches, scores, items
🌡️ IoT 센서    — devices, readings, alerts, locations

💡 핵심: 본인이 잘 아는 도메인을 선택하세요!
   도메인 지식 ↑ → 스키마 품질 ↑ → 질문 자연스러움 ↑ → 에이전트 정확도 ↑
```

## 핵심 내용 — 과제 #1 제안서 작성법

### 제안서 구조

`PROJECT_BRIEF.md`의 템플릿 섹션을 참고하여:

1. **도메인 및 활용 사례** — 1~2문장
2. **데이터베이스 스키마** — 3~5 테이블, CREATE TABLE + COMMENT ON + ERD
3. **샘플 질문 10개** — Easy 3~4 / Medium 3~4 / Hard 2~3, 각각 기대 SQL 포함
4. **데이터 샘플** — 주요 테이블별 5~10행

### 좋은 제안서 vs 나쁜 제안서

```
❌ 나쁜 제안서:
  - 테이블 2개 (너무 적음 → 질문 다양성 부족)
  - 컬럼명 약어 (id, nm, dt → LLM 혼란)
  - COMMENT ON 없음
  - 질문이 모두 Easy ("~은 몇 건?" ×10)
  - 기대 SQL 없음

✅ 좋은 제안서:
  - 테이블 4개 + 적절한 FK 관계
  - 명확한 컬럼명 (patient_id, visit_date)
  - 모든 컬럼에 COMMENT ON
  - 난이도 분포: Easy 3 + Medium 4 + Hard 3
  - 각 질문에 기대 SQL과 결과 형태 명시
```

## 실습 과제 — 과제 #1 (Day 2 제출)

`PROJECT_BRIEF.md`의 템플릿을 복사하여 본인의 내용으로 채우세요:

1. 도메인을 정하세요 (5분)
2. 핵심 테이블 3~5개의 이름과 주요 컬럼을 구상하세요 (10분)
3. 질문 10개를 난이도별로 작성하세요 (20분)
4. 나머지는 집에서 완성하여 **내일(Day 2) 9H에 제출**

## 강사 노트

- **시간 배분**: 프로젝트 개요 10분 → 4단계 마일스톤 5분 → 평가 기준 5분 → 도메인 선정 10분 → 제안서 작성 시작 15분 → Q&A 5분
- 도메인 선정에서 막히는 학생에게: "매일 사용하는 서비스를 떠올려보세요. 넷플릭스? 배달앱? 카페?"
- 테이블이 6개 이상이면 "3~5개로 줄이세요" 권유 — 과도한 스키마는 에이전트 정확도를 떨어뜨림
- **반드시 강조**: "내일 아침에 제안서를 제출합니다. 오늘 밤에 완성하세요!"

---

*Day 1 상세 강의자료 — 강의 교안 및 Colab 노트북 분할을 전제로 작성됨*
