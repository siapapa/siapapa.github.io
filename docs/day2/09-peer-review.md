# 9H · 제안서 피어리뷰

## 학습목표

- 프로젝트 제안서를 구조적으로 평가할 수 있다
- 피어리뷰를 통해 본인 제안서의 약점을 식별하고 개선할 수 있다
- AI-friendly 스키마의 기준을 실제 제안서에 적용할 수 있다

---

## 좋은 제안서의 조건 (체크리스트)

| 항목 | 확인 내용 | 배점 |
|---|---|---|
| 도메인 적절성 | 3~5 테이블로 표현 가능한 범위인가? | 10 |
| 테이블 설계 | PK/FK 명시, 적절한 데이터 타입 | 20 |
| COMMENT ON | 모든 컬럼에 자연어 설명이 있는가? | 20 |
| 질문 난이도 분포 | Easy 3~4 / Medium 3~4 / Hard 2~3 | 20 |
| 기대 SQL | 각 질문에 구체적인 SQL이 있는가? | 20 |
| ERD | 테이블 간 관계가 시각화되었는가? | 10 |

---

## 흔한 문제 패턴 5가지

### 문제 1: "테이블이 너무 많다" (8개 이상)

```
❌ 나쁜 예: 테이블 10개 → AI가 관련 테이블을 찾는 데 실패
✅ 해결: 핵심 3~5개로 축소. 나머지는 리포팅 뷰로 대체
📌 이유: 테이블이 많으면 LLM이 관련 테이블 선택에서 실패
```

### 문제 2: "질문이 모두 같은 난이도"

```
❌ 나쁜 예: 10개 질문 모두 "~는 몇 개?" (Easy만)
✅ 해결: Hard 질문 추가 — 윈도우 함수, 다중 CTE, 자기 참조 필요
📌 이유: 에이전트 성능을 다양한 각도에서 검증해야 함
```

### 문제 3: "컬럼명이 약어"

```
❌ 나쁜 예: ord_dt → order_date, cust_nm → customer_name
✅ 해결: 명시적인 전체 이름을 사용
📌 이유: LLM은 full name을 보고 의미를 파악. 약어는 오역의 원인
```

### 문제 4: "FK 없이 암묵적 관계"

```
❌ 나쁜 예: pid INT (어느 테이블과 연결되는지 알 수 없음)
✅ 해결: FOREIGN KEY 제약 조건 명시
📌 이유: LLM이 JOIN 경로를 FK에서 추론. 없으면 잘못된 JOIN 생성
```

### 문제 5: "기대 SQL이 없거나 부정확"

```
❌ 나쁜 예: Q1: "주문 수?" → SQL 없음
✅ 해결: 실제 실행 가능한 SQL을 작성하고 결과 행 수 기재
📌 이유: 에이전트 출력과 비교할 ground truth가 필요
```

---

## 나쁜 제안서 SQL 예시

!!! warning "이런 제안서는 감점 대상"
    축약 컬럼명, 단일 테이블, Easy 질문만 포함한 제안서입니다.

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

---

## 좋은 제안서 SQL 예시

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

!!! note "핵심 정리"
    좋은 제안서의 핵심 차이:

    - COMMENT ON으로 모든 컬럼에 한국어 설명
    - FK 제약 조건으로 테이블 간 관계 명시
    - Easy/Medium/Hard 질문 골고루 분포
    - 각 질문에 실행 가능한 기대 SQL 포함

---

## 스키마 자동 검증 도구 — validate_schema()

학생들이 자기 스키마의 AI-friendliness를 자동으로 점검하는 도구입니다.

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
```

### 실행 예시

```python
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

출력 예시:

```
📊 스키마 검증 결과: 85.3점 / 100점

  patients: PK ✅ | FK 0개 | COMMENT 7/7
  doctors: PK ✅ | FK 1개 | COMMENT 6/6
  visits: PK ✅ | FK 2개 | COMMENT 8/8
  diagnoses: PK ✅ | FK 2개 | COMMENT 5/6
  departments: PK ✅ | FK 0개 | COMMENT 4/4

⚠️ 개선 필요 (1건):
  ⚠️ diagnoses.notes: COMMENT 없음
```

