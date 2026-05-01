# 16H -- LCEL RAG 체인

## 학습목표

- LCEL로 RAG 체인(Retriever -> Prompt -> LLM -> Parser)을 조립할 수 있다
- 스트리밍, 배치, fallback을 적용할 수 있다
- 대화 히스토리를 RAG 체인에 통합할 수 있다

---

<div class="colab-link" data-notebook="13_lcel_rag_chain"></div>

## ChromaDB 벡터스토어 준비

먼저 병원 관련 문서를 벡터스토어에 저장합니다. 이 문서들이 RAG 체인의 검색 대상이 됩니다.

```python
# ============================================================
# 1. ChromaDB 벡터스토어 준비
# ============================================================
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 병원 문서를 벡터스토어에 저장
hospital_documents = [
    Document(
        page_content="내과에는 김철수(심장내과), 이영희(호흡기내과), 신민아(소화기내과) 전문의가 있습니다.",
        metadata={"dept": "내과"}
    ),
    Document(
        page_content="외과에는 박민수(일반외과), 정수진(흉부외과), 권혁준(혈관외과)이 근무합니다.",
        metadata={"dept": "외과"}
    ),
    Document(
        page_content="진료 시간은 평일 09:00-18:00, 토요일 09:00-13:00입니다. 점심시간 12:30-13:30.",
        metadata={"type": "schedule"}
    ),
    Document(
        page_content="응급실은 24시간 운영됩니다. 야간에는 내과, 외과 당직의가 상주합니다.",
        metadata={"type": "emergency"}
    ),
    Document(
        page_content="입원 병실 가격: 1인실 250,000원/일, 2인실 150,000원/일, 4인실 80,000원/일.",
        metadata={"type": "admission"}
    ),
    Document(
        page_content="소아과에는 최동현, 강미래, 문서영 전문의가 있으며 소아청소년 질환 전반을 진료합니다.",
        metadata={"dept": "소아과"}
    ),
    Document(
        page_content="정형외과에는 윤성호(척추외과), 한지은(관절외과) 전문의가 근무합니다.",
        metadata={"dept": "정형외과"}
    ),
    Document(
        page_content="외래 환자 주차 3시간 무료, 이후 30분당 1,000원. 입원 환자 보호자 1일 5,000원.",
        metadata={"type": "parking"}
    ),
]

# persist_directory 를 지정하면 Colab 런타임이 끊어져도 벡터 인덱스가
# /content/chroma_db 에 남아 17H/18H 재실습에서 재임베딩 비용을 아낄 수 있습니다.
CHROMA_DIR = "/content/chroma_db"
COLLECTION = "hospital_rag"

import os
if os.path.isdir(CHROMA_DIR) and os.listdir(CHROMA_DIR):
    # 이미 한번 빌드해 둔 인덱스가 있으면 재로드 (임베딩 API 호출 0회)
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION,
    )
else:
    vectorstore = Chroma.from_documents(
        hospital_documents,
        embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
    )

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

!!! note "핵심 정리"
    - 문서에 `metadata`를 부여하면 나중에 필터링 검색이 가능합니다
    - `search_kwargs={"k": 3}`은 상위 3개 유사 문서를 반환하라는 의미입니다
    - 8개 문서는 실습용입니다. 실제 프로젝트에서는 수백~수천 개의 문서를 사용합니다

!!! warning "`persist_directory` 없이 만들면 런타임 끊김 = 재빌드"
    Colab 은 무료 인스턴스의 유휴 런타임을 자주 끊습니다. 임베딩 비용을 아끼고 17H/18H 실습으로 바로 넘어가려면 반드시 `persist_directory` 를 지정하세요. ChromaDB 0.4+ 부터는 별도의 `vectorstore.persist()` 호출 없이도 디스크에 쓰여집니다.

---

## LCEL RAG 체인 조립

RAG 체인의 핵심 패턴: **검색기 | 포맷 + 프롬프트 | LLM | 파서**

```python
# ============================================================
# 2. LCEL RAG 체인 조립
# ============================================================
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def format_docs(docs):
    """검색된 문서를 텍스트로 결합"""
    return "\n\n".join(doc.page_content for doc in docs)

rag_prompt = ChatPromptTemplate.from_template("""다음 컨텍스트를 바탕으로 질문에 한국어로 답변하세요.
컨텍스트에 없는 내용은 "해당 정보가 없습니다"라고 답변하세요.

## 컨텍스트
{context}

## 질문
{question}

## 답변""")

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

