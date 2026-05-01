# 📘 Day 3 — Vanna · LangChain · Advanced RAG · LangGraph (13~20H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API

---

## 🔑 용어 사전 (비IT 수강생을 위한)

| 용어 | 쉬운 설명 |
|---|---|
| **파이프라인(Pipeline)** | 여러 단계가 순서대로 연결된 처리 과정. 공장의 "조립 라인"과 같음 |
| **프레임워크(Framework)** | 자주 쓰는 기능이 미리 만들어진 "도구 상자". 처음부터 만들 필요 없이 가져다 쓰면 됨 |
| **하이브리드(Hybrid)** | 두 가지를 섞는 것. 키워드 검색 + 의미 검색을 함께 사용 |
| **노드(Node)** | 그래프에서 하나의 "작업 단위". 네모 칸 하나 |
| **엣지(Edge)** | 노드와 노드를 잇는 "화살표". 작업 순서를 나타냄 |
| **상태 머신(State Machine)** | "현재 상태"에 따라 다음 행동이 달라지는 시스템. 자판기와 비슷 |

---

## 📦 공통 부트스트랩

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
print("✅ 연결 성공!")
```

---

# 13H · Vanna.ai 구조

## 학습목표
- Vanna의 RAG 기반 Text-to-SQL 아키텍처를 이해한다
- LlamaIndex와 Vanna의 차이를 비교한다

## LlamaIndex vs Vanna — "레시피북 vs 학습하는 요리사"

> 💡 **LlamaIndex** = "전체 레시피북을 매번 펼쳐주는 방식". 스키마 전체를 AI에게 보여줌.
> **Vanna** = "학습하는 요리사". 비슷한 요리를 해본 경험을 기억하고, 새 주문에 적용.

| 특성 | LlamaIndex | Vanna |
|---|---|---|
| 방식 | 스키마 전체 주입 | 질문에 관련된 것만 검색·주입 |
| 테이블 30개 이상 | 토큰 초과/정확도 하락 | 관련 테이블만 검색 → 확장 가능 |
| 학습 | few-shot 수동 추가 | DDL/문서/SQL쌍 누적 학습 |
| 정확도 개선 | 프롬프트 튜닝 | 학습 데이터 추가 → 자동 개선 |

### Vanna 내부 RAG 흐름

```
사용자 질문: "지난달 매출 상위 5개 제품은?"
         │
         ▼
┌────────────────────────────┐
│  1. 벡터 검색 (ChromaDB)    │
│     ├── DDL에서 관련 스키마  │ → CREATE TABLE products (...), orders (...)
│     ├── 문서에서 비즈니스 룰  │ → "매출 = orders.total_amount"
│     └── SQL 쌍에서 유사 예시  │ → ("매출 Top 5", "SELECT ... LIMIT 5")
│                              │
│  2. 컨텍스트 조립 → LLM 호출  │
└────────────────────────────┘
         │
         ▼
SQL: SELECT ... ORDER BY revenue DESC LIMIT 5;
```

### 학습 자산 3종

| 종류 | 설명 | 비유 |
|---|---|---|
| **DDL** | 테이블 구조 | 재료 목록 |
| **Documentation** | 비즈니스 규칙/용어 | 조리법 메모 |
| **SQL Pairs** | (질문, 정답SQL) 쌍 | 이전에 만든 요리 사진 |

## 🎯 실습 — Vanna 설치 및 베이스라인

```python
!pip install -q 'vanna[chromadb,openai]'

from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

vn = MyVanna(config={"api_key": os.environ["OPENAI_API_KEY"], "model": "gpt-4o-mini"})

# Neon 연결
dsn = os.environ["NEON_DSN"]
vn.connect_to_postgres(
    host=dsn.split("@")[1].split("/")[0],
    dbname=dsn.split("/")[-1].split("?")[0],
    user=dsn.split("://")[1].split(":")[0],
    password=dsn.split(":")[2].split("@")[0],
    port=5432)
print("✅ Vanna 연결 완료!")

