# Day 2 — 제안서 회수 + Text-to-SQL 상담사 (9~12H)

> 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> 실행 환경: Google Colab + Neon PostgreSQL + OpenAI API

---

## 공통 부트스트랩

```python
!pip install -q \
    llama-index llama-index-llms-openai llama-index-embeddings-openai \
    sqlalchemy psycopg2-binary pandas tabulate gradio \
    openai sqlparse

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text, inspect
import pandas as pd

engine = create_engine(os.environ["NEON_DSN"])
```

---

# 9H · 제안서 피어리뷰

## 학습목표

- 프로젝트 제안서를 구조적으로 평가할 수 있다.
- 피어리뷰를 통해 본인 제안서의 약점을 식별하고 개선할 수 있다.
- AI-friendly 스키마의 기준을 실제 제안서에 적용할 수 있다.

## 이론 — 좋은 제안서의 조건

### 피어리뷰 체크리스트

| 항목 | 확인 내용 | 배점 |
|---|---|---|
| 도메인 적절성 | 3~5 테이블로 표현 가능한 범위인가? | 10 |
| 테이블 설계 | PK/FK 명시, 적절한 데이터 타입 | 20 |
| COMMENT ON | 모든 컬럼에 자연어 설명이 있는가? | 20 |
| 질문 난이도 분포 | Easy 3~4 / Medium 3~4 / Hard 2~3 | 20 |
| 기대 SQL | 각 질문에 구체적인 SQL이 있는가? | 20 |
| ERD | 테이블 간 관계가 시각화되었는가? | 10 |

### 흔한 문제 패턴과 해결 방법

```
문제 1: "테이블이 너무 많다" (8개 이상)
  → 해결: 핵심 3~5개로 축소. 나머지는 리포팅 뷰로 대체.
  → 이유: 테이블이 많으면 LLM이 관련 테이블 선택에서 실패.

문제 2: "질문이 모두 같은 난이도"
  → 해결: Hard 질문 추가 — 윈도우 함수, 다중 CTE, 자기 참조 필요
  → 이유: 에이전트 성능을 다양한 각도에서 검증해야 함.

문제 3: "컬럼명이 약어"
  → 해결: ord_dt → order_date, cust_nm → customer_name
  → 이유: LLM은 full name을 보고 의미를 파악. 약어는 오역의 원인.

문제 4: "FK 없이 암묵적 관계"
  → 해결: FOREIGN KEY 제약 조건 명시
  → 이유: LLM이 JOIN 경로를 FK에서 추론. 없으면 잘못된 JOIN 생성.

문제 5: "기대 SQL이 없거나 부정확"
  → 해결: 실제 실행 가능한 SQL을 작성하고 결과 행 수 기재
  → 이유: 에이전트 출력과 비교할 ground truth가 필요.
```

### 좋은 제안서 vs 나쁜 제안서 예시

**나쁜 제안서:**

```sql
CREATE TABLE ord (
    id INT PRIMARY KEY,
    cust INT,
    dt DATE,
    amt DECIMAL
);
-- COMMENT 없음, FK 없음, 컬럼명 약어
```

```
Q1: 주문 수는? → SELECT COUNT(*) FROM ord;
Q2: 고객 수는? → SELECT COUNT(DISTINCT cust) FROM ord;
Q3: 총 매출은? → SELECT SUM(amt) FROM ord;
-- 모두 Easy, 테이블 1개만 사용
```

**좋은 제안서:**

```sql
CREATE TABLE orders (
    order_id    SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    order_date  DATE NOT NULL,
    status      VARCHAR(20) CHECK (status IN ('pending','shipped','delivered','cancelled')),
    total_amount NUMERIC(12,2) NOT NULL
);
COMMENT ON TABLE orders IS '고객 주문 정보';
COMMENT ON COLUMN orders.status IS '주문 상태: pending=처리중, shipped=배송중, delivered=배송완료, cancelled=취소';
COMMENT ON COLUMN orders.total_amount IS '주문 총액 (원, VAT 포함)';
```

```
[Easy] Q1: "이번 달 총 주문 건수는?"
SQL: SELECT COUNT(*) FROM orders WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE);

[Medium] Q5: "카테고리별 월 매출 추이를 보여주세요."
SQL:
  SELECT c.category_name, TO_CHAR(o.order_date, 'YYYY-MM') AS month,
         SUM(oi.quantity * oi.unit_price) AS revenue
  FROM order_items oi
  JOIN products p ON p.product_id = oi.product_id
  JOIN categories c ON c.category_id = p.category_id
  JOIN orders o ON o.order_id = oi.order_id
  WHERE o.status = 'delivered'
  GROUP BY c.category_name, month
  ORDER BY month, revenue DESC;

[Hard] Q9: "재구매율이 가장 높은 상위 3개 제품은?"
SQL:
  WITH purchase_counts AS (
      SELECT oi.product_id, COUNT(DISTINCT o.customer_id) AS buyers,
             COUNT(DISTINCT CASE WHEN ... END) AS repeat_buyers
      FROM ...
  )
  SELECT p.product_name, pc.repeat_buyers * 100.0 / pc.buyers AS repeat_rate
  FROM purchase_counts pc
  JOIN products p ON p.product_id = pc.product_id
  ORDER BY repeat_rate DESC LIMIT 3;
```

## 핵심 코드 — 스키마 자동 검증 도구

