# 21H · LangSmith 트레이싱

## 학습목표

- LangSmith의 역할(LLM 애플리케이션 관측 가능성)을 설명할 수 있다
- Run/Trace 구조를 이해하고, 에이전트 실행을 트레이싱할 수 있다
- 토큰 사용량, 지연 시간, 비용을 분석할 수 있다
- 평가용 Dataset을 프로그래밍 방식으로 생성할 수 있다

---

<div class="colab-link" data-notebook="18_langsmith_tracing"></div>

## 왜 모니터링이 필요한가?

!!! tip "LangSmith = AI 앱의 "진료 기록부""
    전통 소프트웨어는 로그만 보면 디버깅이 가능하지만, LLM 애플리케이션은 프롬프트, 컨텍스트, 모델 파라미터가 모두 결합되어 비결정적 출력을 만듭니다. LangSmith는 이 모든 것을 **한 곳에서 추적**할 수 있게 해주는 관측 도구입니다.

### 전통 소프트웨어 vs LLM 애플리케이션

| | 전통 소프트웨어 | AI(LLM) 앱 |
|---|---|---|
| 출력 | 항상 같은 결과 (결정적) | 매번 다른 결과 (비결정적) |
| 버그 | 재현 가능 | 재현 어려움 |
| 디버깅 | 로그 확인 | 프롬프트+컨텍스트+모델 모두 확인 필요 |
| 테스트 | 단위 테스트 | **정량 평가 프레임워크** 필요 |

→ AI 앱은 "무엇이 왜 잘못됐는지" 추적하기 어려움 → **관측 가능성(Observability)**이 핵심 → LangSmith가 해결!

---

## Run/Trace 구조

LangSmith에서 모든 에이전트 실행은 **Trace**로 기록되고, 각 단계는 **Run**으로 세분됩니다.

```
Trace (전체 에이전트 실행 1건)
├── Run: generate_sql (AI 호출)
│   ├── 입력: {question: "환자 수?", schema: "..."}
│   ├── 출력: "SELECT COUNT(*) FROM patients"
│   ├── 토큰: 450 (in) + 12 (out) = 462
│   ├── 시간: 1.2초
│   └── 비용: $0.0003
├── Run: run_sql (SQL 실행)
│   ├── 입력: "SELECT COUNT(*) FROM patients"
│   ├── 출력: "30"
│   └── 시간: 0.3초
├── Run: validate (검증)
│   └── 결과: 에러 없음
└── Run: answer (AI 호출)
    ├── 입력: {result: "30", question: "..."}
    ├── 출력: "현재 등록된 환자는 30명입니다."
    ├── 토큰: 280 (in) + 25 (out) = 305
    └── 비용: $0.0002
```

!!! tip "LangSmith UI 화면 구성"
    LangSmith 웹 대시보드는 크게 4가지 화면으로 구성됩니다:

    **1. Trace 목록 (Projects 탭)**
    전체 실행 목록이 시간순으로 나열됩니다. 성공/실패 필터, 기간 필터, Feedback 점수 필터를 사용해 원하는 실행만 골라볼 수 있습니다. 각 행에는 실행 시간, 총 토큰, 지연 시간이 표시됩니다.

    **2. Trace 상세 (개별 Trace 클릭)**
    하나의 Trace를 클릭하면 각 노드의 입출력, 토큰 수, 지연 시간, 비용이 상세하게 표시됩니다. 프롬프트 전문과 LLM 응답 전문을 그대로 볼 수 있어 디버깅에 핵심적입니다.

    **3. Run Tree (트리 뷰)**
    부모-자식 관계로 실행 흐름을 시각화합니다. 어떤 노드가 어떤 순서로 실행되었는지, 재시도가 몇 번 발생했는지를 한눈에 파악할 수 있습니다. 각 Run의 시간 비율이 바 형태로 표시되어 병목을 바로 찾을 수 있습니다.

    **4. Analytics (통계 탭)**
    전체 프로젝트의 총 토큰 사용량, 평균 지연 시간, 비용 추이를 시계열 그래프로 보여줍니다. 일별/주별 추이를 확인하여 비용 관리와 성능 모니터링에 활용합니다.

