# 3H · 집계 · 조인 · CTE · 윈도우 함수

## 학습목표

- `GROUP BY` / `HAVING`으로 데이터를 그룹화하고 필터링할 수 있다
- 다양한 `JOIN` 유형의 차이를 이해하고 적재적소에 사용할 수 있다
- 서브쿼리와 `CTE`로 복잡한 쿼리를 가독성 있게 구조화할 수 있다
- 윈도우 함수(`ROW_NUMBER`, `RANK`, `LAG` 등)의 기본 사용법을 익힌다

!!! tip "🧭 이 시간을 이렇게 읽으세요 (비개발자용)"
    - **한 줄 핵심**: 엑셀의 **피벗 테이블·VLOOKUP** 을 SQL 로 하는 법을 익힙니다.
    - **꼭 이해**: `GROUP BY` = 피벗(같은 값끼리 묶어 통계), `JOIN` = VLOOKUP(다른 표를 공통 컬럼으로 이어 붙이기). `WHERE`(그룹 전 필터) vs `HAVING`(그룹 후 필터) 의 순서.
    - **지금은 몰라도 OK**: 윈도우 함수 전 종류(`RANK / LAG / LEAD / NTILE` …). **`ROW_NUMBER` 한 가지** 만 이해해도 본 강의 전체에서 막힐 일 없습니다.
    - **막히면**: 모르는 단어는 [용어 사전](../appendix/glossary.md) 으로 → JOIN/GROUP BY/CTE/윈도우 함수 모두 비유와 함께 정리되어 있습니다.

---

<div class="colab-link" data-notebook="02_sql_aggregation_join"></div>

## GROUP BY — 엑셀의 "피벗 테이블"

!!! tip "GROUP BY = 엑셀 피벗 테이블"
    데이터를 그룹별로 묶어서 합계, 평균, 개수 등을 계산합니다.
    엑셀에서 피벗 테이블로 "부서별 매출 합계"를 구하는 것과 동일한 개념입니다.

### 집계 함수 요약

| 집계 함수 | 의미 | 엑셀 비유 |
|---|---|---|
| `COUNT(*)` | 행 수 | COUNTA |
| `COUNT(col)` | NULL이 아닌 값 수 | COUNTIF |
| `SUM(col)` | 합계 | SUM |
| `AVG(col)` | 평균 | AVERAGE |
| `MAX(col)` | 최대값 | MAX |
| `MIN(col)` | 최소값 | MIN |

### SQL 실행 순서 — WHERE vs HAVING

```
전체 데이터
  → ① FROM (테이블 선택)
  → ② WHERE (행 필터 — 그룹화 전)
  → ③ GROUP BY (그룹화)
  → ④ HAVING (그룹 필터 — 그룹화 후)
  → ⑤ SELECT (컬럼 선택 + 집계 계산)
  → ⑥ ORDER BY (정렬)
  → ⑦ LIMIT (행 수 제한)
```

!!! warning "WHERE vs HAVING 핵심 차이"
    - **WHERE**는 **그룹화 전**에 개별 행을 필터링합니다.
      예: `WHERE status = 'completed'` → 완료된 행만 남김
    - **HAVING**은 **그룹화 후**에 그룹 단위로 필터링합니다.
      예: `HAVING COUNT(*) >= 3` → 3건 이상인 그룹만 남김
    - WHERE에서는 집계 함수를 쓸 수 없습니다! (`WHERE COUNT(*) >= 3`은 오류)

### 예제 1: 진료과별 의사 수

```python
# 진료과별 의사 수 (피벗: 진료과 기준으로 의사 수 합산)
run_query("""
    SELECT d.name AS department, COUNT(*) AS doctor_count
    FROM doctors doc
    JOIN departments d ON d.department_id = doc.department_id
    GROUP BY d.name
    ORDER BY doctor_count DESC
""", "진료과별 의사 수")
```

### 예제 2: 월별 방문 통계

