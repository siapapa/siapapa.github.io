# Day 3 — Vanna · LangChain · Advanced RAG · LangGraph + 프로젝트 빌드 (13~20H)

> 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> 실행 환경: Google Colab + Neon PostgreSQL + OpenAI API

---

## 공통 부트스트랩

```python
!pip install -q \
    vanna chromadb \
    langchain langchain-openai langchain-community langchain-chroma \
    langgraph \
    llama-index llama-index-llms-openai llama-index-embeddings-openai \
    sqlalchemy psycopg2-binary pandas tabulate \
    rank_bm25 sentence-transformers \
    openai sqlparse pydantic

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])
```

---

# 13H · Vanna.ai 구조

## 학습목표

- Vanna.ai의 RAG 기반 Text-to-SQL 아키텍처를 이해한다.
- LlamaIndex Text-to-SQL과 Vanna의 차이를 비교 분석할 수 있다.
- 학습 자산 3종(DDL / Documentation / SQL Pairs)의 역할을 설명할 수 있다.

## 이론 — Vanna vs LlamaIndex Text-to-SQL

### 두 접근법의 비교

```
LlamaIndex NLSQLTableQueryEngine (프롬프트 중심):
  질문 → [스키마 전체를 프롬프트에 주입] → LLM → SQL

Vanna.ai (RAG/검색 중심):
  질문 → [유사한 DDL/문서/SQL쌍 검색] → [검색 결과를 프롬프트에 주입] → LLM → SQL
```

| 특성 | LlamaIndex | Vanna |
|---|---|---|
| 프롬프트 구성 | 전체 스키마 고정 주입 | 질문에 관련된 것만 검색·주입 |
| 테이블 30개 이상 | 토큰 초과/정확도 하락 | 관련 테이블만 검색하여 확장 가능 |
| 학습 | few-shot 수동 추가 | DDL/문서/SQL쌍을 누적 학습 |
| 정확도 개선 | 프롬프트 튜닝 | 학습 자산 추가 → 자동 개선 |
| 설정 난이도 | 간단 | 약간 복잡 (초기 학습 필요) |

### Vanna 내부 RAG 검색 흐름

```
사용자 질문: "지난달 매출 상위 5개 제품은?"
         │
         ▼
┌─────────────────────────────────┐
│  1. 벡터 검색 (ChromaDB)         │
│     ├── DDL 컬렉션에서 관련 스키마 │ → CREATE TABLE products (...), orders (...)
│     ├── 문서 컬렉션에서 비즈니스 룰  │ → "매출 = orders.total_amount"
│     └── SQL 쌍 컬렉션에서 유사 예시  │ → ("매출 Top 5", "SELECT ... ORDER BY ... LIMIT 5")
│                                   │
│  2. 컨텍스트 조립                  │
│     DDL + 문서 + SQL 예시를 합침    │
│                                   │
│  3. LLM 호출                      │
│     컨텍스트 + 질문 → SQL 생성      │
└─────────────────────────────────┘
         │
         ▼
SQL: SELECT p.name, SUM(o.total_amount) AS revenue
     FROM products p JOIN orders o ...
     ORDER BY revenue DESC LIMIT 5;
```

### 학습 자산 3종

| 종류 | 설명 | 예시 |
|---|---|---|
| **DDL** | 테이블 구조 정보 | `CREATE TABLE patients (patient_id INT, ...)` |
| **Documentation** | 비즈니스 용어·규칙 | "visits.status='completed'만 유효한 진료" |
| **SQL Pairs** | (질문, 정답SQL) 쌍 | ("환자 수?", "SELECT COUNT(*) FROM patients") |

## 핵심 코드 — `10_vanna_intro.ipynb`

```python
# ============================================================
# 1. Vanna 설치 및 초기 설정
# ============================================================
!pip install -q 'vanna[chromadb,openai]'

import vanna
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

vn = MyVanna(config={
    "api_key": os.environ["OPENAI_API_KEY"],
    "model": "gpt-4o-mini",
})

# Neon PostgreSQL 연결
vn.connect_to_postgres(
    host=os.environ["NEON_DSN"].split("@")[1].split("/")[0],
    dbname=os.environ["NEON_DSN"].split("/")[-1].split("?")[0],
    user=os.environ["NEON_DSN"].split("://")[1].split(":")[0],
    password=os.environ["NEON_DSN"].split(":")[2].split("@")[0],
    port=5432,
)

# 또는 DSN 직접 사용 (vanna 0.7+ 지원)
# vn.connect_to_postgres(dsn=os.environ["NEON_DSN"])

print("✅ Vanna + Neon 연결 완료!")
```

```python
# ============================================================
# 2. 학습 없이 바로 질문 (베이스라인)
# ============================================================

# 학습 자산 없이 질문 → 정확도가 낮을 수 있음
baseline_sql = vn.generate_sql("환자 수는 몇 명인가요?")
print(f"📝 베이스라인 SQL: {baseline_sql}")

try:
    result = vn.run_sql(baseline_sql)
    print(f"📊 결과:\n{result}")
except Exception as e:
    print(f"❌ 에러: {e}")
```

```python
# ============================================================
# 3. 현재 학습 자산 확인
# ============================================================
training_data = vn.get_training_data()
print(f"📚 현재 학습 자산 수: {len(training_data) if training_data is not None else 0}")
if training_data is not None and len(training_data) > 0:
    print(training_data.head())
```

## 실습 과제

1. 학습 자산 없이 5개 질문을 테스트하고 정답률을 기록하세요.
2. 어떤 질문이 실패하는지 분류하세요 (스키마 몰라서? 용어 몰라서? 복잡해서?).

## 강사 노트

- **시간 배분**: Vanna vs LlamaIndex 비교 15분 → RAG 흐름 설명 10분 → 설치·연결 10분 → 베이스라인 테스트 10분 → 정리 5분
- Vanna 설치 시 `chromadb` 버전 충돌 가능 → `!pip install -q 'vanna[chromadb,openai]'`로 일괄 설치
- DSN 파싱이 복잡할 수 있음 → 호스트/유저/비밀번호를 분리하는 헬퍼 제공
- 베이스라인 정확도가 낮아야 14H의 학습 효과가 극적으로 대비됨

---

# 14H · Vanna 자가학습 실습

## 학습목표

- DDL, Documentation, SQL Pairs를 Vanna에 학습시킬 수 있다.
- In-Chat Training으로 오답→정답 피드백 루프를 실행할 수 있다.
- 학습 전후 정확도 변화를 측정할 수 있다.

## 핵심 코드 — `11_vanna_training.ipynb`

### DDL 학습