# 학습 없이 질문 (베이스라인 — 정확도가 낮을 수 있음)
sql = vn.generate_sql("환자 수는 몇 명인가요?")
print(f"📝 베이스라인 SQL: {sql}")
```

## 📌 13H 핵심 정리
- **Vanna** = RAG 기반 Text-to-SQL. 학습할수록 정확도 향상
- 학습 자산 3종: DDL(스키마), Documentation(규칙), SQL Pairs(예시)
- 베이스라인(학습 전) 정확도를 먼저 측정 → 14H에서 학습 후 비교

---

# 14H · Vanna 자가학습

## 학습목표
- DDL, Documentation, SQL Pairs를 Vanna에 학습시킨다
- 학습 전후 정확도 변화를 측정한다

## 🎯 실습 — 3종 학습

### DDL 학습 (스키마 구조)

```python
ddl_statements = [
    """CREATE TABLE departments (department_id SERIAL PRIMARY KEY, name VARCHAR(50), floor INT, phone VARCHAR(20));
    -- departments: 병원의 진료과 정보""",
    """CREATE TABLE doctors (doctor_id SERIAL PRIMARY KEY, name VARCHAR(100), department_id INT REFERENCES departments(department_id), specialty VARCHAR(100), hire_date DATE, salary NUMERIC(12,2));
    -- doctors: 의사 정보. department_id로 진료과 참조.""",
    """CREATE TABLE patients (patient_id SERIAL PRIMARY KEY, name VARCHAR(100), birth_date DATE, gender CHAR(1) CHECK (gender IN ('M','F')), phone VARCHAR(20), address VARCHAR(200), blood_type VARCHAR(3));
    -- patients: 환자 기본 정보. gender는 M(남)/F(여).""",
    """CREATE TABLE visits (visit_id SERIAL PRIMARY KEY, patient_id INT REFERENCES patients(patient_id), doctor_id INT REFERENCES doctors(doctor_id), visit_date DATE, visit_type VARCHAR(20), status VARCHAR(20) DEFAULT 'scheduled', chief_complaint TEXT, cost NUMERIC(10,2));
    -- visits: 진료 기록. status가 completed인 것만 유효.""",
    """CREATE TABLE diagnoses (diagnosis_id SERIAL PRIMARY KEY, visit_id INT REFERENCES visits(visit_id), icd_code VARCHAR(10), description VARCHAR(200), severity VARCHAR(10));
    -- diagnoses: 진단 기록. severity: mild/moderate/severe.""",
]
for ddl in ddl_statements:
    vn.train(ddl=ddl)
print(f"✅ DDL {len(ddl_statements)}건 학습!")
```

### Documentation 학습 (비즈니스 규칙)

```python
docs = [
    "visits.status가 'completed'인 것만 실제 완료된 진료입니다.",
    "visit_type: 'outpatient'=외래, 'inpatient'=입원, 'emergency'=응급.",
    "나이 계산: EXTRACT(YEAR FROM AGE(birth_date)).",
    "'지난달' = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month').",
    "patients.gender: 'M'=남성, 'F'=여성.",
    "'재방문 환자' = 같은 patient_id로 2건 이상 completed 기록.",
]
for doc in docs:
    vn.train(documentation=doc)
print(f"✅ Documentation {len(docs)}건 학습!")
```

### SQL Pairs 학습 (질문-정답 쌍)

```python
sql_pairs = [
    {"question": "전체 환자 수는?", "sql": "SELECT COUNT(*) AS total_patients FROM patients;"},
    {"question": "진료과별 의사 수를 보여줘",
     "sql": "SELECT d.name AS department, COUNT(*) AS doctor_count FROM doctors doc JOIN departments d ON d.department_id = doc.department_id GROUP BY d.name ORDER BY doctor_count DESC;"},
    {"question": "지난달 완료 진료 건수는?",
     "sql": "SELECT COUNT(*) FROM visits WHERE status='completed' AND visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND visit_date < DATE_TRUNC('month', CURRENT_DATE);"},
    {"question": "가장 많이 방문한 환자 Top 5는?",
     "sql": "SELECT p.name, COUNT(*) AS visit_count FROM visits v JOIN patients p ON p.patient_id = v.patient_id WHERE v.status='completed' GROUP BY p.patient_id, p.name ORDER BY visit_count DESC LIMIT 5;"},
]
for pair in sql_pairs:
    vn.train(question=pair["question"], sql=pair["sql"])
