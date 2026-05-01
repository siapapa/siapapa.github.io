# Day 4 — 평가·모니터링 + 최종 발표 (21~24H)

> 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> 실행 환경: Google Colab + Neon PostgreSQL + OpenAI API

---

## 공통 부트스트랩

```python
!pip install -q \
    langgraph langchain langchain-openai langsmith \
    ragas datasets \
    sqlalchemy psycopg2-binary pandas tabulate matplotlib \
    openai sqlparse

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"]       = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]             = userdata.get("NEON_DSN")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"]    = userdata.get("LANGSMITH_KEY")
os.environ["LANGCHAIN_PROJECT"]    = "sql-agent-final"

from sqlalchemy import create_engine, text
import pandas as pd
engine = create_engine(os.environ["NEON_DSN"])
```

---

# 21H · LangSmith 트레이싱

## 학습목표

- LangSmith의 역할(LLM 애플리케이션 관측 가능성)을 설명할 수 있다.
- Run/Trace 구조를 이해하고, 에이전트 실행을 트레이싱할 수 있다.
- 토큰 사용량·지연·비용을 분석할 수 있다.
- 평가용 Dataset을 프로그래밍 방식으로 생성할 수 있다.

## 이론 — 왜 모니터링이 필요한가?

### LLM 애플리케이션의 특수성

전통 소프트웨어와 달리, LLM 애플리케이션은:

```
전통 소프트웨어                    LLM 애플리케이션
──────────────────                ──────────────────
입력 → 결정적 출력                 입력 → 비결정적 출력
버그 = 재현 가능                   오류 = 재현 어려움
로그로 디버깅                      프롬프트·컨텍스트·모델 모두 확인 필요
단위 테스트 가능                   정량 평가 프레임워크 필요
```

→ **관측 가능성(Observability)**이 핵심. LangSmith는 이를 위한 도구.

### Run/Trace 구조

```
Trace (전체 에이전트 실행)
├── Run: generate_sql (LLM 호출)
│   ├── input: {question: "환자 수는?", schema: "..."}
│   ├── output: "SELECT COUNT(*) FROM patients"
│   ├── tokens: 450 (in) + 12 (out)
│   ├── latency: 1.2s
│   └── cost: $0.0003
├── Run: run_sql (도구 실행)
│   ├── input: "SELECT COUNT(*) FROM patients"
│   ├── output: "30"
│   └── latency: 0.3s
├── Run: validate (함수 실행)
│   └── output: {error: ""}
└── Run: answer (LLM 호출)
    ├── input: {result: "30", question: "..."}
    ├── output: "현재 등록된 환자는 30명입니다."
    ├── tokens: 280 (in) + 25 (out)
    └── cost: $0.0002
```

### LangSmith UI에서 볼 수 있는 것

| 화면 | 정보 |
|---|---|
| **Trace 목록** | 전체 실행 목록, 성공/실패 필터, 시간순 정렬 |
| **Trace 상세** | 각 노드의 입출력, 토큰, 지연, 비용 |
| **Run Tree** | 부모-자식 관계로 실행 흐름 시각화 |
| **Feedback** | 성공/실패 태깅, 점수 부여 |
| **Datasets** | 평가용 입력-기대출력 쌍 관리 |
| **Analytics** | 전체 통계 — 총 토큰, 평균 지연, 비용 추이 |

## 핵심 코드 — `18_langsmith_tracing.ipynb`

### LangSmith 설정

```python
# ============================================================
# 1. LangSmith 환경변수 설정
# ============================================================

# 이미 부트스트랩에서 설정됨. 확인:
print(f"✅ LANGCHAIN_TRACING_V2: {os.environ.get('LANGCHAIN_TRACING_V2')}")
print(f"✅ LANGCHAIN_PROJECT:    {os.environ.get('LANGCHAIN_PROJECT')}")
print(f"✅ LANGCHAIN_API_KEY:    {'설정됨' if os.environ.get('LANGCHAIN_API_KEY') else '❌ 미설정'}")

# LangSmith 클라이언트
from langsmith import Client
ls_client = Client()

# 프로젝트 확인
print(f"\n📁 현재 프로젝트: {os.environ['LANGCHAIN_PROJECT']}")
```

### Day 3 에이전트 재구성 + 트레이싱