```python
# 월별 방문 건수 + 총 진료비 + 평균 진료비
run_query("""
    SELECT 
        TO_CHAR(visit_date, 'YYYY-MM') AS month,
        COUNT(*) AS visit_count,
        SUM(COALESCE(cost, 0)) AS total_cost,
        ROUND(AVG(cost), 0) AS avg_cost
    FROM visits
    WHERE status = 'completed'
    GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ORDER BY month
""", "월별 방문 통계")
```

### 예제 3: 혈액형별 환자 분포 (%)

```python
# 혈액형별 환자 수 + 비율 (윈도우 함수 SUM OVER 활용)
run_query("""
    SELECT 
        blood_type,
        COUNT(*) AS count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
    FROM patients
    GROUP BY blood_type
    ORDER BY count DESC
""", "혈액형별 환자 분포 (%)")
```

!!! note "핵심 정리"
    `SUM(COUNT(*)) OVER ()`는 전체 행 수를 구합니다.
    `OVER ()`에 PARTITION BY가 없으므로 전체를 하나의 그룹으로 봅니다.
    이렇게 하면 각 그룹의 비율(%)을 한 쿼리로 계산할 수 있습니다.

### 예제 4: HAVING — 3회 이상 방문 환자

```python
# HAVING: 그룹화 후 조건 필터 (3회 이상 방문한 환자만)
run_query("""
    SELECT 
        p.name,
        COUNT(*) AS visit_count,
        SUM(COALESCE(v.cost, 0)) AS total_cost
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE v.status = 'completed'
    GROUP BY p.name
    HAVING COUNT(*) >= 3
    ORDER BY visit_count DESC
""", "3회 이상 방문한 환자")
```

### 예제 5: 평균 급여 750만원 이상 진료과

```python
# 진료과별 평균 급여가 750만원 이상인 곳
run_query("""
    SELECT 
        d.name AS department,
        COUNT(*) AS doctors,
        ROUND(AVG(doc.salary), 0) AS avg_salary,
        MAX(doc.salary) AS max_salary
    FROM doctors doc
    JOIN departments d ON d.department_id = doc.department_id
    GROUP BY d.name
    HAVING AVG(doc.salary) >= 7500000
    ORDER BY avg_salary DESC
""", "평균 급여 750만원 이상 진료과")
```

---

## JOIN — 테이블 합치기

!!! tip "JOIN = 엑셀의 VLOOKUP"
    두 시트를 공통 열로 연결하여 하나의 표로 만듭니다.
    SQL에서는 이를 `JOIN`이라 하며, 결합 방식에 따라 여러 종류가 있습니다.

### JOIN 유형 비교 (벤 다이어그램)

```
테이블 A              테이블 B
┌─────────┐          ┌─────────┐
│         │          │         │
│    ┌────┼──────────┼────┐    │
│    │    │  INNER   │    │    │
│    │    │  JOIN    │    │    │
│    └────┼──────────┼────┘    │
│         │          │         │
└─────────┘          └─────────┘

INNER JOIN: 양쪽 모두에 있는 교집합만 반환
  A ∩ B

LEFT JOIN: 왼쪽 A의 모든 행 + 매칭되는 B (매칭 없으면 NULL)
  A + (A ∩ B)

RIGHT JOIN: 오른쪽 B의 모든 행 + 매칭되는 A (매칭 없으면 NULL)
  (A ∩ B) + B

FULL OUTER JOIN: 양쪽 모두 (매칭 없으면 NULL)
  A + B

SELF JOIN: 같은 테이블을 자기 자신과 결합
  A ⟕ A
```

### 예제 1: INNER JOIN — 완료된 진료 기록

```python
# INNER JOIN: 양쪽 모두 매칭되는 행만
# 환자명, 의사명을 함께 보려면 3개 테이블을 JOIN
run_query("""
    SELECT 
        p.name AS patient_name,
        d.name AS doctor_name,
        v.visit_date,
        v.chief_complaint
    FROM visits v
    INNER JOIN patients p ON p.patient_id = v.patient_id
    INNER JOIN doctors d ON d.doctor_id = v.doctor_id
    WHERE v.status = 'completed'
    ORDER BY v.visit_date DESC
    LIMIT 10
""", "INNER JOIN — 완료된 진료 기록 (최근 10건)")
```

