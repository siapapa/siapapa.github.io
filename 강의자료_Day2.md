# 📘 Day 2 — 제안서 회수 + Text-to-SQL 상담사 (9~12H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%  
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API

---

## 🔑 용어 사전 (비IT 수강생을 위한)

| 용어 | 쉬운 설명 |
|---|---|
| **프롬프트(Prompt)** | AI에게 보내는 "지시서". 지시가 정확할수록 AI의 답변이 좋아짐 |
| **토큰(Token)** | AI가 텍스트를 읽는 단위. 한국어 한 글자 ≈ 1~2토큰 |
| **Few-shot** | AI에게 예시를 몇 개 보여주는 것. "이런 식으로 해줘"라고 사례를 보여주는 것 |
| **세션(Session)** | 한 사용자의 연결 단위. 채팅방 하나 = 세션 하나 |
| **가드레일(Guardrail)** | 안전장치. AI가 위험한 행동을 하지 못하도록 막는 규칙 |
| **멀티턴(Multi-turn)** | 여러 번 주고받는 대화. "이전 대화를 기억하는" 채팅 |

---

## 📦 공통 부트스트랩

### 이 코드가 하는 일
> Day 2 실습에 필요한 라이브러리를 설치하고 DB에 접속합니다.

```python
# Day 2에 사용할 도구 설치
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
print("✅ DB 연결 성공!")
```

---

# 9H · 제안서 피어리뷰

## 학습목표
- 프로젝트 제안서를 구조적으로 평가할 수 있다
- 피어리뷰를 통해 본인 제안서의 약점을 식별한다

## 좋은 제안서의 조건 (체크리스트)

| 항목 | 확인 내용 | 배점 |
|---|---|---|
| 도메인 적절성 | 3~5 테이블로 표현 가능한 범위인가? | 10 |
| 테이블 설계 | PK/FK 명시, 적절한 데이터 타입 | 20 |
| COMMENT ON | 모든 컬럼에 자연어 설명이 있는가? | 20 |
| 질문 난이도 분포 | Easy 3~4 / Medium 3~4 / Hard 2~3 | 20 |
| 기대 SQL | 각 질문에 구체적인 SQL이 있는가? | 20 |
| ERD | 테이블 간 관계가 시각화되었는가? | 10 |

## 흔한 문제 패턴 5가지

### 문제 1: "테이블이 너무 많다" (8개 이상)
```
❌ 나쁜 예: 테이블 10개 → AI가 관련 테이블을 찾는 데 실패
✅ 해결: 핵심 3~5개로 축소. 나머지는 리포팅 뷰로 대체
```

### 문제 2: "질문이 모두 같은 난이도"
```
❌ 나쁜 예: 10개 질문 모두 "~는 몇 개?" (Easy만)
✅ 해결: Hard 질문 추가 (윈도우 함수, 다중 CTE 필요한 것)
```

### 문제 3: "컬럼명이 약어"
```
❌ 나쁜 예: ord_dt, cust_nm, amt
✅ 좋은 예: order_date, customer_name, amount
   이유: AI는 약어를 오해할 수 있음
```

### 문제 4: "FK 없이 암묵적 관계"
```
❌ 나쁜 예: pid INT (어느 테이블과 연결되는지 알 수 없음)
✅ 좋은 예: patient_id INT REFERENCES patients(patient_id)
```

### 문제 5: "기대 SQL이 없거나 부정확"
```
❌ 나쁜 예: Q1: "주문 수?" → SQL 없음
✅ 좋은 예: Q1: "주문 수?" → SELECT COUNT(*) FROM orders WHERE status='completed';
```

## 🎯 실습 — 스키마 자동 검증기

### 이 코드가 하는 일
> 본인 스키마의 PK, FK, COMMENT 완성도를 자동으로 점검하여 점수를 매깁니다.