```python
# ============================================================
# 2. Day 3 에이전트를 트레이싱과 함께 재구성
# ============================================================
import re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import inspect

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 스키마 수집
def collect_schema(engine, tables):
    inspector = inspect(engine)
    parts = []
    for table in tables:
        columns = inspector.get_columns(table)
        fks = inspector.get_foreign_keys(table)
        col_lines = [f"    {c['name']} {c['type']}{'' if c['nullable'] else ' NOT NULL'}" for c in columns]
        fk_lines = [f"    FK ({', '.join(fk['constrained_columns'])}) → {fk['referred_table']}" for fk in fks]
        ddl = f"CREATE TABLE {table} (\n" + ",\n".join(col_lines)
        if fk_lines:
            ddl += ",\n" + ",\n".join(fk_lines)
        ddl += "\n);"
        # COMMENT 수집
        with engine.connect() as conn:
            comments = conn.execute(text(f"""
                SELECT column_name, col_description('{table}'::regclass, ordinal_position)
                FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position
            """)).fetchall()
        for col_name, comment in comments:
            if comment:
                ddl += f"\n-- {table}.{col_name}: {comment}"
        parts.append(ddl)
    return "\n\n".join(parts)

TABLES = ["patients", "doctors", "visits", "diagnoses", "departments"]
SCHEMA = collect_schema(engine, TABLES)

# 상태 정의
class AgentState(TypedDict):
    question: str
    sql: str
    sql_result: str
    error: str
    answer: str
    attempts: int

# 가드레일
BLOCKED = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE)

def sanitize_sql(sql):
    m = BLOCKED.search(sql)
    if m:
        return "", f"보안 위반: '{m.group()}'"
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    return sql, ""

# 노드 함수들
def generate_sql(state: AgentState) -> dict:
    err_fb = ""
    if state.get("error"):
        err_fb = f"\n이전 오류: {state['error']}\n실패 SQL: {state.get('sql','')}\n수정하세요."
    prompt = ChatPromptTemplate.from_template(
        "PostgreSQL 전문가. SELECT만. SQL만 반환.\n\n{schema}\n{err}\n\n질문: {q}\nSQL:"
    )
    chain = prompt | llm | StrOutputParser()
    sql = chain.invoke({"schema": SCHEMA, "q": state["question"], "err": err_fb})
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql).strip()
    return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

def run_sql(state: AgentState) -> dict:
    safe_sql, error = sanitize_sql(state["sql"])
    if error:
        return {"error": error, "sql_result": ""}
    try:
        df = pd.read_sql(safe_sql, engine)
        if df.empty:
            return {"sql_result": "(결과 없음)", "error": ""}
        return {"sql_result": df.head(50).to_markdown(index=False), "error": ""}
    except Exception as e:
        return {"error": f"SQL 오류: {str(e)}", "sql_result": ""}

def validate(state: AgentState) -> dict:
    if state.get("error"):
        return state
    return {"error": ""}

def answer(state: AgentState) -> dict:
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    prompt = ChatPromptTemplate.from_template(
        "결과를 한국어로 요약. 숫자 천 단위 구분.\n\n질문: {q}\nSQL: {sql}\n결과:\n{r}\n\n답변:"
    )
    chain = prompt | llm | StrOutputParser()
    ans = chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})
    return {"answer": ans}

def should_retry(state: AgentState) -> str:
    if not state.get("error"):
        return "answer"
    if state.get("attempts", 0) >= 3:
        return "answer"
    return "generate_sql"

# 그래프 조립
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
print("✅ 에이전트 컴파일 완료 — LangSmith 트레이싱 활성화됨!")
```

### 10개 질문 실행 + 트레이스 확인

```python
# ============================================================
# 3. 10개 질문 실행 — 모든 실행이 LangSmith에 기록됨
# ============================================================

questions = [
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

results = []
for i, q in enumerate(questions):
    print(f"\n[{i+1}/10] {q}")
    result = agent.invoke({"question": q, "attempts": 0})
    status = "✅" if result.get("answer") and "죄송" not in result.get("answer", "") else "❌"
    results.append({
        "question": q,
        "status": status,
        "attempts": result.get("attempts", 0),
        "sql": result.get("sql", ""),
        "answer": result.get("answer", ""),
        "sql_result": result.get("sql_result", ""),
    })
    print(f"  {status} (시도 {result.get('attempts',0)}회) — {result.get('answer','')[:60]}...")

# 요약
df_results = pd.DataFrame(results)
success = len(df_results[df_results["status"] == "✅"])
print(f"\n🎯 정답률: {success}/{len(questions)} ({success/len(questions)*100:.0f}%)")
print(f"\n📊 LangSmith에서 확인: https://smith.langchain.com/")
print(f"   프로젝트: {os.environ['LANGCHAIN_PROJECT']}")
```

### 토큰·비용·지연 분석

```python
# ============================================================
# 4. LangSmith API로 트레이스 분석
# ============================================================
from langsmith import Client
import matplotlib.pyplot as plt

ls = Client()

# 최근 실행 가져오기
runs = list(ls.list_runs(
    project_name=os.environ["LANGCHAIN_PROJECT"],
    execution_order=1,  # root runs만
    limit=10,
))

print(f"📊 최근 {len(runs)}개 트레이스 분석:\n")

trace_stats = []
for run in runs:
    total_tokens = (run.total_tokens or 0)
    latency = (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else 0
    
    # 비용 추정 (gpt-4o-mini 기준)
    prompt_tokens = run.prompt_tokens or 0
    completion_tokens = run.completion_tokens or 0
    cost = (prompt_tokens * 0.15 + completion_tokens * 0.6) / 1_000_000
    
    trace_stats.append({
        "question": (run.inputs or {}).get("question", "?")[:30],
        "tokens": total_tokens,
        "latency_s": round(latency, 2),
        "cost_usd": round(cost, 6),
        "status": run.status,
    })

df_traces = pd.DataFrame(trace_stats)
print(df_traces.to_string(index=False))

print(f"\n📈 합계:")
print(f"  총 토큰: {df_traces['tokens'].sum():,}")
print(f"  평균 지연: {df_traces['latency_s'].mean():.2f}초")
print(f"  총 비용: ${df_traces['cost_usd'].sum():.4f}")
```

```python
# ============================================================
# 5. 시각화 — 질문별 토큰/지연 차트
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 토큰 사용량
axes[0].barh(range(len(df_traces)), df_traces["tokens"], color="steelblue")
axes[0].set_yticks(range(len(df_traces)))
axes[0].set_yticklabels(df_traces["question"], fontsize=8)
axes[0].set_xlabel("Total Tokens")
axes[0].set_title("Tokens per Question")
axes[0].invert_yaxis()

# 지연 시간
axes[1].barh(range(len(df_traces)), df_traces["latency_s"], color="coral")
axes[1].set_yticks(range(len(df_traces)))
axes[1].set_yticklabels(df_traces["question"], fontsize=8)
axes[1].set_xlabel("Latency (seconds)")
axes[1].set_title("Latency per Question")
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig("langsmith_stats.png", dpi=150, bbox_inches="tight")
plt.show()
print("📊 차트 저장: langsmith_stats.png")
```