### LangSmith UI에서 볼 수 있는 것 요약

| 화면 | 정보 |
|---|---|
| **Trace 목록** | 전체 실행 목록, 성공/실패 필터, 시간순 정렬 |
| **Trace 상세** | 각 노드의 입출력, 토큰, 지연, 비용 |
| **Run Tree** | 부모-자식 관계로 실행 흐름 시각화 |
| **Feedback** | 성공/실패 태깅, 점수 부여 |
| **Datasets** | 평가용 입력-기대출력 쌍 관리 |
| **Analytics** | 전체 통계 -- 총 토큰, 평균 지연, 비용 추이 |

!!! warning "무료 플랜 월 5,000 트레이스 제한"
    LangSmith 개인 무료 플랜은 **월 5,000 트레이스**까지 사용할 수 있습니다. 수업 중 실습으로는 충분하지만, 프로덕션 환경에서는 유료 플랜을 고려해야 합니다. 트레이스 수가 한도에 가까워지면 LangSmith 대시보드의 Usage 탭에서 확인할 수 있습니다. 또한 LangSmith 서버에 실행 데이터가 저장되므로, 민감한 의료 데이터 등을 다룰 때는 개인정보 마스킹에 주의하세요.

---

## 실습 1 -- LangSmith 환경변수 설정

### 부트스트랩

```python
!pip install -q \
    "langgraph>=0.2.20" "langchain>=0.3.0" "langchain-openai>=0.2.0" \
    "langsmith>=0.1.70,<0.2" \
    "ragas>=0.1.17,<0.2" datasets \
    sqlalchemy psycopg2-binary pandas tabulate matplotlib \
    "openai>=1.30" sqlparse

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"]     = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]           = userdata.get("NEON_DSN")
# 2024+ 표준 env var 이름. 구버전 LANGCHAIN_* 는 deprecated
os.environ["LANGSMITH_TRACING"]  = "true"
os.environ["LANGSMITH_API_KEY"]  = userdata.get("LANGSMITH_KEY")
os.environ["LANGSMITH_PROJECT"]  = "sql-agent-final"

from sqlalchemy import create_engine, text
import pandas as pd
engine = create_engine(
    os.environ["NEON_DSN"],       # 반드시 ?sslmode=require 포함
    pool_pre_ping=True,
    pool_recycle=300,
)
```

!!! warning "env var 이름에 주의"
    `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` 는 **deprecated**.
    최신 `langsmith` SDK(0.1.70+)는 `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` 를 읽습니다. 두 이름은 당분간 호환되지만 새 프로젝트는 `LANGSMITH_*` 를 기본으로 쓰세요.

### LangSmith 환경변수 확인

```python
# ============================================================
# 1. LangSmith 환경변수 설정 확인
# ============================================================

# 이미 부트스트랩에서 설정됨. 확인:
print(f"LANGSMITH_TRACING: {os.environ.get('LANGSMITH_TRACING')}")
print(f"LANGSMITH_PROJECT: {os.environ.get('LANGSMITH_PROJECT')}")
print(f"LANGSMITH_API_KEY: {'설정됨' if os.environ.get('LANGSMITH_API_KEY') else '미설정'}")
```

!!! note "핵심 정리"
    환경변수 3개만 설정하면 LangSmith 트레이싱이 **자동으로** 활성화됩니다:

    - `LANGSMITH_TRACING` = `"true"` -- 트레이싱 ON
    - `LANGSMITH_API_KEY` = LangSmith API 키
    - `LANGSMITH_PROJECT` = 프로젝트 이름 (트레이스 그룹)

### LangSmith Client 생성 + 프로젝트 확인

```python
# LangSmith 클라이언트
from langsmith import Client
ls_client = Client()

# 프로젝트 확인
print(f"\n현재 프로젝트: {os.environ['LANGSMITH_PROJECT']}")
```

---

## 실습 2 -- Day 3 에이전트 재구성 + 트레이싱

