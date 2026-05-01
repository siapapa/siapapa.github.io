# 📘 Day 4 — 평가 · 모니터링 + 최종 발표 (21~24H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API + LangSmith

---

## 🔑 용어 사전 (비IT 수강생을 위한)

| 용어 | 쉬운 설명 |
|---|---|
| **트레이싱(Tracing)** | AI의 작업 과정을 기록하는 것. 의사의 "진료 기록부"와 같음 |
| **메트릭(Metric)** | 성과를 숫자로 측정한 것. 시험 점수처럼 AI의 성적표 |
| **할루시네이션(Hallucination)** | AI가 없는 정보를 만들어내는 것. "거짓말"이 아니라 "착각" |
| **Ground Truth** | 정답. AI의 답변과 비교할 기준이 되는 올바른 답 |
| **Faithfulness (충실도)** | 주어진 자료만 보고 답했는가? (거짓 없이) |
| **Relevancy (관련성)** | 질문에 맞는 답을 했는가? |

---

## 📦 공통 부트스트랩

### 이 코드가 하는 일
> Day 4 실습 도구를 설치하고, LangSmith 트레이싱을 활성화합니다.

```python
!pip install -q \
    langgraph langchain langchain-openai langsmith \
    ragas datasets \
    sqlalchemy psycopg2-binary pandas tabulate matplotlib \
    openai sqlparse

import os
from google.colab import userdata

# AI 및 DB 설정
os.environ["OPENAI_API_KEY"]       = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]             = userdata.get("NEON_DSN")

# LangSmith 트레이싱 활성화
os.environ["LANGCHAIN_TRACING_V2"] = "true"                    # 트레이싱 ON
os.environ["LANGCHAIN_API_KEY"]    = userdata.get("LANGSMITH_KEY")  # LangSmith API 키
os.environ["LANGCHAIN_PROJECT"]    = "sql-agent-final"          # 프로젝트 이름

from sqlalchemy import create_engine, text
import pandas as pd
engine = create_engine(os.environ["NEON_DSN"])
print("✅ 연결 완료! LangSmith 트레이싱 활성화됨")
```

> ⚠️ **LangSmith API Key가 없다면?** → https://smith.langchain.com 에서 무료 가입 → Settings → API Keys에서 생성

---

# 21H · LangSmith 트레이싱

## 학습목표
- LangSmith로 에이전트 실행을 모니터링할 수 있다
- 토큰 사용량, 지연 시간, 비용을 분석할 수 있다
- 평가용 Dataset을 생성할 수 있다

## 왜 모니터링이 필요한가?

> 💡 **LangSmith = AI 앱의 "진료 기록부"**

| | 전통 소프트웨어 | AI(LLM) 앱 |
|---|---|---|
| 출력 | 항상 같은 결과 | 매번 다른 결과 |
| 버그 | 재현 가능 | 재현 어려움 |
| 디버깅 | 로그 확인 | 프롬프트+컨텍스트+모델 모두 확인 필요 |
| 테스트 | 단위 테스트 | **정량 평가 프레임워크** 필요 |

→ AI 앱은 "무엇이 왜 잘못됐는지" 추적하기 어려움 → LangSmith가 해결!

### Run/Trace 구조

```
Trace (전체 에이전트 실행 1건)
├── Run: generate_sql (AI 호출)
│   ├── 입력: {question: "환자 수?", schema: "..."}
│   ├── 출력: "SELECT COUNT(*) FROM patients"
│   ├── 토큰: 450 + 12 = 462
│   └── 시간: 1.2초
├── Run: run_sql (SQL 실행)
│   ├── 입력: "SELECT COUNT(*) ..."
│   └── 시간: 0.3초
├── Run: validate (검증)
│   └── 결과: 에러 없음
└── Run: answer (AI 호출)
    ├── 출력: "환자는 30명입니다."
    └── 토큰: 280 + 25 = 305
```