```python
# ============================================================
# 제안서 스키마 자동 검증기
# ============================================================
# 학생들이 자기 스키마를 검증하는 데 사용

def validate_schema(engine, table_names: list[str]) -> dict:
    """스키마의 AI-friendliness를 자동 점검"""
    inspector = inspect(engine)
    report = {"tables": {}, "score": 0, "issues": []}
    total_points = 0
    earned_points = 0
    
    for table in table_names:
        table_report = {"columns": 0, "comments": 0, "fks": 0, "pk": False}
        
        # 컬럼 확인
        columns = inspector.get_columns(table)
        table_report["columns"] = len(columns)
        total_points += len(columns)  # 각 컬럼에 COMMENT 있어야 함
        
        # PK 확인
        pk = inspector.get_pk_constraint(table)
        if pk and pk["constrained_columns"]:
            table_report["pk"] = True
            earned_points += 5
        else:
            report["issues"].append(f"⚠️ {table}: PRIMARY KEY 없음")
        total_points += 5
        
        # FK 확인
        fks = inspector.get_foreign_keys(table)
        table_report["fks"] = len(fks)
        
        # COMMENT 확인
        with engine.connect() as conn:
            comments = conn.execute(text(f"""
                SELECT column_name, 
                       col_description('{table}'::regclass, ordinal_position) AS comment
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)).fetchall()
        
        for col_name, comment in comments:
            if comment:
                table_report["comments"] += 1
                earned_points += 1
            else:
                report["issues"].append(f"⚠️ {table}.{col_name}: COMMENT 없음")
        
        # 컬럼명 약어 검사
        short_names = [col["name"] for col in columns if len(col["name"]) <= 3 and col["name"] not in ("id",)]
        if short_names:
            report["issues"].append(
                f"⚠️ {table}: 짧은 컬럼명 발견 {short_names} — 명시적 이름 사용 권장"
            )
        
        report["tables"][table] = table_report
    
    report["score"] = round(earned_points / max(total_points, 1) * 100, 1)
    return report

# 사용 예시
report = validate_schema(engine, ["patients", "doctors", "visits", "diagnoses", "departments"])

print(f"📊 스키마 검증 결과: {report['score']}점 / 100점\n")

for table, info in report["tables"].items():
    pk_icon = "✅" if info["pk"] else "❌"
    comment_ratio = f"{info['comments']}/{info['columns']}"
    print(f"  {table}: PK {pk_icon} | FK {info['fks']}개 | COMMENT {comment_ratio}")

if report["issues"]:
    print(f"\n⚠️ 개선 필요 ({len(report['issues'])}건):")
    for issue in report["issues"][:10]:
        print(f"  {issue}")
```

## 실습 활동 — 피어리뷰 진행

### 진행 순서 (30분)

1. **조 편성** — 3인 1조 (5분)
2. **돌아가며 발표** — 각자 10분:
   - 도메인 소개 (2분)
   - 스키마 설명 (3분)
   - 질문 10개 중 대표 5개 (3분)
   - 피드백 (2분)
3. **스키마 검증기 실행** — 본인 스키마에 대해 `validate_schema()` 실행 (5분)
4. **개선 메모** — 피드백 반영 계획 정리 (5분)

### 피어리뷰 피드백 양식

```markdown
## 피어리뷰 피드백

**발표자:** _______________
**리뷰어:** _______________

### 잘된 점
- 

### 개선이 필요한 점
- 

### 질문 난이도 체크
- Easy: ___개  Medium: ___개  Hard: ___개
- 적절한가? (Y/N): ___

### COMMENT ON 완성도
- 전체 컬럼 수: ___개
- COMMENT 있는 컬럼: ___개
```

## 강사 노트

- **시간 배분**: 체크리스트 설명 10분 → 좋은/나쁜 예시 5분 → 피어리뷰 30분 → 강사 순회 피드백 5분
- 제안서를 제출하지 못한 학생이 있을 수 있음 → 이 시간 동안 작성하게 하고, 피어리뷰는 다른 조원 것을 먼저 리뷰
- 강사가 각 조를 돌며 3분씩 피드백 → "테이블 줄여라", "COMMENT 추가해라", "Hard 질문 넣어라" 위주
- **자주 묻는 질문**: "ERD를 꼭 그려야 하나요?" → "필수는 아니지만 관계를 명확히 이해하는 데 도움됩니다. Mermaid로 5분이면 됩니다."

---

# 10H · NLSQLTableQueryEngine 심화

## 학습목표

- `NLSQLTableQueryEngine`의 내부 프롬프트 구조를 분석할 수 있다.
- `table_info` 수동 주입, few-shot 예제, 테이블 선택 전략으로 정확도를 개선할 수 있다.
- 커스텀 프롬프트 템플릿을 작성하여 LLM의 SQL 생성 품질을 높일 수 있다.

## 이론 — 왜 기본 설정으로는 부족한가?

### NLSQLTableQueryEngine의 한계

Day 1 7H에서 경험한 실패 원인:

```
1. 스키마 정보 부족 — COMMENT가 없거나 부족하면 LLM이 컬럼 의미를 오해
2. 프롬프트 품질 — 기본 프롬프트가 한국어 질문에 최적화되지 않음
3. 테이블 선택 오류 — 테이블이 많을 때 관련 없는 테이블을 프롬프트에 포함
4. 컨텍스트 부족 — 도메인 특수 용어를 LLM이 모름 (예: "본태성 고혈압" = I10)
```

### 개선 전략 3가지

```
전략 1: table_info 보강    → 스키마에 자연어 설명 추가
전략 2: few-shot 주입      → 예시 (질문, SQL) 쌍으로 패턴 학습
전략 3: 테이블 선택 자동화  → ObjectIndex로 관련 테이블만 필터
```

## 핵심 코드 — `08_text_to_sql_advanced.ipynb`

### 1. 내부 프롬프트 분석

```python
# ============================================================
# 1. 내부 프롬프트 뜯어보기
# ============================================================
from llama_index.core import SQLDatabase, Settings
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

sql_db = SQLDatabase(
    engine,
    include_tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)

nlq = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)

# 내부 프롬프트 확인
prompts = nlq.get_prompts()
print("📋 사용 중인 프롬프트 키:")
for key in prompts:
    print(f"  - {key}")

# text_to_sql_prompt 내용 전체 출력
print(f"\n{'='*60}")
print("📝 text_to_sql_prompt:")
print(f"{'='*60}")
print(prompts["text_to_sql_prompt"].template)
```