Day 3에서 만든 SQL 에이전트를 다시 구성합니다. 환경변수 설정만으로 모든 실행이 자동으로 LangSmith에 기록됩니다.

### 스키마 수집 함수

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
        fk_lines = [f"    FK ({', '.join(fk['constrained_columns'])}) -> {fk['referred_table']}" for fk in fks]
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
print(f"스키마 수집 완료: {len(TABLES)}개 테이블")
```

### AgentState + 가드레일

```python
# 상태 정의
class AgentState(TypedDict):
    question: str
    sql: str
    sql_result: str
    error: str
    answer: str
    attempts: int

# 가드레일 — 위험 키워드 차단
BLOCKED = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE)

def sanitize_sql(sql):
    m = BLOCKED.search(sql)
    if m:
        return "", f"보안 위반: '{m.group()}'"
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    return sql, ""
```

### 노드 함수들

```python
# SQL 생성 노드
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

# SQL 실행 노드
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

# 검증 노드
def validate(state: AgentState) -> dict:
    if state.get("error"):
        return state
    return {"error": ""}

# 답변 생성 노드
def answer(state: AgentState) -> dict:
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}
    prompt = ChatPromptTemplate.from_template(
        "결과를 한국어로 요약. 숫자 천 단위 구분.\n\n질문: {q}\nSQL: {sql}\n결과:\n{r}\n\n답변:"
    )
    chain = prompt | llm | StrOutputParser()
    ans = chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})
    return {"answer": ans}

# 재시도 판단
def should_retry(state: AgentState) -> str:
    if not state.get("error"):
        return "answer"
    if state.get("attempts", 0) >= 3:
        return "answer"
    return "generate_sql"
```

### 그래프 조립

```python
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
print("에이전트 컴파일 완료 -- LangSmith 트레이싱 활성화됨!")
```

---

## 실습 3 -- 10개 질문 실행 + 트레이스 확인

모든 실행이 LangSmith에 자동으로 기록됩니다. 실행 후 LangSmith UI에서 트레이스를 확인하세요.

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
    status = "O" if result.get("answer") and "죄송" not in result.get("answer", "") else "X"
    results.append({
        "question": q,
        "status": status,
        "attempts": result.get("attempts", 0),
        "sql": result.get("sql", ""),
        "answer": result.get("answer", ""),
        "sql_result": result.get("sql_result", ""),
    })
    print(f"  {status} (시도 {result.get('attempts',0)}회) -- {result.get('answer','')[:60]}...")

# 요약
df_results = pd.DataFrame(results)
success = len(df_results[df_results["status"] == "O"])
print(f"\n정답률: {success}/{len(questions)} ({success/len(questions)*100:.0f}%)")
print(f"\nLangSmith에서 확인: https://smith.langchain.com/")
print(f"   프로젝트: {os.environ['LANGSMITH_PROJECT']}")
```

---

## 실습 4 -- LangSmith API로 트레이스 분석

### 토큰/비용/지연 분석

```python
# ============================================================
# 4. LangSmith API로 트레이스 분석
# ============================================================
from langsmith import Client
import matplotlib.pyplot as plt

ls = Client()

# 최근 실행 가져오기 — root run만 (is_root=True 가 최신 SDK 표준)
runs = list(ls.list_runs(
    project_name=os.environ["LANGSMITH_PROJECT"],
    is_root=True,
    limit=10,
))

print(f"최근 {len(runs)}개 트레이스 분석:\n")

def _token_usage(run):
    """LangSmith run에서 토큰 사용량을 방어적으로 추출.

    최신 SDK는 `run.total_tokens` 등 상위 속성이 None인 경우가 많음.
    우선 최상위 필드를 보고, 없으면 `run.extra['runtime']['token_usage']`
    또는 `run.outputs['llm_output']['token_usage']` 를 차례로 확인한다.
    """
    total = getattr(run, "total_tokens", None)
    prompt = getattr(run, "prompt_tokens", None)
    completion = getattr(run, "completion_tokens", None)
    if not total:
        extra = (run.extra or {}).get("runtime", {}).get("token_usage", {}) or {}
        prompt = prompt or extra.get("prompt_tokens", 0)
        completion = completion or extra.get("completion_tokens", 0)
        total = extra.get("total_tokens", (prompt or 0) + (completion or 0))
    return (total or 0), (prompt or 0), (completion or 0)

trace_stats = []
for run in runs:
    total_tokens, prompt_tokens, completion_tokens = _token_usage(run)
    latency = (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else 0

    # 비용 추정 (gpt-4o-mini 기준)
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

print(f"\n합계:")
print(f"  총 토큰: {df_traces['tokens'].sum():,}")
print(f"  평균 지연: {df_traces['latency_s'].mean():.2f}초")
print(f"  총 비용: ${df_traces['cost_usd'].sum():.4f}")
```

