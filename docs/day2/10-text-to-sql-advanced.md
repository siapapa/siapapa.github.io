# 10H · NLSQLTableQueryEngine 심화

## 학습목표

- `NLSQLTableQueryEngine`의 내부 프롬프트 구조를 분석할 수 있다
- `table_info` 수동 주입, few-shot 예제, 테이블 선택 전략으로 정확도를 개선할 수 있다
- 커스텀 프롬프트 템플릿을 작성하여 LLM의 SQL 생성 품질을 높일 수 있다

---

<div class="colab-link" data-notebook="08_text_to_sql_advanced"></div>

## 왜 기본 설정으로는 부족한가?

Day 1 7H에서 경험한 실패 원인:

```
1. 스키마 정보 부족 — COMMENT가 없거나 부족하면 LLM이 컬럼 의미를 오해
2. 프롬프트 품질 — 기본 프롬프트가 한국어 질문에 최적화되지 않음
3. 테이블 선택 오류 — 테이블이 많을 때 관련 없는 테이블을 프롬프트에 포함
4. 컨텍스트 부족 — 도메인 특수 용어를 LLM이 모름 (예: "본태성 고혈압" = I10)
```

## 개선 전략 3가지

```
전략 1: table_info 보강    → 스키마에 자연어 설명 추가
전략 2: few-shot 주입      → 예시 (질문, SQL) 쌍으로 패턴 학습
전략 3: 테이블 선택 자동화  → ObjectIndex로 관련 테이블만 필터
```

---

## 1. 내부 프롬프트 분석

!!! tip "get_prompts()로 AI가 실제로 보는 프롬프트를 확인하세요"
    `get_prompts()`를 호출하면 LLM에 전달되는 프롬프트 템플릿을 볼 수 있습니다. 이것이 "아하!" 순간입니다 -- LLM이 실제로 보는 것이 이것입니다.

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

### 스키마가 프롬프트에 어떻게 채워지는지 확인

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

!!! note "핵심 정리"
    `{schema}` 변수에는 `get_single_table_info()`가 반환하는 텍스트가 들어갑니다. 여기에 CREATE TABLE 문, COMMENT, 샘플 데이터 3행이 포함됩니다. COMMENT ON이 없으면 LLM은 컬럼 이름만 보고 추측해야 합니다.

---

## 2. 전략 1 -- 도메인 지식 주입 (context_str_prefix)

!!! tip "도메인 지식 주입"
    AI에게 "이 데이터베이스에서는 이런 규칙이 있어"라고 알려주는 전략입니다. visits.status, 날짜 패턴 등 비즈니스 규칙을 명시합니다.

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
- 나이 계산: EXTRACT(YEAR FROM AGE(birth_date))  -- ※ 연 단위만 취하므로 "올해 생일 안 지남"은 반영되지 않습니다. 정확한 나이는 DATE_PART('year', AGE(CURRENT_DATE, birth_date)) 또는 (CURRENT_DATE - birth_date)/365 권장.

## 자주 사용되는 패턴
- "지난달" = WHERE visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                AND visit_date < DATE_TRUNC('month', CURRENT_DATE)
- "올해" = WHERE EXTRACT(YEAR FROM visit_date) = EXTRACT(YEAR FROM CURRENT_DATE)
- "재방문" = 같은 patient_id로 2건 이상의 visits 레코드
"""

# context_info 를 실제로 프롬프트에 주입하는 전략 1 엔진
# — text_to_sql_prompt 의 {schema} 바로 뒤에 context_info 가 섞이도록 PromptTemplate 로 감쌉니다.
from llama_index.core.prompts import PromptTemplate

enhanced_prompt = PromptTemplate(
    f"""당신은 PostgreSQL 전문가입니다. 아래 스키마와 도메인 지식을 함께 참고해 SQL 을 작성하세요.

## 데이터베이스 스키마
{{schema}}

{context_info}

## 질문
{{query_str}}