```python
# 프롬프트에서 {schema}가 어떻게 채워지는지 확인
print(f"\n{'='*60}")
print("📋 LLM에 전달되는 schema (table_info):")
print(f"{'='*60}")
for table in sql_db.get_usable_table_names():
    info = sql_db.get_single_table_info(table)
    print(f"\n--- {table} ---")
    print(info)
```

### 2. 전략 1 — table_info 보강

```python
# ============================================================
# 2. 전략 1: 컨텍스트 문자열로 도메인 지식 주입
# ============================================================

# 도메인 특수 지식을 context_str_prefix로 주입
context_info = """
## 도메인 설명
이 데이터베이스는 종합병원의 진료 기록 시스템입니다.

## 주요 비즈니스 규칙
- visits.visit_type: 'outpatient'=외래, 'inpatient'=입원, 'emergency'=응급
- visits.status: 'completed'=완료된 진료만 집계 대상 (cancelled, no_show 제외)
- visits.cost: 원(KRW) 단위, NULL이면 미청구
- diagnoses.severity: 'mild'=경증, 'moderate'=중등, 'severe'=중증
- patients.gender: 'M'=남성, 'F'=여성
- 나이 계산: EXTRACT(YEAR FROM AGE(birth_date))

## 자주 사용되는 패턴
- "지난달" = WHERE visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                AND visit_date < DATE_TRUNC('month', CURRENT_DATE)
- "올해" = WHERE EXTRACT(YEAR FROM visit_date) = EXTRACT(YEAR FROM CURRENT_DATE)
- "재방문" = 같은 patient_id로 2건 이상의 visits 레코드
"""

nlq_enhanced = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    text_to_sql_prompt=None,  # 아래에서 커스텀 프롬프트 사용
)
```

### 3. 전략 2 — 커스텀 프롬프트 + Few-shot

```python
# ============================================================
# 3. 전략 2: 커스텀 프롬프트 + Few-shot 예제
# ============================================================
from llama_index.core.prompts import PromptTemplate

custom_text_to_sql_prompt = PromptTemplate(
    """당신은 PostgreSQL 전문가입니다. 아래 스키마와 규칙을 참고하여 질문에 정확한 SQL을 작성하세요.

## 데이터베이스 스키마
{schema}

## 도메인 규칙
- visits.status가 'completed'인 것만 유효한 진료입니다.
- 비용(cost)이 NULL이거나 0인 것은 취소/미방문입니다.
- 나이 계산: EXTRACT(YEAR FROM AGE(birth_date))
- 날짜 필터: PostgreSQL 함수 사용 (DATE_TRUNC, INTERVAL 등)
- 결과는 의미 있는 별칭(AS)을 사용하세요.

## 예시

질문: "전체 환자 수는?"
SQL: SELECT COUNT(*) AS total_patients FROM patients;

질문: "내과 의사 목록을 보여줘"
SQL: SELECT d.name AS doctor_name, d.specialty
     FROM doctors d
     JOIN departments dept ON dept.department_id = d.department_id
     WHERE dept.name = '내과';

질문: "지난달 완료된 진료 건수는?"
SQL: SELECT COUNT(*) AS completed_visits
     FROM visits
     WHERE status = 'completed'
       AND visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
       AND visit_date < DATE_TRUNC('month', CURRENT_DATE);

## 지시사항
- SELECT 문만 작성하세요 (DML/DDL 금지).
- SQL만 반환하세요 (설명 불필요).
- 한국어 질문의 의도를 정확히 파악하세요.

## 질문
{query_str}

## SQL
"""
)

nlq_custom = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    text_to_sql_prompt=custom_text_to_sql_prompt,
)
```

```python
# ============================================================
# 4. Before/After 비교 실험
# ============================================================

test_questions = [
    "지난달 방문 환자 수는?",
    "진료과별 평균 진료비를 보여주세요.",
    "가장 많이 진단된 질병 Top 5는?",
    "40세 이상 남성 환자 중 3회 이상 방문한 사람은?",
    "최근에 많이 온 사람은?",  # 모호한 질문
]

print("📊 기본 NLSQLTableQueryEngine vs 커스텀 프롬프트 비교\n")
print(f"{'질문':<40} {'기본':^10} {'커스텀':^10}")
print("-" * 60)

for q in test_questions:
    # 기본 버전
    try:
        resp_basic = nlq.query(q)
        basic_status = "✅"
    except:
        basic_status = "❌"
    
    # 커스텀 버전
    try:
        resp_custom = nlq_custom.query(q)
        custom_status = "✅"
    except:
        custom_status = "❌"
    
    print(f"{q:<40} {basic_status:^10} {custom_status:^10}")
```

```python
# 상세 비교 — 특정 질문의 SQL 비교
question = "진료과별 평균 진료비를 보여주세요."

print(f"❓ 질문: {question}\n")

resp_basic = nlq.query(question)
print(f"📝 기본 SQL:\n{resp_basic.metadata['sql_query']}\n")

resp_custom = nlq_custom.query(question)
print(f"📝 커스텀 SQL:\n{resp_custom.metadata['sql_query']}\n")

print(f"💬 기본 답변: {resp_basic.response[:100]}...")
print(f"💬 커스텀 답변: {resp_custom.response[:100]}...")
```

### 4. 전략 3 — 테이블 자동 선택