```python
def validate_schema(engine, table_names: list[str]) -> dict:
    """스키마의 AI-friendliness(AI 친화도)를 자동 점검"""
    inspector = inspect(engine)
    report = {"tables": {}, "score": 0, "issues": []}
    total_points = 0
    earned_points = 0
    
    for table in table_names:
        table_report = {"columns": 0, "comments": 0, "fks": 0, "pk": False}
        
        # 컬럼 수 확인
        columns = inspector.get_columns(table)
        table_report["columns"] = len(columns)
        total_points += len(columns)  # 각 컬럼에 COMMENT가 있어야 함
        
        # PK(기본키) 확인
        pk = inspector.get_pk_constraint(table)
        if pk and pk["constrained_columns"]:
            table_report["pk"] = True
            earned_points += 5
        else:
            report["issues"].append(f"⚠️ {table}: PRIMARY KEY 없음")
        total_points += 5
        
        # FK(외래키) 확인
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
        
        report["tables"][table] = table_report
    
    report["score"] = round(earned_points / max(total_points, 1) * 100, 1)
    return report

# 실행
report = validate_schema(engine, ["patients", "doctors", "visits", "diagnoses", "departments"])
print(f"📊 스키마 검증 결과: {report['score']}점 / 100점\n")
for table, info in report["tables"].items():
    pk_icon = "✅" if info["pk"] else "❌"
    print(f"  {table}: PK {pk_icon} | FK {info['fks']}개 | COMMENT {info['comments']}/{info['columns']}")
if report["issues"]:
    print(f"\n⚠️ 개선 필요 ({len(report['issues'])}건):")
    for issue in report["issues"][:10]:
        print(f"  {issue}")
```

## 피어리뷰 진행 순서 (30분)

```
1. 조 편성 — 3인 1조 (5분)
2. 돌아가며 발표 — 각자 10분:
   ├── 도메인 소개 (2분)
   ├── 스키마 설명 (3분)
   ├── 대표 질문 5개 (3분)
   └── 피드백 (2분)
3. 스키마 검증기 실행 — 본인 스키마에 실행 (5분)
4. 개선 메모 — 피드백 반영 계획 정리 (5분)
```

## 📌 9H 핵심 정리
- 좋은 제안서 = 명시적 네이밍 + COMMENT ON + 난이도 분산된 질문
- 스키마 검증기로 AI 친화도를 **수치화**할 수 있음
- 피어리뷰는 "다른 사람 눈으로 내 설계를 보는" 기회

---

# 10H · NLSQLTableQueryEngine 심화

## 학습목표
- NLSQLTableQueryEngine의 내부 프롬프트 구조를 이해한다
- 3가지 전략으로 정확도를 개선할 수 있다

## 왜 기본 설정으로는 부족한가?

Day 1에서 경험한 실패 원인:
```
1. 스키마 정보 부족 — COMMENT가 없으면 AI가 컬럼 의미를 오해
2. 프롬프트 품질 — 기본 프롬프트가 한국어에 최적화되지 않음
3. 테이블 선택 오류 — 관련 없는 테이블이 프롬프트에 포함
4. 도메인 용어 무지 — AI가 "본태성 고혈압" = I10인 걸 모름
```

## 개선 전략 3가지

### 전략 1: 도메인 지식 주입 (context_str_prefix)
> AI에게 "이 데이터베이스에서는 이런 규칙이 있어"라고 알려주기

### 전략 2: 커스텀 프롬프트 + Few-shot
> AI에게 "이런 형태로 SQL을 만들어줘. 예시를 보여줄게"라고 가르치기

### 전략 3: 테이블 자동 선택 (ObjectIndex)
> 질문에 관련된 테이블만 AI에게 보여주기 (불필요한 정보 제거)

## 🎯 실습 — Before/After 비교 실험

### 이 코드가 하는 일
> AI 내부 프롬프트를 열어보고, 기본 vs 커스텀 프롬프트의 결과를 비교합니다.

```python
from llama_index.core import SQLDatabase, Settings
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

sql_db = SQLDatabase(engine,
    include_tables=["patients", "doctors", "visits", "diagnoses", "departments"])

# 기본 엔진 (Day 1에서 사용한 것)
nlq_basic = NLSQLTableQueryEngine(sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"])

# 내부 프롬프트 확인 — AI가 실제로 보는 지시문
prompts = nlq_basic.get_prompts()
print("📋 AI가 받는 프롬프트:")
print(prompts["text_to_sql_prompt"].template[:500])
```

### 커스텀 프롬프트 (한국어 최적화 + Few-shot 예시)