```python
# ============================================================
# 1. DDL 학습 — 스키마 정보를 Vanna에 주입
# ============================================================

# 개별 테이블 DDL 학습
ddl_statements = [
    """
    CREATE TABLE departments (
        department_id   SERIAL PRIMARY KEY,
        name            VARCHAR(50) NOT NULL,
        floor           INT,
        phone           VARCHAR(20)
    );
    -- departments: 병원의 진료과 정보 (내과, 외과, 소아과 등)
    """,
    """
    CREATE TABLE doctors (
        doctor_id       SERIAL PRIMARY KEY,
        name            VARCHAR(100) NOT NULL,
        department_id   INT NOT NULL REFERENCES departments(department_id),
        specialty       VARCHAR(100),
        hire_date       DATE NOT NULL,
        salary          NUMERIC(12,2)
    );
    -- doctors: 의사 정보. department_id로 진료과 참조.
    """,
    """
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
    -- patients: 환자 기본 정보. gender는 M(남)/F(여).
    """,
    """
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
    -- visits: 진료 방문 기록. visit_type은 외래/입원/응급. status가 completed인 것만 유효.
    """,
    """
    CREATE TABLE diagnoses (
        diagnosis_id    SERIAL PRIMARY KEY,
        visit_id        INT NOT NULL REFERENCES visits(visit_id),
        icd_code        VARCHAR(10) NOT NULL,
        description     VARCHAR(200) NOT NULL,
        severity        VARCHAR(10) CHECK (severity IN ('mild','moderate','severe'))
    );
    -- diagnoses: 진단 기록. severity는 mild(경증)/moderate(중등)/severe(중증).
    """,
]

for ddl in ddl_statements:
    vn.train(ddl=ddl)
    table_name = ddl.split("CREATE TABLE")[1].split("(")[0].strip()
    print(f"  ✅ DDL 학습: {table_name}")

print(f"\n✅ DDL {len(ddl_statements)}건 학습 완료!")
```

### Documentation 학습

```python
# ============================================================
# 2. Documentation 학습 — 비즈니스 용어·규칙
# ============================================================

docs = [
    "visits 테이블에서 status가 'completed'인 것만 실제 완료된 진료입니다. 'cancelled'과 'no_show'는 집계에서 제외합니다.",
    "visits.visit_type의 값: 'outpatient'은 외래 진료, 'inpatient'은 입원, 'emergency'는 응급입니다.",
    "visits.cost는 진료비이며 단위는 원(KRW)입니다. NULL이면 아직 청구되지 않은 것입니다.",
    "환자의 나이를 계산하려면 EXTRACT(YEAR FROM AGE(birth_date))를 사용합니다.",
    "patients.gender는 'M'이 남성, 'F'가 여성입니다.",
    "patients.blood_type은 'A', 'B', 'O', 'AB' 중 하나입니다.",
    "diagnoses.severity는 'mild'(경증), 'moderate'(중등), 'severe'(중증)으로 구분합니다.",
    "'재방문 환자'란 같은 patient_id로 visits에 2건 이상의 completed 레코드가 있는 환자입니다.",
    "'지난달'이란 현재 월의 바로 전 달을 의미합니다. DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')으로 계산합니다.",
    "departments 테이블은 병원의 진료과 정보입니다. 의사는 정확히 하나의 진료과에 소속됩니다.",
]

for doc in docs:
    vn.train(documentation=doc)

print(f"✅ Documentation {len(docs)}건 학습 완료!")
```

### SQL Pairs 학습

```python
# ============================================================
# 3. SQL Pairs 학습 — 질문-SQL 정답 쌍
# ============================================================

sql_pairs = [
    {
        "question": "전체 환자 수는 몇 명인가요?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients;"
    },
    {
        "question": "남성 환자 수는?",
        "sql": "SELECT COUNT(*) AS male_patients FROM patients WHERE gender = 'M';"
    },
    {
        "question": "진료과별 의사 수를 보여주세요.",
        "sql": """
            SELECT d.name AS department, COUNT(*) AS doctor_count
            FROM doctors doc
            JOIN departments d ON d.department_id = doc.department_id
            GROUP BY d.name
            ORDER BY doctor_count DESC;
        """
    },
    {
        "question": "지난달 완료된 진료 건수는?",
        "sql": """
            SELECT COUNT(*) AS completed_visits
            FROM visits
            WHERE status = 'completed'
              AND visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
              AND visit_date < DATE_TRUNC('month', CURRENT_DATE);
        """
    },
    {
        "question": "가장 많이 방문한 환자 Top 5는?",
        "sql": """
            SELECT p.name, COUNT(*) AS visit_count
            FROM visits v
            JOIN patients p ON p.patient_id = v.patient_id
            WHERE v.status = 'completed'
            GROUP BY p.patient_id, p.name
            ORDER BY visit_count DESC
            LIMIT 5;
        """
    },
    {
        "question": "진료과별 평균 진료비를 보여줘",
        "sql": """
            SELECT dept.name AS department, ROUND(AVG(v.cost), 0) AS avg_cost
            FROM visits v
            JOIN doctors d ON d.doctor_id = v.doctor_id
            JOIN departments dept ON dept.department_id = d.department_id
            WHERE v.status = 'completed' AND v.cost IS NOT NULL
            GROUP BY dept.name
            ORDER BY avg_cost DESC;
        """
    },
]

for pair in sql_pairs:
    vn.train(question=pair["question"], sql=pair["sql"])

print(f"✅ SQL Pairs {len(sql_pairs)}건 학습 완료!")
```

### 학습 후 정확도 측정

```python
# ============================================================
# 4. 학습 전후 정확도 비교
# ============================================================

test_questions = [
    ("전체 환자 수는?", "단일 숫자"),
    ("남성 환자 중 40세 이상은 몇 명?", "단일 숫자"),
    ("진료과별 의사 수를 보여줘", "진료과-의사수 표"),
    ("지난달 완료 진료 건수는?", "단일 숫자"),
    ("응급 진료 평균 비용은?", "단일 숫자"),
    ("가장 많이 방문한 환자 Top 3는?", "환자명-방문수 표"),
    ("중증 진단을 받은 환자 이름은?", "환자명 목록"),
    ("2026년 월별 방문 수 추이는?", "월-방문수 표"),
    ("내과 의사 중 급여가 가장 높은 사람은?", "의사명+급여"),
    ("혈액형별 환자 분포는?", "혈액형-환자수 표"),
]

results = []
for question, expected_format in test_questions:
    try:
        sql = vn.generate_sql(question)
        df = vn.run_sql(sql)
        status = "✅" if df is not None and len(df) > 0 else "⚠️ 빈 결과"
        results.append({
            "question": question, 
            "status": status, 
            "sql": sql,
            "rows": len(df) if df is not None else 0,
        })
    except Exception as e:
        results.append({
            "question": question, 
            "status": "❌", 
            "sql": str(e)[:80],
            "rows": 0,
        })

import pandas as pd
df_results = pd.DataFrame(results)
print("\n📊 학습 후 정확도:")
print(df_results[["question", "status", "rows"]].to_string(index=False))

success = len(df_results[df_results["status"] == "✅"])
print(f"\n🎯 정답률: {success}/{len(test_questions)} ({success/len(test_questions)*100:.0f}%)")
```

### In-Chat Training (오답 교정)

