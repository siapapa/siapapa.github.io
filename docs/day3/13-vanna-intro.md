# 13H -- Vanna.ai 구조

## 학습목표

- Vanna.ai의 RAG 기반 Text-to-SQL 아키텍처를 이해한다
- LlamaIndex Text-to-SQL과 Vanna의 차이를 비교 분석할 수 있다
- 학습 자산 3종(DDL / Documentation / SQL Pairs)의 역할을 설명할 수 있다

---

<div class="colab-link" data-notebook="10_vanna_intro"></div>

## LlamaIndex vs Vanna 비교

!!! tip "두 접근법을 한 줄로 비교"
    **LlamaIndex** = "전체 레시피북을 매번 펼쳐주는 방식". 스키마 전체를 AI에게 보여줌.
    **Vanna** = "학습하는 요리사". 비슷한 요리를 해본 경험을 기억하고, 새 주문에 적용.

### 아키텍처 차이

```
LlamaIndex NLSQLTableQueryEngine (프롬프트 중심):
  질문 --> [스키마 전체를 프롬프트에 주입] --> LLM --> SQL

Vanna.ai (RAG/검색 중심):
  질문 --> [유사한 DDL/문서/SQL쌍 검색] --> [검색 결과를 프롬프트에 주입] --> LLM --> SQL
```

### 상세 비교표

| 특성 | LlamaIndex | Vanna |
|---|---|---|
| **프롬프트 구성** | 전체 스키마 고정 주입 | 질문에 관련된 것만 검색/주입 |
| **테이블 30개 이상** | 토큰 초과/정확도 하락 | 관련 테이블만 검색하여 확장 가능 |
| **학습** | few-shot 수동 추가 | DDL/문서/SQL쌍을 누적 학습 |
| **정확도 개선** | 프롬프트 튜닝 | 학습 자산 추가 -- 자동 개선 |
| **설정 난이도** | 간단 (스키마 연결만 하면 됨) | 약간 복잡 (초기 학습 필요) |
| **대규모 DB 적합도** | 낮음 (토큰 한계) | 높음 (검색 기반 확장) |
| **비용 효율** | 매 질문마다 전체 스키마 토큰 소모 | 관련 부분만 토큰 소모 |

!!! question "생각해보기"
    여러분의 프로젝트 DB에는 테이블이 몇 개인가요? 5개? 10개? 30개 이상?
    테이블 수에 따라 어떤 접근법이 더 적합할지 생각해 보세요.

---

## Vanna 내부 RAG 검색 흐름

Vanna는 질문을 받으면 내부적으로 3개의 벡터 컬렉션을 검색합니다.

```
사용자 질문: "지난달 매출 상위 5개 제품은?"
         |
         v
+------------------------------------------+
|  1. 벡터 검색 (ChromaDB)                   |
|     +-- DDL 컬렉션에서 관련 스키마           | --> CREATE TABLE products (...), orders (...)
|     +-- 문서 컬렉션에서 비즈니스 룰           | --> "매출 = orders.total_amount"
|     +-- SQL 쌍 컬렉션에서 유사 예시           | --> ("매출 Top 5", "SELECT ... ORDER BY ... LIMIT 5")
|                                            |
|  2. 컨텍스트 조립                           |
|     DDL + 문서 + SQL 예시를 합침             |
|                                            |
|  3. LLM 호출                               |
|     컨텍스트 + 질문 --> SQL 생성              |
+------------------------------------------+
         |
         v
SQL: SELECT p.name, SUM(o.total_amount) AS revenue
     FROM products p JOIN orders o ...
     ORDER BY revenue DESC LIMIT 5;
```

!!! note "핵심 정리"
    Vanna의 핵심 아이디어: **"전체 스키마를 매번 주입하지 않고, 질문에 관련된 정보만 검색하여 프롬프트를 구성한다."**
    이것이 RAG 기반 Text-to-SQL의 본질입니다.

---

## 학습 자산 3종

Vanna가 학습하는 데이터는 3가지 종류입니다.