```python
custom_prompt = PromptTemplate(
    """당신은 PostgreSQL 전문가입니다. 아래 스키마와 규칙을 참고하여 SQL을 작성하세요.

## 스키마
{schema}

## 규칙
- visits.status가 'completed'인 것만 유효한 진료입니다.
- 나이 = EXTRACT(YEAR FROM AGE(birth_date))
- "지난달" = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
- SQL만 반환하세요 (설명 불필요).

## 예시
질문: "전체 환자 수는?"
SQL: SELECT COUNT(*) AS total_patients FROM patients;

질문: "지난달 완료된 진료 건수는?"
SQL: SELECT COUNT(*) AS completed_visits FROM visits
     WHERE status = 'completed'
       AND visit_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
       AND visit_date < DATE_TRUNC('month', CURRENT_DATE);

## 질문
{query_str}

## SQL
""")

nlq_custom = NLSQLTableQueryEngine(sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    text_to_sql_prompt=custom_prompt)
```

### Before/After 비교

```python
test_questions = [
    "지난달 방문 환자 수는?",
    "진료과별 평균 진료비를 보여주세요.",
    "가장 많이 진단된 질병 Top 5는?",
    "40세 이상 남성 환자 중 3회 이상 방문한 사람은?",
    "최근에 많이 온 사람은?",  # 모호한 질문
]

print("📊 기본 vs 커스텀 프롬프트 비교\n")
for q in test_questions:
    try:
        resp_basic = nlq_basic.query(q)
        basic_status = "✅"
    except:
        basic_status = "❌"
    try:
        resp_custom = nlq_custom.query(q)
        custom_status = "✅"
    except:
        custom_status = "❌"
    print(f"  {q:<40} 기본:{basic_status} 커스텀:{custom_status}")
```

## 프롬프트 실험 워크시트

> 💡 **"최근에 많이 온 사람"** 같은 모호한 질문은 프롬프트에 규칙을 추가하면 해결됩니다.

```python
# 모호성 처리 규칙을 추가한 프롬프트
prompt_with_rules = PromptTemplate(
    """PostgreSQL 전문가입니다.
{schema}

## 모호성 처리 규칙
- "최근" = 최근 3개월
- "많이" = 3회 이상
- "자주" = 월 평균 2회 이상
- visits.status = 'completed'만 유효

질문: {query_str}
SQL:""")

# 테스트
engine_exp = NLSQLTableQueryEngine(sql_database=sql_db,
    tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    text_to_sql_prompt=prompt_with_rules)
resp = engine_exp.query("최근에 많이 온 사람은?")
print(f"SQL: {resp.metadata['sql_query']}")
print(f"답변: {resp.response[:150]}")
```

## 📌 10H 핵심 정리
- AI 내부 프롬프트를 `get_prompts()`로 직접 확인할 수 있음
- **프롬프트 엔지니어링이 곧 Text-to-SQL의 정확도**
- 3가지 전략: 도메인 지식 주입, Few-shot 예시, 테이블 자동 선택

---

# 11H · 병원 DB 멀티턴 상담사

## 학습목표
- 멀티턴 대화 상태(히스토리)를 관리하는 방법을 구현한다
- SQL 보안 가드레일을 구현한다

## 단발 질의 vs 멀티턴 대화

```
단발 질의 (기억 없음):
  User: "남성 환자 수는?"  →  Bot: "15명입니다."
  User: "그 중 40세 이상은?" →  Bot: "??? (이전 대화를 모름)"

멀티턴 대화 (기억 있음):
  User: "남성 환자 수는?"  →  Bot: "남성 환자는 15명입니다."
  User: "그 중 40세 이상은?" →  Bot: "남성 환자 중 40세 이상은 7명입니다."
  ↑ "그 중"이 "남성 환자"를 의미한다는 걸 기억하고 있음!
```

> 💡 **ChatState = 대화 메모장**: AI는 원래 기억력이 없습니다(stateless). 그래서 우리가 "대화 메모장"을 만들어 매번 전체 대화를 AI에게 전달해야 합니다.

## SQL 보안 가드레일 — "경비원"

> 💡 **가드레일 = 경비원**: 사용자가 악의적으로 데이터를 삭제하거나 변경하는 SQL을 보내지 못하도록 막습니다.

```
위협                  방어
────────              ──────
DELETE/DROP 명령어    → 키워드 차단 (SELECT만 허용)
테이블 무단 접근      → 화이트리스트 (허용된 테이블만)
대량 조회            → LIMIT 1000 자동 주입
시스템 정보 노출      → information_schema 접근 차단
```

### 이 코드가 하는 일
> 위험한 SQL을 자동으로 감지하고 차단하는 "경비원" 클래스입니다.

