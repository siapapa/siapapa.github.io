# 15H -- LangChain & LCEL 기초

## 학습목표

- LangChain의 핵심 구성요소(PromptTemplate, Model, Parser)를 이해한다
- LCEL(LangChain Expression Language)의 파이프(`|`) 연산자로 체인을 조립할 수 있다
- `Runnable` 인터페이스의 `invoke`, `stream`, `batch` 메서드를 사용할 수 있다
- Pydantic을 활용한 구조화 출력을 생성할 수 있다

!!! tip "🧭 이 시간을 이렇게 읽으세요 (비개발자용)"
    - **한 줄 핵심**: 레고 블록처럼 AI 부품을 **`|` 로 끼워 조립** 하는 LangChain 의 기본 문법.
    - **꼭 이해**: `prompt | model | parser` 는 "프롬프트 만들기 → AI 호출 → 답 정리" 라는 3단 파이프. 그뿐입니다.
    - **지금은 몰라도 OK**: `with_structured_output` / `Pydantic` / `JsonOutputParser` 의 모든 옵션. "AI 에게 양식 채우기 시키기" 라는 한 마디로 통합 이해.
    - **막히면**: 모르는 단어는 [용어 사전](../appendix/glossary.md) 으로 → 처음이라면 [비개발자 학습 가이드](../beginners-guide.md).

---

<div class="colab-link" data-notebook="12_langchain_lcel"></div>

## LCEL 개념 -- "레고 블록 조립"

!!! tip "LCEL을 한 줄로 설명하면"
    **LCEL(LangChain Expression Language)** = 파이프(`|`) 연산자로 AI 기능 블록을 조합하는 문법.
    Unix의 `cat file | grep error | wc -l`처럼, AI 체인도 `prompt | model | parser`로 조립합니다.

!!! note "`|` 은 파이썬의 **연산자 오버로딩** 입니다 — 마법이 아닙니다"
    파이썬에서 `a | b` 는 원래 **비트 OR** 연산자지만, 클래스가 `__or__` 메서드를 정의하면 같은 기호를 **다른 의미로 재사용** 할 수 있습니다 (이를 "오버로딩" 이라 합니다).

    LangChain 의 모든 `Runnable` 은 `__or__` 를 오버로드해 `self.pipe(other)` — 즉 **"이 단계의 출력을 다음 단계의 입력으로"** 를 의미하게 만들었습니다. 그래서 `prompt | model | parser` 는 내부적으로 `prompt.pipe(model).pipe(parser)` 와 동일합니다.

    → `|` 가 파이썬 기본이 아니라 **LangChain 이 재정의한 문법** 이라는 점만 기억하세요.

### LangChain의 핵심 철학

```
LCEL = LangChain Expression Language
  |
  v
"파이프(|) 연산자로 조합 가능한 Runnable 단위"
  |
  v
모든 구성요소가 같은 인터페이스(invoke/stream/batch)를 가짐
  |
  v
레고 블록처럼 자유롭게 조합
```

### 핵심 구성요소

```
+---------------+     +---------------+     +---------------+
| PromptTemplate| --> |   ChatModel   | --> | OutputParser  |
|               |  |  |               |  |  |               |
| 변수 삽입     |     | LLM 호출      |     | 결과 파싱     |
+---------------+     +---------------+     +---------------+

chain = prompt | model | parser
result = chain.invoke({"variable": "value"})
```

---

## 기본 체인 -- Prompt | Model | Parser

```python
# ============================================================
# 1. 기본 체인 -- Prompt | Model | Parser
# ============================================================
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 구성요소 정의
prompt = ChatPromptTemplate.from_template(
    "당신은 {role} 전문가입니다. 다음 질문에 한국어로 간결히 답변하세요.\n\n질문: {question}"
)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# 체인 조립 (파이프 연산자)
chain = prompt | model | parser

# 실행
result = chain.invoke({
    "role": "데이터베이스",
    "question": "인덱스는 왜 중요한가요?"
})
print(result)
```

!!! note "핵심 정리"
    `chain = prompt | model | parser`에서:

    - `prompt`: 변수를 삽입하여 프롬프트 문자열을 생성
    - `model`: 프롬프트를 LLM에 전달하여 응답을 받음
    - `parser`: LLM 응답(AIMessage)에서 텍스트만 추출

---

## invoke / stream / batch

모든 LCEL 체인은 3가지 실행 방법을 지원합니다.