## 🎯 실습 — Day 3 에이전트에 LangSmith 연결

### 이 코드가 하는 일
> Day 3에서 만든 SQL 에이전트를 다시 구성하고, 환경변수 설정만으로 자동 트레이싱됩니다.

```python
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
        col_lines = [f"  {c['name']} {c['type']}" for c in columns]
        fk_lines = [f"  FK ({','.join(fk['constrained_columns'])}) → {fk['referred_table']}" for fk in fks]
        ddl = f"CREATE TABLE {table} (\n" + ",\n".join(col_lines)
        if fk_lines: ddl += ",\n" + ",\n".join(fk_lines)
        ddl += "\n);"
        parts.append(ddl)
    return "\n\n".join(parts)

TABLES = ["patients", "doctors", "visits", "diagnoses", "departments"]
SCHEMA = collect_schema(engine, TABLES)

class AgentState(TypedDict):
    question: str; sql: str; sql_result: str; error: str; answer: str; attempts: int

BLOCKED = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE)

def sanitize_sql(sql):
    m = BLOCKED.search(sql)
    if m: return "", f"보안 위반: '{m.group()}'"
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    return sql, ""

def generate_sql(state):
    err_fb = f"\n이전 오류: {state['error']}\n수정하세요." if state.get("error") else ""
    prompt = ChatPromptTemplate.from_template(
        "PostgreSQL 전문가. SELECT만. SQL만 반환.\n\n{schema}\n{err}\n\n질문: {q}\nSQL:")
    chain = prompt | llm | StrOutputParser()
    sql = chain.invoke({"schema": SCHEMA, "q": state["question"], "err": err_fb})
    sql = re.sub(r"```sql\s*", "", re.sub(r"```\s*", "", sql)).strip()
    return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

def run_sql(state):
    safe_sql, error = sanitize_sql(state["sql"])
    if error: return {"error": error, "sql_result": ""}
    try:
        df = pd.read_sql(safe_sql, engine)
        if df.empty: return {"sql_result": "(결과 없음)", "error": ""}
        return {"sql_result": df.head(50).to_markdown(index=False), "error": ""}
    except Exception as e:
        return {"error": f"SQL 오류: {str(e)}", "sql_result": ""}

def validate(state):
    return {"error": ""} if not state.get("error") else state

def answer(state):
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    prompt = ChatPromptTemplate.from_template(
        "결과를 한국어로 요약. 숫자 천 단위 구분.\n질문: {q}\nSQL: {sql}\n결과:\n{r}\n답변:")
    chain = prompt | llm | StrOutputParser()
    return {"answer": chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})}

def should_retry(state):
    if not state.get("error"): return "answer"
    if state.get("attempts", 0) >= 3: return "answer"
    return "generate_sql"

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
print("✅ 에이전트 컴파일 완료 — LangSmith 트레이싱 활성화!")
```

### 10개 질문 실행 (트레이스 자동 기록)

```python
questions = [
    "전체 환자 수는?", "남성 환자 중 40세 이상은 몇 명?",
    "진료과별 의사 수를 보여줘", "지난달 완료 진료 건수는?",
    "응급 진료 평균 비용은?", "가장 많이 방문한 환자 Top 3는?",
    "중증 진단을 받은 환자 이름은?", "2026년 월별 방문 수 추이는?",
    "내과 의사 중 급여 최고는?", "혈액형별 환자 분포는?",
]

results = []
for i, q in enumerate(questions):
    print(f"[{i+1}/10] {q}")
    result = agent.invoke({"question": q, "attempts": 0})
    status = "✅" if result.get("answer") and "죄송" not in result.get("answer","") else "❌"
    results.append({
        "question": q, "status": status, "attempts": result.get("attempts", 0),
        "sql": result.get("sql", ""), "answer": result.get("answer", ""),
        "sql_result": result.get("sql_result", ""),
    })
    print(f"  {status} (시도 {result.get('attempts',0)}회)")

success = sum(1 for r in results if r["status"] == "✅")
print(f"\n🎯 정답률: {success}/{len(questions)} ({success/len(questions)*100:.0f}%)")
print(f"\n📊 LangSmith에서 확인: https://smith.langchain.com/")
print(f"   프로젝트: {os.environ['LANGCHAIN_PROJECT']}")
```