### 예제 2: LEFT JOIN — 미방문 환자 포함

```python
# LEFT JOIN: 왼쪽(patients) 전체 + 오른쪽(visits) 매칭
# 방문 기록이 없는 환자도 포함 → visit_count = 0
run_query("""
    SELECT 
        p.name,
        COUNT(v.visit_id) AS visit_count
    FROM patients p
    LEFT JOIN visits v ON v.patient_id = p.patient_id
    GROUP BY p.patient_id, p.name
    ORDER BY visit_count, p.name
""", "LEFT JOIN — 모든 환자의 방문 횟수 (0건 포함)")
```

!!! warning "COUNT(*) vs COUNT(col) 차이"
    - `COUNT(*)` : NULL 행도 포함하여 카운트 → LEFT JOIN에서 0건인 환자도 1로 표시됨
    - `COUNT(v.visit_id)` : NULL이 아닌 값만 카운트 → 미방문 환자는 정확히 0으로 표시
    - LEFT JOIN + GROUP BY에서는 반드시 `COUNT(오른쪽_컬럼)` 사용!

### 예제 3: LEFT JOIN + IS NULL — 한번도 미방문

```python
# LEFT JOIN + IS NULL: "한 번도 방문하지 않은 환자"
# 오른쪽 테이블의 PK가 NULL이면 매칭 실패 → 미방문
run_query("""
    SELECT p.name, p.phone
    FROM patients p
    LEFT JOIN visits v ON v.patient_id = p.patient_id
    WHERE v.visit_id IS NULL
""", "LEFT JOIN + IS NULL — 미방문 환자")
```

### 예제 4: SELF JOIN — 같은 진료과 의사 쌍

```python
# SELF JOIN: 같은 테이블을 자기 자신과 JOIN
# a.doctor_id < b.doctor_id 로 중복 쌍 방지
run_query("""
    SELECT 
        a.name AS doctor_a,
        b.name AS doctor_b,
        d.name AS department
    FROM doctors a
    JOIN doctors b ON a.department_id = b.department_id 
                  AND a.doctor_id < b.doctor_id
    JOIN departments d ON d.department_id = a.department_id
    ORDER BY department, doctor_a
""", "SELF JOIN — 같은 진료과 의사 쌍")
```

!!! tip "SELF JOIN 활용 사례"
    - 같은 부서의 직원 쌍 찾기
    - 친구 관계 (A-B, B-A 중복 방지)
    - 조직도에서 상사-부하 관계
    - 같은 날짜에 방문한 환자 쌍

---

## 서브쿼리 — 쿼리 안의 쿼리

서브쿼리는 SQL 문 안에 포함된 또 다른 SQL 문입니다. 위치에 따라 용도가 달라집니다.

### WHERE절 서브쿼리: 평균보다 급여가 높은 의사

```python
# WHERE절 서브쿼리: 안쪽 쿼리의 결과를 조건으로 사용
run_query("""
    SELECT name, salary
    FROM doctors
    WHERE salary > (SELECT AVG(salary) FROM doctors)
    ORDER BY salary DESC
""", "평균 급여 이상인 의사")
```

### FROM절 서브쿼리: 진료과별 최고 급여 의사

```python
# FROM절 서브쿼리 (인라인 뷰): 서브쿼리 결과를 테이블처럼 사용
run_query("""
    SELECT sub.department, sub.doctor_name, sub.salary
    FROM (
        SELECT 
            d.name AS department,
            doc.name AS doctor_name,
            doc.salary,
            ROW_NUMBER() OVER (PARTITION BY d.department_id ORDER BY doc.salary DESC) AS rn
        FROM doctors doc
        JOIN departments d ON d.department_id = doc.department_id
    ) sub
    WHERE sub.rn = 1
    ORDER BY sub.salary DESC
""", "진료과별 최고 급여 의사")
```