### Dataset 생성

```python
# ============================================================
# 6. 평가용 Dataset 생성
# ============================================================

dataset_name = "sql-agent-eval-10q"

# 기존 동명 데이터셋이 있으면 삭제 후 재생성
try:
    existing = ls.read_dataset(dataset_name=dataset_name)
    ls.delete_dataset(dataset_id=existing.id)
except:
    pass

dataset = ls.create_dataset(
    dataset_name=dataset_name,
    description="SQL 에이전트 10개 질문 평가용 데이터셋",
)

# 질문 + 기대 결과(ground truth) 등록
ground_truths = [
    {"question": "전체 환자 수는?", "ground_truth": "30명"},
    {"question": "남성 환자 중 40세 이상은 몇 명?", "ground_truth": "7명 이상"},
    {"question": "진료과별 의사 수를 보여줘", "ground_truth": "8개 진료과, 각 2~3명"},
    {"question": "지난달 완료 진료 건수는?", "ground_truth": "날짜에 따라 다름"},
    {"question": "응급 진료 평균 비용은?", "ground_truth": "약 300,000원"},
    {"question": "가장 많이 방문한 환자 Top 3는?", "ground_truth": "홍길동, 이준석 등"},
    {"question": "중증 진단을 받은 환자 이름은?", "ground_truth": "급성 충수염, 뇌진탕 등 severe 진단"},
    {"question": "2026년 월별 방문 수 추이는?", "ground_truth": "1~4월 데이터"},
    {"question": "내과 의사 중 급여 최고는?", "ground_truth": "김철수 8,500,000원"},
    {"question": "혈액형별 환자 분포는?", "ground_truth": "A, B, O, AB 각각 수"},
]

for gt in ground_truths:
    ls.create_example(
        inputs={"question": gt["question"]},
        outputs={"ground_truth": gt["ground_truth"]},
        dataset_id=dataset.id,
    )

print(f"✅ Dataset '{dataset_name}' 생성 완료 ({len(ground_truths)}개 예시)")
```

### Feedback (태깅)

```python
# ============================================================
# 7. 실행 결과에 Feedback(태깅) 부여
# ============================================================

# 최근 실행에 대해 정답/오답 태깅
runs = list(ls.list_runs(
    project_name=os.environ["LANGCHAIN_PROJECT"],
    execution_order=1,
    limit=10,
))

for run, res in zip(runs, results):
    score = 1.0 if res["status"] == "✅" else 0.0
    ls.create_feedback(
        run_id=run.id,
        key="correctness",
        score=score,
        comment=f"질문: {res['question'][:30]}... → {res['status']}",
    )
    print(f"  📝 Feedback: {res['question'][:30]}... → score={score}")

print(f"\n✅ {len(runs)}개 실행에 Feedback 부여 완료!")
print("   LangSmith UI에서 Feedback 필터로 실패 케이스를 빠르게 확인하세요.")
```

## 실습 과제

1. 본인 에이전트에 LangSmith 트레이싱을 연결하고 10개 질문을 실행하세요.
2. LangSmith UI에서 가장 느린 질문의 트레이스를 열어 병목 노드를 찾으세요.
3. 평가용 Dataset을 본인 질문 10개로 생성하세요.

## 강사 노트

- **시간 배분**: LangSmith 개념 10분 → 환경변수 설정 5분 → 에이전트 실행+트레이스 15분 → 분석+시각화 10분 → Dataset 생성 5분 → 실습 5분
- LangSmith API Key가 없는 학생이 있을 수 있음 → https://smith.langchain.com/ 에서 무료 가입 안내
- **핵심 메시지**: "LangSmith는 LLM 앱의 '디버거'. printf 디버깅 대신 트레이스를 보세요."
- **자주 묻는 질문**:
  - "무료인가요?" → 개인 무료 플랜으로 충분 (월 5,000 트레이스)
  - "데이터가 외부로 나가나요?" → LangSmith 서버에 저장됨. 민감 데이터는 주의

---

# 22H · Ragas 정량 평가

## 학습목표

- RAG 시스템의 4대 평가 메트릭(Faithfulness, Answer Relevancy, Context Precision, Context Recall)을 설명할 수 있다.
- Ragas로 본인 에이전트를 정량적으로 평가할 수 있다.
- 낮은 점수의 원인을 진단하고 개선할 수 있다.

## 이론 — 왜 정량 평가가 필요한가?

### "좋아 보여요"는 평가가 아니다

```
주관적 평가의 문제:
  👤 "잘 되는 것 같은데요?" → 실제로는 10개 중 3개만 정답
  👤 "정확한 것 같아요" → 실제로는 할루시네이션 포함
  👤 "빨라졌어요" → 정확도는 떨어졌는데 응답만 빨라진 것

정량 평가의 장점:
  📊 Faithfulness: 0.72 → 0.85 (개선됨!)
  📊 Answer Relevancy: 0.65 → 0.78 (개선됨!)
  📊 "왜 0.65인가?" → 질문 3, 7, 9에서 실패 → 스키마 COMMENT 부족이 원인
```

### 4대 메트릭 상세

#### 1. Faithfulness (충실도)

```
측정: "답변이 주어진 컨텍스트에 근거하는가?"

방법:
  1. 답변에서 개별 주장(claim)을 추출
  2. 각 주장이 컨텍스트에서 뒷받침되는지 검증
  3. 뒷받침되는 주장 수 / 전체 주장 수

예시:
  컨텍스트: "내과에는 김철수, 이영희, 신민아 의사가 있습니다."
  답변: "내과에는 김철수, 이영희, 신민아, 박준혁 의사가 있습니다."
  → 3/4 = 0.75 (박준혁은 컨텍스트에 없음 = 할루시네이션)

낮은 점수 원인: 할루시네이션, 컨텍스트에 없는 정보 추가
개선 방법: 프롬프트에 "컨텍스트에 있는 정보만 사용하세요" 강조
```