print(f"✅ SQL Pairs {len(sql_pairs)}건 학습!")
```

### 학습 후 정확도 측정

```python
test_questions = [
    "전체 환자 수는?", "남성 환자 중 40세 이상은?",
    "진료과별 의사 수를 보여줘", "응급 진료 평균 비용은?",
    "가장 많이 방문한 환자 Top 3는?",
]
import pandas as pd
results = []
for q in test_questions:
    try:
        sql = vn.generate_sql(q)
        df = vn.run_sql(sql)
        status = "✅" if df is not None and len(df) > 0 else "⚠️"
    except:
        status = "❌"
    results.append({"question": q, "status": status})
    print(f"{status} {q}")

success = sum(1 for r in results if r["status"] == "✅")
print(f"\n🎯 정답률: {success}/{len(test_questions)} ({success/len(test_questions)*100:.0f}%)")
```

## 📌 14H 핵심 정리
- Vanna에 DDL → Documentation → SQL Pairs 순으로 학습
- 학습할수록 정확도 향상 → **오답→정답 피드백 루프**가 핵심
- 본인 프로젝트 DB에도 동일한 방식으로 적용 가능

---

# 15H · LangChain & LCEL 기초

## 학습목표
- LCEL의 파이프(`|`) 연산자로 체인을 조립할 수 있다
- Pydantic 구조화 출력을 생성할 수 있다

## LCEL이란? — "레고 블록 조립"

> 💡 **LCEL(LangChain Expression Language)** = 레고 블록처럼 AI 기능을 조합하는 문법
> - 블록 1: 프롬프트 (질문 틀)
> - 블록 2: AI 모델 (답변 생성)
> - 블록 3: 파서 (결과 정리)
> - 조립: `프롬프트 | 모델 | 파서` → 완성된 체인!

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ PromptTemplate│ ──→ │   ChatModel   │ ──→ │ OutputParser  │
│ (질문 틀)     │  |  │ (AI 두뇌)    │  |  │ (결과 정리)  │
└──────────────┘     └──────────────┘     └──────────────┘

chain = prompt | model | parser
result = chain.invoke({"variable": "value"})
```

## 🎯 실습 — 기본 체인

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 블록 정의
prompt = ChatPromptTemplate.from_template(
    "당신은 {role} 전문가입니다. 다음 질문에 한국어로 간결히 답변하세요.\n\n질문: {question}")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# 조립! (파이프 연산자로 연결)
chain = prompt | model | parser

# 실행
result = chain.invoke({"role": "데이터베이스", "question": "인덱스는 왜 중요한가요?"})
print(result)
```

### invoke / stream / batch

```python
# invoke: 단건 실행
result = chain.invoke({"role": "SQL", "question": "CTE란?"})

# stream: 글자가 하나씩 나오는 스트리밍
for chunk in chain.stream({"role": "SQL", "question": "윈도우 함수란?"}):
    print(chunk, end="", flush=True)

# batch: 여러 질문 동시 실행
results = chain.batch([
    {"role": "Python", "question": "리스트와 튜플 차이?"},
    {"role": "AI", "question": "RAG란?"},
])
```

### 구조화 출력 (Pydantic)

> 💡 **구조화 출력**: AI 답변을 "정해진 형식"으로 받는 것. JSON처럼 필드별로 깔끔하게.

```python
from pydantic import BaseModel, Field

class SQLAnalysis(BaseModel):
    tables: list[str] = Field(description="사용해야 할 테이블 목록")
    join_needed: bool = Field(description="JOIN이 필요한지")
    difficulty: str = Field(description="난이도: easy, medium, hard")
    sql: str = Field(description="생성된 SQL")