# 테스트
print(rag_chain.invoke("내과에 어떤 의사가 있나요?"))
print("\n---\n")
print(rag_chain.invoke("주차 요금이 어떻게 되나요?"))
```

!!! tip "RAG 체인 패턴 해부 — dict 와 함수가 자동으로 Runnable 로 바뀐다"
    ```python
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    ```
    이 한 줄이 핵심입니다:

    - `retriever | format_docs`: 질문으로 문서를 검색하고, 텍스트로 변환
    - `RunnablePassthrough()`: 질문을 그대로 전달
    - 결과는 `{"context": "검색된 문서들...", "question": "원래 질문"}` 딕셔너리

    LCEL 은 파이프라인 중간에 만나는 값들을 **자동으로 `Runnable` 객체로 감쌉니다**.

    - `dict`  → `RunnableParallel` : key 별로 **동시에** 실행하고 결과를 다시 dict 로 합침
    - 함수   → `RunnableLambda`   : 파이프라인 안에서 실행되는 "한 단계 함수"로 승격
    - `Runnable` 들 사이의 `|` 는 "앞 단계의 출력을 뒷 단계의 입력으로" 연결하는 `Runnable.pipe()` 연산

    즉 위 한 줄은 내부적으로 `RunnableParallel(context=retriever | format_docs, question=RunnablePassthrough())` 으로 변환돼 두 키가 **병렬** 로 채워집니다. dict 에 키가 10개여도 동시에 수행됩니다.

---

## 스트리밍 출력

```python
# ============================================================
# 3. 스트리밍 출력
# ============================================================
print("🔄 스트리밍 답변: ", end="")
for chunk in rag_chain.stream("입원 1인실 비용은?"):
    print(chunk, end="", flush=True)
print()
```

!!! tip "스트리밍이 중요한 이유"
    LLM 응답은 보통 2~5초 걸립니다. 스트리밍을 사용하면 첫 글자가 0.5초 안에 나타나서
    사용자가 기다리는 느낌이 크게 줄어듭니다. Gradio `ChatInterface`에서도 스트리밍을 사용합니다.

---

## 에러 Fallback

```python
# ============================================================
# 4. 에러 Fallback
# ============================================================

# 고가 모델 --> 저가 모델 fallback
primary_llm = ChatOpenAI(model="gpt-4o", temperature=0)
fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

rag_chain_robust = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | primary_llm.with_fallbacks([fallback_llm])
    | StrOutputParser()
)

print(rag_chain_robust.invoke("응급실 운영 시간은?"))
```

!!! warning "Fallback 사용 시 주의"
    `with_fallbacks`는 **예외(Exception)가 발생했을 때만** 대체 모델로 전환합니다.
    API 키 오류, 요금 한도 초과, 모델 과부하 등의 상황에서 유용합니다.
    정상 응답이지만 품질이 낮은 경우에는 fallback이 동작하지 않습니다.

---

## 대화 히스토리 통합 RAG

이전 대화를 기억하는 RAG 체인입니다. "그 중에", "아까 말한" 같은 참조를 처리할 수 있습니다.

```python
# ============================================================
# 5. 대화 히스토리 통합 RAG
# ============================================================
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

history_rag_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 병원 안내 도우미입니다. 컨텍스트를 바탕으로 답변하세요.\n\n컨텍스트:\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])

history_rag_chain = (
    {
        "context": (lambda x: x["question"]) | retriever | format_docs,
        "chat_history": lambda x: x["chat_history"],
        "question": lambda x: x["question"],
    }
    | history_rag_prompt
    | llm
    | StrOutputParser()
)
```

### 멀티턴 대화 테스트

```python
# 멀티턴 대화
chat_history = []

q1 = "내과에 어떤 의사가 있어?"
a1 = history_rag_chain.invoke({"question": q1, "chat_history": chat_history})
print(f"Q: {q1}\nA: {a1}\n")
chat_history.extend([HumanMessage(content=q1), AIMessage(content=a1)])