#### 2. Answer Relevancy (답변 관련성)

```
측정: "답변이 질문에 직접 부합하는가?"

방법:
  1. 답변에서 역질문(reverse question)을 생성
  2. 역질문과 원래 질문의 유사도 측정
  3. 유사도가 높으면 답변이 질문에 잘 부합

예시:
  질문: "내과 의사는 몇 명인가요?"
  답변: "내과에는 김철수, 이영희, 신민아 3명의 의사가 있습니다."
  역질문: "내과에 있는 의사 수는?" → 원래 질문과 매우 유사 → 높은 점수

  답변: "병원에는 총 20명의 의사가 근무합니다."
  역질문: "병원의 전체 의사 수는?" → 원래 질문과 다름 → 낮은 점수

낮은 점수 원인: 질문과 관련 없는 답변, 너무 일반적인 답변
개선 방법: 프롬프트에 "질문에 직접 답하세요" 지시
```

#### 3. Context Precision (컨텍스트 정밀도)

```
측정: "검색된 컨텍스트 중 정답에 기여한 비율은?"

방법: 검색된 문서들 중 실제로 답변에 필요한 문서의 비율

예시:
  질문: "내과 의사 목록"
  검색 결과:
    [1] "내과에는 김철수, 이영희..." ← 관련 ✅
    [2] "주차 요금은 3시간 무료..." ← 무관 ❌
    [3] "내과 진료 시간은..."      ← 약간 관련 ⚠️
  → Precision = 1~2/3

낮은 점수 원인: 관련 없는 문서가 검색됨
개선 방법: 임베딩 모델 변경, Re-ranking 적용, 메타데이터 필터
```

#### 4. Context Recall (컨텍스트 재현율)

```
측정: "정답에 필요한 정보를 얼마나 빠뜨리지 않고 검색했는가?"

방법: ground truth의 주장들 중 컨텍스트에서 찾을 수 있는 비율

예시:
  Ground truth: "내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기)가 있다"
  검색된 컨텍스트에 김철수, 이영희만 포함 → Recall = 2/3

낮은 점수 원인: 관련 문서를 검색하지 못함
개선 방법: Top-K 증가, 하이브리드 검색, 청킹 전략 변경
```

## 핵심 코드 — `19_ragas_eval.ipynb`

### Ragas 데이터 준비

```python
# ============================================================
# 1. 에이전트 실행 결과 수집
# ============================================================

# 21H에서 실행한 results를 사용하거나, 다시 실행
# results 리스트에는 question, answer, sql, sql_result 등이 있음

# Ragas 입력 데이터 구성
eval_data = {
    "question": [],
    "answer": [],
    "contexts": [],
    "ground_truth": [],
}

ground_truths = {
    "전체 환자 수는?": "전체 환자 수는 30명입니다.",
    "남성 환자 중 40세 이상은 몇 명?": "남성 환자 중 40세 이상은 약 7명입니다.",
    "진료과별 의사 수를 보여줘": "내과 3명, 외과 3명, 소아과 3명, 정형외과 2명, 피부과 2명, 신경과 3명, 산부인과 2명, 안과 2명입니다.",
    "지난달 완료 진료 건수는?": "지난달 완료된 진료 건수를 보여줍니다.",
    "응급 진료 평균 비용은?": "응급 진료의 평균 비용은 약 300,000원입니다.",
    "가장 많이 방문한 환자 Top 3는?": "홍길동, 이준석, 강현우 등이 가장 많이 방문한 환자입니다.",
    "중증 진단을 받은 환자 이름은?": "급성 충수염, 담낭결석, 뇌진탕 등 중증 진단을 받은 환자 목록입니다.",
    "2026년 월별 방문 수 추이는?": "2026년 1월부터 4월까지 월별 방문 수 추이를 보여줍니다.",
    "내과 의사 중 급여 최고는?": "내과 의사 중 김철수가 월 8,500,000원으로 가장 높습니다.",
    "혈액형별 환자 분포는?": "A형, B형, O형, AB형 각각의 환자 수 분포입니다.",
}

for res in results:
    q = res["question"]
    eval_data["question"].append(q)
    eval_data["answer"].append(res.get("answer", ""))
    # contexts는 SQL 결과 + 스키마 정보 (에이전트가 참조한 컨텍스트)
    context = f"SQL: {res.get('sql', '')}\n결과: {res.get('sql_result', '')}"
    eval_data["contexts"].append([context])
    eval_data["ground_truth"].append(ground_truths.get(q, ""))

print(f"✅ 평가 데이터 준비: {len(eval_data['question'])}개 질문")
```

### Ragas 평가 실행

```python
# ============================================================
# 2. Ragas 평가 실행
# ============================================================
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

# HuggingFace Dataset 형식으로 변환
eval_dataset = Dataset.from_dict(eval_data)

# 평가 실행 (약 2~5분 소요)
print("⏳ Ragas 평가 실행 중... (약 2~5분)")
report = evaluate(
    eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)

print(f"\n{'='*50}")
print(f"📊 Ragas 평가 결과")
print(f"{'='*50}")
for metric, score in report.items():
    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"  {metric:<25} {bar} {score:.4f}")
```

### 질문별 상세 분석