llm_struct = model.with_structured_output(SQLAnalysis)
prompt_s = ChatPromptTemplate.from_template(
    "다음 질문을 분석하여 SQL을 생성하세요.\n\nDB: 병원 (patients, doctors, visits, diagnoses, departments)\n질문: {question}")

chain_s = prompt_s | llm_struct
result = chain_s.invoke({"question": "진료과별 평균 진료비를 보여주세요"})
print(f"테이블: {result.tables}, JOIN: {result.join_needed}, 난이도: {result.difficulty}")
print(f"SQL: {result.sql}")
```

## 📌 15H 핵심 정리
- **LCEL** = `prompt | model | parser` 파이프로 체인 조립
- `invoke`(단건), `stream`(스트리밍), `batch`(동시) 3가지 실행 방법
- **구조화 출력** = AI 답변을 정해진 필드로 받기 (20H 에이전트에서 핵심)

---

# 16H · LCEL RAG 체인

## 학습목표
- LCEL로 RAG 체인을 조립할 수 있다
- 대화 히스토리를 RAG에 통합할 수 있다

## 🎯 실습 — RAG 체인 조립

```python
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 병원 문서 → 벡터 저장소
hospital_documents = [
    Document(page_content="내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기) 전문의가 있습니다."),
    Document(page_content="외과에는 박민수(일반), 정수진(흉부), 권혁준(혈관) 전문의가 있습니다."),
    Document(page_content="진료 시간: 평일 09:00-18:00, 토요일 09:00-13:00. 응급실 24시간."),
    Document(page_content="입원 병실: 1인실 250,000원/일, 2인실 150,000원/일, 4인실 80,000원/일."),
    Document(page_content="외래 환자 주차 3시간 무료, 이후 30분당 1,000원."),
]

vectorstore = Chroma.from_documents(hospital_documents, embeddings, collection_name="hospital_rag")
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_prompt = ChatPromptTemplate.from_template("""컨텍스트를 바탕으로 답변하세요.

## 컨텍스트
{context}

## 질문
{question}

## 답변""")

# RAG 체인 조립
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt | llm | StrOutputParser()
)

print(rag_chain.invoke("내과에 어떤 의사가 있나요?"))
print(rag_chain.invoke("주차 요금이 어떻게 되나요?"))
```

## 📌 16H 핵심 정리
- RAG 체인 = `검색기 | 포맷 + 프롬프트 | LLM | 파서`
- `format_docs`: 검색 결과를 텍스트로 변환하는 브릿지
- `with_fallbacks`로 고가 모델 → 저가 모델 자동 전환 가능

---

# 17H · Advanced RAG — 쿼리 변환

## 학습목표
- HyDE, Multi-Query, Query Decomposition 3가지 기법을 구현한다

## Naive RAG의 한계

```
질문: "재방문율이 높은 진료과는?"
검색: "재방문율이 높은 진료과" → ❌ 관련 문서 못 찾음 (문서에 "재방문율"이란 단어가 없을 수 있음)
```

### 3가지 해결법

| 기법 | 원리 | 비유 |
|---|---|---|
| **HyDE** | 가상 답변을 만들어 그걸로 검색 | "정답이 이런 모양일 것 같으니 비슷한 걸 찾아줘" |
| **Multi-Query** | 같은 질문을 여러 각도로 변형 | "다른 말로 바꿔서 여러 번 검색" |
| **Decomposition** | 복잡한 질문을 작은 질문으로 분해 | "큰 질문을 쪼개서 각각 검색" |

## 🎯 실습 — HyDE

```python
hyde_prompt = ChatPromptTemplate.from_template(
    "다음 질문에 대한 답변이 포함된 문서를 작성하세요.\n질문: {question}\n가상 문서:")
hyde_chain = hyde_prompt | llm | StrOutputParser()

question = "병원에서 가장 바쁜 진료과는?"
hypo_doc = hyde_chain.invoke({"question": question})
print(f"📄 가상 문서:\n{hypo_doc}\n")

# 가상 문서로 검색 (원래 질문 대신)
hyde_results = vectorstore.similarity_search(hypo_doc, k=3)
print("🔍 HyDE 검색 결과:")
for doc in hyde_results:
    print(f"  - {doc.page_content[:60]}...")