### EXISTS 서브쿼리: 진단 기록이 있는 방문

```python
# EXISTS: 서브쿼리에 결과가 존재하면 TRUE
# IN보다 대용량 데이터에서 효율적 (조기 종료 가능)
run_query("""
    SELECT v.visit_id, p.name, v.visit_date
    FROM visits v
    JOIN patients p ON p.patient_id = v.patient_id
    WHERE EXISTS (
        SELECT 1 FROM diagnoses dg WHERE dg.visit_id = v.visit_id
    )
    ORDER BY v.visit_date DESC
    LIMIT 10
""", "진단 기록이 존재하는 방문")
```

!!! note "핵심 정리"
    | 서브쿼리 위치 | 반환 | 용도 |
    |---|---|---|
    | WHERE절 | 단일 값 또는 목록 | 조건 비교 |
    | FROM절 | 테이블 (인라인 뷰) | 임시 테이블로 활용 |
    | EXISTS | TRUE/FALSE | 존재 여부 확인 |

---

## CTE — "단계별 레시피"

!!! tip "CTE(Common Table Expression) = 요리 레시피"
    복잡한 요리를 단계별로 나누어 만드는 것처럼, 복잡한 SQL을 단계별로 나눕니다.
    `WITH` 키워드로 시작하며, 여러 단계를 쉼표(`,`)로 연결합니다.

    **CTE vs 서브쿼리** — 같은 결과를 낼 수 있지만:

    - CTE는 이름을 붙여서 **가독성**이 높음
    - CTE는 여러 번 참조 가능 (서브쿼리는 매번 반복 작성)
    - CTE는 **디버깅이 쉬움** (단계별로 따로 실행 가능)

### 2단계 CTE: 월별 방문 vs 전체 평균 비교

```python
# CTE 없이 → 읽기 어려운 중첩 쿼리
# CTE 사용 → 단계별로 명확하게

run_query("""
    WITH monthly_visits AS (
        -- 1단계: 월별 방문 집계 (재료 준비)
        SELECT
            TO_CHAR(visit_date, 'YYYY-MM') AS month,
            COUNT(*) AS cnt
        FROM visits
        WHERE status = 'completed'
        GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ),
    avg_visits AS (
        -- 2단계: 전체 월 평균 계산 (소스 만들기)
        SELECT AVG(cnt) AS avg_cnt FROM monthly_visits
    )
    -- 3단계: 비교 (완성!)
    SELECT
        mv.month,
        mv.cnt AS visits,
        ROUND(av.avg_cnt, 1) AS overall_avg,
        CASE WHEN mv.cnt > av.avg_cnt THEN '평균 이상'
             ELSE '평균 미만' END AS status
    FROM monthly_visits mv
    CROSS JOIN avg_visits av   -- av는 1행짜리 스칼라 → CROSS JOIN 이 의도를 명확히 표현
    ORDER BY mv.month
""", "CTE — 월별 방문 vs 평균 비교")
```

!!! note "핵심 정리"
    CTE를 읽을 때는 위에서 아래로 "1단계 → 2단계 → 최종"으로 순서대로 읽으면 됩니다.
    각 CTE 블록은 독립적으로 실행해볼 수 있어 디버깅이 쉽습니다.

!!! tip "`FROM a, b` 쉼표 조인은 피하세요"
    `FROM monthly_visits mv, avg_visits av` 처럼 **쉼표로 나열하는 것도 작동**하지만 이는 암묵적 `CROSS JOIN` 입니다. 의도가 감춰져서:

    - 리뷰어가 "JOIN 조건 빠뜨린 거 아닌가?" 하고 오해합니다.
    - 양쪽이 여러 행이면 **행 수가 곱해져** 성능 장애의 원인이 됩니다.

    1행짜리 스칼라와 곱할 때는 위처럼 `CROSS JOIN`을 명시하거나, **스칼라 서브쿼리**로 바꾸세요:

    ```sql
    SELECT month, cnt,
           (SELECT AVG(cnt) FROM monthly_visits) AS overall_avg
    FROM monthly_visits;
    ```