### 토큰/비용/지연 분석

```python
from langsmith import Client
import matplotlib.pyplot as plt

ls = Client()
runs = list(ls.list_runs(
    project_name=os.environ["LANGCHAIN_PROJECT"],
    execution_order=1, limit=10))

trace_stats = []
for run in runs:
    total_tokens = run.total_tokens or 0
    latency = (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else 0
    prompt_tokens = run.prompt_tokens or 0
    completion_tokens = run.completion_tokens or 0
    cost = (prompt_tokens * 0.15 + completion_tokens * 0.6) / 1_000_000
    trace_stats.append({
        "question": (run.inputs or {}).get("question", "?")[:30],
        "tokens": total_tokens, "latency_s": round(latency, 2), "cost_usd": round(cost, 6),
    })

df_traces = pd.DataFrame(trace_stats)
print(df_traces.to_string(index=False))
print(f"\n📈 총 토큰: {df_traces['tokens'].sum():,} | 평균 지연: {df_traces['latency_s'].mean():.2f}초 | 총 비용: ${df_traces['cost_usd'].sum():.4f}")
```

### 평가용 Dataset 생성

```python
dataset_name = "sql-agent-eval-10q"
try:
    existing = ls.read_dataset(dataset_name=dataset_name)
    ls.delete_dataset(dataset_id=existing.id)
except: pass

dataset = ls.create_dataset(dataset_name=dataset_name, description="SQL 에이전트 10개 질문 평가용")

ground_truths = [
    {"question": "전체 환자 수는?", "ground_truth": "30명"},
    {"question": "남성 환자 중 40세 이상은 몇 명?", "ground_truth": "7명 이상"},
    {"question": "진료과별 의사 수를 보여줘", "ground_truth": "8개 진료과, 각 2~3명"},
    {"question": "지난달 완료 진료 건수는?", "ground_truth": "날짜에 따라 다름"},
    {"question": "응급 진료 평균 비용은?", "ground_truth": "약 300,000원"},
    {"question": "가장 많이 방문한 환자 Top 3는?", "ground_truth": "홍길동 등"},
    {"question": "중증 진단을 받은 환자 이름은?", "ground_truth": "severe 진단 환자 목록"},
    {"question": "2026년 월별 방문 수 추이는?", "ground_truth": "1~4월 데이터"},
    {"question": "내과 의사 중 급여 최고는?", "ground_truth": "김철수 8,500,000원"},
    {"question": "혈액형별 환자 분포는?", "ground_truth": "A, B, O, AB 각각 수"},
]

for gt in ground_truths:
    ls.create_example(inputs={"question": gt["question"]},
                      outputs={"ground_truth": gt["ground_truth"]}, dataset_id=dataset.id)
print(f"✅ Dataset '{dataset_name}' 생성 완료 ({len(ground_truths)}개)")
```

## 📌 21H 핵심 정리
- **LangSmith** = AI 앱의 "진료 기록부". 환경변수 3줄 설정으로 자동 트레이싱
- Run/Trace 구조로 각 노드의 입출력·토큰·지연·비용 확인
- **Dataset** = 평가용 질문+정답 모음 → 22H Ragas에서 사용

---

# 22H · Ragas 정량 평가

## 학습목표
- 4대 평가 메트릭을 이해하고 Ragas로 측정할 수 있다
- 낮은 점수의 원인을 진단하고 개선할 수 있다

## "좋아 보여요"는 평가가 아니다

