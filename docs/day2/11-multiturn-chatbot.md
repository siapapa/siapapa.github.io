# 11H · 병원 DB 멀티턴 상담사

## 학습목표

- 멀티턴 대화에서 상태(히스토리)를 관리하는 방법을 구현할 수 있다
- 이전 맥락을 참조하는 질문("그 중에서...")을 처리할 수 있다
- SQL 보안 가드레일(위험 SQL 차단, 화이트리스트, LIMIT 주입)을 구현할 수 있다

---

<div class="colab-link" data-notebook="09_gradio_chatbot"></div>

## 단발 질의 vs 멀티턴 대화

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

!!! tip "ChatState = 대화 메모장"
    AI는 원래 기억력이 없습니다(stateless). 그래서 우리가 "대화 메모장"을 만들어 매번 전체 대화를 AI에게 전달해야 합니다. 이것이 멀티턴 대화의 핵심 원리입니다.

---

## ChatState 데이터클래스

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
        # 1턴 = (사용자 메시지 + 시스템 응답) 2개가 짝이므로, max_turns*2 개를 잘라야
        # 사용자 N번 + 시스템 N번이 정확히 남습니다. (예: max_turns=5 → 최근 10개 메시지)
        recent = self.history[-(max_turns * 2):]
        lines = []
        for role, msg in recent:
            prefix = "사용자" if role == "user" else "시스템"
            lines.append(f"{prefix}: {msg}")
        return "\n".join(lines)
```

---

## SQL 보안 가드레일

### 보안 위협 유형 표

| 위협 유형 | 설명 | 방어 전략 |
|---|---|---|
| **DML 공격** | DELETE/DROP/UPDATE로 데이터 변경/삭제 | 키워드 차단 (SELECT만 허용) |
| **SQL 인젝션** | 악의적인 SQL 코드 삽입 | 패턴 차단 (주석, 세미콜론+DML) |
| **테이블 무단 접근** | 허용되지 않은 테이블 조회 | 화이트리스트로 허용 테이블 제한 |
| **대량 조회** | SELECT * FROM 큰_테이블 (서버 과부하) | LIMIT 1000 자동 주입 |
| **시스템 정보 노출** | information_schema, pg_roles 등 조회 | 시스템 테이블 접근 차단 |

### SQLGuardrail 클래스 전체 코드

```python
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

        # 3. 허용 테이블만 사용했는지 확인 (간이 방식)
        #    주의: EXTRACT(YEAR FROM birth_date), POSITION('a' IN col) 같은
        #    함수형 FROM/IN 을 오탐하지 않도록, 먼저 해당 함수 호출을 제거한 뒤
        #    FROM/JOIN 뒤의 식별자만 추출합니다. CTE 별칭·서브쿼리 별칭은
        #    allowed_tables 검사에서 제외됩니다.
        parsed = sqlparse.parse(sql)
        cte_names = set(re.findall(r'\bwith\s+(\w+)\s+as\b', sql, re.IGNORECASE))

        for stmt in parsed:
            tokens_str = str(stmt).lower()
            # 함수형 FROM/IN 제거
            tokens_str = re.sub(
                r'\b(extract|position|substring|trim|cast)\s*\([^()]*\)',
                ' ',
                tokens_str,
            )
            from_match = re.findall(r'\bfrom\s+([a-z_][a-z0-9_]*)', tokens_str)
            join_match = re.findall(r'\bjoin\s+([a-z_][a-z0-9_]*)', tokens_str)
            used_tables = {t for t in (from_match + join_match) if t not in cte_names}

            for table in used_tables:
                if table not in self.allowed_tables:
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
```

### 가드레일 테스트

```python
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