---

## 윈도우 함수 — "모든 행에 메모 추가하기"

!!! tip "윈도우 함수 vs GROUP BY 차이"
    - **GROUP BY**: 그룹별로 **한 행으로 요약** (10행 -> 3행)
    - **윈도우 함수**: 원래 행을 유지하면서 **추가 정보를 옆에 붙임** (10행 -> 10행 + 추가 열)

    ```
    GROUP BY:     10행 ──────→ 3행 (그룹별 합계)
    윈도우 함수:   10행 ──────→ 10행 + 새 컬럼 (각 행에 순위/누적값)
    ```

!!! note "언제 윈도우 함수를 꺼내야 하나? -- 신호 5가지"
    질문에 다음 표현이 등장하면 **윈도우 함수가 정답일 확률이 높습니다**. 조인+서브쿼리로 풀 수 있어도 코드가 길어지고 성능도 나빠집니다.

    | 질문 유형 | 신호 표현 | 적합한 함수 |
    |---|---|---|
    | 순위 | "가장 많이 ... Top N", "N위", "등수", "진료과별 가장 ..." | `ROW_NUMBER() / RANK() / DENSE_RANK()` |
    | 직전 값 비교 | "전월 대비", "이전 방문과 차이", "증감" | `LAG() / LEAD()` |
    | 누적 | "누적 매출", "월초부터 지금까지 합계" | `SUM() OVER (ORDER BY ...)` |
    | 이동평균 | "최근 N일/N건 평균", "moving average" | `AVG() OVER (ROWS BETWEEN ...)` |
    | 비율 | "전체 중 비중 %", "카테고리 내 점유율" | `SUM(x) / SUM(x) OVER (PARTITION BY ...)` |

    공통 패턴: "**그룹별 요약값**이 아니라, 각 행 옆에 **추가 정보**가 필요한가?" → 예라면 윈도우 함수.

    헷갈릴 때 가장 쉬운 판별법: 원하는 **결과 행 수**가 원래 테이블과 **같아야** 한다면 윈도우 함수, **줄어들어야** 한다면 GROUP BY.

### 기본 구문

```sql
함수() OVER (
    PARTITION BY 그룹_컬럼     -- 어떤 그룹 안에서? (생략 = 전체)
    ORDER BY 정렬_컬럼         -- 어떤 순서로?
    ROWS BETWEEN ... AND ...  -- 범위 지정 (선택)
)
```

### 예제 1: ROW_NUMBER — 전체 순위 vs 진료과별 순위

```python
# ROW_NUMBER: 순번 부여 (중복 없이 1, 2, 3, ...)
run_query("""
    SELECT
        name, salary,
        department_id,
        ROW_NUMBER() OVER (ORDER BY salary DESC) AS overall_rank,
        ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dept_rank
    FROM doctors
""", "ROW_NUMBER — 전체 순위 vs 진료과별 순위")
```

!!! note "핵심 정리"
    - `OVER (ORDER BY salary DESC)` → **전체**에서 급여 높은 순으로 번호
    - `OVER (PARTITION BY department_id ORDER BY salary DESC)` → **진료과별로** 급여 높은 순 번호
    - `PARTITION BY`는 GROUP BY처럼 그룹을 나누되, 행을 합치지 않음

### 예제 2: RANK vs DENSE_RANK — 동점 처리

```python
# RANK vs DENSE_RANK: 동점일 때 순위가 다르게 매겨짐
run_query("""
    SELECT
        name, salary,
        RANK() OVER (ORDER BY salary DESC) AS rank,
        DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
    FROM doctors
    ORDER BY salary DESC
""", "RANK vs DENSE_RANK 비교")
```

