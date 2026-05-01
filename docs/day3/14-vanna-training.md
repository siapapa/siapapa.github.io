# 14H -- Vanna 자가학습 실습

## 학습목표

- DDL, Documentation, SQL Pairs를 Vanna에 학습시킬 수 있다
- In-Chat Training으로 오답 -> 정답 피드백 루프를 실행할 수 있다
- 학습 전후 정확도 변화를 측정할 수 있다

---

<div class="colab-link" data-notebook="11_vanna_training"></div>

## DDL 학습 -- 스키마 정보 주입

DDL(Data Definition Language)은 테이블의 구조 정보입니다. Vanna가 SQL을 생성하려면 먼저 테이블 구조를 알아야 합니다.

!!! tip "DDL 학습의 핵심"
    DDL에 **주석(COMMENT)**을 함께 넣으면 Vanna가 컬럼의 의미를 더 잘 이해합니다.
    FK 관계를 명시하면 JOIN 쿼리의 정확도가 크게 향상됩니다.

```python
# ============================================================
# 1. DDL 학습 -- 스키마 정보를 Vanna에 주입
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

### Day 1 4H 에서 만든 `COMMENT ON` 을 Vanna 에 함께 학습

!!! info "왜 COMMENT 를 별도로 학습시키나요?"
    Day 1 4H Schema Intelligence 에서 `COMMENT ON COLUMN ...` 으로 컬럼별 주석을 DB 에 저장했습니다. 그 정보가 Vanna 학습 자산에도 포함돼야 **20H 에서 `col_description()` 으로 스키마를 수집해 프롬프팅하는 설계가 의미 있게 동작**합니다 (Day 1 4H → Day 3 14H → Day 3 20H 로 이어지는 Schema Intelligence 라인).

```python
# ---- 실제 DB 의 COMMENT 를 Vanna DDL 자산으로 함께 학습 ----
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT c.relname, a.attname, pgd.description
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        JOIN pg_description pgd
             ON pgd.objoid = c.oid AND pgd.objsubid = a.attnum
        WHERE n.nspname = 'public'
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum
    """)).fetchall()

for table_name, col_name, comment in rows:
    # 작은 DDL 스니펫 형태로 Vanna 에 주입 — col_description() 와 같은 맥락을 학습
    safe = comment.replace("'", "''")
    vn.train(ddl=f"COMMENT ON COLUMN {table_name}.{col_name} IS '{safe}';")

print(f"✅ COMMENT ON {len(rows)}건 학습 (Day 1 4H 의 주석을 Vanna 와 공유)")
```

!!! note "핵심 정리"
    각 DDL 문에 포함된 주석(`-- departments: 병원의 진료과 정보`)과 위에서 추가한 `COMMENT ON COLUMN ...` 들이 Vanna 의 **DDL 자산** 으로 함께 임베딩됩니다. 덕분에 Vanna 는 같은 컬럼 의미를 Day 1~4 전 구간에서 일관되게 사용합니다.

---

## Documentation 학습 -- 비즈니스 용어와 규칙

Documentation은 데이터의 의미, 비즈니스 규칙, 용어 정의를 Vanna에 알려줍니다.

```python
# ============================================================
# 2. Documentation 학습 -- 비즈니스 용어/규칙
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

!!! tip "Documentation 작성 요령"
    - **한 문장에 하나의 규칙**을 넣는 것이 효과적입니다
    - 자연어 용어(예: "지난달")와 SQL 표현을 매핑하세요
    - NULL 값의 의미를 명확히 기술하세요 (예: cost가 NULL이면 미청구)
    - CHECK 제약 조건의 값과 한국어 의미를 연결하세요

---

## SQL Pairs 학습 -- 질문과 정답 SQL 쌍

SQL Pairs는 "이 질문에는 이 SQL이 정답"이라는 예시를 제공합니다. Vanna가 유사한 질문을 받으면 이 예시를 참고하여 SQL을 생성합니다.

```python
# ============================================================
# 3. SQL Pairs 학습 -- 질문-SQL 정답 쌍
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

---

## 학습 현황 확인

```python
# ============================================================
# 4. 학습 자산 현황 확인
# ============================================================
training_data = vn.get_training_data()
print(f"📚 총 학습 자산: {len(training_data)}건")
print(f"  - DDL: {len(training_data[training_data['training_data_type'] == 'ddl'])}건")
print(f"  - Documentation: {len(training_data[training_data['training_data_type'] == 'documentation'])}건")
print(f"  - SQL: {len(training_data[training_data['training_data_type'] == 'sql'])}건")
print("\n📋 학습 데이터 미리보기:")
print(training_data.head(10))
```

---

## 학습 후 정확도 측정 (10개 질문)

!!! example "실습 -- 학습 전후 정답률 비교"
    13H에서 측정한 베이스라인 정답률과 비교하세요!

```python
# ============================================================
# 5. 학습 후 정확도 측정 (10개 질문)
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

!!! example "실습 -- 학습 전후 정답률 비교표 작성"
    아래 표를 복사하여 본인의 결과를 채워 넣으세요.

    | # | 질문 | 학습 전 | 학습 후 | 개선 |
    |---|---|---|---|---|
    | 1 | 전체 환자 수는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 2 | 남성 환자 중 40세 이상은? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 3 | 진료과별 의사 수를 보여줘 | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 4 | 지난달 완료 진료 건수는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 5 | 응급 진료 평균 비용은? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 6 | 가장 많이 방문한 환자 Top 3는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 7 | 중증 진단을 받은 환자 이름은? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 8 | 2026년 월별 방문 수 추이는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 9 | 내과 의사 중 급여 최고는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | 10 | 혈액형별 환자 분포는? | ❌ / ✅ | ❌ / ✅ | - / 개선 |
    | | **합계** | **/10** | **/10** | |

---

## In-Chat Training -- 오답 교정 피드백 루프

실패한 질문을 찾아 정답 SQL을 직접 작성하고 재학습시킵니다. 이 **오답 -> 정답 피드백 루프**가 Vanna 정확도 개선의 핵심입니다.

!!! tip "In-Chat Training 전략"
    1. 실패한 질문의 생성된 SQL을 확인합니다
    2. 무엇이 잘못되었는지 분석합니다 (테이블명? JOIN? 조건?)
    3. 정답 SQL을 직접 작성합니다
    4. `vn.train(question=..., sql=...)`으로 학습시킵니다
    5. 같은 질문을 다시 테스트합니다

```python
# ============================================================
# 6. In-Chat Training -- 오답을 교정하여 재학습
# ============================================================

# 실패한 질문을 찾아 수동으로 정답 SQL 작성 후 학습
failed = df_results[df_results["status"] != "✅"]

if len(failed) > 0:
    print("❌ 실패한 질문들:")
    for _, row in failed.iterrows():
        print(f"  - {row['question']}")
        print(f"    생성된 SQL: {row['sql'][:100]}")

    print("\n🔄 수동 교정 후 재학습:")

    # 예: 실패한 질문들에 대한 정답 SQL 작성
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
            print(f"  --> ✅ 성공 ({len(df)}행)")
        except:
            print(f"  --> ❌ 여전히 실패")
```

!!! warning "Colab 런타임 재시작 시 주의"
    Vanna ChromaDB는 기본적으로 **인메모리**입니다. Colab 런타임이 재시작되면 학습 데이터가 사라집니다.
    `vn.get_training_data()` 결과를 CSV로 백업해두세요:

    ```python
    training_data = vn.get_training_data()
    training_data.to_csv("vanna_training_backup.csv", index=False)
    print("✅ 학습 데이터 백업 완료!")
    ```

---

## 본인 프로젝트 DB에 Vanna 적용

```python
# ============================================================
# 7. 본인 프로젝트 DB에 Vanna 적용 (실습 가이드)
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

5. 10개 질문 테스트 --> 정답률 측정

6. 실패한 질문 교정 --> 재학습 --> 재측정

💡 목표: 학습 전 vs 후 정답률 비교. 몇 개가 개선되었나?
""")
```

!!! example "실습 -- 본인 프로젝트 적용 체크리스트"
    아래 항목을 순서대로 완료하세요:

    - [ ] 본인 Neon DSN으로 Vanna 연결
    - [ ] DDL 학습 (본인 테이블 전체)
    - [ ] Documentation 학습 (비즈니스 규칙 5개 이상)
    - [ ] SQL Pairs 학습 (최소 4개)
    - [ ] 학습 전 5개 질문 테스트 (정답률 기록)
    - [ ] 학습 후 10개 질문 테스트 (정답률 기록)
    - [ ] 실패 질문 In-Chat Training
    - [ ] 최종 정답률 비교

---

## 실습 과제

1. DDL 5개, Documentation 10개, SQL Pairs 6개를 학습시키고 정확도를 측정하세요.
2. 실패한 질문 2개 이상을 In-Chat Training으로 교정하세요.
3. 학습 전후 정답률 비교표를 작성하세요.

!!! question "생각해보기"
    - DDL만 학습했을 때 vs DDL+Documentation까지 학습했을 때, 어떤 질문의 정답률이 달라지나요?
    - SQL Pairs를 추가하면 어떤 유형의 질문이 개선되나요?
    - 학습 자산의 **종류별 기여도**를 어떻게 측정할 수 있을까요?

---

!!! note "핵심 정리"
    - Vanna에 **DDL -> Documentation -> SQL Pairs** 순으로 학습
    - 학습할수록 정확도 향상 -- **오답 -> 정답 피드백 루프**가 핵심
    - 10개 질문으로 정확도를 측정하고, 실패한 질문을 교정하여 재학습
    - 본인 프로젝트 DB에도 동일한 방식으로 적용 가능
    - ChromaDB 인메모리 특성 -- 런타임 재시작 시 학습 데이터 소실 주의