```python
# ============================================================
# 5. In-Chat Training — 오답을 교정하여 재학습
# ============================================================

# 실패한 질문을 찾아 수동으로 정답 SQL 작성 후 학습
failed = df_results[df_results["status"] != "✅"]

if len(failed) > 0:
    print("❌ 실패한 질문들:")
    for _, row in failed.iterrows():
        print(f"  - {row['question']}")
        print(f"    생성된 SQL: {row['sql'][:100]}")
    
    print("\n🔄 수동 교정 후 재학습:")
    
    # 예: "중증 진단을 받은 환자 이름은?"이 실패했다면
    corrected_pairs = [
        {
            "question": "중증 진단을 받은 환자 이름은?",
            "sql": """
                SELECT DISTINCT p.name
                FROM patients p
                JOIN visits v ON v.patient_id = p.patient_id
                JOIN diagnoses dg ON dg.visit_id = v.visit_id
                WHERE dg.severity = 'severe';
            """
        },
        {
            "question": "2026년 월별 방문 수 추이는?",
            "sql": """
                SELECT TO_CHAR(visit_date, 'YYYY-MM') AS month, COUNT(*) AS visit_count
                FROM visits
                WHERE EXTRACT(YEAR FROM visit_date) = 2026
                  AND status = 'completed'
                GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
                ORDER BY month;
            """
        },
    ]
    
    for pair in corrected_pairs:
        vn.train(question=pair["question"], sql=pair["sql"])
        print(f"  ✅ 재학습: {pair['question']}")
    
    # 재테스트
    print("\n🔄 재학습 후 재테스트:")
    for pair in corrected_pairs:
        sql = vn.generate_sql(pair["question"])
        print(f"  Q: {pair['question']}")
        print(f"  SQL: {sql}")
        try:
            df = vn.run_sql(sql)
            print(f"  → ✅ 성공 ({len(df)}행)")
        except:
            print(f"  → ❌ 여전히 실패")
```

```python
# ============================================================
# 6. 본인 프로젝트 DB에 Vanna 적용 (실습 가이드)
# ============================================================

print("""
🎯 실습: 본인 프로젝트 DB에 Vanna 적용하기

1. 본인 Neon DSN으로 Vanna 연결
   vn.connect_to_postgres(host=..., dbname=..., user=..., password=...)

2. DDL 학습 (본인 스키마의 CREATE TABLE 문 전부)
   vn.train(ddl="CREATE TABLE ...")

3. Documentation 학습 (비즈니스 용어 5개 이상)
   vn.train(documentation="...")

4. SQL Pairs 학습 (Easy 2개 + Medium 2개)
   vn.train(question="...", sql="...")

5. 10개 질문 테스트 → 정답률 측정

6. 실패한 질문 교정 → 재학습 → 재측정

💡 목표: 학습 전 vs 후 정답률 비교. 몇 개가 개선되었나?
""")
```

## 강사 노트

- **시간 배분**: DDL 학습 10분 → Documentation 5분 → SQL Pairs 10분 → 정확도 측정 10분 → In-Chat Training 10분 → 본인 프로젝트 실습 5분
- DDL 학습 시 COMMENT와 FK 관계를 함께 넣으면 효과적
- In-Chat Training의 "오답→정답 피드백 루프"가 핵심 교육 포인트 — 학습할수록 정확도가 올라가는 것을 체감
- **주의**: Vanna ChromaDB는 인메모리일 수 있음 → Colab 런타임 재시작 시 학습 데이터 소실. `vn.get_training_data()` 결과를 CSV로 백업 권장

---

# 15H · LangChain & LCEL 기초

## 학습목표

- LangChain의 핵심 구성요소(PromptTemplate, Model, Parser)를 이해한다.
- LCEL(LangChain Expression Language)의 파이프(`|`) 연산자로 체인을 조립할 수 있다.
- `Runnable` 인터페이스의 `invoke`, `stream`, `batch` 메서드를 사용할 수 있다.
- Pydantic을 활용한 구조화 출력을 생성할 수 있다.

## 이론 — LCEL이란?

### LangChain의 핵심 철학

```
LCEL = LangChain Expression Language
  ↓
"파이프(|) 연산자로 조합 가능한 Runnable 단위"
  ↓
모든 구성요소가 같은 인터페이스(invoke/stream/batch)를 가짐
  ↓
레고 블록처럼 자유롭게 조합
```

### 핵심 구성요소

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ PromptTemplate│ ──→ │   ChatModel   │ ──→ │ OutputParser  │
│              │  |  │              │  |  │              │
│ 변수 삽입    │     │ LLM 호출     │     │ 결과 파싱    │
└──────────────┘     └──────────────┘     └──────────────┘

chain = prompt | model | parser
result = chain.invoke({"variable": "value"})
```

## 핵심 코드 — `12_langchain_lcel.ipynb`

```python
# ============================================================
# 1. 기본 체인 — Prompt | Model | Parser
# ============================================================
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 구성요소 정의
prompt = ChatPromptTemplate.from_template(
    "당신은 {role} 전문가입니다. 다음 질문에 한국어로 간결히 답변하세요.\n\n질문: {question}"
)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# 체인 조립 (파이프 연산자)
chain = prompt | model | parser

# 실행
result = chain.invoke({
    "role": "데이터베이스",
    "question": "인덱스는 왜 중요한가요?"
})
print(result)
```

```python
# ============================================================
# 2. invoke / stream / batch
# ============================================================

# invoke: 단건 실행
result = chain.invoke({"role": "SQL", "question": "CTE란 무엇인가요?"})
print(f"invoke: {result[:100]}...\n")

# stream: 스트리밍 (토큰 단위 출력)
print("stream: ", end="")
for chunk in chain.stream({"role": "SQL", "question": "윈도우 함수를 설명해주세요"}):
    print(chunk, end="", flush=True)
print("\n")

# batch: 여러 입력 동시 실행
results = chain.batch([
    {"role": "Python", "question": "리스트와 튜플의 차이?"},
    {"role": "SQL", "question": "GROUP BY의 용도?"},
    {"role": "AI", "question": "RAG란?"},
])
for i, r in enumerate(results):
    print(f"batch[{i}]: {r[:80]}...")
```

```python
# ============================================================
# 3. 다양한 PromptTemplate
# ============================================================
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# System + Human 메시지 분리
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 {domain} 분야의 전문 분석가입니다. 항상 한국어로 답변하세요."),
    ("human", "{question}"),
])

chain2 = chat_prompt | model | parser
print(chain2.invoke({"domain": "의료", "question": "병원 데이터 분석의 핵심은?"}))
```

```python
# ============================================================
# 4. RunnablePassthrough, RunnableLambda, RunnableParallel
# ============================================================
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel

# RunnablePassthrough: 입력을 그대로 전달
chain_pass = (
    {"question": RunnablePassthrough()}
    | ChatPromptTemplate.from_template("질문: {question}\n한국어로 답변:")
    | model
    | parser
)
print("PassThrough:", chain_pass.invoke("PostgreSQL이란?")[:100])

# RunnableLambda: 커스텀 변환 함수
upper = RunnableLambda(lambda x: x.upper())
result = upper.invoke("hello world")
print(f"\nLambda: {result}")