!!! note "핵심 정리"
    `list_runs()`의 `is_root=True` 옵션은 **root run만** 가져옵니다 (`langsmith>=0.1.70`). 이는 하위 노드 Run이 아닌, 에이전트 전체 실행 단위의 Trace를 의미합니다. 개별 노드의 세부 정보는 LangSmith UI의 Run Tree에서 확인하거나, `is_root` 를 생략하여 모든 Run을 가져올 수 있습니다.

!!! warning "토큰/비용이 0으로만 찍힌다면"
    최신 SDK에서 `run.total_tokens` / `run.prompt_tokens` 등 최상위 속성은 많은 경우 `None` 입니다. 위 `_token_usage()` 처럼 `run.extra["runtime"]["token_usage"]` 로 폴백하거나, LangSmith UI의 **Analytics** 탭에서 프로젝트 단위 집계로 확인하는 편이 더 안정적입니다.

### 시각화 -- 질문별 토큰/지연 2-패널 차트

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
print("차트 저장: langsmith_stats.png")
```

!!! example "실습 -- 가장 느린 질문의 트레이스 열어 병목 찾기"
    1. 위 차트에서 **지연 시간이 가장 긴 질문**을 확인합니다.
    2. LangSmith UI (https://smith.langchain.com/) 에 접속합니다.
    3. 프로젝트 `sql-agent-final`을 클릭합니다.
    4. 해당 질문의 Trace를 클릭하여 **Run Tree**를 엽니다.
    5. 각 노드(generate_sql, run_sql, validate, answer)의 소요 시간을 비교합니다.
    6. **병목 노드**를 찾으세요:
        - `generate_sql`이 느리면: 프롬프트가 너무 길거나, 스키마 정보가 과다한 것
        - `run_sql`이 느리면: SQL 쿼리가 비효율적이거나, 데이터베이스 인덱스 부족
        - `answer`가 느리면: 결과 데이터가 너무 많아 요약에 시간이 걸린 것
        - **재시도(retry)**가 발생했다면: generate_sql이 여러 번 호출된 것이 원인
    7. 병목 원인과 개선 아이디어를 메모하세요 -- 발표에서 활용할 수 있습니다.

---

## 실습 5 -- 평가용 Dataset 생성

LangSmith Dataset은 질문(input)과 기대 답변(output)의 쌍입니다. 22H Ragas 평가에서 ground truth로 사용됩니다.

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

print(f"Dataset '{dataset_name}' 생성 완료 ({len(ground_truths)}개 예시)")
```

!!! tip "Dataset 활용 팁"
    Dataset은 단순히 저장만 하는 것이 아닙니다. LangSmith UI에서:

    - **Datasets 탭**에서 생성한 데이터셋을 확인할 수 있습니다.
    - 각 Example을 클릭하면 입력(질문)과 기대 출력(ground truth)을 편집할 수 있습니다.
    - **Evaluator**를 연결하면 에이전트를 Dataset 전체에 대해 자동으로 평가할 수 있습니다.
    - 본인 프로젝트에서는 **본인 도메인의 질문 10개**로 Dataset을 만드세요.

---

## 실습 6 -- Feedback 태깅

실행 결과에 정답/오답 태그를 붙여 LangSmith에서 필터링하고 분석할 수 있습니다.