```python
# ============================================================
# 3. 질문별 상세 분석
# ============================================================

# Ragas 결과를 DataFrame으로 변환
df_eval = report.to_pandas()

print("\n📋 질문별 상세 점수:")
display_cols = ["question", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]
available_cols = [c for c in display_cols if c in df_eval.columns]

if available_cols:
    print(df_eval[available_cols].to_string(index=False))
else:
    print(df_eval.head(10).to_string())
```

### 시각화

```python
# ============================================================
# 4. 시각화 — 4-패널 차트
# ============================================================
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
titles = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]

for ax, metric, color, title in zip(axes.flat, metrics, colors, titles):
    if metric in df_eval.columns:
        values = df_eval[metric].fillna(0)
        short_labels = [q[:15] + "..." for q in df_eval["question"]]
        
        bars = ax.barh(range(len(values)), values, color=color, alpha=0.8)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(short_labels, fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axvline(x=0.7, color="red", linestyle="--", alpha=0.5, label="Target (0.7)")
        ax.invert_yaxis()
        
        # 점수 표시
        for bar, val in zip(bars, values):
            ax.text(val + 0.02, bar.get_y() + bar.get_height()/2, 
                   f"{val:.2f}", va="center", fontsize=8)

plt.suptitle("Ragas Evaluation Report", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("ragas_report.png", dpi=150, bbox_inches="tight")
plt.show()
print("📊 리포트 저장: ragas_report.png")
```

```python
# ============================================================
# 5. 레이더 차트 — 전체 요약
# ============================================================
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

metric_names = titles
metric_values = [report.get(m, 0) for m in metrics]
metric_values.append(metric_values[0])  # 원형으로 닫기

angles = np.linspace(0, 2 * np.pi, len(metric_names), endpoint=False).tolist()
angles.append(angles[0])

ax.plot(angles, metric_values, "o-", linewidth=2, color="#2196F3")
ax.fill(angles, metric_values, alpha=0.25, color="#2196F3")
ax.set_thetagrids(np.degrees(angles[:-1]), metric_names)
ax.set_ylim(0, 1)
ax.set_title("Agent Performance Radar", fontsize=12, fontweight="bold", pad=20)

# 점수 표시
for angle, value, name in zip(angles[:-1], metric_values[:-1], metric_names):
    ax.annotate(f"{value:.2f}", xy=(angle, value), fontsize=10, ha="center")

plt.tight_layout()
plt.savefig("ragas_radar.png", dpi=150, bbox_inches="tight")
plt.show()
```

### 원인 진단 + 튜닝 루프

```python
# ============================================================
# 6. 낮은 점수 원인 진단
# ============================================================

print("🔍 낮은 점수 케이스 분석:\n")

for _, row in df_eval.iterrows():
    low_metrics = []
    for m in metrics:
        if m in row and row[m] is not None and row[m] < 0.7:
            low_metrics.append(f"{m}={row[m]:.2f}")
    
    if low_metrics:
        print(f"⚠️ Q: {row['question'][:40]}...")
        print(f"   낮은 메트릭: {', '.join(low_metrics)}")
        
        # 원인 추정
        for m in metrics:
            if m in row and row[m] is not None and row[m] < 0.7:
                if m == "faithfulness":
                    print(f"   → 진단: 답변에 컨텍스트에 없는 정보가 포함됨 (할루시네이션)")
                    print(f"   → 처방: 프롬프트에 '주어진 결과만 사용' 강조")
                elif m == "answer_relevancy":
                    print(f"   → 진단: 답변이 질문과 직접 관련 없음")
                    print(f"   → 처방: 프롬프트에 '질문에 직접 답변' 지시")
                elif m == "context_precision":
                    print(f"   → 진단: 검색된 컨텍스트에 불필요한 정보가 많음")
                    print(f"   → 처방: Re-ranking 적용 또는 검색 범위 축소")
                elif m == "context_recall":
                    print(f"   → 진단: 정답에 필요한 정보가 검색되지 않음")
                    print(f"   → 처방: 스키마 COMMENT 보강 또는 검색 범위 확대")
        print()
```

```python
# ============================================================
# 7. 튜닝 → 재평가 → Before/After 비교
# ============================================================

# 예시: answer 노드의 프롬프트를 개선
def answer_v2(state: AgentState) -> dict:
    """개선된 답변 프롬프트 — Faithfulness 향상 목적"""
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    
    prompt = ChatPromptTemplate.from_template(
        """아래 SQL 쿼리 결과를 바탕으로 질문에 답변하세요.

## 중요 규칙
- 반드시 아래 결과에 있는 정보만 사용하세요.
- 결과에 없는 정보를 추가하거나 추측하지 마세요.
- 숫자는 천 단위 구분자를 사용하세요.
- 질문에 직접적으로 답변하세요.

## 질문
{q}

## 실행된 SQL
{sql}

## 쿼리 결과
{r}

## 답변"""
    )
    chain = prompt | llm | StrOutputParser()
    ans = chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})
    return {"answer": ans}

# 개선된 에이전트로 재실행
os.environ["LANGCHAIN_PROJECT"] = "sql-agent-final-v2"

graph_v2 = StateGraph(AgentState)
graph_v2.add_node("generate_sql", generate_sql)
graph_v2.add_node("run_sql", run_sql)
graph_v2.add_node("validate", validate)
graph_v2.add_node("answer", answer_v2)  # ← 개선된 답변 노드
graph_v2.set_entry_point("generate_sql")
graph_v2.add_edge("generate_sql", "run_sql")
graph_v2.add_edge("run_sql", "validate")
graph_v2.add_conditional_edges("validate", should_retry)
graph_v2.add_edge("answer", END)
agent_v2 = graph_v2.compile()

# v2 실행 + Ragas 재평가
results_v2 = []
for q in questions:
    result = agent_v2.invoke({"question": q, "attempts": 0})
    results_v2.append(result)

# v2 평가 데이터 준비
eval_data_v2 = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
for q, res in zip(questions, results_v2):
    eval_data_v2["question"].append(q)
    eval_data_v2["answer"].append(res.get("answer", ""))
    eval_data_v2["contexts"].append([f"SQL: {res.get('sql','')}\n결과: {res.get('sql_result','')}"]) 
    eval_data_v2["ground_truth"].append(ground_truths.get(q, ""))

report_v2 = evaluate(Dataset.from_dict(eval_data_v2),
                      metrics=[faithfulness, answer_relevancy, context_precision, context_recall])

# Before/After 비교
print(f"\n{'='*60}")
print(f"📊 Before/After 비교")
print(f"{'='*60}")
print(f"{'메트릭':<25} {'v1':>8} {'v2':>8} {'변화':>8}")
print("-" * 49)
for m in metrics:
    v1 = report.get(m, 0)
    v2 = report_v2.get(m, 0)
    diff = v2 - v1
    arrow = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
    print(f"  {m:<23} {v1:>7.4f} {v2:>7.4f} {arrow} {diff:>+.4f}")
```

