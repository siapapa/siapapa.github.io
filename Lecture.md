# AI 기반 SQL 분석 에이전트 구축 — 강의자료 (초안)

> 24시간 · 4일 과정 · 이론 30% / 실습 70%
> 전 실습 Google Colab + Neon(Postgres) + OpenAI API 기반
> 교재: 『현장에서 바로 써먹는 SQL with PostgreSQL』(김임용) · 『LLM과 RAG로 구현하는 AI 애플리케이션』(에디 유) · 『랭체인과 랭그래프로 구현하는 RAG·AI 에이전트 실전 입문』(강병진)

---

## 📦 사전 준비 (강의 시작 전 수강생 안내)

1. **Google 계정** — Colab 사용
2. **Neon 가입** (https://neon.tech) — 무료 Postgres 인스턴스 1개 생성 → Connection String 확보
3. **OpenAI API Key** (또는 학교 제공 키) — Colab Secrets에 `OPENAI_API_KEY`로 저장
4. **GitHub 계정** — 강의 리포 `git clone`용

각 노트북 첫 셀 공통 부트스트랩:

```python
!pip install -q llama-index langchain langgraph langsmith ragas vanna \
              chromadb gradio psycopg2-binary sqlalchemy openai

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
```

---

# 🗓 Day 1 — 개관 · SQL · RAG 파이프라인 + 프로젝트 브리핑

## 1H · OT & Agentic Analytics 전체 데모

### 학습목표
- "에이전틱 분석(Agentic Analytics)"이 기존 BI/Text-to-SQL과 어떻게 다른지 설명할 수 있다.
- 4일간 만들어 갈 최종 산출물의 모습을 이해한다.

### 핵심 개념
**Analytics의 진화 3단계**

| 단계 | 방식 | 사용자 경험 | 한계 |
|---|---|---|---|
| Traditional BI | 분석가가 대시보드·쿼리 수작업 | 정적 | 질문이 미리 정의되어야 함 |
| Text-to-SQL | LLM이 자연어 → SQL 1회 변환 | 단발성 | 복잡한 추론·검증 불가 |
| **Agentic Analytics** | LLM이 상태를 갖고 다단계 계획·검증·재시도 | 대화형·자율 | 신뢰성 관리 필요 |

**에이전트의 4요소**: 상태(State) · 도구(Tools) · 계획(Planning) · 검증(Validation)

### 시연 — `00_demo_agent.ipynb`
강사가 완성본을 시연:
```
질문: "지난 3개월 동안 매출 상위 5개 제품과 전년 대비 성장률을 알려줘"
→ [SQL 생성] → [실행] → [결과 검증] → [자연어 답변 + 차트]
```
LangSmith 트레이스를 열어 내부 동작을 함께 관찰한다.

### 4일 로드맵
```
Day1  SQL + RAG 기초 + 프로젝트 브리핑
Day2  Text-to-SQL + 상담사 에이전트 + 제안서 제출
Day3  Vanna + LangChain + Advanced RAG + LangGraph + 프로젝트 빌드
Day4  LangSmith + Ragas 평가 + 최종 발표
```

---

## 2H · PostgreSQL 기초 (Colab + Neon)

### 학습목표
- Colab에서 Neon Postgres에 접속하고 샘플 DB를 조회할 수 있다.
- `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`을 자유롭게 쓸 수 있다.

### 왜 Neon?
- 설치 불필요 · 무료 티어 · Colab/IDE 어디서나 동일 DSN으로 접속
- 학생마다 개인 인스턴스 = 서로 간섭 없이 DDL 가능

### 실습 — `01_postgres_basics.ipynb`
```python
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])

with engine.connect() as conn:
    rows = conn.execute(text("SELECT version();")).fetchall()
    print(rows)
```

**샘플 DB 임포트** (강의 리포의 `hospital.sql` 실행):
```python
with open("hospital.sql") as f:
    ddl = f.read()
with engine.begin() as conn:
    conn.execute(text(ddl))
```

**기본 조회 연습**
```sql
SELECT patient_id, name, age
FROM patients
WHERE age >= 60
ORDER BY age DESC
LIMIT 10;
```

### 실습 과제 (10분)
교재 1~3장 연습문제 5개를 Neon에서 풀어 결과 스크린샷.

---

## 3H · 집계·조인·CTE·윈도우 함수

### 핵심 문법 요약

```sql
-- GROUP BY + HAVING
SELECT department_id, COUNT(*) AS cnt, AVG(salary) AS avg_sal
FROM employees
GROUP BY department_id
HAVING COUNT(*) >= 5;

-- JOIN
SELECT p.name, v.visit_date, d.name AS doctor
FROM patients  p
JOIN visits    v ON v.patient_id = p.patient_id
JOIN doctors   d ON d.doctor_id  = v.doctor_id;

-- CTE
WITH recent_visits AS (
  SELECT * FROM visits WHERE visit_date > CURRENT_DATE - INTERVAL '30 days'
)
SELECT patient_id, COUNT(*) FROM recent_visits GROUP BY patient_id;

-- Window
SELECT patient_id, visit_date,
       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY visit_date DESC) AS rn
FROM visits;
```

### 실습 과제
"각 의사별로 최근 진료 환자 3명을 뽑아라" — 윈도우 함수 + CTE 조합으로 해결.

---

## 4H · Schema Intelligence — AI가 읽기 좋은 스키마

### 왜 중요한가?
LLM은 스키마를 **프롬프트 텍스트**로 읽는다. 스키마 가독성 = 에이전트 정확도.

### 설계 원칙
1. **명시적 네이밍** — `p_id` ❌ → `patient_id` ✅
2. **COMMENT ON** — 컬럼 의미를 DB 자체에 기록
   ```sql
   COMMENT ON COLUMN visits.status IS
     '진료 상태: scheduled | completed | cancelled | no_show';
   ```
3. **FK 명시** — LLM이 조인 경로를 추론할 수 있도록
4. **ENUM보다 lookup 테이블** — 값 목록을 LLM에 주입하기 쉬움
5. **비정규화 판단** — 조인이 너무 깊으면 LLM 정확도 급락. 리포팅용 뷰(`vw_*`)로 완충.

### 실습
본인 프로젝트용 ERD 초안 작성 (3테이블 이상, `COMMENT` 필수). dbdiagram.io 또는 Mermaid.

```
Table patients {
  patient_id int [pk]
  name varchar
  age int
  gender varchar
}
```

---

## 5H · LlamaIndex 파이프라인 개론

### 아키텍처 5단계
```
Documents → Nodes(chunks) → Embeddings → Index → Query Engine
```

### 실습 — `04_llamaindex_intro.ipynb`
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

docs = SimpleDirectoryReader("./sample_docs").load_data()
index = VectorStoreIndex.from_documents(docs)
qe = index.as_query_engine()
print(qe.query("환자 동의서의 핵심 조항을 요약해줘"))
```

### 청킹 전략
- `SentenceSplitter(chunk_size=512, chunk_overlap=50)` — 일반적 기본
- 메타데이터(`doc_type`, `section`) 부여 → 나중에 필터 검색

---

## 6H · 임베딩 + ChromaDB 영속화

### 임베딩 개념 (10분)
- 텍스트 → 고차원 벡터
- 의미적으로 가까운 텍스트 = 벡터 공간에서 가까움
- 코사인 유사도: `cos(a,b) = (a·b) / (||a|| ||b||)`

### 실습
```python
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

client = chromadb.PersistentClient(path="./chroma_db")
coll   = client.get_or_create_collection("hospital_docs")
vstore = ChromaVectorStore(chroma_collection=coll)
sctx   = StorageContext.from_defaults(vector_store=vstore)

index = VectorStoreIndex.from_documents(docs, storage_context=sctx)
```

세션 종료 후에도 `./chroma_db`가 남아 재사용 가능함을 확인.

---

## 7H · Text-to-SQL 맛보기

### NLSQLTableQueryEngine 최소 예제
```python
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

sql_db = SQLDatabase(engine, include_tables=["patients","visits","doctors"])
nlq = NLSQLTableQueryEngine(sql_database=sql_db, tables=["patients","visits","doctors"])

resp = nlq.query("지난달에 내원한 환자 수는?")
print(resp.response)
print(resp.metadata["sql_query"])
```

### 관찰 포인트
1. LLM에 전달되는 `table_info`가 어떻게 생겼는가? (`sql_db.get_single_table_info("patients")`)
2. `COMMENT ON`이 프롬프트에 반영되는가? → Schema Intelligence가 왜 중요한지 재확인
3. 실패 케이스: 모호한 질문 ("최근에 많이 온 사람") — Day 2에서 개선

---

## 8H · 🎯 최종 프로젝트 브리핑

### 프로젝트 목표
> 자신이 선택한 도메인에서, 자연어 질문을 SQL로 변환·실행·검증하여 답하는 **자율형 AI 분석 에이전트**를 구축한다.

### 4단계 제출물
| 시점 | 제출물 |
|---|---|
| Day 2 시작 | 과제 #1 · 제안서 (도메인/스키마/질문 10개/샘플 SQL) |
| Day 3 시작 | 과제 #2 · Neon에 스키마 + 시드 데이터 50행 이상 |
| Day 4 시작 | 과제 #3 · LangGraph 에이전트 v1 + LangSmith 트레이스 |
| Day 4 종료 | 최종 발표 5~7분 · 데모 + Ragas 평가 리포트 |

### 평가 루브릭
- 동작성 30% / Ragas 정확도 25% / LangGraph 설계 20% / 발표 15% / 과제 성실 10%

### 도메인 예시
매출·물류·HR·IoT 센서·학사·운동 기록·게임 로그 등 — **본인이 잘 아는 데이터가 최고**.

### Day 1 숙제
`PROJECT_BRIEF.md` 양식에 맞춰 제안서 작성 → Day 2 9H에 공유.

---

# 🗓 Day 2 — 제안서 회수 + Text-to-SQL 상담사

## 9H · 제안서 피어리뷰

### 진행 방식
1. 3인 1조, 각자 10분씩 설명 + 피드백
2. 체크리스트
   - 스키마에 FK·COMMENT가 있는가?
   - 질문 10개가 난이도(상/중/하)별로 분포하는가?
   - 기대 SQL이 구체적인가?
3. 강사 5명씩 라운드로 피드백

### 흔한 피드백 패턴 (강사용 cheat sheet)
- "너무 단순" — 집계/조인 없는 조회만 → 윈도우/CTE 필요 질문 추가 요구
- "스키마가 LLM-unfriendly" — 약어 컬럼명, COMMENT 없음
- "범위 과대" — 10개 테이블 → 3~5개로 축소 권유

---

## 10H · NLSQLTableQueryEngine 심화

### 내부 프롬프트 뜯어보기
```python
from llama_index.core.prompts import PromptTemplate
print(nlq.get_prompts())
```
→ `text_to_sql_prompt`가 어떻게 `{schema}` / `{query_str}`을 채우는지 확인.

### 개선 기법
1. **table_info 수동 주입** — COMMENT가 부족한 테이블에 자연어 설명 추가
   ```python
   context = {"visits": "환자의 진료 방문 기록. 하루 여러 건 가능."}
   nlq = NLSQLTableQueryEngine(sql_database=sql_db, context_str_prefix=..., ...)
   ```
2. **few-shot 예제** — `(질문, SQL)` 페어 2~3개를 프롬프트에 포함
3. **table selection** — 테이블이 많으면 `ObjectIndex`로 관련 테이블만 뽑기

### 실습
Day 1에 실패했던 모호 질문 ("최근에 많이 온 사람")을 위의 3가지 기법으로 개선.

---

## 11H · 병원 DB 멀티턴 상담사 설계

### 상태 관리 모델
```python
from dataclasses import dataclass, field
@dataclass
class ChatState:
    history: list = field(default_factory=list)   # (role, text)
    last_sql: str | None = None
    last_result: list | None = None
```

### 컨텍스트 누적 예
```
User: "30대 여성 환자 수는?"
Bot : SELECT COUNT(*) FROM patients WHERE age BETWEEN 30 AND 39 AND gender='F'; → 127명
User: "그 중에 지난달 방문한 사람은?"  ← "그 중" = 이전 조건 참조
```
→ 프롬프트에 `history`를 포함시키고, LLM이 직전 SQL을 참고하도록 유도.

### 가드레일
- **금칙 SQL**: `DELETE`, `DROP`, `UPDATE` 차단 (정규식 + `sqlparse`)
- **범위 제한**: 허용 테이블 화이트리스트
- **행 수 제한**: 자동 `LIMIT 1000` 주입

---

## 12H · Gradio in Colab 데모

### 최소 코드
```python
import gradio as gr

def chat(message, history):
    state.history.append(("user", message))
    resp = nlq.query(build_prompt(state))
    state.history.append(("assistant", resp.response))
    return resp.response

gr.ChatInterface(chat).launch(share=True)
```

### Colab 특이사항
- `share=True` → 72시간 유효 공개 URL
- 수강생끼리 서로 URL 교환하여 QA 세션

### 과제 #2 안내
본인 프로젝트 스키마 + 시드 데이터 50행 이상을 Neon에 적재, DSN 공유(강사만).

---

# 🗓 Day 3 — Vanna · LangChain · Advanced RAG · LangGraph + 프로젝트 빌드

## 13H · Vanna.ai 구조

### 왜 Vanna인가?
LlamaIndex Text-to-SQL은 *프롬프트* 중심, Vanna는 *검색(RAG)* 중심:
```
질문 → 유사 DDL/문서/SQL 페어 검색 → 컨텍스트 조립 → SQL 생성
```
→ 학습시킬수록 정확도가 올라가는 구조.

### 학습 자산 3종
| 종류 | 예시 |
|---|---|
| **DDL** | `CREATE TABLE patients (...)` |
| **Documentation** | "visits.status는 완료/예약/취소/노쇼 4가지" |
| **SQL Pairs** | ("지난달 매출", "SELECT SUM(...) WHERE ...") |

---

## 14H · Vanna 자가학습 실습

```python
import vanna
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

vn = MyVanna(config={"api_key": os.environ["OPENAI_API_KEY"], "model": "gpt-4o-mini"})
vn.connect_to_postgres(...)

# 학습
vn.train(ddl=open("schema.sql").read())
vn.train(documentation="visits 테이블은 환자의 외래 방문 기록이다.")
vn.train(question="지난달 방문 수?", sql="SELECT COUNT(*) FROM visits WHERE visit_date >= ...")

# 질의
vn.ask("이번 달과 지난달 방문 수 비교")
```

### In-Chat Training (오답 → 정답 피드백)
```python
sql = vn.generate_sql("...")
# 사용자가 확인 후 수정한 SQL을
vn.train(question="...", sql=corrected_sql)
```

### 실습
**본인 프로젝트 DB**에 Vanna 적용, 10개 질문 중 몇 개가 정답인지 측정 → 학습 추가 → 재측정.

---

## 15H · LangChain & LCEL 기초

### 왜 LCEL?
파이프(`|`) 연산자로 조합 가능한 `Runnable` 단위. 스트리밍·배치·비동기 자동.

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("질문: {q}\n한국어로 간결히 답변:")
llm    = ChatOpenAI(model="gpt-4o-mini")
chain  = prompt | llm | StrOutputParser()

print(chain.invoke({"q": "RAG가 뭐야?"}))
```

### 구조화 출력
```python
from pydantic import BaseModel
class SQLPlan(BaseModel):
    tables: list[str]
    sql: str

llm_struct = llm.with_structured_output(SQLPlan)
```

---

## 16H · LCEL RAG 체인

```python
retriever = vectorstore.as_retriever(k=4)

rag_chain = (
    {"context": retriever, "q": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

### 실습
- 스트리밍: `for chunk in rag_chain.stream(...)`
- 배치: `rag_chain.batch([...])`
- fallback: `chain.with_fallbacks([backup_chain])`

---

## 17H · Advanced RAG — 쿼리 변환

### HyDE (Hypothetical Document Embeddings)
1. LLM이 질문을 받아 "가상의 정답 문서"를 생성
2. 그 가상 문서를 임베딩해서 검색
3. 질문보다 답변이 실제 문서와 더 가깝다는 가정

### Multi-Query
```python
from langchain.retrievers.multi_query import MultiQueryRetriever
mq = MultiQueryRetriever.from_llm(retriever=retriever, llm=llm)
```
→ 하나의 질문을 LLM이 3~5개로 변형 → 각각 검색 → 합집합.

### 실습
같은 질문을 Naive / HyDE / Multi-Query로 검색 후 Top-K 결과 비교.

---

## 18H · 하이브리드 검색 + Re-rank

### BM25 + Vector Ensemble
```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever

bm25 = BM25Retriever.from_documents(docs); bm25.k = 4
ensemble = EnsembleRetriever(retrievers=[bm25, vector_retriever], weights=[0.4, 0.6])
```

### Re-rank (CrossEncoder)
```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("BAAI/bge-reranker-base")
pairs = [(query, d.page_content) for d in candidates]
scores = reranker.predict(pairs)
```
→ 키워드(BM25)의 정밀성 + 의미검색의 재현율 + Re-rank의 최종 정확도.

---

## 19H · LangGraph 개념

### 왜 그래프인가?
LCEL 체인은 DAG(한 방향) — 루프·재시도가 어렵다. LangGraph는 **상태 기반 FSM**.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class State(TypedDict):
    question: str
    sql: str
    result: list
    error: str | None
    attempts: int

def generate_sql(state): ...
def run_sql(state): ...
def validate(state): ...
def answer(state): ...

g = StateGraph(State)
g.add_node("gen",   generate_sql)
g.add_node("run",   run_sql)
g.add_node("valid", validate)
g.add_node("ans",   answer)

g.set_entry_point("gen")
g.add_edge("gen", "run")
g.add_edge("run", "valid")
g.add_conditional_edges("valid",
    lambda s: "ans" if s["error"] is None else ("gen" if s["attempts"] < 3 else "ans"))
g.add_edge("ans", END)

app = g.compile()
```

### 포인트
- `attempts` 카운터로 무한루프 방지
- `error` 필드가 재생성 분기의 신호

---

## 20H · SQL 에이전트 빌드 (본인 프로젝트)

### 노드 상세
1. **generate_sql** — Vanna 또는 LCEL 체인으로 SQL 생성
2. **run_sql** — `engine.execute`; 예외는 `state["error"]`에 저장
3. **validate** — `EXPLAIN`으로 문법 확인 + 결과 행 수 sanity check
4. **answer** — 결과를 자연어로 요약 (표 / 한 줄 요약 선택)

### 실습 — `17_my_sql_agent.ipynb`
본인 프로젝트의 10개 질문 중 최소 7개 정답 목표.

### 과제 #3 안내
에이전트 v1 + LangSmith 트레이스 URL 제출.

---

# 🗓 Day 4 — 평가·모니터링 + 최종 발표

## 21H · LangSmith 트레이싱

### 셋업
```python
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"]    = userdata.get("LANGSMITH_KEY")
os.environ["LANGCHAIN_PROJECT"]    = "sql-agent-<이름>"
```

### 볼 수 있는 것
- 각 노드의 입출력 · 토큰 · 지연 · 비용
- 실패한 run에 바로 annotation 달기
- Dataset으로 묶어 재실행 가능

### 실습
본인 에이전트의 10개 질문을 실행 → LangSmith UI에서 트레이스 관찰 → Dataset 생성.

---

## 22H · Ragas 정량 평가

### 4대 메트릭
| 메트릭 | 의미 |
|---|---|
| **Faithfulness** | 답변이 검색 컨텍스트에 근거했는가 |
| **Answer Relevancy** | 답변이 질문에 부합하는가 |
| **Context Precision** | 검색 결과 중 정답에 기여한 비율 |
| **Context Recall** | 정답 근거를 얼마나 빠뜨리지 않았는가 |

### 코드
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

ds = Dataset.from_dict({
    "question":     questions,
    "answer":       answers,
    "contexts":     contexts_list,
    "ground_truth": gts,
})
report = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])
print(report)
```

### 튜닝 루프
1. 낮은 점수 케이스 식별 → 원인 진단(검색 실패 / 프롬프트 / 스키마)
2. 개선 → 재평가 → 점수 변화 기록
3. 발표 슬라이드의 "Before/After" 장표로 사용

---

## 23H · 최종 튜닝 & 리허설

### 발표 슬라이드 3장 템플릿
1. **문제 정의** — 도메인, 에이전트가 답할 질문 유형, 사용자
2. **아키텍처** — LangGraph 다이어그램 + 데이터 흐름
3. **결과 & 회고** — Ragas 점수, 대표 성공/실패 사례, 다음 단계

### 강사 1:1
수강생당 5분 — 발표 흐름 리허설 + 라이브 데모 리스크 체크.

---

## 24H · 최종 발표 & 수료

### 진행
- 1인 5~7분 발표 + 2분 Q&A
- 라이브 데모 필수 (실패해도 감점 없음 — 디버깅 설명이 더 중요)
- 전원 발표 후 상호 투표로 **Best Agent / Best Insight / Best Presentation** 선정

### 수료 요건
- 4일 전 출석 + 과제 3건 제출 + 최종 발표

---

# 📎 부록

## A. 강의 리포 구조 (예정)
```
lecture/
  notebooks/
    00_demo_agent.ipynb
    01_postgres_basics.ipynb
    ...
    19_ragas_eval.ipynb
  data/
    hospital.sql
    ecommerce.sql
    sample_docs/
  project/
    PROJECT_BRIEF.md
    rubric.md
```

## B. 자주 발생하는 이슈
- **Neon 연결 타임아웃** — Colab 세션 재시작 후 DSN 재주입
- **OpenAI 토큰 초과** — `gpt-4o-mini`로 전환
- **Ragas 평가 느림** — 질문 10개 → 3~5개로 축소 후 튜닝

## C. 읽을거리
- LlamaIndex Docs — Text-to-SQL 가이드
- LangGraph Tutorial — SQL Agent 예제
- Ragas 논문 — "Automated Evaluation of RAG"
- Vanna 블로그 — "How accurate is Vanna?"

---

*초안 v0.1 — 각 절은 슬라이드화 + Colab 노트북 분할을 전제로 작성됨.*