!!! example "실습"
    **validate_schema를 본인 스키마에 실행하세요.**

    1. 본인의 Neon DB에 접속합니다
    2. 본인이 설계한 테이블 이름 리스트로 `validate_schema(engine, my_tables)` 를 호출하세요
    3. 점수와 함께 각 테이블의 PK / FK / COMMENT 비율을 출력해, 어디가 부족한지 확인하세요
    4. 점수가 80점 미만이면 COMMENT를 추가하세요
    5. 피어리뷰에서 이 결과를 공유하세요

    *힌트: 위 "실행 예시" 셀의 출력 형식을 참고해, `report["tables"]` 와 `report["issues"]` 를 순회하며 직접 출력해 보세요. 정답 코드는 제공되지 않습니다 -- 본인 손으로 작성해야 점수의 의미가 체감됩니다.*

---

## 피어리뷰 진행 순서 (30분)

```
1. 조 편성 — 3인 1조 (5분)
2. 돌아가며 발표 — 각자 10분:
   ├── 도메인 소개 (2분)
   ├── 스키마 설명 (3분)
   ├── 대표 질문 5개 (3분)
   └── 피드백 (2분)
3. 스키마 검증기 실행 — 본인 스키마에 validate_schema() 실행 (5분)
4. 개선 메모 — 피드백 반영 계획 정리 (5분)
```

### 타임라인 상세

| 시간 | 활동 | 내용 |
|---|---|---|
| 0~5분 | 조 편성 | 3인 1조 구성, 발표 순서 결정 |
| 5~15분 | 1번째 발표 | 도메인 소개 + 스키마 + 질문 + 피드백 |
| 15~25분 | 2번째 발표 | 동일한 형식 |
| 25~35분 | 3번째 발표 | 동일한 형식 |
| 35~40분 | 검증기 실행 | validate_schema()로 본인 스키마 점검 |
| 40~45분 | 개선 메모 | 피드백 반영 계획 정리 |
| 45~50분 | 강사 순회 | 강사가 각 조를 돌며 3분씩 피드백 |

---

## 피어리뷰 피드백 양식

아래 양식을 복사하여 사용하세요.

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

### FK 관계
- FK 제약 조건 수: ___개
- 누락된 관계: ___

### 종합 의견
-
```

---

!!! tip "ERD를 꼭 그려야 하나요?"
    **필수는 아니지만 강력히 권장합니다.**

    ERD를 그리면:

    - 테이블 간 관계를 한눈에 파악할 수 있음
    - 누락된 FK를 발견하기 쉬움
    - 피어리뷰에서 설명이 훨씬 수월함
    - Day 3에서 에이전트가 JOIN 경로를 찾는 데 도움

    Mermaid로 5분이면 됩니다:

    ```
    erDiagram
        customers ||--o{ orders : "주문"
        orders ||--o{ order_items : "포함"
        products ||--o{ order_items : "주문됨"
    ```

    MkDocs, GitHub, Notion 등에서 바로 렌더링됩니다.

!!! question "생각해보기"
    1. 내 제안서의 COMMENT ON 완성도는 몇 %인가요?
    2. Hard 질문이 2개 이상 포함되어 있나요? 없다면 어떤 질문을 추가할 수 있을까요?
    3. 다른 학생의 제안서에서 배울 점은 무엇이었나요?

---

!!! note "9H 핵심 정리"
    - 좋은 제안서 = 명시적 네이밍 + COMMENT ON + 난이도 분산된 질문
    - 스키마 검증기로 AI 친화도를 **수치화**할 수 있음
    - 피어리뷰는 "다른 사람 눈으로 내 설계를 보는" 기회
    - validate_schema() 점수가 80점 이상이면 합격

---