# RunnableParallel: 병렬 실행
parallel_chain = RunnableParallel(
    summary=ChatPromptTemplate.from_template("'{topic}'을 한 문장으로 요약:") | model | parser,
    keywords=ChatPromptTemplate.from_template("'{topic}'의 핵심 키워드 3개 나열:") | model | parser,
)
result = parallel_chain.invoke({"topic": "벡터 데이터베이스"})
print(f"\n요약: {result['summary']}")
print(f"키워드: {result['keywords']}")
```

### 구조화 출력 (Pydantic)

```python
# ============================================================
# 5. 구조화 출력 — with_structured_output
# ============================================================
from pydantic import BaseModel, Field

class SQLAnalysis(BaseModel):
    """SQL 쿼리 분석 결과"""
    tables: list[str] = Field(description="사용해야 할 테이블 목록")
    join_needed: bool = Field(description="JOIN이 필요한지 여부")
    aggregation: str | None = Field(description="필요한 집계 함수 (COUNT, SUM 등)")
    difficulty: str = Field(description="난이도: easy, medium, hard")
    sql: str = Field(description="생성된 SQL 쿼리")

llm_structured = model.with_structured_output(SQLAnalysis)

prompt_struct = ChatPromptTemplate.from_template(
    """다음 자연어 질문을 분석하여 SQL 쿼리를 생성하세요.

데이터베이스: 병원 (patients, doctors, visits, diagnoses, departments)

질문: {question}"""
)

struct_chain = prompt_struct | llm_structured

result = struct_chain.invoke({"question": "진료과별 평균 진료비를 보여주세요"})
print(f"테이블: {result.tables}")
print(f"JOIN 필요: {result.join_needed}")
print(f"집계 함수: {result.aggregation}")
print(f"난이도: {result.difficulty}")
print(f"SQL: {result.sql}")
```

```python
# ============================================================
# 6. JsonOutputParser (Pydantic 미지원 환경용)
# ============================================================
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser(pydantic_object=SQLAnalysis)

prompt_json = ChatPromptTemplate.from_template(
    """다음 질문을 분석하세요.
{format_instructions}

질문: {question}"""
).partial(format_instructions=json_parser.get_format_instructions())

json_chain = prompt_json | model | json_parser
result = json_chain.invoke({"question": "남성 환자 수는?"})
print(f"JSON 결과: {result}")
```

## 실습 과제

1. `PromptTemplate`을 수정하여 SQL 생성 체인을 만들고, 병원 DB 질문 3개를 테스트하세요.
2. `with_structured_output`으로 테이블 목록 + SQL + 난이도를 동시에 반환하는 체인을 만드세요.
3. `RunnableParallel`로 같은 질문에 대해 "SQL 생성"과 "자연어 답변"을 동시에 실행하세요.

## 강사 노트

- **시간 배분**: LCEL 개념 10분 → 기본 체인 10분 → invoke/stream/batch 5분 → Runnable 변형들 10분 → 구조화 출력 10분 → 실습 5분
- 파이프(`|`) 연산자가 핵심 — Unix 파이프와 비유하면 이해가 빠름
- `with_structured_output`은 20H LangGraph 에이전트에서 핵심적으로 사용됨 → 여기서 확실히 익혀야 함

---

# 16H · LCEL RAG 체인

## 학습목표

- LCEL로 RAG 체인(Retriever → Prompt → LLM → Parser)을 조립할 수 있다.
- 스트리밍, 배치, fallback을 적용할 수 있다.
- 대화 히스토리를 RAG 체인에 통합할 수 있다.

## 핵심 코드 — `13_lcel_rag_chain.ipynb`

```python
# ============================================================
# 1. ChromaDB 벡터스토어 준비
# ============================================================
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 병원 문서를 벡터스토어에 저장
hospital_documents = [
    Document(page_content="내과에는 김철수(심장내과), 이영희(호흡기내과), 신민아(소화기내과) 전문의가 있습니다.", metadata={"dept": "내과"}),
    Document(page_content="외과에는 박민수(일반외과), 정수진(흉부외과), 권혁준(혈관외과)이 근무합니다.", metadata={"dept": "외과"}),
    Document(page_content="진료 시간은 평일 09:00-18:00, 토요일 09:00-13:00입니다. 점심시간 12:30-13:30.", metadata={"type": "schedule"}),
    Document(page_content="응급실은 24시간 운영됩니다. 야간에는 내과, 외과 당직의가 상주합니다.", metadata={"type": "emergency"}),
    Document(page_content="입원 병실 가격: 1인실 250,000원/일, 2인실 150,000원/일, 4인실 80,000원/일.", metadata={"type": "admission"}),
    Document(page_content="소아과에는 최동현, 강미래, 문서영 전문의가 있으며 소아청소년 질환 전반을 진료합니다.", metadata={"dept": "소아과"}),
    Document(page_content="정형외과에는 윤성호(척추외과), 한지은(관절외과) 전문의가 근무합니다.", metadata={"dept": "정형외과"}),
    Document(page_content="외래 환자 주차 3시간 무료, 이후 30분당 1,000원. 입원 환자 보호자 1일 5,000원.", metadata={"type": "parking"}),
]