```python
# ============================================================
# 8. Before/After 비교 차트 (발표 슬라이드용)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))

x = np.arange(len(metrics))
width = 0.35

v1_scores = [report.get(m, 0) for m in metrics]
v2_scores = [report_v2.get(m, 0) for m in metrics]

bars1 = ax.bar(x - width/2, v1_scores, width, label="v1 (Before)", color="#90CAF9", edgecolor="white")
bars2 = ax.bar(x + width/2, v2_scores, width, label="v2 (After)", color="#2196F3", edgecolor="white")

ax.set_ylabel("Score")
ax.set_title("Ragas Evaluation: Before vs After Tuning")
ax.set_xticks(x)
ax.set_xticklabels(titles)
ax.legend()
ax.set_ylim(0, 1)
ax.axhline(y=0.7, color="red", linestyle="--", alpha=0.5, label="Target")

for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
           f"{bar.get_height():.2f}", ha="center", fontsize=9)
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
           f"{bar.get_height():.2f}", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("ragas_before_after.png", dpi=150, bbox_inches="tight")
plt.show()
print("📊 발표 슬라이드용 Before/After 차트 저장: ragas_before_after.png")
```

## 실습 과제

1. 본인 에이전트의 10개 질문에 대해 Ragas 평가를 실행하세요.
2. 가장 낮은 점수의 질문을 찾아 원인을 진단하세요 (검색 실패? 할루시네이션? 프롬프트?).
3. 하나 이상의 개선을 적용하고 Before/After 비교를 기록하세요 (발표에 사용).

## 강사 노트

- **시간 배분**: 4대 메트릭 설명 15분 → Ragas 실행 10분 → 시각화 5분 → 원인 진단 10분 → 튜닝+재평가 5분 → 실습 5분
- Ragas 실행이 느릴 수 있음 (LLM 호출이 많음) → 10개 질문 → 5개로 줄여서 먼저 실행
- **핵심 메시지**: "점수가 낮아도 괜찮습니다. 중요한 것은 '왜 낮은지 진단하고 어떻게 개선했는지' — 이것이 발표의 핵심입니다."
- Before/After 차트를 발표 슬라이드 3장째에 사용 → "결과 & 회고" 슬라이드의 핵심 시각 자료

---

# 23H · 최종 튜닝 & 리허설

## 학습목표

- 발표 슬라이드 3장을 완성할 수 있다.
- 라이브 데모의 리스크를 점검하고 대비할 수 있다.
- 5~7분 발표를 리허설할 수 있다.

## 이론 — 발표 구성 가이드

### 슬라이드 3장 구조

```
슬라이드 1: 문제 정의 (1분)
├── 도메인 소개 ("나는 ___를 분석하는 에이전트를 만들었습니다")
├── 대상 사용자 ("___가 사용합니다")
├── 핵심 질문 유형 ("이런 질문에 답합니다: ...")
└── 왜 에이전트인가? ("단순 SQL이 아니라 에이전트가 필요한 이유")

슬라이드 2: 아키텍처 (1.5분)
├── LangGraph 상태 다이어그램 (Mermaid 스크린샷)
├── 데이터 흐름: 스키마 → 검색 → SQL 생성 → 실행 → 검증 → 답변
├── 사용 도구 및 선택 이유
└── 특별히 고민한 설계 포인트 1가지

슬라이드 3: 결과 & 회고 (1.5분)
├── Ragas Before/After 차트
├── 성공 사례 2건 (질문 → SQL → 답변)
├── 실패 사례 1건 + 디버깅 과정
└── 배운 점 / 향후 개선 방향
```

### 라이브 데모 리스크 체크리스트

```
□ Colab 런타임이 살아있는가? (타임아웃 주의)
□ Neon DSN이 유효한가? (세션 만료 확인)
□ OpenAI API Key 잔액이 남아있는가?
□ LangSmith 트레이싱이 작동하는가?
□ 데모할 질문 3~5개를 미리 선정했는가?
□ 네트워크가 불안정할 경우 백업 스크린샷이 있는가?
□ 에이전트가 실패하는 질문을 알고 있는가? (설명용)
```

### 발표 시간 배분 가이드

```
5~7분 발표:
  0:00 ~ 1:00  슬라이드 1: 문제 정의
  1:00 ~ 2:30  슬라이드 2: 아키텍처
  2:30 ~ 4:00  라이브 데모 (3~4개 질문)
  4:00 ~ 5:30  슬라이드 3: 결과 & 회고
  5:30 ~ 6:00  정리 ("한 줄 요약")
  6:00 ~ 7:00  (여유 시간)
```