```python
# ============================================================
# 2. invoke / stream / batch
# ============================================================

# invoke: 단건 실행
result = chain.invoke({"role": "SQL", "question": "CTE란 무엇인가요?"})
print(f"invoke: {result[:100]}...\n")

# stream: 스트리밍 (토큰 단위 출력)
print("stream: ", end="")
for chunk in chain.stream({"role": "SQL", "question": "윈도우 함수를 설명해주세요"}):
    print(chunk, end="", flush=True)
print("\n")

# batch: 여러 입력 동시 실행
results = chain.batch([
    {"role": "Python", "question": "리스트와 튜플의 차이?"},
    {"role": "SQL", "question": "GROUP BY의 용도?"},
    {"role": "AI", "question": "RAG란?"},
])
for i, r in enumerate(results):
    print(f"batch[{i}]: {r[:80]}...")
```

| 메서드 | 용도 | 특징 | 사용 예시 |
|---|---|---|---|
| `invoke` | 단건 실행 | 결과를 한 번에 반환 | 단일 질문 처리 |
| `stream` | 스트리밍 | 토큰 단위로 순차 반환 | 채팅 UI (실시간 출력) |
| `batch` | 동시 실행 | 여러 입력을 병렬 처리 | 대량 테스트, 배치 평가 |

!!! tip "언제 어떤 메서드를 사용하나?"
    - **invoke**: 대부분의 경우. 결과를 한 번에 받아서 처리할 때
    - **stream**: Gradio/웹 UI에서 실시간으로 글자가 나타나게 할 때
    - **batch**: 10개 질문을 한꺼번에 테스트할 때 (20H에서 사용)

---

## 다양한 PromptTemplate

### System + Human 메시지 분리

```python
# ============================================================
# 3. 다양한 PromptTemplate
# ============================================================
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# System + Human 메시지 분리
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 {domain} 분야의 전문 분석가입니다. 항상 한국어로 답변하세요."),
    ("human", "{question}"),
])

chain2 = chat_prompt | model | parser
print(chain2.invoke({"domain": "의료", "question": "병원 데이터 분석의 핵심은?"}))
```

!!! tip "System vs Human 메시지"
    - **System**: AI의 역할, 성격, 규칙을 정의. "당신은 ~입니다" 형태.
    - **Human**: 사용자의 실제 질문. 매번 달라지는 입력.
    - System 메시지로 일관된 행동을 유도하고, Human 메시지로 구체적 질문을 전달합니다.

---

## RunnablePassthrough, RunnableLambda, RunnableParallel

LCEL에서 데이터 흐름을 제어하는 유틸리티 Runnable들입니다.

```python
# ============================================================
# 4. RunnablePassthrough, RunnableLambda, RunnableParallel
# ============================================================
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel

# RunnablePassthrough: 입력을 그대로 전달
chain_pass = (
    {"question": RunnablePassthrough()}
    | ChatPromptTemplate.from_template("질문: {question}\n한국어로 답변:")
    | model
    | parser
)
print("PassThrough:", chain_pass.invoke("PostgreSQL이란?")[:100])

# RunnableLambda: 커스텀 변환 함수
upper = RunnableLambda(lambda x: x.upper())
result = upper.invoke("hello world")
print(f"\nLambda: {result}")

# RunnableParallel: 병렬 실행
parallel_chain = RunnableParallel(
    summary=ChatPromptTemplate.from_template("'{topic}'을 한 문장으로 요약:") | model | parser,
    keywords=ChatPromptTemplate.from_template("'{topic}'의 핵심 키워드 3개 나열:") | model | parser,
)
result = parallel_chain.invoke({"topic": "벡터 데이터베이스"})
print(f"\n요약: {result['summary']}")
print(f"키워드: {result['keywords']}")
```

| Runnable | 역할 | 비유 | 사용 예시 |
|---|---|---|---|
| `RunnablePassthrough` | 입력을 그대로 통과 | 배달 파이프 | RAG 체인에서 질문을 그대로 전달 |
| `RunnableLambda` | 커스텀 함수 적용 | 변환 장치 | 문자열 변환, 데이터 가공 |
| `RunnableParallel` | 여러 체인 동시 실행 | 갈림길 | 요약 + 키워드 동시 생성 |