```python
# ============================================================
# 5. 전략 3: ObjectIndex로 관련 테이블만 자동 선택
# ============================================================
from llama_index.core.objects import (
    SQLTableNodeMapping,
    ObjectIndex,
    SQLTableSchema,
)

# 각 테이블에 자연어 설명 부여
table_schemas = [
    SQLTableSchema(
        table_name="patients",
        context_str="환자 기본 정보. 이름, 생년월일, 성별, 혈액형 등."
    ),
    SQLTableSchema(
        table_name="doctors",
        context_str="의사 정보. 이름, 소속 진료과, 전공, 급여 등."
    ),
    SQLTableSchema(
        table_name="visits",
        context_str="환자의 진료 방문 기록. 방문일, 진료 유형(외래/입원/응급), 상태, 진료비."
    ),
    SQLTableSchema(
        table_name="diagnoses",
        context_str="진료 시 내려진 진단 기록. ICD-10 코드, 진단명, 중증도."
    ),
    SQLTableSchema(
        table_name="departments",
        context_str="병원 진료과 정보. 진료과명, 위치(층), 전화번호."
    ),
]

# 테이블 노드 매핑
table_node_mapping = SQLTableNodeMapping(sql_db)

# ObjectIndex: 질문에 관련된 테이블을 벡터 검색으로 자동 선택
obj_index = ObjectIndex.from_objects(
    table_schemas,
    table_node_mapping,
    index_cls=None,  # default VectorStoreIndex
)

# ObjectIndex 기반 Query Engine
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine

nlq_auto = SQLTableRetrieverQueryEngine(
    sql_database=sql_db,
    table_retriever=obj_index.as_retriever(similarity_top_k=3),
    text_to_sql_prompt=custom_text_to_sql_prompt,
)

# 테스트
response = nlq_auto.query("가장 많이 진단된 질병 Top 5는?")
print(f"💬 답변: {response.response}")
print(f"📝 SQL: {response.metadata['sql_query']}")
# diagnoses 테이블이 자동으로 선택되었는지 확인
```

### 5. 프롬프트 실험 워크시트

```python
# ============================================================
# 6. 프롬프트 실험 워크시트
# ============================================================

def experiment(question: str, prompt_template: PromptTemplate, label: str = ""):
    """프롬프트 실험 — SQL 생성 결과와 정확도 확인"""
    try:
        engine_exp = NLSQLTableQueryEngine(
            sql_database=sql_db,
            tables=["patients", "doctors", "visits", "diagnoses", "departments"],
            text_to_sql_prompt=prompt_template,
        )
        resp = engine_exp.query(question)
        print(f"\n🔬 [{label}] {question}")
        print(f"   SQL: {resp.metadata['sql_query']}")
        print(f"   답변: {resp.response[:150]}")
        return resp
    except Exception as e:
        print(f"\n🔬 [{label}] {question}")
        print(f"   ❌ 에러: {str(e)[:100]}")
        return None

# 실험: "최근에 많이 온 사람"이라는 모호한 질문을 다양한 프롬프트로 시도

# 프롬프트 A: 기본
prompt_a = PromptTemplate(
    "Given the schema:\n{schema}\n\nWrite SQL for: {query_str}\n\nSQL:"
)

# 프롬프트 B: 모호성 처리 규칙 추가
prompt_b = PromptTemplate(
    """PostgreSQL 전문가로서 다음 규칙을 따르세요:
{schema}

## 모호성 처리 규칙
- "최근" = 최근 3개월
- "많이" = 3회 이상
- "자주" = 월 평균 2회 이상
- visits.status = 'completed'만 유효

질문: {query_str}
SQL:"""
)

# 프롬프트 C: few-shot + 모호성 규칙
prompt_c = PromptTemplate(
    """PostgreSQL 전문가입니다.
{schema}

## 규칙
- "최근" = 최근 3개월, "많이" = 3회 이상
- completed 상태만 유효한 진료

## 예시
Q: "최근에 자주 온 환자는?"
SQL: SELECT p.name, COUNT(*) AS visit_count
     FROM visits v JOIN patients p ON p.patient_id = v.patient_id
     WHERE v.status = 'completed'
       AND v.visit_date >= CURRENT_DATE - INTERVAL '3 months'
     GROUP BY p.patient_id, p.name
     HAVING COUNT(*) >= 2
     ORDER BY visit_count DESC;

질문: {query_str}
SQL:"""
)

# 실험 실행
q = "최근에 많이 온 사람은?"
experiment(q, prompt_a, "A: 기본")
experiment(q, prompt_b, "B: 모호성 규칙")
experiment(q, prompt_c, "C: few-shot + 규칙")
```

## 실습 과제

1. Day 1에서 실패했던 질문 3개를 커스텀 프롬프트로 재시도하고 Before/After를 기록하세요.
2. 본인 도메인에 맞는 모호성 처리 규칙 3개를 작성하세요 (예: "최근"의 정의).
3. few-shot 예제를 2개 추가하고 정확도가 향상되는지 확인하세요.

## 강사 노트

- **시간 배분**: 프롬프트 분석 10분 → 3가지 전략 설명 10분 → Before/After 실험 15분 → 실습 10분 → 정리 5분
- `get_prompts()`의 출력이 학생들에게 "아하!" 순간을 줌 — LLM이 실제로 보는 것이 이거라는 깨달음
- 프롬프트 실험 워크시트는 Day 3 Vanna 자가학습의 예고편 — "수동으로 하던 것을 Vanna가 자동화"
- **핵심 메시지**: "프롬프트 엔지니어링이 곧 Text-to-SQL의 정확도"

---

# 11H · 병원 DB 멀티턴 상담사 설계

## 학습목표

- 멀티턴 대화에서 상태(히스토리)를 관리하는 방법을 구현할 수 있다.
- 이전 맥락을 참조하는 질문("그 중에서...")을 처리할 수 있다.
- SQL 보안 가드레일(위험 SQL 차단, 화이트리스트, LIMIT 주입)을 구현할 수 있다.

## 이론 — 멀티턴 대화의 도전

### 단발 질의 vs 멀티턴 대화

```
단발 질의 (Stateless):
  User: "남성 환자 수는?"
  Bot:  "남성 환자는 15명입니다."
  (끝 — 이전 대화 기억 없음)

멀티턴 대화 (Stateful):
  User: "남성 환자 수는?"
  Bot:  "남성 환자는 15명입니다."
  User: "그 중에 40세 이상은?"          ← "그 중" = 이전 조건 참조
  Bot:  "남성 환자 중 40세 이상은 7명입니다."
  User: "그 사람들의 최근 방문일을 보여줘"  ← "그 사람들" = 이전 결과 참조
  Bot:  "..."
```