```
주관적 평가의 문제:
  👤 "잘 되는 것 같은데요?" → 실제로는 10개 중 3개만 정답
  👤 "정확한 것 같아요"     → 실제로는 할루시네이션(착각) 포함

정량 평가의 장점:
  📊 Faithfulness: 0.72 → 0.85 (프롬프트 개선 후 향상!)
  📊 "왜 0.72인가?" → 질문 3, 7에서 실패 → COMMENT 부족이 원인 → 수정 가능!
```

## 4대 메트릭 — AI의 성적표

### 1. Faithfulness (충실도) — "교과서에 있는 내용만 답했는가?"

> 💡 **비유**: 오픈북 시험에서 교재에 없는 내용을 적으면 감점

```
컨텍스트: "내과에는 김철수, 이영희, 신민아가 있습니다."
답변: "내과에는 김철수, 이영희, 신민아, 박준혁이 있습니다."
→ 3/4 = 0.75 (박준혁은 컨텍스트에 없음 = 할루시네이션!)

낮은 점수 → 프롬프트에 "주어진 결과만 사용하세요" 강조
```

### 2. Answer Relevancy (답변 관련성) — "질문에 제대로 답했는가?"

```
질문: "내과 의사는 몇 명?"
좋은 답변: "내과에는 3명의 의사가 있습니다." → 높은 점수
나쁜 답변: "병원에는 총 20명의 의사가 있습니다." → 낮은 점수 (질문과 다름)

낮은 점수 → 프롬프트에 "질문에 직접 답하세요" 지시
```

### 3. Context Precision (컨텍스트 정밀도) — "검색한 자료 중 쓸모있는 비율은?"

```
질문: "내과 의사 목록"
검색 결과: [1] 내과 의사 정보 ✅ [2] 주차 요금 ❌ [3] 내과 진료시간 ⚠️
→ Precision ≈ 1~2/3

낮은 점수 → Re-ranking 적용, 메타데이터 필터 추가
```

### 4. Context Recall (컨텍스트 재현율) — "필요한 자료를 빠뜨리지 않았는가?"

```
정답: "김철수(심장), 이영희(호흡기), 신민아(소화기)"
검색된 자료에 김철수, 이영희만 포함 → Recall = 2/3

낮은 점수 → Top-K 증가, 하이브리드 검색 적용
```

## 🎯 실습 — Ragas 평가 실행

### 이 코드가 하는 일
> 21H에서 실행한 결과 + 정답(ground truth)을 Ragas에 넣어 4개 메트릭을 측정합니다.

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

# 평가 데이터 준비
eval_data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}

gt_map = {
    "전체 환자 수는?": "전체 환자 수는 30명입니다.",
    "남성 환자 중 40세 이상은 몇 명?": "남성 환자 중 40세 이상은 약 7명입니다.",
    "진료과별 의사 수를 보여줘": "내과 3명, 외과 3명, 소아과 3명 등 총 20명.",
    "지난달 완료 진료 건수는?": "지난달 완료된 진료 건수입니다.",
    "응급 진료 평균 비용은?": "응급 진료 평균 비용은 약 300,000원입니다.",
    "가장 많이 방문한 환자 Top 3는?": "홍길동, 이준석, 강현우 등입니다.",
    "중증 진단을 받은 환자 이름은?": "급성 충수염, 담낭결석 등 중증 진단 환자 목록.",
    "2026년 월별 방문 수 추이는?": "2026년 1~4월 월별 방문 수 추이.",
    "내과 의사 중 급여 최고는?": "김철수 월 8,500,000원.",
    "혈액형별 환자 분포는?": "A형, B형, O형, AB형 각각 환자 수.",
}

for res in results:
    q = res["question"]
    eval_data["question"].append(q)
    eval_data["answer"].append(res.get("answer", ""))
    eval_data["contexts"].append([f"SQL: {res.get('sql','')}\n결과: {res.get('sql_result','')}"]) 
    eval_data["ground_truth"].append(gt_map.get(q, ""))