| 종류 | 설명 | 예시 | 비유 |
|---|---|---|---|
| **DDL** | 테이블 구조 정보 | `CREATE TABLE patients (patient_id INT, ...)` | 재료 목록 |
| **Documentation** | 비즈니스 용어/규칙 | "visits.status='completed'만 유효한 진료" | 조리법 메모 |
| **SQL Pairs** | (질문, 정답SQL) 쌍 | ("환자 수?", "SELECT COUNT(*) FROM patients") | 이전에 만든 요리 사진 |

!!! tip "학습 자산 우선순위"
    실무에서는 **DDL을 가장 먼저** 학습시킵니다. 테이블 구조를 모르면 SQL을 생성할 수 없습니다.
    다음으로 **Documentation**으로 비즈니스 규칙을 알려주고,
    마지막으로 **SQL Pairs**로 정답 예시를 제공하면 정확도가 크게 향상됩니다.

---

## Vanna 설치 및 초기 설정

```python
# ============================================================
# 1. Vanna 설치 (ChromaDB + OpenAI 백엔드)
# ============================================================
!pip install -q 'vanna[chromadb,openai]'

import os
import vanna
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore
```

### MyVanna 클래스 정의

Vanna는 벡터 저장소와 LLM 백엔드를 조합하여 사용합니다. 다중 상속으로 두 기능을 결합합니다.

```python
# ============================================================
# 2. MyVanna 클래스 정의 (ChromaDB + OpenAI 조합)
# ============================================================
class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

vn = MyVanna(config={
    "api_key": os.environ["OPENAI_API_KEY"],
    "model": "gpt-4o-mini",
})
```

!!! note "핵심 정리"
    `MyVanna`는 두 개의 부모 클래스를 결합합니다:

    - `ChromaDB_VectorStore`: DDL/문서/SQL 쌍을 벡터로 저장하고 검색
    - `OpenAI_Chat`: 검색 결과 + 질문을 OpenAI LLM에 전달하여 SQL 생성

---

## Neon PostgreSQL 연결

```python
# ============================================================
# 3. Neon PostgreSQL 연결
# ============================================================
from urllib.parse import urlparse

# Neon DSN 구조: postgresql://user:password@host/dbname?sslmode=require
#   → 특수문자 비밀번호·리전 접미사가 있어 수기 split 파싱은 쉽게 깨집니다.
#   반드시 urlparse + sslmode="require" 로 연결하세요.
parsed = urlparse(os.environ["NEON_DSN"])

vn.connect_to_postgres(
    host=parsed.hostname,
    dbname=parsed.path.lstrip("/"),
    user=parsed.username,
    password=parsed.password,
    port=parsed.port or 5432,
    sslmode="require",   # Neon 은 SSL 필수 — 누락 시 연결 거부
)

print("✅ Vanna + Neon 연결 완료!")
```

!!! warning "DSN 파싱·SSL 체크리스트"
    - 수기 `.split("@")`, `.split(":")` 파싱은 `password` 에 `@` `:` `/` 같은 특수문자가 섞이면 바로 깨집니다. `urllib.parse.urlparse()` 로 통일하세요.
    - Neon 은 기본적으로 `sslmode=require` 가 필요합니다. `connect_to_postgres(sslmode="require")` 를 빼먹거나, DSN 끝에 `?sslmode=require` 가 빠지면 `SSL required` 오류로 연결이 거부됩니다.
    - 환경변수로 대체하려면 `os.environ["PGSSLMODE"] = "require"` 를 부트스트랩 셀에 추가해도 됩니다.

---

## 베이스라인 테스트 (학습 전)

학습 자산 없이 바로 질문하여 Vanna의 기본 성능을 확인합니다.

```python
# ============================================================
# 4. 학습 없이 바로 질문 (베이스라인)
# ============================================================

# 학습 자산 없이 질문 -- 정확도가 낮을 수 있음
baseline_sql = vn.generate_sql("환자 수는 몇 명인가요?")
print(f"📝 베이스라인 SQL: {baseline_sql}")

try:
    result = vn.run_sql(baseline_sql)
    print(f"📊 결과:\n{result}")
except Exception as e:
    print(f"❌ 에러: {e}")
```