### 상태 관리 모델

```python
from dataclasses import dataclass, field

@dataclass
class ChatState:
    """대화 상태를 관리하는 클래스"""
    history: list = field(default_factory=list)   # [(role, message), ...]
    last_sql: str | None = None                   # 마지막 실행 SQL
    last_result: str | None = None                # 마지막 결과
    
    def add_user(self, msg: str):
        self.history.append(("user", msg))
    
    def add_assistant(self, msg: str, sql: str = None, result: str = None):
        self.history.append(("assistant", msg))
        if sql:
            self.last_sql = sql
        if result:
            self.last_result = result
    
    def get_history_text(self, max_turns: int = 5) -> str:
        """최근 N턴의 대화를 텍스트로 변환"""
        recent = self.history[-(max_turns * 2):]
        lines = []
        for role, msg in recent:
            prefix = "사용자" if role == "user" else "시스템"
            lines.append(f"{prefix}: {msg}")
        return "\n".join(lines)
```

### 보안 가드레일

```
위협 유형              방어 전략
───────────────────    ─────────────────────────────────
DML 공격               DELETE/DROP/UPDATE/INSERT 키워드 차단
SQL 인젝션             파라미터 바인딩 사용
테이블 무단 접근        화이트리스트로 허용 테이블 제한
대량 조회              LIMIT 1000 자동 주입
시스템 정보 노출        information_schema 접근 차단
```

## 핵심 코드 — 병원 DB 멀티턴 상담사

```python
# ============================================================
# 1. SQL 보안 가드레일
# ============================================================
import re
import sqlparse

class SQLGuardrail:
    """SQL 보안 가드레일 — 위험한 쿼리를 사전 차단"""
    
    BLOCKED_KEYWORDS = re.compile(
        r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
        r"COPY|EXECUTE|DO|CALL)\b",
        re.IGNORECASE,
    )
    
    BLOCKED_PATTERNS = re.compile(
        r"(information_schema|pg_catalog|pg_stat|pg_roles|"
        r"--\s|/\*|\*/|;\s*DROP|;\s*DELETE)",
        re.IGNORECASE,
    )
    
    def __init__(self, allowed_tables: list[str], max_limit: int = 1000):
        self.allowed_tables = [t.lower() for t in allowed_tables]
        self.max_limit = max_limit
    
    def check(self, sql: str) -> tuple[bool, str]:
        """SQL을 검증. (통과 여부, 에러 메시지) 반환"""
        # 1. 위험 키워드 차단
        match = self.BLOCKED_KEYWORDS.search(sql)
        if match:
            return False, f"🚫 '{match.group()}' 명령은 허용되지 않습니다. SELECT만 사용 가능합니다."
        
        # 2. SQL 인젝션 패턴 차단
        match = self.BLOCKED_PATTERNS.search(sql)
        if match:
            return False, f"🚫 보안 위반이 감지되었습니다: '{match.group()[:30]}'"
        
        # 3. 허용 테이블만 사용했는지 확인
        parsed = sqlparse.parse(sql)
        for stmt in parsed:
            tokens_str = str(stmt).lower()
            # FROM 절에서 사용된 테이블 추출 (간이 방식)
            from_match = re.findall(r'\bfrom\s+(\w+)', tokens_str)
            join_match = re.findall(r'\bjoin\s+(\w+)', tokens_str)
            used_tables = set(from_match + join_match)
            
            for table in used_tables:
                if table not in self.allowed_tables and table not in ('select', 'where'):
                    return False, f"🚫 '{table}' 테이블에 대한 접근이 허용되지 않습니다."
        
        return True, ""
    
    def inject_limit(self, sql: str) -> str:
        """LIMIT 절이 없으면 자동으로 추가"""
        sql_upper = sql.upper().strip()
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip().rstrip(";")
            sql += f"\nLIMIT {self.max_limit};"
        return sql
    
    def sanitize(self, sql: str) -> tuple[str, str]:
        """검증 + LIMIT 주입. (정제된 SQL, 에러 메시지) 반환"""
        is_safe, error = self.check(sql)
        if not is_safe:
            return "", error
        return self.inject_limit(sql), ""

# 테스트
guardrail = SQLGuardrail(
    allowed_tables=["patients", "doctors", "visits", "diagnoses", "departments", "vw_visit_details"],
    max_limit=1000,
)

# 정상 쿼리
sql_ok, err = guardrail.sanitize("SELECT * FROM patients WHERE gender = 'M'")
print(f"✅ 정상: {sql_ok}")

# 위험 쿼리
_, err = guardrail.sanitize("DROP TABLE patients")
print(f"❌ 차단: {err}")

_, err = guardrail.sanitize("SELECT * FROM pg_roles")
print(f"❌ 차단: {err}")
```