print(f"✅ 평가 데이터 준비: {len(eval_data['question'])}개 질문")
```

```python
# Ragas 평가 실행 (약 2~5분 소요)
eval_dataset = Dataset.from_dict(eval_data)
print("⏳ Ragas 평가 실행 중... (약 2~5분)")

report = evaluate(eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall])

print(f"\n{'='*50}")
print(f"📊 Ragas 평가 결과")
print(f"{'='*50}")
for metric, score in report.items():
    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"  {metric:<25} {bar} {score:.4f}")
```

### 시각화 — 4-패널 차트 + 레이더 차트

```python
import matplotlib.pyplot as plt
import numpy as np

# 질문별 상세 분석
df_eval = report.to_pandas()
metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

# 4-패널 차트
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
titles = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]

for ax, metric, color, title in zip(axes.flat, metrics, colors, titles):
    if metric in df_eval.columns:
        values = df_eval[metric].fillna(0)
        labels = [q[:15]+"..." for q in df_eval["question"]]
        ax.barh(range(len(values)), values, color=color, alpha=0.8)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axvline(x=0.7, color="red", linestyle="--", alpha=0.5)
        ax.invert_yaxis()

plt.suptitle("Ragas Evaluation Report", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("ragas_report.png", dpi=150, bbox_inches="tight")
plt.show()

# 레이더 차트
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
values = [report.get(m, 0) for m in metrics] + [report.get(metrics[0], 0)]
angles = np.linspace(0, 2*np.pi, len(titles), endpoint=False).tolist() + [0]
ax.plot(angles, values, "o-", linewidth=2, color="#2196F3")
ax.fill(angles, values, alpha=0.25, color="#2196F3")
ax.set_thetagrids(np.degrees(angles[:-1]), titles)
ax.set_ylim(0, 1)
ax.set_title("Agent Performance Radar", fontsize=12, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig("ragas_radar.png", dpi=150, bbox_inches="tight")
plt.show()
```

### 낮은 점수 원인 진단

```python
print("🔍 낮은 점수 케이스 분석:\n")
for _, row in df_eval.iterrows():
    for m in metrics:
        if m in row and row[m] is not None and row[m] < 0.7:
            print(f"⚠️ Q: {row['question'][:40]}... → {m}={row[m]:.2f}")
            if m == "faithfulness":
                print(f"   → 진단: 할루시네이션 | 처방: '주어진 결과만 사용' 프롬프트 강조")
            elif m == "answer_relevancy":
                print(f"   → 진단: 질문과 무관한 답변 | 처방: '질문에 직접 답변' 지시")
            elif m == "context_precision":
                print(f"   → 진단: 불필요한 컨텍스트 | 처방: Re-ranking 또는 검색 범위 축소")
            elif m == "context_recall":
                print(f"   → 진단: 필요한 정보 누락 | 처방: COMMENT 보강 또는 검색 범위 확대")
```

### 튜닝 → 재평가 → Before/After 비교

```python
# 개선된 답변 프롬프트 (Faithfulness 향상 목적)
def answer_v2(state):
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    prompt = ChatPromptTemplate.from_template(
        """아래 SQL 결과를 바탕으로 답변하세요.
## 중요 규칙
- 반드시 아래 결과에 있는 정보만 사용하세요.
- 결과에 없는 정보를 추가하거나 추측하지 마세요.
- 숫자는 천 단위 구분자 사용.
- 질문에 직접적으로 답변하세요.

질문: {q}
SQL: {sql}
결과: {r}
답변:""")
    chain = prompt | llm | StrOutputParser()
    return {"answer": chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})}