vectorstore = Chroma.from_documents(
    hospital_documents,
    embeddings,
    collection_name="hospital_rag",
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

```python
# ============================================================
# 2. LCEL RAG 체인 조립
# ============================================================
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def format_docs(docs):
    """검색된 문서를 텍스트로 결합"""
    return "\n\n".join(doc.page_content for doc in docs)

rag_prompt = ChatPromptTemplate.from_template("""다음 컨텍스트를 바탕으로 질문에 한국어로 답변하세요.
컨텍스트에 없는 내용은 "해당 정보가 없습니다"라고 답변하세요.

## 컨텍스트
{context}

## 질문
{question}

## 답변""")

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

# 테스트
print(rag_chain.invoke("내과에 어떤 의사가 있나요?"))
print("\n---\n")
print(rag_chain.invoke("주차 요금이 어떻게 되나요?"))
```

```python
# ============================================================
# 3. 스트리밍 출력
# ============================================================
print("🔄 스트리밍 답변: ", end="")
for chunk in rag_chain.stream("입원 1인실 비용은?"):
    print(chunk, end="", flush=True)
print()
```

```python
# ============================================================
# 4. 에러 Fallback
# ============================================================

# 고가 모델 → 저가 모델 fallback
primary_llm = ChatOpenAI(model="gpt-4o", temperature=0)
fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

rag_chain_robust = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | primary_llm.with_fallbacks([fallback_llm])
    | StrOutputParser()
)

print(rag_chain_robust.invoke("응급실 운영 시간은?"))
```

```python
# ============================================================
# 5. 대화 히스토리 통합 RAG
# ============================================================
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

history_rag_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 병원 안내 도우미입니다. 컨텍스트를 바탕으로 답변하세요.\n\n컨텍스트:\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])

history_rag_chain = (
    {
        "context": (lambda x: x["question"]) | retriever | format_docs,
        "chat_history": lambda x: x["chat_history"],
        "question": lambda x: x["question"],
    }
    | history_rag_prompt
    | llm
    | StrOutputParser()
)

# 멀티턴 대화
chat_history = []

q1 = "내과에 어떤 의사가 있어?"
a1 = history_rag_chain.invoke({"question": q1, "chat_history": chat_history})
print(f"Q: {q1}\nA: {a1}\n")
chat_history.extend([HumanMessage(content=q1), AIMessage(content=a1)])

q2 = "그 중에 심장 전문의는 누구야?"
a2 = history_rag_chain.invoke({"question": q2, "chat_history": chat_history})
print(f"Q: {q2}\nA: {a2}")
```

## 강사 노트

- **시간 배분**: RAG 체인 조립 15분 → 스트리밍/배치 5분 → fallback 5분 → 히스토리 통합 15분 → 실습 10분
- `format_docs` 함수는 단순하지만 핵심적 — 검색 결과를 프롬프트에 삽입하는 브릿지
- RAG 체인의 `{"context": retriever | format_docs, "question": RunnablePassthrough()}` 패턴을 반드시 이해시키기

---

# 17H · Advanced RAG — 쿼리 변환

## 학습목표

- Naive RAG의 한계를 이해하고 쿼리 변환의 필요성을 설명할 수 있다.
- HyDE, Multi-Query, Query Decomposition 3가지 기법을 구현할 수 있다.
- 같은 질문에 대해 세 기법의 검색 결과를 비교 분석할 수 있다.

## 이론 — 왜 쿼리 변환이 필요한가?

```
Naive RAG의 문제:
  질문: "재방문율이 높은 진료과는?"
  
  검색: "재방문율이 높은 진료과" 임베딩 → 벡터 검색
  결과: ❌ 관련 문서를 찾지 못함 (문서에 "재방문율"이라는 단어가 없을 수 있음)

쿼리 변환의 해결:
  HyDE: "재방문율이 높은 진료과" → 가상 답변 생성 → 가상 답변으로 검색
  Multi-Query: 1개 질문 → 3~5개 변형 → 각각 검색 → 합집합
  Decomposition: 1개 복잡 질문 → 여러 하위 질문 → 각각 검색 → 통합
```

## 핵심 코드 — `14_advanced_rag_query.ipynb`

```python
# ============================================================
# 1. HyDE (Hypothetical Document Embeddings)
# ============================================================
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 가상 문서 생성 프롬프트
hyde_prompt = ChatPromptTemplate.from_template(
    """다음 질문에 대한 답변이 포함된 문서를 작성하세요. 
실제 데이터가 없어도 괜찮습니다. 문서 형태로 가상의 답변을 만들어주세요.

질문: {question}

가상 문서:"""
)

# HyDE 체인
hyde_chain = hyde_prompt | llm | StrOutputParser()

# 테스트
question = "병원에서 가장 바쁜 진료과는 어디인가요?"
hypothetical_doc = hyde_chain.invoke({"question": question})
print(f"❓ 질문: {question}")
print(f"📄 가상 문서:\n{hypothetical_doc}\n")

# 가상 문서로 검색 (질문 대신)
hyde_results = vectorstore.similarity_search(hypothetical_doc, k=3)
print("🔍 HyDE 검색 결과:")
for i, doc in enumerate(hyde_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")

# 비교: 원래 질문으로 직접 검색
naive_results = vectorstore.similarity_search(question, k=3)
print("\n🔍 Naive 검색 결과:")
for i, doc in enumerate(naive_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")
```

```python
# ============================================================
# 2. Multi-Query Retriever
# ============================================================
from langchain.retrievers.multi_query import MultiQueryRetriever

# Multi-Query: LLM이 질문을 여러 관점으로 변형
multi_retriever = MultiQueryRetriever.from_llm(
    retriever=retriever,
    llm=llm,
)

# 로깅으로 생성된 질문 확인
import logging
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

question = "입원 비용이 얼마나 드나요?"
multi_results = multi_retriever.invoke(question)

print(f"\n❓ 원래 질문: {question}")
print(f"🔍 Multi-Query 검색 결과 ({len(multi_results)}개):")
for i, doc in enumerate(multi_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")
```

```python
# ============================================================
# 3. Query Decomposition — 복잡한 질문을 하위 질문으로 분해
# ============================================================

decompose_prompt = ChatPromptTemplate.from_template(
    """다음 복잡한 질문을 2-4개의 단순한 하위 질문으로 분해하세요.
각 하위 질문은 한 줄에 하나씩 작성하세요.

복잡한 질문: {question}

하위 질문:"""
)

decompose_chain = decompose_prompt | llm | StrOutputParser()

complex_question = "내과와 외과 중 어느 쪽이 더 많은 의사가 있고, 각 과의 전문 분야는 무엇인가요?"
sub_questions = decompose_chain.invoke({"question": complex_question})
print(f"❓ 복잡한 질문: {complex_question}")
print(f"\n📋 하위 질문:\n{sub_questions}")

# 각 하위 질문으로 검색
sub_q_list = [q.strip().lstrip("0123456789.-) ") for q in sub_questions.split("\n") if q.strip()]
all_results = []
for sq in sub_q_list:
    if sq:
        results = retriever.invoke(sq)
        all_results.extend(results)
        print(f"\n🔍 '{sq[:50]}...' → {len(results)}개 결과")

# 중복 제거
unique_contents = set()
unique_results = []
for doc in all_results:
    if doc.page_content not in unique_contents:
        unique_contents.add(doc.page_content)
        unique_results.append(doc)

print(f"\n📊 통합 결과: {len(unique_results)}개 (중복 제거)")
```

```python
# ============================================================
# 4. 세 기법 비교 실험
# ============================================================

def compare_retrieval(question: str):
    """Naive / HyDE / Multi-Query 세 기법 비교"""
    print(f"\n{'='*60}")
    print(f"❓ 질문: {question}")
    print(f"{'='*60}")
    
    # Naive
    naive = retriever.invoke(question)
    print(f"\n🔵 Naive ({len(naive)}개):")
    for doc in naive:
        print(f"  - {doc.page_content[:60]}...")
    
    # HyDE
    hypo = hyde_chain.invoke({"question": question})
    hyde = vectorstore.similarity_search(hypo, k=3)
    print(f"\n🟢 HyDE ({len(hyde)}개):")
    for doc in hyde:
        print(f"  - {doc.page_content[:60]}...")
    
    # Multi-Query
    multi = multi_retriever.invoke(question)
    print(f"\n🟡 Multi-Query ({len(multi)}개):")
    for doc in multi:
        print(f"  - {doc.page_content[:60]}...")

compare_retrieval("야간에 응급 진료를 받으려면 어떻게 하나요?")
compare_retrieval("가장 경험이 많은 의사는 누구인가요?")
```

## 강사 노트

- **시간 배분**: Naive RAG 한계 5분 → HyDE 15분 → Multi-Query 10분 → Decomposition 10분 → 비교 실험 10분
- HyDE의 직관: "질문보다 답변이 문서와 더 비슷하다" — 이 한 문장이 핵심
- Multi-Query는 가장 실용적 — 프로덕션에서도 자주 사용

---

# 18H · Advanced RAG — 검색 고도화

## 학습목표

- BM25와 벡터 검색의 차이를 이해하고 하이브리드 검색을 구현할 수 있다.
- Re-ranking(CrossEncoder)으로 검색 정밀도를 높일 수 있다.
- Parent-Child 청킹 전략을 이해한다.

## 핵심 코드 — `15_advanced_rag_retrieval.ipynb`

```python
# ============================================================
# 1. BM25 + 벡터 하이브리드 검색
# ============================================================
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# BM25 Retriever (키워드 기반)
bm25_retriever = BM25Retriever.from_documents(hospital_documents)
bm25_retriever.k = 3

# 벡터 Retriever (의미 기반)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 하이브리드: BM25 40% + 벡터 60%
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6],
)

# 비교 테스트
question = "심장내과 김철수 의사"

print(f"❓ {question}\n")

bm25_results = bm25_retriever.invoke(question)
print(f"🔵 BM25 (키워드):")
for doc in bm25_results:
    print(f"  - {doc.page_content[:60]}...")

vector_results = vector_retriever.invoke(question)
print(f"\n🟢 벡터 (의미):")
for doc in vector_results:
    print(f"  - {doc.page_content[:60]}...")

ensemble_results = ensemble_retriever.invoke(question)
print(f"\n🟡 하이브리드:")
for doc in ensemble_results:
    print(f"  - {doc.page_content[:60]}...")
```

```python
# ============================================================
# 2. Re-ranking (CrossEncoder)
# ============================================================
from sentence_transformers import CrossEncoder

# CrossEncoder 로드
reranker = CrossEncoder("BAAI/bge-reranker-base")

def rerank(query: str, documents, top_k: int = 3):
    """CrossEncoder로 검색 결과 재정렬"""
    pairs = [(query, doc.page_content) for doc in documents]
    scores = reranker.predict(pairs)
    
    # 점수 기준 정렬
    scored_docs = list(zip(documents, scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    return scored_docs[:top_k]

# 테스트
question = "야간에 어떤 과에서 진료를 받을 수 있나요?"

# 1단계: 하이브리드 검색 (후보 5개)
candidates = ensemble_retriever.invoke(question)[:5]
print(f"🔍 1단계 — 후보 ({len(candidates)}개):")
for doc in candidates:
    print(f"  - {doc.page_content[:60]}...")

# 2단계: Re-ranking (상위 3개 선정)
reranked = rerank(question, candidates, top_k=3)
print(f"\n🏆 2단계 — Re-rank 후 (상위 3개):")
for doc, score in reranked:
    print(f"  [{score:.4f}] {doc.page_content[:60]}...")
```

```python
# ============================================================
# 3. 하이브리드 + Re-rank RAG 체인
# ============================================================

def hybrid_rerank_retriever(query: str) -> str:
    """하이브리드 검색 + Re-rank → 문서 텍스트"""
    candidates = ensemble_retriever.invoke(query)
    if not candidates:
        return "(검색 결과 없음)"
    
    reranked = rerank(query, candidates, top_k=3)
    return "\n\n".join(doc.page_content for doc, score in reranked)

final_rag_chain = (
    {"context": hybrid_rerank_retriever, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

answer = final_rag_chain.invoke("야간에 심장 문제가 생기면 어떻게 하나요?")
print(f"💬 {answer}")
```

```python
# ============================================================
# 4. 검색 품질 비교 — weight 실험
# ============================================================
question = "정형외과 척추 전문의"

for bm25_w in [0.0, 0.3, 0.5, 0.7, 1.0]:
    vec_w = 1.0 - bm25_w
    ens = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[bm25_w, vec_w],
    )
    results = ens.invoke(question)
    top_doc = results[0].page_content[:50] if results else "(없음)"
    print(f"  BM25={bm25_w:.1f} / Vector={vec_w:.1f} → {top_doc}...")
```

## 강사 노트

- **시간 배분**: BM25 개념 5분 → 하이브리드 구현 15분 → Re-ranking 15분 → weight 실험 10분 → 정리 5분
- "BM25 = 키워드 매칭(정밀), 벡터 = 의미 검색(재현율)" — 이 한 줄로 차이 설명
- CrossEncoder 다운로드에 시간이 걸림 (약 400MB) → 미리 로드해두기

---

# 19H · LangGraph 개념

## 학습목표

- LCEL 체인의 한계(DAG만 가능)를 이해하고 LangGraph의 필요성을 설명할 수 있다.
- `StateGraph`, `Node`, `Edge`, `ConditionalEdge`로 그래프를 구성할 수 있다.
- 루프와 재시도 패턴을 구현할 수 있다.

## 이론 — 왜 그래프인가?

```
LCEL 체인 (DAG — 한 방향):
  A → B → C → D
  ❌ B에서 실패하면? → 되돌아갈 수 없음
  ❌ 조건에 따라 C를 건너뛰려면? → 복잡한 분기 불가

LangGraph (FSM — 상태 머신):
  A → B → C → D
       ↑      ↓
       └──────┘  ← 실패 시 B로 되돌아가서 재시도
  ✅ 루프, 조건부 분기, 재시도 모두 가능
```

### LangGraph 핵심 개념

```
StateGraph      — 상태(State)를 중심으로 동작하는 그래프
State           — TypedDict로 정의. 모든 노드가 읽고 쓰는 공유 데이터.
Node            — 상태를 변환하는 함수. (State → partial State)
Edge            — 노드 간 연결 (무조건 이동)
ConditionalEdge — 조건에 따라 다른 노드로 분기
EntryPoint      — 그래프 시작점
END             — 그래프 종료
```

## 핵심 코드 — `16_langgraph_concept.ipynb`

```python
# ============================================================
# 1. 최소 LangGraph 예제
# ============================================================
!pip install -q langgraph

from typing import TypedDict
from langgraph.graph import StateGraph, END

# 상태 정의
class SimpleState(TypedDict):
    message: str
    step: int

# 노드 함수들
def greet(state: SimpleState) -> dict:
    return {"message": f"안녕하세요! (step={state['step']})", "step": state["step"] + 1}

def process(state: SimpleState) -> dict:
    return {"message": state["message"] + " → 처리 완료!", "step": state["step"] + 1}

def finish(state: SimpleState) -> dict:
    return {"message": state["message"] + " → 종료.", "step": state["step"] + 1}

# 그래프 조립
graph = StateGraph(SimpleState)
graph.add_node("greet", greet)
graph.add_node("process", process)
graph.add_node("finish", finish)

graph.set_entry_point("greet")
graph.add_edge("greet", "process")
graph.add_edge("process", "finish")
graph.add_edge("finish", END)

app = graph.compile()

# 실행
result = app.invoke({"message": "", "step": 0})
print(f"최종 메시지: {result['message']}")
print(f"총 스텝: {result['step']}")
```

```python
# ============================================================
# 2. 그래프 시각화
# ============================================================
from IPython.display import Image, display

try:
    display(Image(app.get_graph().draw_mermaid_png()))
except Exception:
    print(app.get_graph().draw_mermaid())
```

```python
# ============================================================
# 3. 조건부 분기 + 루프
# ============================================================
import random

class RetryState(TypedDict):
    task: str
    result: str
    error: str
    attempts: int

def try_task(state: RetryState) -> dict:
    """작업 시도 (30% 확률로 실패)"""
    state_attempts = state.get("attempts", 0) + 1
    if random.random() < 0.3 and state_attempts <= 3:
        return {
            "error": f"시도 {state_attempts}에서 랜덤 에러 발생!",
            "attempts": state_attempts,
        }
    return {
        "result": f"✅ 시도 {state_attempts}에서 성공!",
        "error": "",
        "attempts": state_attempts,
    }

def handle_success(state: RetryState) -> dict:
    return {"result": state["result"] + " → 완료 처리됨."}

def should_retry(state: RetryState) -> str:
    """재시도 여부 판단"""
    if not state.get("error"):
        return "success"
    if state.get("attempts", 0) >= 3:
        return "success"  # 최대 시도 초과 → 강제 종료
    return "retry"

# 그래프 조립
retry_graph = StateGraph(RetryState)
retry_graph.add_node("try_task", try_task)
retry_graph.add_node("success", handle_success)

retry_graph.set_entry_point("try_task")
retry_graph.add_conditional_edges(
    "try_task",
    should_retry,
    {"success": "success", "retry": "try_task"},  # retry → 다시 try_task로!
)
retry_graph.add_edge("success", END)

retry_app = retry_graph.compile()

# 실행 (여러 번 해보면 재시도 횟수가 다름)
for i in range(3):
    result = retry_app.invoke({"task": "데이터 처리", "result": "", "error": "", "attempts": 0})
    print(f"[실행 {i+1}] 시도 {result['attempts']}회: {result['result']}")
```

```python
# 그래프 시각화
try:
    display(Image(retry_app.get_graph().draw_mermaid_png()))
except:
    print(retry_app.get_graph().draw_mermaid())
```

```python
# ============================================================
# 4. 실행 추적 — 어떤 노드를 거쳤는지 확인
# ============================================================

# stream으로 각 노드의 실행 과정을 추적
print("🔍 실행 추적:")
for event in retry_app.stream({"task": "추적 테스트", "result": "", "error": "", "attempts": 0}):
    for node_name, node_output in event.items():
        print(f"  📍 {node_name}: attempts={node_output.get('attempts', '?')}, "
              f"error='{node_output.get('error', '')[:30]}', "
              f"result='{node_output.get('result', '')[:30]}'")
```

## 강사 노트

- **시간 배분**: LCEL 한계 5분 → LangGraph 개념 10분 → 최소 예제 10분 → 조건부 분기+루프 15분 → 실행 추적 5분 → 정리 5분
- `conditional_edges`의 반환값이 **노드 이름 문자열**이라는 점을 강조
- `stream()` vs `invoke()` — stream이 디버깅에 유용
- 20H에서 실제 SQL 에이전트에 적용할 것이므로, 여기서 패턴만 확실히 이해시키기

---

# 20H · SQL 에이전트 빌드 (본인 프로젝트)

## 학습목표

- LangGraph로 완전한 SQL 분석 에이전트를 구축할 수 있다.
- generate_sql → run_sql → validate → answer 노드 구조를 구현할 수 있다.
- 보안 가드레일을 에이전트에 통합할 수 있다.
- 본인 프로젝트 DB에 에이전트를 연결할 수 있다.

## 핵심 코드 — `17_my_sql_agent.ipynb`

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q langgraph langchain-openai sqlalchemy psycopg2-binary \
    pandas tabulate sqlparse openai

import os, re
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text, inspect
import pandas as pd

engine = create_engine(os.environ["NEON_DSN"])
```

```python
# ============================================================
# 1. 스키마 정보 수집
# ============================================================
def collect_schema(engine, tables: list[str] = None) -> str:
    """DB 스키마를 LLM 프롬프트용 텍스트로 변환"""
    inspector = inspect(engine)
    if tables is None:
        tables = inspector.get_table_names()
    
    parts = []
    for table in tables:
        columns = inspector.get_columns(table)
        fks = inspector.get_foreign_keys(table)
        
        col_lines = []
        for col in columns:
            nullable = "" if col["nullable"] else " NOT NULL"
            col_lines.append(f"    {col['name']} {col['type']}{nullable}")
        
        fk_lines = []
        for fk in fks:
            fk_lines.append(
                f"    FOREIGN KEY ({', '.join(fk['constrained_columns'])}) "
                f"REFERENCES {fk['referred_table']}({', '.join(fk['referred_columns'])})"
            )
        
        ddl = f"CREATE TABLE {table} (\n"
        ddl += ",\n".join(col_lines)
        if fk_lines:
            ddl += ",\n" + ",\n".join(fk_lines)
        ddl += "\n);"
        
        # COMMENT 수집
        with engine.connect() as conn:
            comments = conn.execute(text(f"""
                SELECT column_name, col_description('{table}'::regclass, ordinal_position)
                FROM information_schema.columns
                WHERE table_name = '{table}' ORDER BY ordinal_position
            """)).fetchall()
        
        for col_name, comment in comments:
            if comment:
                ddl += f"\n-- {table}.{col_name}: {comment}"
        
        parts.append(ddl)
    
    return "\n\n".join(parts)

TABLES = ["patients", "doctors", "visits", "diagnoses", "departments"]
SCHEMA = collect_schema(engine, TABLES)
print(SCHEMA[:500] + "...")
```

```python
# ============================================================
# 2. 에이전트 상태 정의
# ============================================================
from typing import TypedDict
from langgraph.graph import StateGraph, END

class SQLAgentState(TypedDict):
    question: str           # 사용자 질문
    sql: str                # 생성된 SQL
    sql_result: str         # SQL 실행 결과
    error: str              # 에러 메시지
    answer: str             # 최종 자연어 답변
    attempts: int           # 재시도 횟수
    history: list           # 대화 히스토리
```

```python
# ============================================================
# 3. 보안 가드레일
# ============================================================
BLOCKED_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

def sanitize_sql(sql: str) -> tuple[str, str]:
    """SQL 검증 + LIMIT 주입. (정제SQL, 에러메시지) 반환"""
    match = BLOCKED_SQL.search(sql)
    if match:
        return "", f"보안 위반: '{match.group()}' 명령 차단"
    
    # LIMIT 주입
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    
    return sql, ""
```

```python
# ============================================================
# 4. 노드 함수 구현
# ============================================================
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- 노드 1: SQL 생성 ---
def generate_sql(state: SQLAgentState) -> dict:
    error_feedback = ""
    if state.get("error"):
        error_feedback = f"""
이전 시도에서 오류가 발생했습니다:
- 오류: {state['error']}
- 실패한 SQL: {state.get('sql', '')}
이 오류를 피해서 SQL을 다시 작성하세요."""

    prompt = ChatPromptTemplate.from_template("""PostgreSQL 전문가로서 SQL을 작성하세요.

## 스키마
{schema}

## 규칙
- SELECT 문만 작성. DML/DDL 금지.
- visits.status = 'completed'만 유효한 진료.
- 나이 = EXTRACT(YEAR FROM AGE(birth_date))
- SQL만 반환 (설명 없이).
{error_feedback}

## 질문
{question}

SQL:""")
    
    chain = prompt | llm | StrOutputParser()
    sql = chain.invoke({
        "schema": SCHEMA,
        "question": state["question"],
        "error_feedback": error_feedback,
    })
    
    # 마크다운 코드 블록 제거
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql).strip()
    
    return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