```

> 💡 **HyDE의 직관**: "질문보다 답변이 문서와 더 비슷하다"

## 📌 17H 핵심 정리
- **HyDE**: 가상 답변 생성 → 답변으로 검색 (질문보다 답변이 문서와 유사)
- **Multi-Query**: 1개 질문 → 3~5개 변형 → 각각 검색 → 합집합
- **Decomposition**: 복잡한 질문 → 하위 질문 → 각각 검색 → 통합

---

# 18H · Advanced RAG — 검색 고도화

## 학습목표
- BM25 + 벡터 하이브리드 검색을 구현한다
- Re-ranking으로 정밀도를 높인다

## BM25 vs 벡터 검색

> 💡 **BM25 = 키워드 매칭** (정확히 그 단어가 있는 문서를 찾음)
> **벡터 검색 = 의미 검색** (비슷한 뜻의 문서를 찾음)
> **하이브리드 = 둘 다 사용** (장점만 결합!)

```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

bm25_retriever = BM25Retriever.from_documents(hospital_documents)
bm25_retriever.k = 3
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 하이브리드: BM25 40% + 벡터 60%
ensemble = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever], weights=[0.4, 0.6])

results = ensemble.invoke("심장내과 김철수 의사")
for doc in results:
    print(f"  - {doc.page_content[:60]}...")
```

### Re-ranking — "서류 전형 후 면접"

> 💡 **Re-ranking**: 1차 검색(서류 전형)으로 후보를 뽑고, CrossEncoder(면접관)가 정밀하게 재정렬

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-base")

def rerank(query, documents, top_k=3):
    pairs = [(query, doc.page_content) for doc in documents]
    scores = reranker.predict(pairs)
    scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    return scored[:top_k]

candidates = ensemble.invoke("야간에 어떤 진료를 받을 수 있나요?")
reranked = rerank("야간에 어떤 진료를 받을 수 있나요?", candidates)
for doc, score in reranked:
    print(f"  [{score:.4f}] {doc.page_content[:60]}...")
```

## 📌 18H 핵심 정리
- **하이브리드 검색** = BM25(키워드) + 벡터(의미)의 장점 결합
- **Re-ranking** = 1차 검색 후 CrossEncoder로 정밀 재정렬
- 비율(weights)을 조절하여 최적 성능 찾기

---

# 19H · LangGraph 개념

## 학습목표
- LangGraph의 필요성을 이해한다
- StateGraph, Node, Edge, ConditionalEdge를 사용한다

## LCEL의 한계 → LangGraph

```
LCEL 체인: A → B → C → D (한 방향으로만 진행)
  ❌ B에서 실패하면 되돌아갈 수 없음
  ❌ 조건에 따라 다른 경로로 갈 수 없음

LangGraph: A → B → C → D
                ↑      ↓
                └──────┘  ← 실패 시 B로 되돌아가서 재시도!
  ✅ 루프, 조건 분기, 재시도 모두 가능
```

> 💡 **LangGraph = 자판기**: 동전을 넣으면(상태 변경) → 음료를 선택하면(조건 분기) → 음료가 나옴(결과). 중간에 잔돈이 부족하면 다시 동전을 넣으라고 함(재시도).

## 🎯 실습 — 최소 예제

```python
!pip install -q langgraph
from typing import TypedDict
from langgraph.graph import StateGraph, END

# 상태: 모든 노드가 읽고 쓰는 공유 데이터
class SimpleState(TypedDict):
    message: str
    step: int

# 노드: 상태를 변환하는 함수
def greet(state): return {"message": f"안녕하세요! (step={state['step']})", "step": state["step"] + 1}
def process(state): return {"message": state["message"] + " → 처리 완료!", "step": state["step"] + 1}
def finish(state): return {"message": state["message"] + " → 종료.", "step": state["step"] + 1}

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
result = app.invoke({"message": "", "step": 0})
print(f"결과: {result['message']} (총 {result['step']}스텝)")
```

### 조건부 분기 + 재시도