q2 = "그 중에 심장 전문의는 누구야?"
a2 = history_rag_chain.invoke({"question": q2, "chat_history": chat_history})
print(f"Q: {q2}\nA: {a2}")
```

!!! note "핵심 정리"
    `MessagesPlaceholder(variable_name="chat_history")`가 이전 대화를 프롬프트에 삽입합니다.
    "그 중에"라는 표현은 이전 대화 맥락이 없으면 해석할 수 없습니다.
    `chat_history`에 `HumanMessage`와 `AIMessage`를 순서대로 쌓아갑니다.

---

## batch로 3개 질문 동시 실행

!!! example "실습 -- batch로 3개 질문 동시 실행"
    `batch` 메서드를 사용하면 여러 질문을 동시에 처리할 수 있습니다.

    ```python
    # ============================================================
    # 6. batch로 3개 질문 동시 실행
    # ============================================================
    questions = [
        "내과에 어떤 의사가 있나요?",
        "입원 병실 가격을 알려주세요",
        "주차 요금이 어떻게 되나요?",
    ]

    import time

    # 순차 실행 시간 측정
    start = time.time()
    sequential_results = [rag_chain.invoke(q) for q in questions]
    seq_time = time.time() - start

    # 배치 실행 시간 측정
    start = time.time()
    batch_results = rag_chain.batch(questions)
    batch_time = time.time() - start

    print(f"⏱️ 순차 실행: {seq_time:.2f}초")
    print(f"⏱️ 배치 실행: {batch_time:.2f}초")
    print(f"🚀 속도 향상: {seq_time/batch_time:.1f}배\n")

    for q, a in zip(questions, batch_results):
        print(f"Q: {q}")
        print(f"A: {a[:100]}...")
        print()
    ```

    **기대 결과:** 배치 실행이 순차 실행보다 2~3배 빠릅니다.

---

## RAG 체인 구성요소 정리

전체 RAG 체인의 데이터 흐름을 정리합니다:

```
사용자 질문: "내과에 어떤 의사가 있나요?"
     |
     v
+--------------------------------------------------+
| Step 1: 검색 (retriever)                          |
|   질문 임베딩 --> ChromaDB에서 유사 문서 3개 검색   |
|   결과: [내과 문서, 외과 문서, 소아과 문서]         |
+--------------------------------------------------+
     |
     v
+--------------------------------------------------+
| Step 2: 포맷 (format_docs)                        |
|   문서 리스트 --> 하나의 텍스트 문자열로 결합        |
|   결과: "내과에는 김철수...\n\n외과에는 박민수..."   |
+--------------------------------------------------+
     |
     v
+--------------------------------------------------+
| Step 3: 프롬프트 조립 (rag_prompt)                 |
|   context + question --> 완성된 프롬프트            |
+--------------------------------------------------+
     |
     v
+--------------------------------------------------+
| Step 4: LLM 호출 + 파싱                           |
|   프롬프트 --> GPT-4o-mini --> 텍스트 답변          |
+--------------------------------------------------+
     |
     v
답변: "내과에는 김철수(심장내과), 이영희(호흡기내과),
       신민아(소화기내과) 전문의가 있습니다."
```

!!! tip "format_docs 커스터마이즈"
    기본 `format_docs`는 단순히 문서를 줄바꿈으로 연결합니다.
    문서마다 번호를 붙이면 LLM이 출처를 참조할 수 있습니다:

    ```python
    def format_docs_numbered(docs):
        """문서에 번호를 붙여서 결합"""
        return "\n\n".join(
            f"[문서 {i+1}] {doc.page_content}"
            for i, doc in enumerate(docs)
        )
    ```

---

## 실습 과제

1. `hospital_documents`에 문서를 2개 추가하고 RAG 체인을 테스트하세요.
2. `batch`로 5개 질문을 동시에 실행하고 순차 실행과 시간을 비교하세요.
3. 멀티턴 대화에서 3번의 질문을 연속으로 해보세요 (맥락이 유지되는지 확인).

!!! question "생각해보기"
    - `format_docs` 함수를 수정하여 문서마다 번호를 붙이면 답변 품질이 달라질까요?
    - 컨텍스트에 없는 질문을 했을 때 "해당 정보가 없습니다"라고 답변하나요?
    - `search_kwargs={"k": 3}`을 `{"k": 1}`이나 `{"k": 5}`로 바꾸면 어떤 차이가 있나요?

---

!!! note "핵심 정리"
    - **RAG 체인** = `{"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm | parser`
    - **format_docs**: 검색 결과를 텍스트로 변환하는 브릿지 함수 (단순하지만 핵심적)
    - **with_fallbacks**: 고가 모델 실패 시 저가 모델로 자동 전환
    - **MessagesPlaceholder**: 대화 히스토리를 RAG에 통합하여 멀티턴 대화 지원
    - **batch**: 여러 질문을 동시에 처리하여 2~3배 속도 향상