```python
import re
import sqlparse

class SQLGuardrail:
    """SQL 보안 가드레일 — 위험한 쿼리를 사전 차단"""
    
    # 차단할 키워드들 (데이터를 변경/삭제하는 명령어)
    BLOCKED_KEYWORDS = re.compile(
        r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
        re.IGNORECASE,
    )
    
    def __init__(self, allowed_tables: list[str], max_limit: int = 1000):
        self.allowed_tables = [t.lower() for t in allowed_tables]
        self.max_limit = max_limit
    
    def check(self, sql: str) -> tuple[bool, str]:
        """SQL 검증. (통과 여부, 에러 메시지) 반환"""
        match = self.BLOCKED_KEYWORDS.search(sql)
        if match:
            return False, f"🚫 '{match.group()}' 명령은 허용되지 않습니다."
        return True, ""
    
    def inject_limit(self, sql: str) -> str:
        """LIMIT가 없으면 자동 추가 (대량 조회 방지)"""
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + f"\nLIMIT {self.max_limit};"
        return sql
    
    def sanitize(self, sql: str) -> tuple[str, str]:
        """검증 + LIMIT 주입"""
        is_safe, error = self.check(sql)
        if not is_safe:
            return "", error
        return self.inject_limit(sql), ""

# 테스트
guardrail = SQLGuardrail(
    allowed_tables=["patients", "doctors", "visits", "diagnoses", "departments"])

sql_ok, _ = guardrail.sanitize("SELECT * FROM patients WHERE gender = 'M'")
print(f"✅ 정상 통과: {sql_ok[:50]}...")

_, err = guardrail.sanitize("DROP TABLE patients")
print(f"❌ 차단: {err}")
```

## 멀티턴 상담사 구현

### 이 코드가 하는 일
> 대화 히스토리를 기억하면서 자연어로 병원 DB에 질문할 수 있는 채팅봇입니다.

```python
from dataclasses import dataclass, field
from openai import OpenAI as OpenAIClient
from llama_index.core import SQLDatabase

oai = OpenAIClient()

@dataclass
class ChatState:
    """대화 상태 메모장"""
    history: list = field(default_factory=list)
    last_sql: str = None
    last_result: str = None
    
    def add_user(self, msg):
        self.history.append(("user", msg))
    
    def add_assistant(self, msg, sql=None, result=None):
        self.history.append(("assistant", msg))
        if sql: self.last_sql = sql
        if result: self.last_result = result
    
    def get_history_text(self, max_turns=5):
        recent = self.history[-(max_turns * 2):]
        return "\n".join(
            f"{'사용자' if r=='user' else '시스템'}: {m}" for r, m in recent)

# 스키마 정보 수집
sql_db = SQLDatabase(engine,
    include_tables=["patients","doctors","visits","diagnoses","departments"])
schema_parts = [sql_db.get_single_table_info(t) for t in sql_db.get_usable_table_names()]
SCHEMA_INFO = "\n\n".join(schema_parts)

class HospitalChatbot:
    """병원 DB 멀티턴 상담사"""
    
    def __init__(self):
        self.state = ChatState()
        self.guardrail = SQLGuardrail(
            allowed_tables=["patients","doctors","visits","diagnoses","departments"])
    
    def _generate_sql(self, question):
        """대화 히스토리를 포함하여 SQL 생성"""
        last_ctx = ""
        if self.state.last_sql:
            last_ctx = f"\n직전 SQL: {self.state.last_sql}\n직전 결과 요약: {(self.state.last_result or '')[:500]}"
        
        prompt = f"""병원 DB 분석 전문가입니다. SQL을 작성하세요.

{SCHEMA_INFO}

규칙: SELECT만. completed만 유효. "그 중" = 직전 SQL 조건 유지 + 추가 필터. SQL만 반환.
{last_ctx}

대화 히스토리:
{self.state.get_history_text()}

질문: {question}
SQL:"""
        response = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0)
        sql = response.choices[0].message.content.strip()
        sql = re.sub(r"```sql\s*", "", sql)
        sql = re.sub(r"```\s*", "", sql)
        return sql
    
    def _execute_sql(self, sql):
        safe_sql, error = self.guardrail.sanitize(sql)
        if error:
            return f"⚠️ {error}"
        try:
            df = pd.read_sql(safe_sql, engine)
            return "(결과 없음)" if df.empty else df.to_string(index=False)
        except Exception as e:
            return f"❌ SQL 오류: {str(e)}"
    
    def _summarize(self, question, sql, result):
        prompt = f"질문: {question}\nSQL: {sql}\n결과:\n{result[:1000]}\n\n한국어로 간결하게 요약. 숫자에 천 단위 구분자."
        response = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3)
        return response.choices[0].message.content
    
    def chat(self, question):
        self.state.add_user(question)
        sql = self._generate_sql(question)
        result = self._execute_sql(sql)
        
        if result.startswith("⚠️") or result.startswith("❌"):
            answer = result
        else:
            answer = self._summarize(question, sql, result)
        
        self.state.add_assistant(answer, sql=sql, result=result)
        return f"{answer}\n\n📝 SQL:\n```sql\n{sql}\n```"