!!! danger "정규식 가드레일은 **보조 방어선**일 뿐 — 진짜 방어는 read-only 세션"
    정규식 블랙리스트만으로는 막을 수 없는 치명적 케이스가 있습니다.

    **우회 가능한 사례:**

    - 대소문자 혼합: `DrOp TaBlE patients` -- 현재 코드는 `re.IGNORECASE`로 방어
    - 유니코드 치환: `ＤＲＯＰ TABLE` (전각 문자) -- 방어 불가
    - 동적 SQL: `EXECUTE 'DROP TABLE patients'` -- EXECUTE 키워드 차단으로 부분 방어
    - 인코딩 우회: `SELECT CHR(68)||CHR(82)||CHR(79)||CHR(80)` -- 방어 불가
    - **data-modifying CTE**: `WITH x AS (DELETE FROM patients RETURNING *) SELECT * FROM x` — SELECT 로 시작해도 DELETE 가 실행됩니다.

    **진짜 방어선 (꼭 둘 다 적용)**:

    1. **DB 레벨 read-only 세션** — 에이전트 전용 커넥션을 read-only 로 만들면 LLM 이 어떤 SQL 을 만들어도 DB 가 `cannot execute DELETE in a read-only transaction` 로 거부합니다.
       ```python
       agent_engine = create_engine(
           os.environ["NEON_DSN"],
           connect_args={"options": "-c default_transaction_read_only=on"},
       )
       ```
       ([사전 준비 > 공통 부트스트랩](../setup.md#bootstrap-common)의 `agent_engine` 참고.)
    2. **DB 롤 분리** — Neon 대시보드에서 `agent_ro` 롤을 만들고 `GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_ro` 만 부여. 에이전트는 이 롤로 접속.

    정규식 가드(`SQLGuardrail`)는 오탐·오답을 일찍 잡아주는 보조 장치로만 쓰세요. 정규식을 통과했다는 이유로 read-only 를 풀지 마세요.

---

## HospitalChatbot 클래스 전체 코드

```python
from openai import OpenAI as OpenAIClient
import pandas as pd

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
- 나이 = EXTRACT(YEAR FROM AGE(birth_date))  -- ※ 정확히는 DATE_PART('year', AGE(CURRENT_DATE, birth_date))
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
```

---

## 스키마 정보 수집 함수

```python
from llama_index.core import SQLDatabase

def get_full_schema(engine) -> str:
    tables = ["patients", "doctors", "visits", "diagnoses", "departments"]
    sql_db_temp = SQLDatabase(engine, include_tables=tables)
    parts = []
    for t in tables:
        parts.append(sql_db_temp.get_single_table_info(t))
    return "\n\n".join(parts)

schema_info = get_full_schema(engine)
```

---

## 4턴 멀티턴 테스트

```python
# ============================================================
# 멀티턴 대화 테스트
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

!!! note "핵심 정리"
    - 턴 1: 일반 질문 -> SQL 생성 -> 결과 반환
    - 턴 2: "그 중에" -> 직전 SQL 조건(gender='M') 유지 + 나이 필터 추가
    - 턴 3: "그 사람들" -> 직전 결과(남성 40세 이상)를 참조하여 진료과 분석
    - 턴 4: "삭제해줘" -> 가드레일이 DROP/DELETE 차단

---

## RobustHospitalChatbot (에러 재시도 로직)

```python
class RobustHospitalChatbot(HospitalChatbot):
    """에러 발생 시 자동 재시도하는 상담사"""

    MAX_RETRIES = 2

    def chat(self, question: str) -> str:
        self.state.add_user(question)

        # 루프 진입 전 초기화 — 이전 호출의 sql/last_error 가 남지 않도록
        sql = ""
        result = ""
        last_error = ""
        attempt = 0

        for attempt in range(self.MAX_RETRIES + 1):
            # 매 반복에서 _generate_sql 을 정확히 1회만 호출 (비용 ×2 방지)
            if attempt == 0:
                sql = self._generate_sql(question)
            else:
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

---

!!! example "실습"
    **5턴 이상 연속 대화를 시도하세요.**

    아래 시나리오를 참고하여 5턴 이상의 연속 대화를 진행해보세요. 맥락이 잘 유지되는지 확인합니다.

    시나리오 예시 (참고용):

    1. "여성 환자는 몇 명인가요?"
    2. "그 중에 30세 미만은?"
    3. "그 사람들 중 응급 진료를 받은 적 있는 사람은?"
    4. "그 환자들의 진단명을 보여줘"
    5. "그 중 중증(severe) 진단은?"

    *힌트: `HospitalChatbot(engine, schema_info)` 인스턴스를 만들고 질문을 리스트로 정리한 뒤 for 루프로 `bot.chat(q)` 를 호출해 출력하세요. 정답 코드는 숨겨져 있습니다 -- 본인이 직접 시나리오를 짜서 돌려 보아야 맥락 유지가 어디서 깨지는지 보입니다.*

    **확인할 점:**

    - "그 중에", "그 사람들" 표현이 올바르게 해석되는가?
    - 3턴 이후에도 처음 조건(여성)이 유지되는가?
    - 5턴에서 맥락이 흐려지거나 잘못된 SQL이 생성되지는 않는가?

!!! example "실습"
    **UNION 차단 패턴을 SQLGuardrail에 추가하세요.**

    `SQLGuardrail` 을 상속한 `EnhancedSQLGuardrail` 클래스를 만들고, `BLOCKED_PATTERNS` 정규식에 `UNION SELECT` / `UNION ALL SELECT` 를 잡아내는 항목을 추가하세요.

    아래 3가지 케이스로 동작을 검증하세요:

    1. 정상 쿼리: `SELECT name FROM patients WHERE gender = 'M'` -> 통과
    2. UNION 인젝션: `SELECT name FROM patients UNION SELECT password FROM pg_roles` -> 차단
    3. UNION ALL 인젝션: `SELECT name FROM patients UNION ALL SELECT table_name FROM information_schema.tables` -> 차단

    *힌트: 기존 `SQLGuardrail.BLOCKED_PATTERNS` 정규식을 그대로 복사한 뒤, alternation(`|`) 으로 `\bUNION\b\s+(ALL\s+)?SELECT` 같은 패턴을 한 줄 끼워 넣으면 됩니다. 정답 코드는 숨겨져 있습니다 -- 정규식을 직접 작성해 보아야 escape/대소문자 처리가 손에 익습니다.*

---

!!! warning "정규식만으로는 완벽하지 않다 -- 보안 한계 설명"
    가드레일의 정규식 기반 차단은 **1차 방어선**일 뿐입니다. 프로덕션 환경에서는 반드시 추가 보안 레이어가 필요합니다.

    **정규식의 한계:**

    | 공격 방법 | 예시 | 정규식 차단 가능? |
    |---|---|---|
    | 대소문자 혼합 | `DrOp TaBlE` | O (IGNORECASE) |
    | 전각 문자 | `ＤＲＯＰ` | X |
    | CHR 함수 | `SELECT CHR(68)\|\|CHR(82)\|\|CHR(79)\|\|CHR(80)` | X |
    | 동적 SQL | `PREPARE stmt AS ...` | 부분적 |
    | 주석 우회 | `DR/**/OP TABLE` | X |
    | 공백 변형 | `DROP\tTABLE` | O (\b 경계) |

    **프로덕션 필수 보안:**

    1. DB 사용자 권한: `GRANT SELECT ON ALL TABLES TO readonly_user`
    2. Read-only 레플리카에서만 쿼리 실행
    3. `sqlparse` AST 분석으로 SELECT 문만 허용
    4. 쿼리 실행 타임아웃 설정 (statement_timeout)
    5. 감사 로그(audit log) 기록

---

!!! note "11H 핵심 정리"
    - **멀티턴** = 이전 대화를 기억하는 채팅. "대화 메모장(ChatState)"이 핵심
    - **가드레일** = SQL 경비원. DELETE/DROP 차단, LIMIT 자동 주입, 화이트리스트
    - AI는 원래 기억력이 없으므로, **매번 전체 대화 히스토리를 프롬프트에 포함**해야 함
    - 정규식 가드레일은 1차 방어선 -- 프로덕션에서는 DB 권한 + AST 분석 필수

---