## SQL
"""
)

nlq_enhanced = NLSQLTableQueryEngine(
    sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    text_to_sql_prompt=enhanced_prompt,
)
```

---

## 3. 전략 2 -- 커스텀 프롬프트 + Few-shot

한국어 최적화 + few-shot 3개를 포함한 커스텀 프롬프트입니다.

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
- 나이 계산: EXTRACT(YEAR FROM AGE(birth_date))  -- ※ 연 단위만 취하므로 "올해 생일 안 지남"은 반영되지 않습니다. 정확한 나이는 DATE_PART('year', AGE(CURRENT_DATE, birth_date)) 또는 (CURRENT_DATE - birth_date)/365 권장.
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

---

## 4. Before/After 비교 실험

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

print("📊 기본 / context_info 주입 / 커스텀+Few-shot 3종 비교\n")
print(f"{'질문':<40} {'기본':^10} {'context':^10} {'커스텀':^10}")
print("-" * 80)

for q in test_questions:
    # 기본 버전
    try:
        resp_basic = nlq.query(q)
        basic_status = "✅"
    except Exception:
        basic_status = "❌"

    # 전략 1 — context_info 주입 버전 (nlq_enhanced)
    try:
        resp_enh = nlq_enhanced.query(q)
        enh_status = "✅"
    except Exception:
        enh_status = "❌"

    # 전략 2 — 커스텀 프롬프트 + Few-shot 버전
    try:
        resp_custom = nlq_custom.query(q)
        custom_status = "✅"
    except Exception:
        custom_status = "❌"

    print(f"{q:<40} {basic_status:^10} {enh_status:^10} {custom_status:^10}")
```

!!! tip "Before/After 체감 포인트"
    - `기본` 은 `status='completed'` 조건이 빠져 cancelled·no_show 까지 집계에 섞입니다.
    - `context` 는 도메인 규칙을 알게 되지만 예시가 없어 포맷은 거친 편.
    - `커스텀` 은 Few-shot 3건으로 별칭·날짜 필터까지 기대 형태를 따라갑니다.

    "모호한 질문(최근에 많이 온 사람은?)" 한 행만 골라 생성된 SQL 을 직접 비교해 보면 효과가 가장 잘 드러납니다.

### 상세 비교 -- 특정 질문의 SQL 비교

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

!!! note "핵심 정리"
    커스텀 프롬프트에서 `status = 'completed'` 규칙과 `AS` 별칭 규칙을 추가했기 때문에, 생성되는 SQL의 품질이 향상됩니다. 기본 프롬프트는 이런 도메인 지식이 없어 부정확한 결과를 반환할 수 있습니다.

!!! tip "기대 결과 -- 실행 전에 "이러면 성공" 기준부터 정리"
    출력이 다양하게 바뀔 수 있기 때문에, 실습 전에 **어느 쪽이 더 잘 나온 것인지** 기준을 잡고 시작하세요.

    | 질문 | 기본(Before)이 흔히 만드는 SQL | 커스텀(After)에서 기대하는 SQL | 우리가 보는 차이 |
    |---|---|---|---|
    | 진료과별 평균 진료비 | `SELECT dept, AVG(fee) FROM visits GROUP BY dept` (status 조건 없음, 별칭 없음) | `SELECT d.name AS 진료과, AVG(v.fee) AS 평균진료비 FROM visits v JOIN departments d ... WHERE v.status='completed' GROUP BY d.name` | `status='completed'` 필터, 한글 별칭, JOIN 으로 이름 표시 |
    | 지난달 방문 환자 수 | `WHERE visit_date >= '2026-03-01'` 같이 하드코딩 | `WHERE visit_date >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month' AND visit_date < date_trunc('month', CURRENT_DATE)` | 상대 날짜 표현, "지난달" 정의가 명확 |
    | 최근에 많이 온 사람은? (모호) | 아무 기준 없이 `COUNT(*) DESC LIMIT 10` | "최근 = 최근 3개월" 가정을 주석/WHERE 로 명시 + `status='completed'` | 모호한 조건을 도메인 규칙으로 해석 |

    이 표를 기준으로, 실제 실행 결과가 "왜 Before 는 부족하고 After 가 더 나은가"를 설명할 수 있는지 확인하세요. 단순히 `✅/❌` 만 보지 말고 **생성된 SQL 자체**를 비교해야 합니다.

---

## 5. 전략 3 -- 테이블 자동 선택 (ObjectIndex)

질문에 관련된 테이블만 벡터 검색으로 자동 선택하는 전략입니다. 여기서는 세 가지 LlamaIndex API 를 조합합니다. 먼저 역할부터 한 줄씩 이해하세요.

| API | 역할 | 한 줄 비유 |
|---|---|---|
| `SQLTableSchema` | 각 테이블에 **자연어 설명(context)** 을 붙인 객체 | 테이블마다 달아둔 **짧은 소개문** |
| `SQLTableNodeMapping` | 테이블 ↔ 벡터 인덱스 노드 변환기 | 테이블 이름을 벡터 검색용 **주소표** 로 바꿔 주는 어댑터 |
| `ObjectIndex` | 위 소개문들을 임베딩해 **"질문 → 관련 테이블 Top-K"** 를 반환하는 인덱스 | **테이블 전용 검색 엔진** |
| `SQLTableRetrieverQueryEngine` | 테이블을 먼저 검색한 뒤 `NLSQLTableQueryEngine` 처럼 SQL 을 생성·실행 | **테이블 검색기 + Text-to-SQL** 이 합쳐진 쿼리 엔진 |

!!! tip "왜 이렇게 여러 단계로 쪼갤까?"
    테이블이 수십 개인 실제 DB 에서는 프롬프트에 스키마를 전부 붙이면 토큰이 터지고 LLM 이 헷갈립니다. 그래서 "질문과 가장 관련된 3개 테이블만" RAG 스타일로 먼저 고르고, 그 스키마만 프롬프트에 넣습니다. 위 3개 클래스는 이 RAG 조각의 재료입니다.

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

!!! tip "ObjectIndex의 장점"
    테이블이 많은 데이터베이스에서는 프롬프트에 모든 테이블 스키마를 넣으면 토큰이 낭비되고 LLM이 혼란을 겪습니다. ObjectIndex는 질문과 관련된 테이블 2~3개만 선택하여 프롬프트를 최적화합니다.

---

## 6. 프롬프트 실험 워크시트

같은 모호한 질문을 3가지 프롬프트로 실험하여 차이를 관찰합니다.

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
```

### 프롬프트 A: 기본

```python
# 프롬프트 A: 기본
prompt_a = PromptTemplate(
    "Given the schema:\n{schema}\n\nWrite SQL for: {query_str}\n\nSQL:"
)
```

### 프롬프트 B: 모호성 처리 규칙 추가

```python
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
```

### 프롬프트 C: few-shot + 모호성 규칙

```python
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
```

### 실험 실행

```python
# 실험 실행
q = "최근에 많이 온 사람은?"
experiment(q, prompt_a, "A: 기본")
experiment(q, prompt_b, "B: 모호성 규칙")
experiment(q, prompt_c, "C: few-shot + 규칙")
```

!!! note "핵심 정리"
    프롬프트 A(기본)에서는 "최근"과 "많이"를 자의적으로 해석하지만, 프롬프트 B(규칙)와 C(few-shot+규칙)에서는 명확한 기준을 따릅니다. **프롬프트 엔지니어링이 곧 Text-to-SQL의 정확도**입니다.

---

!!! example "실습"
    **Day 1에서 실패한 질문 3개를 커스텀 프롬프트로 재시도하세요.**

    1. Day 1 7H에서 실패했거나 어색했던 질문 3개를 리스트로 정리하세요
    2. 각 질문을 `nlq.query(...)` (기본) 와 `nlq_custom.query(...)` (커스텀) 에 동일하게 던지세요
    3. 각 시도에서 `response.metadata["sql_query"]` 를 꺼내 두 SQL 을 나란히 출력하세요
    4. 단순 ✅/❌ 가 아니라 **생성된 SQL의 차이**(필터 조건, 별칭, JOIN 경로)를 직접 비교 정리하세요

    *힌트: 위의 "Before/After 비교 실험" 셀을 참고해 try/except 로 두 엔진을 모두 호출하면 됩니다. 정답 코드는 숨겨져 있으니, 실패 질문을 본인 메모에서 꺼내 직접 작성해 보세요.*

!!! question "생각해보기"
    **본인 도메인에 맞는 모호성 처리 규칙을 3개 작성하세요.**

    예시 (병원 도메인):

    - "최근" = 최근 3개월
    - "많이" = 3회 이상
    - "자주" = 월 평균 2회 이상

    본인 도메인에서는:

    - "___" = ___
    - "___" = ___
    - "___" = ___

    예: 쇼핑몰 도메인이라면

    - "최근" = 최근 30일
    - "인기" = 주문 100건 이상
    - "고액" = 50만원 이상

    이 규칙을 커스텀 프롬프트에 추가하면 본인 도메인의 에이전트 정확도가 올라갑니다.

---

## 실습 과제

1. Day 1에서 실패했던 질문 3개를 커스텀 프롬프트로 재시도하고 Before/After를 기록하세요
2. 본인 도메인에 맞는 모호성 처리 규칙 3개를 작성하세요 (예: "최근"의 정의)
3. few-shot 예제를 2개 추가하고 정확도가 향상되는지 확인하세요

---

!!! note "10H 핵심 정리"
    - AI 내부 프롬프트를 `get_prompts()`로 직접 확인할 수 있음
    - **프롬프트 엔지니어링이 곧 Text-to-SQL의 정확도**
    - 3가지 전략: 도메인 지식 주입, Few-shot 예시, 테이블 자동 선택 (ObjectIndex)
    - Day 3에서 Vanna가 이 과정을 자동화합니다 -- "수동으로 하던 것을 Vanna가 자동화"

---