# v2 에이전트로 재실행 + 재평가 후 비교
# (코드는 21H 에이전트에서 answer 노드만 answer_v2로 교체)
```

> 💡 **발표 슬라이드 3장째에 Before/After 차트를 넣으세요!** 이것이 발표의 핵심 시각 자료입니다.

## 📌 22H 핵심 정리
- **4대 메트릭**: Faithfulness(충실도), Answer Relevancy(관련성), Context Precision(정밀도), Context Recall(재현율)
- 점수가 낮아도 OK — **"왜 낮은지 진단하고 어떻게 개선했는지"가 중요**
- Before/After 차트가 발표의 핵심 시각 자료

---

# 23H · 최종 튜닝 & 리허설

## 학습목표
- 발표 슬라이드 3장을 완성한다
- 라이브 데모를 리허설한다

## 발표 슬라이드 3장 구조

### 슬라이드 1: 문제 정의 (1분)
```
├── 도메인 소개: "나는 ___를 분석하는 에이전트를 만들었습니다"
├── 대상 사용자: "___가 사용합니다"
├── 핵심 질문 유형: "이런 질문에 답합니다: ..."
└── 왜 에이전트인가?: "단순 SQL이 아니라 에이전트가 필요한 이유"
```

### 슬라이드 2: 아키텍처 (1.5분)
```
├── LangGraph 상태 다이어그램 (Mermaid 스크린샷)
├── 데이터 흐름: 스키마 → SQL 생성 → 실행 → 검증 → 답변
├── 사용 도구 및 선택 이유
└── 특별히 고민한 설계 포인트 1가지
```

### 슬라이드 3: 결과 & 회고 (1.5분)
```
├── Ragas Before/After 차트 ← 핵심!
├── 성공 사례 2건 (질문 → SQL → 답변)
├── 실패 사례 1건 + 디버깅 과정
└── 배운 점 / 향후 개선 방향
```

## 라이브 데모 리스크 체크리스트

```
□ Colab 런타임이 살아있는가? (타임아웃 주의)
□ Neon DSN이 유효한가?
□ OpenAI API Key 잔액이 남아있는가?
□ LangSmith 트레이싱이 작동하는가?
□ 데모할 질문 3~5개를 미리 선정했는가?
□ 네트워크 불안정 시 백업 스크린샷이 있는가?
□ 에이전트가 실패하는 질문을 알고 있는가? (설명용)
```

## 발표 시간 배분

```
0:00 ~ 1:00  슬라이드 1: 문제 정의
1:00 ~ 2:30  슬라이드 2: 아키텍처
2:30 ~ 4:00  라이브 데모 (3~4개 질문)
4:00 ~ 5:30  슬라이드 3: 결과 & 회고
5:30 ~ 6:00  한 줄 요약
```

## 발표 스크립트 템플릿

```
"안녕하세요. 저는 [도메인] 데이터를 분석하는 AI 에이전트를 만들었습니다.

이 에이전트의 사용자는 [대상]이고, [이런 질문]에 답할 수 있습니다.

아키텍처를 보면, LangGraph로 SQL 생성 → 실행 → 검증 → 답변 
4단계로 동작합니다. 특히 [특별 포인트]를 고민했습니다.

지금 실시간으로 보여드리겠습니다. [데모 3~4개 질문]

Ragas 평가 결과, Faithfulness는 X에서 Y로 개선되었고,
[성공 사례]는 잘 동작했지만,
[실패 사례]는 [원인] 때문에 실패했고, [이렇게 디버깅]했습니다.

가장 큰 교훈은 [한 줄]입니다. 감사합니다."
```

> 💡 **"완벽한 에이전트보다 '실패에서 배운 것'이 더 중요합니다."**

## 📌 23H 핵심 정리
- 슬라이드 3장: 문제 정의 / 아키텍처 / 결과 & 회고
- 라이브 데모 리스크를 사전에 점검하고 백업 준비
- 실패 사례 + 디버깅 과정이 발표의 차별점

---

# 24H · 최종 발표 & 수료

## 발표 규칙

```
✅ 해야 할 것:
  - 라이브 데모 최소 2개 질문 실행
  - Ragas 점수 또는 Before/After 공유
  - 실패 사례 1건 이상 설명 (디버깅 포함)
  - 7분 이내에 마무리