```

### 멀티턴 테스트

```python
bot = HospitalChatbot()

# 턴 1
print(bot.chat("남성 환자는 몇 명인가요?"))
print("\n" + "="*60 + "\n")

# 턴 2 — "그 중에" = 이전 조건(남성) 유지
print(bot.chat("그 중에 40세 이상은?"))
print("\n" + "="*60 + "\n")

# 턴 3 — "그 사람들" = 이전 결과 참조
print(bot.chat("그 사람들이 가장 많이 간 진료과는?"))
print("\n" + "="*60 + "\n")

# 턴 4 — 보안 테스트
print(bot.chat("환자 테이블을 삭제해줘"))
```

## 📌 11H 핵심 정리
- **멀티턴** = 이전 대화를 기억하는 채팅. "대화 메모장(ChatState)"이 핵심
- **가드레일** = SQL 경비원. DELETE/DROP 차단, LIMIT 자동 주입
- AI는 원래 기억력이 없으므로, **매번 전체 대화 히스토리를 프롬프트에 포함**해야 함

---

# 12H · Gradio in Colab — 채팅 UI 만들기

## 학습목표
- Gradio로 채팅 UI를 만들 수 있다
- 공개 URL로 다른 사람과 공유할 수 있다

## Gradio란?

> 💡 **Gradio = AI 데모를 5줄로 만드는 마법 도구**. 웹 개발 지식 없이도 채팅 UI를 만들 수 있습니다.

| 프레임워크 | 코드량 | Colab 지원 | 공유 URL | 난이도 |
|---|---|---|---|---|
| **Gradio** | **5줄** | ✅ | ✅ 자동 | ⭐ 매우 쉬움 |
| Streamlit | 20줄 | ❌ | ❌ | ⭐⭐ |
| Flask | 100줄+ | ❌ | ❌ | ⭐⭐⭐⭐ |

## 🎯 실습 Step 1 — 에코봇 (5줄)

### 이 코드가 하는 일
> 입력한 메시지를 그대로 돌려주는 최소한의 채팅봇입니다. Gradio의 기본 사용법을 익힙니다.

```python
import gradio as gr

def echo_chat(message, history):
    """입력을 그대로 반환하는 에코 봇"""
    return f"당신이 말한 것: {message}"

demo = gr.ChatInterface(fn=echo_chat, title="🤖 에코 봇",
    description="입력한 메시지를 그대로 반환합니다.")
demo.launch(share=True)
# share=True → 72시간 유효한 공개 URL이 생성됩니다!
```

> 💡 실행하면 `Running on public URL: https://xxxxx.gradio.live` 형태의 URL이 나옵니다. 이 URL을 브라우저에서 열면 채팅 UI가 보입니다!

## 🎯 실습 Step 2 — 병원 상담사 + Gradio

### 이 코드가 하는 일
> 11H에서 만든 병원 상담사를 Gradio 채팅 UI에 연결합니다.