```python
# ============================================================
# 7. 실행 결과에 Feedback(태깅) 부여
# ============================================================

# 최근 실행에 대해 정답/오답 태깅
# ⚠️ list_runs()는 기본적으로 최신→과거 역순입니다.
#    results(질문 순서)와 그냥 zip하면 엉뚱한 run에 feedback이 붙습니다.
#    반드시 start_time 오름차순으로 정렬하거나, 질문 문자열로 매칭하세요.
runs = list(ls.list_runs(
    project_name=os.environ["LANGSMITH_PROJECT"],
    is_root=True,
    limit=len(results),
))
runs_sorted = sorted(runs, key=lambda r: r.start_time)  # 오래된 순 → 질문 순서와 일치

# 더 안전한 매칭: 질문 문자열로 run을 찾는다
runs_by_question = {
    (r.inputs or {}).get("question"): r for r in runs_sorted
}

for res in results:
    run = runs_by_question.get(res["question"])
    if run is None:
        print(f"  (건너뜀) 매칭되는 run 없음: {res['question'][:30]}...")
        continue
    score = 1.0 if res["status"] == "O" else 0.0
    ls.create_feedback(
        run_id=run.id,
        key="correctness",
        score=score,
        comment=f"질문: {res['question'][:30]}... -> {res['status']}",
    )
    print(f"  Feedback: {res['question'][:30]}... -> score={score}")

print(f"\n{len(runs_by_question)}개 실행에 Feedback 부여 완료!")
print("   LangSmith UI에서 Feedback 필터로 실패 케이스를 빠르게 확인하세요.")
```

!!! tip "Feedback 활용법"
    Feedback을 부여하면 LangSmith UI에서 강력한 필터링이 가능합니다:

    - **Feedback 탭**에서 `correctness` 키로 필터링
    - `score=0` (실패)만 골라서 원인 분석
    - 시간대별 성공률 추이 확인
    - 특정 질문 유형별 성공률 비교

    프로덕션 환경에서는 사용자 피드백(좋아요/싫어요)을 `create_feedback`으로 기록하여 지속적인 품질 모니터링에 활용합니다.

---

## 실습 과제

!!! example "실습"
    1. **본인 에이전트에 LangSmith 트레이싱을 연결**하고 10개 질문을 실행하세요.
    2. LangSmith UI에서 **가장 느린 질문의 트레이스를 열어 병목 노드를 찾으세요**.
        - 어떤 노드가 가장 오래 걸렸나요?
        - 재시도(retry)가 발생했나요?
    3. **평가용 Dataset을 본인 질문 10개로 생성**하세요.
    4. (도전) Feedback으로 정답/오답을 태깅하고, LangSmith UI에서 실패 케이스만 필터링해보세요.

!!! question "생각해보기"
    - LangSmith 트레이싱 없이 에이전트를 디버깅하려면 어떻게 해야 할까요? print 문을 곳곳에 넣는 방법과 비교하면 어떤 장점이 있나요?
    - 토큰 사용량이 가장 많은 질문과 가장 적은 질문의 차이는 무엇인가요? 어떤 유형의 질문이 토큰을 많이 소비하나요?
    - 프로덕션 환경에서 LangSmith를 사용할 때, 민감한 데이터(환자 정보 등)를 어떻게 처리해야 할까요?

---

!!! note "핵심 정리"
    - **LangSmith** = LLM 앱의 관측 도구. 환경변수 3줄 설정으로 자동 트레이싱
    - **Run/Trace 구조**로 각 노드의 입출력, 토큰, 지연, 비용을 상세히 확인
    - `list_runs()` API로 프로그래밍 방식으로 트레이스 데이터 분석 가능
    - **matplotlib 시각화**로 질문별 토큰/지연 패턴을 한눈에 파악
    - **Dataset** = 평가용 질문+정답 모음 -- 22H Ragas에서 ground truth로 사용
    - **Feedback** = 실행 결과에 태그를 부여하여 성공/실패 필터링 및 품질 추적