!!! tip "세 가지, 언제 무엇을 써야 할까?"
    세 개 모두 "`|` 연산자에 그냥 꽂히는 함수 같은 것"이지만, 해결하는 문제가 다릅니다.

    | 상황 | 어떤 Runnable? | 왜? |
    |---|---|---|
    | 질문을 그대로 다음 단계에 전달해야 하는데 `|`에 꽂을 "값"이 없다 | `RunnablePassthrough()` | 체인은 "실행 가능한 객체"만 `|` 로 연결 가능 → 값을 객체로 포장해주는 자리채우기 |
    | 입력을 **변형**해야 한다 (예: 문자열 strip, dict 재구성, 외부 API 호출) | `RunnableLambda(함수)` | 일반 파이썬 함수를 체인에 끼워 넣는 어댑터 |
    | 같은 입력에서 **여러 결과**가 동시에 필요하다 (요약 + 감정 + 키워드) | `RunnableParallel({...})` | 순차 실행 대비 실행 시간↓, 결과를 dict 로 묶어 다음 단계로 |
    | "질문은 그대로, context 는 새로 계산" 처럼 **일부만 바꾸고 일부는 유지** | `RunnablePassthrough.assign(context=...)` | Passthrough + 추가 필드 계산을 한 번에 (RAG 체인 최빈 패턴) |

!!! warning "RunnablePassthrough 주의"
    `RunnablePassthrough()`는 입력을 **그대로** 전달합니다.
    딕셔너리 입력이 필요한 경우 `{"key": RunnablePassthrough()}` 형태로 감싸야 합니다.
    16H RAG 체인에서 이 패턴이 핵심적으로 사용됩니다.

---

## 구조화 출력 -- with_structured_output (Pydantic)

!!! tip "구조화 출력이란?"
    **구조화 출력**: AI 답변을 자유 형식 텍스트가 아닌 "정해진 필드"로 받는 것.
    JSON처럼 필드별로 깔끔하게 파싱할 수 있어서 후속 프로그래밍이 쉬워집니다.
    20H LangGraph 에이전트에서 핵심적으로 사용됩니다.

### 구조화 출력에 필요한 5개 개념 — 한 번에 몰아 배우지 말고 1개씩

| 개념 | 한 줄 설명 | 비유 |
|---|---|---|
| `pydantic.BaseModel` | 파이썬으로 "데이터 양식"(클래스) 을 만드는 라이브러리. 필드 이름·타입·설명을 선언합니다. | **폼 양식** (이름·나이·주소 란을 미리 그려둔 A4 용지) |
| `Field(description="...")` | 각 필드에 **LLM 이 읽을 힌트** 를 붙입니다. `with_structured_output` 이 이 설명을 프롬프트에 자동 주입합니다. | 양식 옆 **작성 안내문** |
| `list[str]` | 파이썬 3.9+ 타입 힌트. "문자열의 리스트". | "항목을 여러 개 써도 되는 칸" |
| `str \| None` | 파이썬 3.10+ 타입 힌트. "문자열 또는 비어 있을 수 있음". 기존 `Optional[str]` 과 동일. | "쓰거나 비워 둘 수 있는 칸" |
| `model.with_structured_output(Schema)` | LLM 호출을 래핑해 **응답을 `Schema` 인스턴스로 반환** 하게 만듭니다. 내부적으로 OpenAI function calling 을 사용. | "프롬프트 대신 **양식** 을 주고 그대로 채워 오라고 시키는 방식" |

이 다섯 개가 어떻게 합쳐지는지 아래 예제에서 확인하세요.

```python
# ============================================================
# 5. 구조화 출력 -- with_structured_output
# ============================================================
from pydantic import BaseModel, Field

class SQLAnalysis(BaseModel):
    """SQL 쿼리 분석 결과 — Pydantic 이 이 클래스를 LLM 이 읽을 수 있는 JSON 스키마로 바꿉니다."""
    tables: list[str]  = Field(description="사용해야 할 테이블 목록")
    join_needed: bool  = Field(description="JOIN이 필요한지 여부")
    aggregation: str | None = Field(description="필요한 집계 함수 (COUNT, SUM 등, 없으면 null)")
    difficulty: str    = Field(description="난이도: easy, medium, hard")
    sql: str           = Field(description="생성된 SQL 쿼리")

# method="function_calling" 을 명시하면 OpenAI 의 function calling 기능을
# 사용해 JSON 파싱이 실패할 가능성이 거의 없어집니다.
llm_structured = model.with_structured_output(SQLAnalysis, method="function_calling")

prompt_struct = ChatPromptTemplate.from_template(
    """다음 자연어 질문을 분석하여 SQL 쿼리를 생성하세요.

데이터베이스: 병원 (patients, doctors, visits, diagnoses, departments)

질문: {question}"""
)

struct_chain = prompt_struct | llm_structured

result = struct_chain.invoke({"question": "진료과별 평균 진료비를 보여주세요"})
print(f"테이블: {result.tables}")
print(f"JOIN 필요: {result.join_needed}")
print(f"집계 함수: {result.aggregation}")
print(f"난이도: {result.difficulty}")
print(f"SQL: {result.sql}")
```

---