```python
# ============================================================
# 2. 멀티턴 상담사 핵심 로직
# ============================================================
from openai import OpenAI as OpenAIClient

oai = OpenAIClient()

class HospitalChatbot:
    """병원 DB 멀티턴 상담사"""
    
    def __init__(self, engine, schema_info: str):
        self.engine = engine
        self.schema_info = schema_info
        self.state = ChatState()
        self.guardrail = SQLGuardrail(
            allowed_tables=["patients", "doctors", "visits", "diagnoses", 
                          "departments", "vw_visit_details"],
        )
    
    def _generate_sql(self, question: str) -> str:
        """대화 히스토리를 포함하여 SQL 생성"""
        history_text = self.state.get_history_text(max_turns=5)
        
        last_context = ""
        if self.state.last_sql:
            last_context = f"""
## 직전 SQL
{self.state.last_sql}

## 직전 결과 요약
{self.state.last_result[:500] if self.state.last_result else '(없음)'}
"""
        
        prompt = f"""당신은 병원 데이터베이스 분석 전문가입니다.
아래 스키마와 대화 맥락을 참고하여 PostgreSQL 쿼리를 작성하세요.

## 데이터베이스 스키마
{self.schema_info}

## 규칙
- SELECT 문만 작성하세요.
- visits.status = 'completed'만 유효한 진료입니다.
- 나이 = EXTRACT(YEAR FROM AGE(birth_date))
- "그 중에서", "위 결과에서" 같은 표현은 직전 SQL의 조건을 유지하면서 추가 필터를 적용하세요.
- SQL만 반환하세요 (설명 없이).
{last_context}

## 대화 히스토리
{history_text}

## 현재 질문
{question}

## SQL
"""
        response = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        
        sql = response.choices[0].message.content.strip()
        sql = re.sub(r"```sql\s*", "", sql)
        sql = re.sub(r"```\s*", "", sql)
        return sql
    
    def _execute_sql(self, sql: str) -> str:
        """SQL 실행 (가드레일 적용)"""
        safe_sql, error = self.guardrail.sanitize(sql)
        if error:
            return f"⚠️ {error}"
        
        try:
            df = pd.read_sql(safe_sql, self.engine)
            if df.empty:
                return "(결과 없음)"
            return df.to_string(index=False)
        except Exception as e:
            return f"❌ SQL 실행 오류: {str(e)}"
    
    def _generate_answer(self, question: str, sql: str, result: str) -> str:
        """결과를 자연어로 요약"""
        prompt = f"""아래 SQL 결과를 한국어로 친절하게 요약해주세요.

질문: {question}
SQL: {sql}
결과:
{result[:1000]}

규칙:
- 숫자에 천 단위 구분자를 사용하세요.
- 표 형태면 핵심만 요약하세요.
- 친절하지만 간결하게 답변하세요.
"""
        response = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content
    
    def chat(self, question: str) -> str:
        """사용자 질문에 응답"""
        self.state.add_user(question)
        
        # 1. SQL 생성
        sql = self._generate_sql(question)
        
        # 2. SQL 실행
        result = self._execute_sql(sql)
        
        # 3. 에러 처리
        if result.startswith("⚠️") or result.startswith("❌"):
            answer = result
        else:
            # 4. 자연어 답변 생성
            answer = self._generate_answer(question, sql, result)
        
        self.state.add_assistant(answer, sql=sql, result=result)
        
        return f"{answer}\n\n📝 *실행된 SQL:*\n```sql\n{sql}\n```"

# 스키마 정보 수집
def get_full_schema(engine) -> str:
    tables = ["patients", "doctors", "visits", "diagnoses", "departments"]
    sql_db_temp = SQLDatabase(engine, include_tables=tables)
    parts = []
    for t in tables:
        parts.append(sql_db_temp.get_single_table_info(t))
    return "\n\n".join(parts)

schema_info = get_full_schema(engine)
```

```python
# ============================================================
# 3. 멀티턴 대화 테스트
# ============================================================
bot = HospitalChatbot(engine, schema_info)

# 턴 1
print(bot.chat("남성 환자는 몇 명인가요?"))
print("\n" + "="*60 + "\n")

# 턴 2 — 이전 맥락 참조
print(bot.chat("그 중에 40세 이상은?"))
print("\n" + "="*60 + "\n")

# 턴 3 — 이전 결과 참조
print(bot.chat("그 사람들이 가장 많이 간 진료과는?"))
print("\n" + "="*60 + "\n")

# 턴 4 — 보안 테스트
print(bot.chat("환자 테이블을 삭제해줘"))
```

```python
# ============================================================
# 4. 에러 복구 — 재시도 로직
# ============================================================
class RobustHospitalChatbot(HospitalChatbot):
    """에러 발생 시 자동 재시도하는 상담사"""
    
    MAX_RETRIES = 2
    
    def chat(self, question: str) -> str:
        self.state.add_user(question)
        
        for attempt in range(self.MAX_RETRIES + 1):
            sql = self._generate_sql(question)
            
            if attempt > 0:
                # 재시도 시 이전 에러를 피드백으로 전달
                sql = self._generate_sql(
                    f"이전 SQL이 오류 발생: {last_error}\n원래 질문: {question}\n수정된 SQL을 작성하세요."
                )
            
            result = self._execute_sql(sql)
            
            if not result.startswith("❌"):
                break
            last_error = result
        
        if result.startswith("⚠️") or result.startswith("❌"):
            answer = result
        else:
            answer = self._generate_answer(question, sql, result)
        
        self.state.add_assistant(answer, sql=sql, result=result)
        return f"{answer}\n\n📝 *SQL (시도 {attempt + 1}회):*\n```sql\n{sql}\n```"

# 테스트
rbot = RobustHospitalChatbot(engine, schema_info)
print(rbot.chat("진료과별 월 평균 방문 수를 최근 3개월 기준으로 보여줘"))
```

## 실습 과제

1. `HospitalChatbot`에 5턴 이상의 연속 대화를 시도하세요. 맥락이 잘 유지되나요?
2. `SQLGuardrail`에 새로운 차단 패턴을 추가하세요 (예: `UNION` 차단).
3. 가드레일 우회를 시도해 보세요 (예: 대소문자 혼합 `DrOp TaBlE`). 방어되나요?

## 강사 노트

- **시간 배분**: 멀티턴 개념 5분 → ChatState 설계 5분 → 가드레일 구현 10분 → 상담사 코드 15분 → 테스트 10분 → 실습 5분
- 가드레일 우회 시도는 보안 교육의 좋은 기회 — "정규식만으로는 완벽하지 않다. 프로덕션에서는 sqlparse + role-based access가 필수"
- 멀티턴 맥락 유지가 어려운 학생에게: "핵심은 프롬프트에 히스토리를 넣는 것. LLM은 stateless이므로 매번 전체 맥락을 전달해야 함"

---

# 12H · Gradio in Colab 데모

## 학습목표

- Gradio `ChatInterface`로 대화형 UI를 만들 수 있다.
- `share=True`로 공개 URL을 생성하여 다른 사람과 공유할 수 있다.
- 세션별 상태를 관리하여 여러 사용자가 독립적으로 사용할 수 있게 한다.

## 이론 — 왜 Gradio인가?

### 프론트엔드 프레임워크 비교

| 프레임워크 | 코드량 | Colab 지원 | 공유 URL | 학습 곡선 |
|---|---|---|---|---|
| **Gradio** | 5줄 | ✅ | ✅ (자동) | ⭐ (매우 쉬움) |
| Streamlit | 20줄 | ❌ (터널 필요) | ❌ | ⭐⭐ |
| Flask/FastAPI | 100줄+ | ❌ | ❌ | ⭐⭐⭐⭐ |
| React | 500줄+ | ❌ | ❌ | ⭐⭐⭐⭐⭐ |

> Gradio는 **ML 데모에 최적화**된 UI 프레임워크. Colab에서 5줄이면 채팅 UI 완성.

## 핵심 코드 — `09_gradio_chatbot.ipynb`

### 기본 ChatInterface

```python
# ============================================================
# 📦 패키지 설치
# ============================================================
!pip install -q gradio sqlalchemy psycopg2-binary openai sqlparse pandas \
    llama-index llama-index-llms-openai llama-index-embeddings-openai

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
```

```python
# ============================================================
# 1. 최소 Gradio ChatInterface (Echo Bot)
# ============================================================
import gradio as gr