```python
import random

class RetryState(TypedDict):
    task: str; result: str; error: str; attempts: int

def try_task(state):
    attempts = state.get("attempts", 0) + 1
    if random.random() < 0.3 and attempts <= 3:
        return {"error": f"시도 {attempts}에서 에러!", "attempts": attempts}
    return {"result": f"✅ 시도 {attempts}에서 성공!", "error": "", "attempts": attempts}

def handle_success(state):
    return {"result": state["result"] + " → 완료!"}

def should_retry(state):
    if not state.get("error"): return "success"
    if state.get("attempts", 0) >= 3: return "success"
    return "retry"

retry_graph = StateGraph(RetryState)
retry_graph.add_node("try_task", try_task)
retry_graph.add_node("success", handle_success)
retry_graph.set_entry_point("try_task")
retry_graph.add_conditional_edges("try_task", should_retry,
    {"success": "success", "retry": "try_task"})
retry_graph.add_edge("success", END)

retry_app = retry_graph.compile()
for i in range(3):
    r = retry_app.invoke({"task": "테스트", "result": "", "error": "", "attempts": 0})
    print(f"[실행 {i+1}] 시도 {r['attempts']}회: {r['result']}")
```

## 📌 19H 핵심 정리
- **LangGraph** = LCEL의 확장. 루프, 조건 분기, 재시도 지원
- **StateGraph**: 상태(TypedDict) + 노드(함수) + 엣지(연결)
- `add_conditional_edges`로 조건에 따라 다른 노드로 분기

---

# 20H · SQL 에이전트 빌드 (본인 프로젝트)

## 학습목표
- LangGraph로 완전한 SQL 분석 에이전트를 구축한다
- 본인 프로젝트 DB에 연결한다

> 🎯 **이 시간이 과정의 정점입니다!** Day 1~3에서 배운 모든 것이 합쳐집니다.

## 에이전트 아키텍처

```
질문 → [generate_sql] → [run_sql] → [validate] → [answer] → 답변
                ↑                         │
                └────── 에러 시 재시도 ─────┘
```

### 이 코드가 하는 일
> 4개 노드(SQL 생성 → 실행 → 검증 → 답변)로 구성된 SQL 분석 에이전트를 만듭니다.

```python
import os, re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import create_engine, text, inspect
import pandas as pd

engine = create_engine(os.environ["NEON_DSN"])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 스키마 수집
def collect_schema(engine, tables):
    inspector = inspect(engine)
    parts = []
    for table in tables:
        columns = inspector.get_columns(table)
        fks = inspector.get_foreign_keys(table)
        col_lines = [f"  {c['name']} {c['type']}" for c in columns]
        fk_lines = [f"  FK ({','.join(fk['constrained_columns'])}) → {fk['referred_table']}" for fk in fks]
        ddl = f"CREATE TABLE {table} (\n" + ",\n".join(col_lines)
        if fk_lines: ddl += ",\n" + ",\n".join(fk_lines)
        ddl += "\n);"
        parts.append(ddl)
    return "\n\n".join(parts)

TABLES = ["patients", "doctors", "visits", "diagnoses", "departments"]
SCHEMA = collect_schema(engine, TABLES)

# 상태 정의
class SQLAgentState(TypedDict):
    question: str; sql: str; sql_result: str; error: str; answer: str; attempts: int

# 가드레일
BLOCKED = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE)

def sanitize_sql(sql):
    m = BLOCKED.search(sql)
    if m: return "", f"보안 위반: '{m.group()}'"
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    return sql, ""

# 노드 1: SQL 생성
def generate_sql(state):
    err_fb = ""
    if state.get("error"):
        err_fb = f"\n이전 오류: {state['error']}\n실패 SQL: {state.get('sql','')}\n수정하세요."
    prompt = ChatPromptTemplate.from_template(
        "PostgreSQL 전문가. SELECT만. SQL만 반환.\n\n{schema}\n{err}\n\n질문: {q}\nSQL:")
    chain = prompt | llm | StrOutputParser()
    sql = chain.invoke({"schema": SCHEMA, "q": state["question"], "err": err_fb})
    sql = re.sub(r"```sql\s*", "", re.sub(r"```\s*", "", sql)).strip()
    return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

# 노드 2: SQL 실행
def run_sql(state):
    safe_sql, error = sanitize_sql(state["sql"])
    if error: return {"error": error, "sql_result": ""}
    try:
        df = pd.read_sql(safe_sql, engine)
        if df.empty: return {"sql_result": "(결과 없음)", "error": ""}
        return {"sql_result": df.head(50).to_markdown(index=False), "error": ""}
    except Exception as e:
        return {"error": f"SQL 오류: {str(e)}", "sql_result": ""}

# 노드 3: 검증
def validate(state):
    return {"error": ""} if not state.get("error") else state

# 노드 4: 답변 생성
def answer(state):
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    prompt = ChatPromptTemplate.from_template(
        "결과를 한국어로 요약. 숫자 천 단위 구분.\n\n질문: {q}\nSQL: {sql}\n결과:\n{r}\n\n답변:")
    chain = prompt | llm | StrOutputParser()
    return {"answer": chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})}

# 분기 함수
def should_retry(state):
    if not state.get("error"): return "answer"
    if state.get("attempts", 0) >= 3: return "answer"
    return "generate_sql"

# 그래프 조립
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
print("✅ 에이전트 컴파일 완료!")
```