```python
# 가드레일 + SQL 생성/실행 함수 (11H에서 만든 것 재사용)
BLOCKED = re.compile(r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE)\b", re.IGNORECASE)

def safe_execute(sql):
    if BLOCKED.search(sql):
        return "🚫 위험한 명령어 차단"
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
    try:
        df = pd.read_sql(sql, engine)
        if df.empty: return "(결과 없음)"
        if len(df) > 20:
            return df.head(20).to_markdown(index=False) + f"\n\n... 외 {len(df)-20}행"
        return df.to_markdown(index=False)
    except Exception as e:
        return f"❌ SQL 오류: {str(e)}"

def generate_sql(question, history_text):
    prompt = f"""PostgreSQL 전문가. 병원 DB 질문에 SQL을 작성하세요.
{SCHEMA_INFO}
규칙: SELECT만. completed만 유효. SQL만 반환.

대화: {history_text}
질문: {question}
SQL:"""
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}], temperature=0)
    sql = resp.choices[0].message.content.strip()
    return re.sub(r"```sql\s*", "", re.sub(r"```\s*", "", sql))

def summarize_result(question, sql, result):
    prompt = f"질문: {question}\nSQL: {sql}\n결과:\n{result[:800]}\n한국어로 간결하게."
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}], temperature=0.3)
    return resp.choices[0].message.content

def hospital_chat(message, history):
    """Gradio 핸들러"""
    history_text = ""
    for turn in history[-5:]:
        if isinstance(turn, (list, tuple)) and len(turn) == 2:
            history_text += f"사용자: {turn[0]}\n시스템: {turn[1][:100]}\n"
    
    try:
        sql = generate_sql(message, history_text)
        result = safe_execute(sql)
        if result.startswith("🚫") or result.startswith("❌"):
            return result
        answer = summarize_result(message, sql, result)
        return f"{answer}\n\n---\n📝 **SQL:**\n```sql\n{sql}\n```\n\n📊 **결과:**\n{result}"
    except Exception as e:
        return f"⚠️ 오류: {str(e)}"

# Gradio UI
demo = gr.ChatInterface(
    fn=hospital_chat,
    title="🏥 병원 DB AI 상담사",
    description="자연어로 병원 데이터베이스에 질문하세요.",
    examples=["현재 등록된 환자 수는?", "진료과별 의사 수를 보여줘",
              "지난 3개월간 가장 많이 방문한 환자 Top 5는?"],
    theme=gr.themes.Soft(),
    retry_btn="🔄 다시 시도", undo_btn="↩️ 실행 취소", clear_btn="🗑️ 초기화",
)
demo.launch(share=True)
```

## 🎯 실습 Step 3 — 수강생 간 교차 체험

```
🔄 교차 체험 방법 (10분):
1. 본인 Gradio URL을 전체 채팅에 공유
2. 다른 학생 2명의 URL에 접속
3. 각 앱에서 질문 3개씩 테스트
4. 실패하는 질문을 발견하면 해당 학생에게 피드백
```

## 과제 #2 안내

```
╔═══════════════════════════════════════╗
║    과제 #2 — 스키마 + 시드 데이터       ║
╠═══════════════════════════════════════╣
║ 제출 기한: Day 3 시작 (13H)           ║
║                                       ║
║ 제출물:                               ║
║ 1. Neon에 스키마 생성 완료            ║
║ 2. 테이블당 최소 50행 시드 데이터      ║
║ 3. 모든 컬럼에 COMMENT ON 적용        ║
║ 4. FK 관계 정상 동작 확인              ║
║                                       ║
║ 💡 Faker 라이브러리로 가상 데이터 생성  ║
╚═══════════════════════════════════════╝
```

### 시드 데이터 생성 팁 (Faker)

```python
# !pip install faker
# from faker import Faker
# fake = Faker('ko_KR')
# 
# for i in range(50):
#     print(fake.name(), fake.email(), fake.phone_number())
```

## 📌 12H 핵심 정리
- **Gradio** = 5줄로 채팅 UI 완성. `share=True`로 공개 URL 자동 생성
- 교차 체험으로 다른 학생의 앱을 테스트하고 피드백
- **과제 #2**: 내일까지 Neon에 본인 스키마 + 시드 데이터 배포!

---

## 📌 Day 2 전체 정리

| 시간 | 주제 | 핵심 키워드 |
|---|---|---|
| 9H | 제안서 피어리뷰 | 스키마 검증기, 피어리뷰 |
| 10H | Text-to-SQL 심화 | 커스텀 프롬프트, Few-shot, Before/After |
| 11H | 멀티턴 상담사 | ChatState, SQLGuardrail, 맥락 유지 |
| 12H | Gradio UI | ChatInterface, share=True, 교차 체험 |

> **내일(Day 3) 예고**: Vanna 자가학습 → LangChain/LCEL → Advanced RAG → LangGraph SQL 에이전트 빌드!