def echo_chat(message, history):
    """입력을 그대로 반환하는 에코 봇"""
    return f"당신이 말한 것: {message}"

demo = gr.ChatInterface(
    fn=echo_chat,
    title="🤖 에코 봇",
    description="입력한 메시지를 그대로 반환합니다.",
)
demo.launch(share=True)
# share=True → 72시간 유효한 공개 URL 생성
```

### 병원 DB 상담사 + Gradio 통합

```python
# ============================================================
# 2. 병원 DB 상담사 + Gradio 통합
# ============================================================
import re
import pandas as pd
from sqlalchemy import create_engine, text
from openai import OpenAI as OpenAIClient
import sqlparse

engine = create_engine(os.environ["NEON_DSN"])
oai = OpenAIClient()

# 스키마 정보 (간소화)
from llama_index.core import SQLDatabase, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

sql_db = SQLDatabase(
    engine,
    include_tables=["patients", "doctors", "visits", "diagnoses", "departments"],
)
schema_parts = []
for t in sql_db.get_usable_table_names():
    schema_parts.append(sql_db.get_single_table_info(t))
SCHEMA_INFO = "\n\n".join(schema_parts)

# 가드레일
BLOCKED = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
ALLOWED_TABLES = {"patients", "doctors", "visits", "diagnoses", "departments", "vw_visit_details"}

def safe_execute(sql: str) -> str:
    """가드레일 적용 후 SQL 실행"""
    if BLOCKED.search(sql):
        return "🚫 위험한 명령어가 포함되어 있어 실행할 수 없습니다."
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    try:
        df = pd.read_sql(sql, engine)
        if df.empty:
            return "(결과 없음)"
        if len(df) > 20:
            return df.head(20).to_markdown(index=False) + f"\n\n... 외 {len(df)-20}행"
        return df.to_markdown(index=False)
    except Exception as e:
        return f"❌ SQL 오류: {str(e)}"

def generate_sql(question: str, history_text: str, last_sql: str = "") -> str:
    """LLM으로 SQL 생성"""
    last_ctx = f"\n직전 SQL:\n{last_sql}" if last_sql else ""
    prompt = f"""PostgreSQL 전문가입니다. 병원 DB에 대한 질문에 SQL을 작성하세요.

{SCHEMA_INFO}

규칙:
- SELECT만 사용. completed 상태만 유효.
- "그 중" = 직전 SQL 조건 유지 + 추가 필터
- SQL만 반환 (설명 없이).
{last_ctx}

대화:
{history_text}

질문: {question}
SQL:"""
    
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = resp.choices[0].message.content.strip()
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    return sql

def summarize_result(question: str, sql: str, result: str) -> str:
    """결과를 자연어로 요약"""
    prompt = f"""질문: {question}
SQL: {sql}
결과:
{result[:800]}

한국어로 간결하게 요약하세요. 숫자에 천 단위 구분자 사용."""
    
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content
```

```python
# ============================================================
# 3. Gradio ChatInterface + 세션 상태 관리
# ============================================================

def hospital_chat(message: str, history: list) -> str:
    """Gradio ChatInterface용 핸들러"""
    
    # history에서 대화 텍스트 생성
    history_text = ""
    last_sql = ""
    for turn in history[-5:]:  # 최근 5턴만
        if isinstance(turn, dict):
            history_text += f"사용자: {turn.get('content', '')}\n"
        elif isinstance(turn, (list, tuple)) and len(turn) == 2:
            history_text += f"사용자: {turn[0]}\n시스템: {turn[1][:100]}\n"
    
    try:
        # SQL 생성
        sql = generate_sql(message, history_text, last_sql)
        
        # SQL 실행
        result = safe_execute(sql)
        
        if result.startswith("🚫") or result.startswith("❌"):
            return result
        
        # 자연어 답변
        answer = summarize_result(message, sql, result)
        
        return f"{answer}\n\n---\n📝 **실행된 SQL:**\n```sql\n{sql}\n```\n\n📊 **원본 결과:**\n{result}"
    
    except Exception as e:
        return f"⚠️ 처리 중 오류가 발생했습니다: {str(e)}"

# Gradio UI 구성
demo = gr.ChatInterface(
    fn=hospital_chat,
    title="🏥 병원 DB AI 상담사",
    description="자연어로 병원 데이터베이스에 질문하세요. 환자, 의사, 진료 기록을 분석합니다.",
    examples=[
        "현재 등록된 환자 수는?",
        "진료과별 의사 수를 보여줘",
        "지난 3개월간 가장 많이 방문한 환자 Top 5는?",
        "응급 진료 건수와 평균 비용은?",
    ],
    theme=gr.themes.Soft(),
    retry_btn="🔄 다시 시도",
    undo_btn="↩️ 실행 취소",
    clear_btn="🗑️ 대화 초기화",
)