!!! warning "베이스라인 결과가 부정확할 수 있습니다"
    학습 자산 없이는 Vanna가 테이블 구조를 정확히 모르기 때문에 잘못된 SQL을 생성할 수 있습니다.
    이것이 정상입니다! 14H에서 학습 후 정확도가 어떻게 변하는지 비교할 것입니다.

---

## 현재 학습 자산 확인

```python
# ============================================================
# 5. 현재 학습 자산 확인
# ============================================================
training_data = vn.get_training_data()
print(f"📚 현재 학습 자산 수: {len(training_data) if training_data is not None else 0}")
if training_data is not None and len(training_data) > 0:
    print(training_data.head())
```

---

## 베이스라인 정답률 측정

!!! example "실습 -- 베이스라인 5개 질문 테스트"
    학습 전 상태에서 5개 질문을 테스트하고 정답률을 기록하세요.
    14H에서 학습 후 결과와 비교할 것입니다.

    아래 5개 질문에 대해 학습 자산 없이 `vn.generate_sql()` + `vn.run_sql()` 을 실행하고, `pandas` DataFrame 으로 결과표를 만들어 정답률(`✅ 성공` 비율)을 출력하세요.

    | # | 질문 | 기대 형식 |
    |---|---|---|
    | 1 | 전체 환자 수는 몇 명인가요? | 단일 숫자 |
    | 2 | 남성 환자 수는? | 단일 숫자 |
    | 3 | 진료과별 의사 수를 보여줘 | 진료과-의사수 표 |
    | 4 | 지난달 완료 진료 건수는? | 단일 숫자 |
    | 5 | 가장 많이 방문한 환자 Top 5는? | 환자명-방문수 표 |

    *힌트: `try/except` 로 SQL 생성·실행 실패를 분류하고, 결과를 리스트에 모아 `pd.DataFrame` 으로 출력하세요. 정답률은 성공 건수를 전체 건수로 나눠 계산합니다.*

    **예상 결과 (학습 전):**

    | 질문 | 기대 형식 | 결과 |
    |---|---|---|
    | 전체 환자 수는 몇 명인가요? | 단일 숫자 | ✅ 또는 ❌ |
    | 남성 환자 수는? | 단일 숫자 | ❌ (gender 컬럼 모름) |
    | 진료과별 의사 수를 보여줘 | 진료과-의사수 표 | ❌ (JOIN 관계 모름) |
    | 지난달 완료 진료 건수는? | 단일 숫자 | ❌ (status 조건 모름) |
    | 가장 많이 방문한 환자 Top 5는? | 환자명-방문수 표 | ❌ (복잡한 JOIN) |

    학습 전에는 보통 **0~2개 정도만 정답**입니다.
    14H에서 학습 후 **8~10개 정답**을 목표로 합니다.

---

## 실습 과제

1. 학습 자산 없이 5개 질문을 테스트하고 정답률을 기록하세요.
2. 어떤 질문이 실패하는지 분류하세요:
    - 스키마를 몰라서 실패한 경우 (DDL 학습 필요)
    - 비즈니스 용어를 몰라서 실패한 경우 (Documentation 학습 필요)
    - 복잡한 쿼리라서 실패한 경우 (SQL Pairs 학습 필요)

!!! question "생각해보기"
    실패한 질문들을 보고, **어떤 학습 자산을 추가하면 해결될지** 분류해 보세요.
    이 분류가 14H에서의 학습 전략을 결정합니다.

---

!!! note "핵심 정리"
    - **Vanna** = RAG 기반 Text-to-SQL. 학습할수록 정확도 향상
    - **LlamaIndex와 차이**: LlamaIndex는 전체 스키마 주입, Vanna는 관련 정보만 검색/주입
    - **학습 자산 3종**: DDL(스키마), Documentation(규칙), SQL Pairs(예시)
    - **베이스라인 측정**: 학습 전 정확도를 먼저 기록 -- 14H에서 학습 후 비교하여 개선 효과 확인