# --- 노드 2: SQL 실행 ---
def run_sql(state: SQLAgentState) -> dict:
    sql = state["sql"]
    safe_sql, error = sanitize_sql(sql)
    
    if error:
        return {"error": error, "sql_result": ""}
    
    try:
        df = pd.read_sql(safe_sql, engine)
        if df.empty:
            return {"sql_result": "(결과 없음 — 조건을 확인하세요)", "error": ""}
        
        result = df.head(50).to_markdown(index=False)
        if len(df) > 50:
            result += f"\n\n... 외 {len(df) - 50}행"
        return {"sql_result": result, "error": ""}
    except Exception as e:
        return {"error": f"SQL 실행 오류: {str(e)}", "sql_result": ""}

# --- 노드 3: 검증 ---
def validate(state: SQLAgentState) -> dict:
    # 에러가 있으면 그대로 전달 (재시도 분기에서 처리)
    if state.get("error"):
        return state
    # 빈 결과 확인
    if state.get("sql_result") == "(결과 없음 — 조건을 확인하세요)":
        return {"error": "결과가 비어 있습니다. 날짜 조건이나 필터를 확인하세요."}
    return {"error": ""}

# --- 노드 4: 답변 생성 ---
def answer(state: SQLAgentState) -> dict:
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 질문에 답변하지 못했습니다.\n오류: {state['error']}"}
    
    prompt = ChatPromptTemplate.from_template("""SQL 결과를 한국어로 요약하세요.

질문: {question}
SQL: {sql}
결과:
{result}

규칙: 숫자에 천 단위 구분자. 핵심만 간결하게.""")
    
    chain = prompt | llm | StrOutputParser()
    ans = chain.invoke({
        "question": state["question"],
        "sql": state["sql"],
        "result": state["sql_result"][:1500],
    })
    return {"answer": ans}