demo.launch(share=True)
```

```python
# ============================================================
# 4. 고급: 커스텀 CSS + 부가 기능
# ============================================================

custom_css = """
.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
}
.message-bubble-border {
    border-radius: 12px !important;
}
"""

with gr.Blocks(css=custom_css, theme=gr.themes.Soft(), title="병원 DB 상담사") as advanced_demo:
    gr.Markdown("# 🏥 병원 DB AI 상담사")
    gr.Markdown("자연어로 병원 데이터를 분석하세요. SQL을 자동으로 생성·실행합니다.")
    
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=500,
                bubble_full_width=False,
                show_label=False,
            )
            msg = gr.Textbox(
                placeholder="질문을 입력하세요... (예: 남성 환자 수는?)",
                show_label=False,
                scale=4,
            )
            with gr.Row():
                submit_btn = gr.Button("📤 전송", variant="primary")
                clear_btn = gr.Button("🗑️ 초기화")
        
        with gr.Column(scale=1):
            gr.Markdown("### 📋 예시 질문")
            gr.Markdown("""
            - 환자 수는 몇 명?
            - 진료과별 의사 수
            - 월별 방문 추이
            - 가장 비싼 진료 5건
            - 중증 진단 환자 목록
            """)
            gr.Markdown("### ⚠️ 주의사항")
            gr.Markdown("""
            - SELECT 쿼리만 가능
            - 데이터 수정/삭제 불가
            - 결과는 최대 1000행
            """)
    
    def respond(message, chat_history):
        response = hospital_chat(message, chat_history)
        chat_history.append((message, response))
        return "", chat_history
    
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
    clear_btn.click(lambda: None, None, chatbot, queue=False)

advanced_demo.launch(share=True)
```

### 수강생 간 교차 체험 가이드

```python
# ============================================================
# 5. 교차 체험 — URL 교환
# ============================================================

# 실행 후 출력되는 공개 URL:
# Running on public URL: https://xxxxx.gradio.live

# 교차 체험 진행:
# 1. 각자의 Gradio URL을 채팅/슬랙에 공유
# 2. 다른 학생의 URL에 접속하여 질문 테스트
# 3. 실패하는 질문을 발견하면 피드백
# 4. 5분 후 다른 학생의 앱으로 이동

print("""
🔄 교차 체험 진행 방법:

1. 본인 Gradio URL을 복사하여 전체 채팅에 공유
2. 다른 학생 2명의 URL에 접속
3. 각 앱에서 질문 3개씩 테스트
4. 발견한 문제점을 정리하여 해당 학생에게 피드백

⏱ 소요 시간: 약 10분
""")
```

## 과제 #2 안내

```python
# ============================================================
# 📋 과제 #2 — 스키마 + 시드 데이터 배포
# ============================================================

print("""
╔════════════════════════════════════════════╗
║           과제 #2 — 스키마 + 시드 데이터        ║
╠════════════════════════════════════════════╣
║                                            ║
║  제출 기한: Day 3 시작 (13H)                ║
║                                            ║
║  제출물:                                    ║
║  1. Neon PostgreSQL에 스키마 생성 완료       ║
║  2. 테이블당 최소 50행 시드 데이터           ║
║  3. 모든 컬럼에 COMMENT ON 적용             ║
║  4. FK 관계 정상 동작 확인                   ║
║  5. DSN을 강사에게 공유                      ║
║                                            ║
║  체크리스트:                                 ║
║  □ 제안서 스키마가 Neon에 반영되었는가?       ║
║  □ 시드 데이터가 10개 질문을 답할 수 있는가?  ║
║  □ COMMENT ON이 누락된 컬럼이 없는가?        ║
║  □ FK 제약 조건이 정상 작동하는가?            ║
║                                            ║
║  💡 Faker 라이브러리로 가상 데이터 생성 추천   ║
║                                            ║
╚════════════════════════════════════════════╝
""")
```

```python
# 시드 데이터 생성 도우미 (선택 사용)
print("""
💡 시드 데이터 생성 팁:

# Faker로 50행 이상의 가상 데이터 생성
!pip install faker

from faker import Faker
fake = Faker('ko_KR')

# 예: 고객 데이터 생성
customers = []
for i in range(50):
    customers.append({
        'name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': fake.address(),
        'created_at': fake.date_between('-1y', 'today'),
    })

import pandas as pd
df = pd.DataFrame(customers)
# df.to_sql('customers', engine, if_exists='append', index=False)
""")
```

## 실습 과제

1. `hospital_chat` 함수를 수정하여 질문에 "감사합니다", "안녕" 같은 인사가 오면 SQL 없이 인사로 응답하세요.
2. Gradio `examples`에 본인이 만든 흥미로운 질문 3개를 추가하세요.
3. 다른 학생 2명의 Gradio URL에 접속하여 질문 3개씩 테스트하고 피드백을 공유하세요.

## 강사 노트

- **시간 배분**: Gradio 소개 5분 → 에코봇 5분 → 병원 상담사 통합 15분 → 교차 체험 10분 → 과제 #2 안내 10분 → 정리 5분
- `share=True`가 Colab에서 잘 작동함 — 방화벽 이슈 거의 없음
- 교차 체험이 이 시간의 하이라이트 — 학생들이 서로의 앱을 써보며 경쟁심과 동기부여 자극
- **자주 묻는 질문**: 
  - "URL이 안 열려요" → Colab 런타임이 끊겼을 수 있음. 다시 실행.
  - "다른 사람이 내 DB를 수정할 수 있나요?" → 가드레일이 SELECT만 허용. 안전함.
- **과제 #2 강조**: "내일(Day 3)까지 Neon에 스키마와 데이터를 올려야 합니다. 오늘 밤에 완성하세요!"

---

*Day 2 상세 강의자료 — 강의 교안 및 Colab 노트북 분할을 전제로 작성됨*
