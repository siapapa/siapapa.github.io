# 17H -- Advanced RAG -- 쿼리 변환

## 학습목표

- Naive RAG의 한계를 이해하고 쿼리 변환의 필요성을 설명할 수 있다
- HyDE, Multi-Query, Query Decomposition 3가지 기법을 구현할 수 있다
- 같은 질문에 대해 세 기법의 검색 결과를 비교 분석할 수 있다

---

<div class="colab-link" data-notebook="14_advanced_rag_query"></div>

## Naive RAG의 한계

```
Naive RAG의 문제:
  질문: "재방문율이 높은 진료과는?"

  검색: "재방문율이 높은 진료과" 임베딩 --> 벡터 검색
  결과: ❌ 관련 문서를 찾지 못함 (문서에 "재방문율"이라는 단어가 없을 수 있음)

쿼리 변환의 해결:
  HyDE: "재방문율이 높은 진료과" --> 가상 답변 생성 --> 가상 답변으로 검색
  Multi-Query: 1개 질문 --> 3~5개 변형 --> 각각 검색 --> 합집합
  Decomposition: 1개 복잡 질문 --> 여러 하위 질문 --> 각각 검색 --> 통합
```

!!! warning "Naive RAG가 실패하는 3가지 경우"
    1. **용어 불일치**: 질문의 "재방문율"과 문서의 "2건 이상 방문"이 다른 표현
    2. **추상적 질문**: "가장 효율적인 진료과는?"처럼 직접적 답변이 없는 경우
    3. **복합 질문**: 여러 정보를 조합해야 답할 수 있는 경우

### 3가지 해결법 비교

| 기법 | 원리 | 비유 | 적합한 경우 |
|---|---|---|---|
| **HyDE** | 가상 답변을 만들어 그걸로 검색 | "정답이 이런 모양일 것 같으니 비슷한 걸 찾아줘" | 질문과 문서의 어휘가 다를 때 |
| **Multi-Query** | 같은 질문을 여러 각도로 변형 | "다른 말로 바꿔서 여러 번 검색" | 검색 재현율을 높이고 싶을 때 |
| **Decomposition** | 복잡한 질문을 작은 질문으로 분해 | "큰 질문을 쪼개서 각각 검색" | 복합적인 질문일 때 |

---

## HyDE (Hypothetical Document Embeddings)

!!! tip "HyDE의 핵심 직관"
    **"질문보다 답변이 문서와 더 비슷하다."**
    질문: "병원에서 가장 바쁜 진료과는?" (짧고 추상적)
    가상 답변: "내과는 가장 많은 환자를 진료하며..." (문서와 비슷한 형태)
    --> 가상 답변으로 검색하면 더 관련 높은 문서를 찾을 수 있습니다.

```python
# ============================================================
# 1. HyDE (Hypothetical Document Embeddings)
# ============================================================
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 가상 문서 생성 프롬프트
hyde_prompt = ChatPromptTemplate.from_template(
    """다음 질문에 대한 답변이 포함된 문서를 작성하세요.
실제 데이터가 없어도 괜찮습니다. 문서 형태로 가상의 답변을 만들어주세요.

질문: {question}

가상 문서:"""
)

# HyDE 체인
hyde_chain = hyde_prompt | llm | StrOutputParser()

# 테스트
question = "병원에서 가장 바쁜 진료과는 어디인가요?"
hypothetical_doc = hyde_chain.invoke({"question": question})
print(f"❓ 질문: {question}")
print(f"📄 가상 문서:\n{hypothetical_doc}\n")

# 가상 문서로 검색 (질문 대신)
hyde_results = vectorstore.similarity_search(hypothetical_doc, k=3)
print("🔍 HyDE 검색 결과:")
for i, doc in enumerate(hyde_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")

# 비교: 원래 질문으로 직접 검색
naive_results = vectorstore.similarity_search(question, k=3)
print("\n🔍 Naive 검색 결과:")
for i, doc in enumerate(naive_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")
```

---

## Multi-Query Retriever

Multi-Query는 하나의 질문을 여러 관점에서 재작성하여 각각 검색한 뒤 결과를 합칩니다.

```python
# ============================================================
# 2. Multi-Query Retriever
# ============================================================
from langchain.retrievers.multi_query import MultiQueryRetriever

# Multi-Query: LLM이 질문을 여러 관점으로 변형
multi_retriever = MultiQueryRetriever.from_llm(
    retriever=retriever,
    llm=llm,
)

# 로깅으로 생성된 질문 확인
import logging
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

question = "입원 비용이 얼마나 드나요?"
multi_results = multi_retriever.invoke(question)

print(f"\n❓ 원래 질문: {question}")
print(f"🔍 Multi-Query 검색 결과 ({len(multi_results)}개):")
for i, doc in enumerate(multi_results):
    print(f"  [{i+1}] {doc.page_content[:80]}...")
```