# --- 분기 함수 ---
def should_retry(state: SQLAgentState) -> str:
    if not state.get("error"):
        return "answer"
    if state.get("attempts", 0) >= 3:
        return "answer"
    return "generate_sql"
```

```python
# ============================================================
# 5. 그래프 조립 + 컴파일
# ============================================================
graph = StateGraph(SQLAgentState)

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

# 시각화
try:
    from IPython.display import Image, display
    display(Image(agent.get_graph().draw_mermaid_png()))
except:
    print(agent.get_graph().draw_mermaid())
```

```python
# ============================================================
# 6. 에이전트 실행 + 추적
# ============================================================
def ask_agent(question: str, verbose: bool = True) -> dict:
    """에이전트에 질문하고 과정을 추적"""
    print(f"\n{'='*60}")
    print(f"❓ {question}")
    print(f"{'='*60}")
    
    if verbose:
        for event in agent.stream({"question": question, "attempts": 0, "history": []}):
            for node_name, output in event.items():
                print(f"\n📍 [{node_name}]")
                if "sql" in output and output["sql"]:
                    print(f"   SQL: {output['sql'][:100]}...")
                if "error" in output and output["error"]:
                    print(f"   ❌ Error: {output['error']}")
                if "answer" in output and output["answer"]:
                    print(f"   💬 Answer: {output['answer']}")
    else:
        result = agent.invoke({"question": question, "attempts": 0, "history": []})
        print(f"\n📝 SQL: {result['sql']}")
        print(f"💬 답변: {result['answer']}")
        return result