❌ 하지 말 것:
  - 코드를 줄 단위로 설명 (아키텍처 흐름만)
  - 시간 초과 (타이머 경고 후 1분 내 종료)
```

## 평가 기준

| 항목 | 배점 | 기준 |
|---|---|---|
| 에이전트 동작 | 30점 | 라이브 데모 성공 (실패 시 디버깅 설명으로 대체 가능) |
| Ragas 평가 | 25점 | 정량 평가 수행 + 개선 노력 |
| LangSmith 활용 | 15점 | 트레이싱 연결 + 분석 |
| 발표 품질 | 20점 | 구조적 전달, 시간 준수, 명확성 |
| 회고 깊이 | 10점 | 실패 분석, 개선 시도, 배운 점 |

## 상호 피드백 양식

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
- 🏆 Best Agent:       _______________
- 💡 Best Insight:     _______________
- 🎤 Best Presentation:_______________
```

## 수료 요건

```
수료에 필요한 5가지:
  ✅ 4일간 출석
  ✅ 과제 #1: 프로젝트 제안서
  ✅ 과제 #2: 스키마 + 시드 데이터
  ✅ 과제 #3: 에이전트 v1 + LangSmith
  ✅ 최종 발표 수행
```

## 4일간 배운 것 회고

```
Day 1: 기초 재료
  PostgreSQL + SQL → Schema Intelligence → LlamaIndex + ChromaDB → Text-to-SQL

Day 2: 첫 요리
  프롬프트 튜닝 → 멀티턴 상담사 → Gradio UI

Day 3: 본격 빌드
  Vanna → LangChain/LCEL → Advanced RAG → LangGraph 에이전트

Day 4: 검증 & 발표
  LangSmith → Ragas → Before/After 튜닝 → 최종 발표
```

## 향후 학습 로드맵

| 분야 | 추천 주제 |
|---|---|
| SQL 심화 | 윈도우 함수, 재귀 CTE, 성능 최적화, pgvector |
| RAG 심화 | Semantic Chunking, 멀티모달 RAG, Graph RAG |
| 에이전트 심화 | 멀티에이전트, Tool Use 확장, Plan-and-Execute |
| 평가 심화 | 자동 평가 파이프라인, A/B 테스트 |
| 배포 | FastAPI + Docker, 클라우드 배포 |

## 추천 자료

**교재**
- 『현장에서 바로 써먹는 SQL with PostgreSQL』(김임용)
- 『랭체인과 랭그래프로 구현하는 RAG·AI 에이전트 실전 입문』(강병진)

**온라인 문서**
- LlamaIndex: docs.llamaindex.ai
- LangChain: python.langchain.com
- LangGraph: langchain-ai.github.io/langgraph
- Ragas: docs.ragas.io
- Vanna.ai: vanna.ai/docs

---

## 부록: 노트북 번호 체계

| 번호 | 파일명 | 시간 |
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
| Neon 연결 실패 | DSN에 `?sslmode=require` 누락 | DSN 끝에 추가 |
| OpenAI 토큰 초과 | 프롬프트가 너무 길음 | 스키마 축소, gpt-4o-mini 사용 |
| Ragas 실행 느림 | LLM 호출 횟수 많음 | 질문 5개로 줄여서 먼저 테스트 |
| ChromaDB 데이터 소실 | Colab 런타임 재시작 | 재학습 필요 |
| LangSmith 트레이스 안 보임 | API Key 미설정 | LANGCHAIN_API_KEY 확인 |
| Gradio URL 안 열림 | 런타임 종료 | Colab 다시 실행 |
| SQL 생성 반복 실패 | 스키마 COMMENT 부족 | COMMENT ON 추가 |

---

*Day 4 강의자료 — AI 기반 SQL 분석 에이전트 구축*