!!! tip "Multi-Query의 장점"
    - LLM이 자동으로 3~5개의 변형 질문을 생성합니다
    - 각 변형 질문으로 독립적으로 검색합니다
    - 결과를 합집합(union)하여 중복을 제거합니다
    - **가장 실용적인 기법** -- 프로덕션에서도 자주 사용됩니다

---

## Query Decomposition -- 복잡한 질문 분해

복잡한 질문을 2~4개의 단순한 하위 질문으로 분해하여 각각 검색합니다.

```python
# ============================================================
# 3. Query Decomposition -- 복잡한 질문을 하위 질문으로 분해
# ============================================================

decompose_prompt = ChatPromptTemplate.from_template(
    """다음 복잡한 질문을 2-4개의 단순한 하위 질문으로 분해하세요.
각 하위 질문은 한 줄에 하나씩 작성하세요.

복잡한 질문: {question}

하위 질문:"""
)

decompose_chain = decompose_prompt | llm | StrOutputParser()

complex_question = "내과와 외과 중 어느 쪽이 더 많은 의사가 있고, 각 과의 전문 분야는 무엇인가요?"
sub_questions = decompose_chain.invoke({"question": complex_question})
print(f"❓ 복잡한 질문: {complex_question}")
print(f"\n📋 하위 질문:\n{sub_questions}")

# 각 하위 질문으로 검색
sub_q_list = [q.strip().lstrip("0123456789.-) ") for q in sub_questions.split("\n") if q.strip()]
all_results = []
for sq in sub_q_list:
    if sq:
        results = retriever.invoke(sq)
        all_results.extend(results)
        print(f"\n🔍 '{sq[:50]}...' --> {len(results)}개 결과")

# 중복 제거
unique_contents = set()
unique_results = []
for doc in all_results:
    if doc.page_content not in unique_contents:
        unique_contents.add(doc.page_content)
        unique_results.append(doc)

print(f"\n📊 통합 결과: {len(unique_results)}개 (중복 제거)")
```

!!! tip "실전에서는 자유 텍스트 대신 JSON 으로 뽑는 편이 안전합니다"
    위 예제는 "한 줄에 하나씩" 포맷으로 받아 `split("\n")` + 번호/기호 `lstrip()` 으로 파싱합니다. LLM 이 가끔 "하위 질문:" 머리말을 붙이거나, 빈 줄·번호·불릿을 섞으면 파서가 흔들립니다.

    프로덕션·과제에서는 **구조화 출력**(15H `with_structured_output`)을 사용해 `List[str]` 로 바로 받는 편이 훨씬 견고합니다.

    ```python
    from pydantic import BaseModel, Field

    class SubQuestions(BaseModel):
        questions: list[str] = Field(description="2-4개의 단순 하위 질문")

    structured = llm.with_structured_output(SubQuestions)
    sub_q_list = structured.invoke(decompose_prompt.format(question=complex_question)).questions
    # 파싱 코드 불필요. 타입이 list[str] 로 보장됨.
    ```

    수업에서는 **포맷 깨짐 디버깅 체감**을 위해 자유 텍스트 파싱을 먼저 보여주지만, 본인 프로젝트에 적용할 때는 JSON 방식을 권장합니다.

---

## 세 기법 비교 실험

같은 질문에 대해 Naive / HyDE / Multi-Query 세 기법의 검색 결과를 비교합니다.

```python
# ============================================================
# 4. 세 기법 비교 실험
# ============================================================

def compare_retrieval(question: str):
    """Naive / HyDE / Multi-Query 세 기법 비교"""
    print(f"\n{'='*60}")
    print(f"❓ 질문: {question}")
    print(f"{'='*60}")

    # Naive
    naive = retriever.invoke(question)
    print(f"\n🔵 Naive ({len(naive)}개):")
    for doc in naive:
        print(f"  - {doc.page_content[:60]}...")

    # HyDE
    hypo = hyde_chain.invoke({"question": question})
    hyde = vectorstore.similarity_search(hypo, k=3)
    print(f"\n🟢 HyDE ({len(hyde)}개):")
    for doc in hyde:
        print(f"  - {doc.page_content[:60]}...")

    # Multi-Query
    multi = multi_retriever.invoke(question)
    print(f"\n🟡 Multi-Query ({len(multi)}개):")
    for doc in multi:
        print(f"  - {doc.page_content[:60]}...")

compare_retrieval("야간에 응급 진료를 받으려면 어떻게 하나요?")
compare_retrieval("가장 경험이 많은 의사는 누구인가요?")
```