# 테스트
ask_agent("현재 등록된 환자 수는 몇 명인가요?")
ask_agent("진료과별 의사 수를 보여주세요.")
ask_agent("지난 3개월간 가장 많이 방문한 환자 Top 5는?")
```

```python
# ============================================================
# 7. 10개 질문 일괄 테스트
# ============================================================

project_questions = [
    "전체 환자 수는?",
    "남성 환자 중 40세 이상은 몇 명?",
    "진료과별 의사 수를 보여줘",
    "지난달 완료 진료 건수는?",
    "응급 진료 평균 비용은?",
    "가장 많이 방문한 환자 Top 3는?",
    "중증 진단을 받은 환자 이름은?",
    "2026년 월별 방문 수 추이는?",
    "내과 의사 중 급여 최고는?",
    "혈액형별 환자 분포는?",
]

test_results = []
for q in project_questions:
    result = agent.invoke({"question": q, "attempts": 0, "history": []})
    status = "✅" if result.get("answer") and "죄송" not in result.get("answer", "") else "❌"
    test_results.append({
        "question": q,
        "status": status,
        "attempts": result.get("attempts", 0),
        "sql": result.get("sql", "")[:80],
    })
    print(f"{status} [{result.get('attempts',0)}회] {q}")

df_test = pd.DataFrame(test_results)
success = len(df_test[df_test["status"] == "✅"])
print(f"\n🎯 정답률: {success}/{len(project_questions)} ({success/len(project_questions)*100:.0f}%)")
```

### 과제 #3 안내

```python
print("""
╔════════════════════════════════════════════╗
║           과제 #3 — 에이전트 v1               ║
╠════════════════════════════════════════════╣
║                                            ║
║  제출 기한: Day 4 시작 (21H)                ║
║                                            ║
║  제출물:                                    ║
║  1. Colab 노트북: <이름>_sql_agent.ipynb    ║
║  2. LangGraph SQL 에이전트 (위 구조 참고)    ║
║  3. 10개 질문 실행 결과                      ║
║  4. LangSmith trace URL (내일 연결)         ║
║                                            ║
║  합격 기준: 7/10 정답                        ║
║                                            ║
║  💡 오늘 밤에 본인 프로젝트 DB로 에이전트를   ║
║     구축하세요. 내일 LangSmith를 연결합니다. ║
║                                            ║
╚════════════════════════════════════════════╝
""")
```

## 강사 노트

- **시간 배분**: 상태 설계 5분 → 노드 구현 20분 → 그래프 조립 5분 → 테스트 10분 → 본인 프로젝트 적용 시작 10분
- 이 시간이 **과정의 정점** — Day 1~3에서 배운 모든 것이 합쳐지는 순간
- 학생들이 본인 프로젝트로 전환할 때 가장 많이 막히는 부분: 스키마 수집 → `collect_schema()` 함수를 그대로 복사하여 본인 DSN으로 교체
- **과제 #3 강조**: "내일(Day 4) 아침까지 에이전트 v1을 완성해야 합니다. LangSmith 연결은 내일 수업에서 합니다."

---

*Day 3 상세 강의자료 — 강의 교안 및 Colab 노트북 분할을 전제로 작성됨*