## 핵심 활동

### 개인 작업 시간 (25분)

```
📋 해야 할 것:
1. Ragas 평가 결과를 기반으로 에이전트 최종 튜닝 (10분)
2. 발표 슬라이드 3장 작성 (10분)
   - Google Slides, PowerPoint, 또는 Markdown
3. 데모할 질문 3~5개 선정 + 테스트 (5분)
```

### 강사 1:1 피드백 (20분, 수강생당 5분)

```
강사 체크리스트:
□ 에이전트가 정상 동작하는가? (기본 질문 1개 실행)
□ LangSmith 트레이스가 기록되고 있는가?
□ Ragas 리포트가 준비되었는가?
□ 발표 흐름이 자연스러운가?
□ 라이브 데모 리스크가 관리되고 있는가?
□ 발표 시간이 7분 이내인가?
```

### 발표 스크립트 팁

```
"안녕하세요. 저는 [도메인] 데이터를 분석하는 AI 에이전트를 만들었습니다.

이 에이전트의 사용자는 [대상]이고, [이런 질문]에 답할 수 있습니다.

아키텍처를 보면, LangGraph 기반으로 SQL 생성 → 실행 → 검증 → 답변
4단계로 동작합니다. 특히 [특별 포인트]를 고민했습니다.

지금 실시간으로 보여드리겠습니다.
[데모 3~4개 질문]

Ragas로 평가한 결과, Faithfulness는 X에서 Y로 개선되었고,
[성공 사례]는 이렇게 잘 동작했지만,
[실패 사례]는 [원인] 때문에 실패했고, [이렇게 디버깅]했습니다.

이 프로젝트에서 배운 가장 큰 교훈은 [한 줄]입니다. 감사합니다."
```

## 실습 과제

1. 발표 슬라이드 3장을 완성하세요.
2. 라이브 데모를 1회 리허설하세요 (타이머로 시간 측정).
3. 백업 스크린샷을 최소 3장 준비하세요.

## 강사 노트

- **시간 배분**: 발표 가이드 설명 10분 → 개인 작업 25분 → 1:1 피드백 15분 (3~4명)
- 남은 학생은 자유 튜닝 또는 피어 리허설 진행
- **핵심 메시지**: "완벽한 에이전트보다 '실패에서 배운 것'이 더 중요합니다. 디버깅 과정을 보여주세요."
- 학생이 불안해하면: "실패해도 감점 없습니다. 왜 실패했는지 설명하는 것이 더 인상적입니다."

---

# 24H · 최종 발표 & 수료

## 학습목표

- 5~7분 내에 본인 프로젝트를 발표하고 라이브 데모를 수행할 수 있다.
- 동료의 발표에 건설적인 피드백을 제공할 수 있다.

## 진행 방식

### 발표 순서

```
발표 진행 (총 50분):
  - 수강생 인원에 따라 조정
  - 10명 기준: 1인 5분 발표 = 50분
  - 15명 기준: 1인 3.5분 발표 = 52분 (데모 축소)
  - 20명 이상: 5명씩 4조로 분할, 조별 발표

발표 순서: 자원자 우선 → 나머지 랜덤
```

### 발표 규칙

```
✅ 해야 할 것:
  - 라이브 데모 최소 2개 질문 실행
  - Ragas 점수 또는 Before/After 공유
  - 실패 사례 1건 이상 설명 (디버깅 포함)
  - 7분 이내에 마무리

❌ 하지 말 것:
  - 코드를 줄 단위로 설명 (아키텍처 흐름만)
  - 시간 초과 (타이머 경고 후 1분 내 종료)
  - 다른 발표 중 대화/작업
```

### 평가 기준 (최종 발표 15%)

| 항목 | 배점 | 기준 |
|---|---|---|
| 에이전트 동작 | 30점 | 라이브 데모 성공 여부 (실패 시 디버깅 설명으로 대체 가능) |
| Ragas 평가 | 25점 | 정량 평가 수행 + 개선 노력 |
| LangSmith 활용 | 15점 | 트레이싱 연결 + 분석 |
| 발표 품질 | 20점 | 구조적 전달, 시간 준수, 명확성 |
| 회고 깊이 | 10점 | 실패 분석, 개선 시도, 배운 점 |

### 상호 피드백 양식

```markdown
## 발표 피드백

**발표자:** _______________
**피드백 작성자:** _______________

### 인상적이었던 점
- 

### 개선 제안
- 

### 질문
- 

### 투표 (각 1명에게만)
- Best Agent:       _______________
- Best Insight:     _______________
- Best Presentation:_______________
```

## 핵심 활동

### 발표 진행 (40분)

강사 역할:
- 타이머 관리 (5분 경고, 7분 종료)
- 각 발표 후 강사 질문 1개
- 메모 (평가용)

### 동료 투표 (5분)

```
투표 방법:
1. 전원 발표 완료 후 투표 진행
2. 각 카테고리에서 본인 외 1명 선택:
   🏆 Best Agent       — 가장 정확하고 안정적인 에이전트
   💡 Best Insight      — 가장 통찰력 있는 회고/디버깅
   🎤 Best Presentation — 가장 명확하고 인상적인 발표

3. 결과 발표 (동점 시 공동 수상)
```

### 수료 요건 최종 확인

```
수료에 필요한 4가지:
  ✅ 4일간 출석 (지각 3회 = 결석 1회)
  ✅ 과제 #1 제출 (프로젝트 제안서)
  ✅ 과제 #2 제출 (스키마 + 시드 데이터)
  ✅ 과제 #3 제출 (에이전트 v1 + LangSmith)
  ✅ 최종 발표 수행
```