## JsonOutputParser (대안)

Pydantic `with_structured_output`이 지원되지 않는 환경에서는 `JsonOutputParser`를 사용할 수 있습니다.

```python
# ============================================================
# 6. JsonOutputParser (Pydantic 미지원 환경용)
# ============================================================
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser(pydantic_object=SQLAnalysis)

prompt_json = ChatPromptTemplate.from_template(
    """다음 질문을 분석하세요.
{format_instructions}

질문: {question}"""
).partial(format_instructions=json_parser.get_format_instructions())

json_chain = prompt_json | model | json_parser
result = json_chain.invoke({"question": "남성 환자 수는?"})
print(f"JSON 결과: {result}")
```

!!! note "핵심 정리"
    `with_structured_output`은 LLM에게 직접 스키마를 전달하여 구조화 출력을 강제합니다.
    `JsonOutputParser`는 프롬프트에 포맷 지시를 삽입하여 JSON 형태로 답변하도록 유도합니다.
    두 방식 모두 결과는 Python 딕셔너리/Pydantic 객체로 받을 수 있습니다.

---

## SQL 생성 체인 실습

!!! example "실습 -- SQL 생성 체인으로 병원 DB 질문 3개 테스트"
    `with_structured_output`을 활용하여 병원 DB 질문 3개를 테스트합니다.

    아래 3개 질문을 위에서 만든 `struct_chain` 으로 실행하고, 반환된 `SQLAnalysis` 객체의 `tables / join_needed / aggregation / difficulty / sql` 을 출력하세요.

    1. 전체 환자 수는 몇 명인가요?
    2. 진료과별 의사 수를 보여주세요
    3. 지난달 응급 진료 건수와 평균 비용은?

    *힌트: `struct_chain.invoke({"question": q})` 의 반환값은 Pydantic 객체이므로 점 표기법(`result.tables`, `result.sql` 등)으로 필드에 접근할 수 있습니다.*

    **기대 결과:**

    | 질문 | 테이블 | JOIN | 집계 | 난이도 |
    |---|---|---|---|---|
    | 전체 환자 수 | [patients] | False | COUNT | easy |
    | 진료과별 의사 수 | [doctors, departments] | True | COUNT, GROUP BY | medium |
    | 지난달 응급 진료 | [visits] | False | COUNT, AVG | medium |

---

## 실습 과제

1. `PromptTemplate`을 수정하여 SQL 생성 체인을 만들고, 병원 DB 질문 3개를 테스트하세요.
2. `with_structured_output`으로 테이블 목록 + SQL + 난이도를 동시에 반환하는 체인을 만드세요.
3. `RunnableParallel`로 같은 질문에 대해 "SQL 생성"과 "자연어 답변"을 동시에 실행하세요.

!!! question "생각해보기"
    - `invoke`와 `stream`의 결과가 동일한가요? 어떤 상황에서 `stream`이 더 유용한가요?
    - `with_structured_output`과 `JsonOutputParser`의 차이점은 무엇인가요?
    - `RunnableParallel`은 실행 시간을 어떻게 줄여주나요?

---

!!! note "핵심 정리"
    - **LCEL** = `prompt | model | parser` 파이프로 체인 조립
    - `invoke`(단건), `stream`(스트리밍), `batch`(동시) 3가지 실행 방법
    - **System+Human 메시지**: System으로 역할 정의, Human으로 질문 전달
    - **RunnablePassthrough/Lambda/Parallel**: 데이터 흐름 제어 유틸리티
    - **구조화 출력** = AI 답변을 정해진 필드로 받기 (20H 에이전트에서 핵심)
    - **JsonOutputParser** = `with_structured_output` 대안

---

!!! warning "🆘 비개발자를 위한 회복 가이드 — 여기까지 어렵다면"
    Day 3 부터는 새 개념이 누적되는 구간입니다. 이 시간이 어렵게 느껴진다면 다음만 가져가세요.

    1. `prompt | model | parser` — 이 한 줄이 LCEL 전부입니다. 나머지는 변형판입니다.
    2. `Pydantic / TypedDict` 는 **"AI 에게 양식을 채우게 시키는 도구"** 라는 한 마디면 충분합니다. 내부 동작은 4일 후에도 안 봐도 됩니다.
    3. `RunnablePassthrough / Lambda / Parallel` 은 16H RAG 체인에서 다시 만나니, 지금은 "통과·변환·동시" 세 단어만 외워 두세요.

    → 더 막힌다면 [용어 사전 — LangChain·LCEL·Pydantic](../appendix/glossary.md#e-langchain-lcel-pydantic-langgraph) 으로.