### 10개 질문 테스트

```python
questions = [
    "전체 환자 수는?", "남성 환자 중 40세 이상은?",
    "진료과별 의사 수를 보여줘", "지난달 완료 진료 건수는?",
    "응급 진료 평균 비용은?", "가장 많이 방문한 환자 Top 3는?",
    "중증 진단을 받은 환자 이름은?", "2026년 월별 방문 수 추이는?",
    "내과 의사 중 급여 최고는?", "혈액형별 환자 분포는?",
]

for q in questions:
    result = agent.invoke({"question": q, "attempts": 0})
    status = "✅" if result.get("answer") and "죄송" not in result.get("answer","") else "❌"
    print(f"{status} [{result.get('attempts',0)}회] {q}")
```

## 과제 #3 안내

```
╔═══════════════════════════════════════╗
║      과제 #3 — 에이전트 v1             ║
╠═══════════════════════════════════════╣
║ 제출 기한: Day 4 시작 (21H)           ║
║                                       ║
║ 제출물:                               ║
║ 1. Colab 노트북: <이름>_sql_agent.ipynb║
║ 2. LangGraph SQL 에이전트             ║
║ 3. 10개 질문 실행 결과                 ║
║ 4. LangSmith trace URL (내일 연결)    ║
║                                       ║
║ 합격 기준: 7/10 정답                   ║
╚═══════════════════════════════════════╝
```

## 📌 20H 핵심 정리
- 4개 노드: generate_sql → run_sql → validate → answer
- `conditional_edges`로 에러 시 자동 재시도 (최대 3회)
- 본인 프로젝트 DB로 전환: `collect_schema(engine, 본인_테이블_목록)` 수정

---

## 📌 Day 3 전체 정리

| 시간 | 주제 | 핵심 키워드 |
|---|---|---|
| 13H | Vanna 구조 | RAG 기반 Text-to-SQL, 학습 자산 3종 |
| 14H | Vanna 자가학습 | DDL/Documentation/SQL Pairs 학습, 정확도 비교 |
| 15H | LangChain/LCEL | 파이프 연산자, invoke/stream/batch, 구조화 출력 |
| 16H | LCEL RAG 체인 | Retriever → Prompt → LLM → Parser |
| 17H | 쿼리 변환 | HyDE, Multi-Query, Decomposition |
| 18H | 검색 고도화 | BM25+벡터 하이브리드, Re-ranking |
| 19H | LangGraph | StateGraph, Node, Edge, 조건부 분기 |
| 20H | SQL 에이전트 | 4노드 그래프, 재시도, 10개 질문 테스트 |

> **내일(Day 4)**: LangSmith 모니터링 → Ragas 정량 평가 → 최종 발표!