## 과정 회고 — 4일간 배운 것

```
Day 1: 기초 재료
  PostgreSQL + SQL → Schema Intelligence → LlamaIndex + ChromaDB → Text-to-SQL 맛보기

Day 2: 첫 요리
  프롬프트 튜닝 → 멀티턴 상담사 → Gradio UI

Day 3: 본격 빌드
  Vanna 자가학습 → LangChain/LCEL → Advanced RAG → LangGraph 에이전트

Day 4: 검증 & 발표
  LangSmith 모니터링 → Ragas 정량 평가 → Before/After 튜닝 → 최종 발표
```

### 향후 학습 로드맵

```
이 과정을 마친 후 더 배울 것들:

📊 SQL 심화
  - 복잡한 윈도우 함수, 재귀 CTE, 성능 최적화
  - PostgreSQL 확장 (PostGIS, pgvector)

🔍 RAG 심화
  - 청킹 최적화 (Semantic Chunking)
  - 멀티모달 RAG (이미지, 테이블)
  - Graph RAG (지식 그래프 기반)

🤖 에이전트 심화
  - 멀티에이전트 시스템 (LangGraph)
  - 도구 사용 (Tool Use) 확장
  - 자율 계획 수립 (Plan-and-Execute)

📈 평가 심화
  - 자동 평가 파이프라인 (CI/CD)
  - A/B 테스트
  - Human-in-the-loop 평가

🚀 배포
  - FastAPI + Docker 컨테이너화
  - 클라우드 배포 (AWS, GCP)
  - 프로덕션 모니터링
```

### 추천 자료

```
📚 교재 (이미 사용한 것):
  - 『현장에서 바로 써먹는 SQL with PostgreSQL』(김임용)
  - 『LLM과 RAG로 구현하는 AI 애플리케이션』(에디 유)
  - 『랭체인과 랭그래프로 구현하는 RAG·AI 에이전트 실전 입문』(강병진)

🌐 온라인 자료:
  - LlamaIndex Docs — https://docs.llamaindex.ai
  - LangChain Docs — https://python.langchain.com
  - LangGraph Tutorial — https://langchain-ai.github.io/langgraph/
  - Ragas Docs — https://docs.ragas.io
  - Vanna.ai Docs — https://vanna.ai/docs

🎥 강의/영상:
  - DeepLearning.AI — "Building and Evaluating Advanced RAG"
  - LangChain YouTube — LangGraph 튜토리얼 시리즈
```

## 강사 노트

- **시간 배분**: 발표 40분 (8~10명) → 투표 5분 → 결과 발표+수료 5분
- 시간 압박이 심할 수 있음 — 발표 시간을 엄격히 관리
- 마지막 발표자까지 집중력이 떨어지지 않도록 중간에 박수/격려
- **수료 후**: 수강생 슬랙/카톡 그룹 생성 권장 → 이후 질문·공유 채널
- 사진 촬영 시간 확보 (수료증 배포와 함께)

---

## 부록: 노트북 번호 체계

| 번호 | 파일명 | 대응 시간 |
|---|---|---|
| 00 | `00_demo_agent.ipynb` | 1H |
| 01 | `01_postgres_basics.ipynb` | 2H |
| 02 | `02_sql_aggregation_join.ipynb` | 3H |
| 03 | `03_schema_intelligence.ipynb` | 4H |
| 04 | `04_llamaindex_intro.ipynb` | 5H |
| 05 | `05_embedding_chromadb.ipynb` | 6H |
| 06 | `06_text_to_sql.ipynb` | 7H |
| 07 | `07_project_briefing.ipynb` | 8H |
| 08 | `08_text_to_sql_advanced.ipynb` | 10H |
| 09 | `09_gradio_chatbot.ipynb` | 11~12H |
| 10 | `10_vanna_intro.ipynb` | 13H |
| 11 | `11_vanna_training.ipynb` | 14H |
| 12 | `12_langchain_lcel.ipynb` | 15H |
| 13 | `13_lcel_rag_chain.ipynb` | 16H |
| 14 | `14_advanced_rag_query.ipynb` | 17H |
| 15 | `15_advanced_rag_retrieval.ipynb` | 18H |
| 16 | `16_langgraph_concept.ipynb` | 19H |
| 17 | `17_my_sql_agent.ipynb` | 20H |
| 18 | `18_langsmith_tracing.ipynb` | 21H |
| 19 | `19_ragas_eval.ipynb` | 22H |

## 부록: 자주 발생하는 문제 해결

| 문제 | 원인 | 해결 |
|---|---|---|
| Neon 연결 실패 | DSN 오타 또는 `?sslmode=require` 누락 | DSN 재확인, sslmode 추가 |
| OpenAI 토큰 초과 | 프롬프트가 너무 길음 | 스키마 축소, `gpt-4o-mini` 사용 |
| Ragas 실행 느림 | LLM 호출 횟수 많음 | 질문 5개로 줄여서 먼저 테스트 |
| ChromaDB 데이터 소실 | Colab 런타임 재시작 | Google Drive 마운트 또는 재학습 |
| LangSmith 트레이스 안 보임 | API Key 미설정 | `LANGCHAIN_API_KEY` 환경변수 확인 |
| Gradio share URL 안 열림 | 방화벽 또는 런타임 종료 | Colab 다시 실행, `share=True` 확인 |
| SQL 생성 실패 반복 | 스키마 COMMENT 부족 | `COMMENT ON` 추가, 프롬프트 개선 |

---

*Day 4 상세 강의자료 — 강의 교안 및 Colab 노트북 분할을 전제로 작성됨*