```
RANK:       공동 1위 2명 → 다음은 3위 (2위를 건너뜀)
              1, 1, 3, 4, 5, ...

DENSE_RANK: 공동 1위 2명 → 다음은 2위 (건너뛰지 않음)
              1, 1, 2, 3, 4, ...

ROW_NUMBER: 동점이어도 중복 없이 유일한 번호
              1, 2, 3, 4, 5, ...
```

### 예제 3: LAG — 전월 대비 증감

```python
# LAG: "이전 행의 값"을 참조 (LEAD는 "다음 행")
run_query("""
    SELECT
        TO_CHAR(visit_date, 'YYYY-MM') AS month,
        COUNT(*) AS visits,
        LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS prev_month,
        COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY TO_CHAR(visit_date, 'YYYY-MM')) AS diff
    FROM visits
    WHERE status = 'completed'
    GROUP BY TO_CHAR(visit_date, 'YYYY-MM')
    ORDER BY month
""", "LAG — 전월 대비 방문 증감")
```

!!! tip "LAG / LEAD 활용"
    - `LAG(col)` : 이전 행의 값 → 전월 대비, 전일 대비 비교
    - `LEAD(col)` : 다음 행의 값 → 다음 달 예측치와 비교
    - `LAG(col, 2)` : 2행 이전의 값 → 2개월 전과 비교
    - 첫 번째 행의 LAG는 NULL → `COALESCE`로 기본값 지정 가능

### 예제 4: SUM OVER — 누적 합계 + 이동평균

```python
# SUM OVER: 누적 합계 (Running Total)
# AVG OVER ROWS: 이동 평균 (Moving Average)
run_query("""
    SELECT
        visit_date,
        cost,
        SUM(cost) OVER (ORDER BY visit_date) AS running_total,
        AVG(cost) OVER (ORDER BY visit_date 
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3
    FROM visits
    WHERE status = 'completed' AND cost > 0
    ORDER BY visit_date
    LIMIT 15
""", "SUM OVER — 누적 진료비 + 3건 이동평균")
```

!!! note "핵심 정리"
    - `SUM(cost) OVER (ORDER BY visit_date)` → 날짜순 누적 합계
    - `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` → 현재 행 포함 최근 3건
    - 이동평균은 트렌드 파악에 유용 (주식 차트의 이동평균선과 동일 개념)

---

## 윈도우 함수 종합 정리

| 함수 | 용도 | 예시 |
|---|---|---|
| `ROW_NUMBER()` | 유일한 순번 | 그룹 내 Top-N 추출 |
| `RANK()` | 동점 허용 순위 (건너뜀) | 성적 등수 |
| `DENSE_RANK()` | 동점 허용 순위 (안 건너뜀) | 급여 등급 |
| `LAG(col)` | 이전 행 참조 | 전월 대비 증감 |
| `LEAD(col)` | 다음 행 참조 | 다음 달 예측 비교 |
| `SUM() OVER` | 누적/이동 합계 | 누적 매출 |
| `AVG() OVER` | 이동 평균 | 3개월 이동평균 |
| `NTILE(n)` | n등분 | 상위 25% 환자 |

---

## 실습 과제

!!! example "실습 — 각 의사별 최근 진료 환자 3명"
    **문제**: 각 의사별로 가장 최근에 진료한 환자 3명을 추출하세요.

    **힌트**: 윈도우 함수 + CTE 조합

    - CTE에서 `ROW_NUMBER()`로 의사별 최근 방문에 순번 부여
    - 외부 쿼리에서 `rn <= 3` 필터
    - 의사 이름, 환자 이름, 방문일 출력

    기대 결과:

    ```
    doctor_name | patient_name | visit_date | visit_rank
    김철수       | 홍길동        | 2026-04-01 | 1
    김철수       | 홍길동        | 2026-01-10 | 2
    ...
    ```

    **정답:**

    ```sql
    WITH ranked AS (
        SELECT
            d.name AS doctor_name,
            p.name AS patient_name,
            v.visit_date,
            ROW_NUMBER() OVER (
                PARTITION BY v.doctor_id 
                ORDER BY v.visit_date DESC
            ) AS rn
        FROM visits v
        JOIN doctors d ON d.doctor_id = v.doctor_id
        JOIN patients p ON p.patient_id = v.patient_id
    )
    SELECT doctor_name, patient_name, visit_date, rn AS visit_rank
    FROM ranked
    WHERE rn <= 3
    ORDER BY doctor_name, visit_rank;
    ```