!!! note "핵심 정리"
    - **Naive**: 질문을 그대로 임베딩하여 검색. 단순하지만 어휘 불일치에 취약.
    - **HyDE**: 가상 답변 생성 후 검색. 추상적 질문에 강하지만 LLM 호출 비용 추가.
    - **Multi-Query**: 질문 변형 후 합집합. 재현율이 높고 가장 실용적.

---

## 본인 프로젝트 질문으로 3기법 비교

!!! example "실습 -- 본인 프로젝트 질문으로 3기법 비교"
    본인 프로젝트의 도메인에 맞는 질문 2개를 선택하여 3기법을 비교하세요.

    ```python
    # ============================================================
    # 5. 본인 프로젝트 질문으로 비교
    # ============================================================

    # 본인 프로젝트 도메인에 맞게 질문을 수정하세요
    my_questions = [
        "가장 매출이 높은 부서는 어디인가요?",        # 본인 도메인 질문 1
        "최근 3개월간 가장 활발한 고객 유형은?",       # 본인 도메인 질문 2
    ]

    for q in my_questions:
        compare_retrieval(q)
    ```

    **비교 결과를 아래 표에 기록하세요:**

    | 질문 | Naive 결과 수 | HyDE 결과 수 | Multi-Query 결과 수 | 가장 좋은 기법 |
    |---|---|---|---|---|
    | (질문 1) | | | | |
    | (질문 2) | | | | |

    어떤 기법이 본인 도메인에서 가장 좋은 결과를 보이나요?

---

## 기법별 특성 정리

| 특성 | Naive | HyDE | Multi-Query | Decomposition |
|---|---|---|---|---|
| **LLM 호출 횟수** | 0회 (검색만) | 1회 (가상 문서) | 1회 (변형 질문) | 1회 (하위 질문) |
| **검색 횟수** | 1회 | 1회 | 3~5회 | 2~4회 |
| **결과 수** | k개 | k개 | k*3~5개 (합집합) | k*2~4개 (합집합) |
| **추가 비용** | 없음 | 낮음 | 중간 | 중간 |
| **어휘 불일치 해결** | 못함 | 강함 | 중간 | 중간 |
| **복합 질문 해결** | 못함 | 약함 | 약함 | 강함 |
| **프로덕션 적합도** | 기본 | 중간 | 높음 | 상황별 |

!!! tip "실전에서의 조합"
    실제 프로덕션에서는 기법을 **조합**하여 사용합니다:

    - **Multi-Query + Re-ranking** (18H): 재현율과 정밀도 모두 향상
    - **HyDE + 하이브리드 검색**: 의미 검색과 키워드 검색을 동시 활용
    - **Decomposition + Multi-Query**: 복합 질문을 분해하고 각각 다양한 관점에서 검색

---

## 실습 과제

1. `compare_retrieval` 함수로 병원 도메인 질문 3개를 테스트하세요.
2. HyDE가 Naive보다 더 좋은 결과를 보이는 질문과 그렇지 않은 질문의 차이를 분석하세요.
3. Query Decomposition으로 복합 질문 1개를 분해하고 통합 검색하세요.

!!! question "생각해보기"
    - HyDE가 Naive보다 **나쁜 결과**를 보이는 경우가 있나요? 어떤 경우일까요?
    - Multi-Query에서 LLM이 생성하는 변형 질문의 수를 늘리면 항상 좋아질까요?
    - Query Decomposition은 어떤 유형의 질문에 가장 효과적인가요?

---

!!! note "핵심 정리"
    - **HyDE**: 가상 답변 생성 -> 답변으로 검색 (질문보다 답변이 문서와 유사)
    - **Multi-Query**: 1개 질문 -> 3~5개 변형 -> 각각 검색 -> 합집합 (가장 실용적)
    - **Decomposition**: 복잡한 질문 -> 하위 질문 -> 각각 검색 -> 통합
    - `compare_retrieval` 함수로 같은 질문에 대해 세 기법을 쉽게 비교할 수 있다
    - 18H에서 검색 결과의 **품질**을 높이는 Re-ranking을 배운다
    - 실전에서는 **Multi-Query가 가장 범용적**이고, 복합 질문에는 Decomposition을 추가

## 강사 참고

- **시간 배분**: Naive RAG 한계 5분 -> HyDE 15분 -> Multi-Query 10분 -> Decomposition 10분 -> 비교 실험 10분
- HyDE의 직관: "질문보다 답변이 문서와 더 비슷하다" -- 이 한 문장이 핵심
- Multi-Query는 가장 실용적 -- 프로덕션에서도 자주 사용됨을 강조
- 로깅(`logging.INFO`)으로 Multi-Query가 생성하는 변형 질문을 직접 확인시키기