!!! example "추가 실습 — 진료과별 월 매출 추이"
    **문제**: 각 진료과별로 월별 진료비 합계를 구하고, 전월 대비 증감을 표시하세요.

    **힌트**: GROUP BY + LAG 윈도우 함수 조합

    ```sql
    WITH monthly_dept_revenue AS (
        SELECT 
            dept.name AS department,
            TO_CHAR(v.visit_date, 'YYYY-MM') AS month,
            SUM(COALESCE(v.cost, 0)) AS revenue
        FROM visits v
        JOIN doctors d ON d.doctor_id = v.doctor_id
        JOIN departments dept ON dept.department_id = d.department_id
        WHERE v.status = 'completed'
        GROUP BY dept.name, TO_CHAR(v.visit_date, 'YYYY-MM')
    )
    SELECT 
        department,
        month,
        revenue,
        LAG(revenue) OVER (PARTITION BY department ORDER BY month) AS prev_month_revenue,
        revenue - LAG(revenue) OVER (PARTITION BY department ORDER BY month) AS diff
    FROM monthly_dept_revenue
    ORDER BY department, month;
    ```

!!! example "도전 과제 — 재방문율이 가장 높은 진료과"
    **문제**: 2회 이상 방문한 환자 비율이 가장 높은 진료과를 구하세요.

    **힌트**: 

    1. 진료과별 전체 고유 환자 수와 2회 이상 방문 환자 수를 구한다
    2. (2회이상 환자 / 전체 환자) * 100 = 재방문율

    ```sql
    WITH dept_patient_visits AS (
        SELECT 
            dept.name AS department,
            v.patient_id,
            COUNT(*) AS visit_count
        FROM visits v
        JOIN doctors d ON d.doctor_id = v.doctor_id
        JOIN departments dept ON dept.department_id = d.department_id
        WHERE v.status = 'completed'
        GROUP BY dept.name, v.patient_id
    )
    SELECT 
        department,
        COUNT(*) AS total_patients,
        COUNT(*) FILTER (WHERE visit_count >= 2) AS returning_patients,
        ROUND(
            COUNT(*) FILTER (WHERE visit_count >= 2) * 100.0 / COUNT(*), 
            1
        ) AS return_rate_pct
    FROM dept_patient_visits
    GROUP BY department
    ORDER BY return_rate_pct DESC;
    ```

    `FILTER (WHERE ...)` 구문은 PostgreSQL 전용이며, 집계 함수에 조건을 걸 수 있는 편리한 기능입니다.

!!! question "생각해보기"
    1. GROUP BY + HAVING으로 구한 결과를 윈도우 함수로도 구할 수 있을까요? 어떤 경우에 어떤 것이 더 적합할까요?
    2. SELF JOIN은 어떤 비즈니스 시나리오에서 유용할까요? 3가지 사례를 생각해보세요.
    3. CTE와 임시 테이블(TEMP TABLE)의 차이는 무엇일까요?

---

## 핵심 정리

!!! note "핵심 정리"
    - **GROUP BY** = 피벗 테이블 (그룹화 + 집계). HAVING으로 그룹 필터링
    - **JOIN** = VLOOKUP (테이블 결합). INNER는 교집합, LEFT는 왼쪽 전체
    - **서브쿼리** = WHERE/FROM/EXISTS에서 사용. CTE로 대체하면 가독성 향상
    - **CTE** = 단계별 레시피 (복잡한 쿼리를 읽기 쉽게, 디버깅 쉽게)
    - **윈도우 함수** = 행을 줄이지 않고 순위/누적/비교 추가. PARTITION BY로 그룹 지정
