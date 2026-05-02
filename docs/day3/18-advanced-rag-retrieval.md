# 18H -- Advanced RAG -- 검색 고도화

## 학습목표

- BM25와 벡터 검색의 차이를 이해하고 하이브리드 검색을 구현할 수 있다
- Re-ranking(CrossEncoder)으로 검색 정밀도를 높일 수 있다
- weight 실험으로 최적 비율을 찾을 수 있다

---

<div class="colab-link" data-notebook="15_advanced_rag_retrieval"></div>

## BM25 vs 벡터 검색

!!! tip "BM25=키워드(정밀), 벡터=의미(재현율)"
    | 방식 | 원리 | 장점 | 단점 | 적합한 질문 |
    |---|---|---|---|---|
    | **BM25** | 키워드 빈도 매칭 (TF-IDF 계열) | 정확한 키워드에 강함 | 유의어/동의어 못 찾음 | "김철수 의사", "ICD-J45" |
    | **벡터** | 임베딩 코사인 유사도 | 의미적 유사성 파악 | 고유명사에 약함 | "호흡기 관련 의사", "천식 진단" |
    | **하이브리드** | 두 방식 가중 결합 | 장점 결합 | 비율 조정 필요 | 모든 유형 |

    **핵심**: BM25는 "그 단어가 있느냐"를 찾고, 벡터는 "그 의미와 비슷하냐"를 찾습니다.

---

## BM25 Retriever

!!! warning "한국어 토크나이징 주의"
    `BM25Retriever.from_documents(...)`는 기본적으로 **공백 단위**로 토크나이징합니다. 한국어는 조사가 붙어 "의사가"와 "의사를"이 **서로 다른 토큰**으로 계산되기 때문에 BM25 점수가 왜곡됩니다.

    본인 프로젝트에 적용할 때는 `preprocess_func`로 형태소 분석기를 주입하세요. 예:

    ```python
    try:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
        def ko_tokenize(text: str) -> list[str]:
            return [t.form for t in _kiwi.tokenize(text) if t.tag.startswith(("N", "V"))]
        bm25_retriever = BM25Retriever.from_documents(hospital_documents, preprocess_func=ko_tokenize)
    except ImportError:
        bm25_retriever = BM25Retriever.from_documents(hospital_documents)
    ```

    수업에서는 빠른 시연을 위해 기본 토크나이저로 진행합니다.

```python
# ============================================================
# 1. BM25 + 벡터 하이브리드 검색
# ============================================================
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# BM25 Retriever (키워드 기반)
bm25_retriever = BM25Retriever.from_documents(hospital_documents)
bm25_retriever.k = 3

# 벡터 Retriever (의미 기반)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

---

## EnsembleRetriever -- 하이브리드 검색

BM25와 벡터 검색을 가중 결합합니다. `weights=[0.4, 0.6]`은 BM25 40%, 벡터 60%를 의미합니다.

```python
# 하이브리드: BM25 40% + 벡터 60%
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6],
)
```

### 비교 테스트

```python
# 비교 테스트
question = "심장내과 김철수 의사"

print(f"❓ {question}\n")

bm25_results = bm25_retriever.invoke(question)
print(f"🔵 BM25 (키워드):")
for doc in bm25_results:
    print(f"  - {doc.page_content[:60]}...")

vector_results = vector_retriever.invoke(question)
print(f"\n🟢 벡터 (의미):")
for doc in vector_results:
    print(f"  - {doc.page_content[:60]}...")

ensemble_results = ensemble_retriever.invoke(question)
print(f"\n🟡 하이브리드:")
for doc in ensemble_results:
    print(f"  - {doc.page_content[:60]}...")
```

!!! note "핵심 정리"
    "심장내과 김철수 의사"처럼 **고유명사가 포함된 질문**에서는 BM25가 벡터보다 강합니다.
    반면 "심장 관련 전문의"처럼 **의미적 질문**에서는 벡터가 더 강합니다.
    하이브리드는 두 장점을 결합하여 **대부분의 질문에서 안정적인 성능**을 보입니다.

---

## Re-ranking (CrossEncoder) -- 2단계 검색

!!! tip "Re-ranking = 서류 전형 후 면접"
    1단계 (서류 전형): BM25+벡터로 후보 5~10개를 빠르게 뽑습니다.
    2단계 (면접): CrossEncoder가 각 후보를 정밀하게 점수 매기고 재정렬합니다.
    CrossEncoder는 질문-문서 쌍을 동시에 보고 관련성을 판단하므로 정확도가 높습니다.

```python
# ============================================================
# 2. Re-ranking (CrossEncoder)
# ============================================================
from sentence_transformers import CrossEncoder

# CrossEncoder 로드
reranker = CrossEncoder("BAAI/bge-reranker-base")

def rerank(query: str, documents, top_k: int = 3):
    """CrossEncoder로 검색 결과 재정렬"""
    pairs = [(query, doc.page_content) for doc in documents]
    scores = reranker.predict(pairs)

    # 점수 기준 정렬
    scored_docs = list(zip(documents, scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return scored_docs[:top_k]
```

!!! warning "CrossEncoder 다운로드"
    `BAAI/bge-reranker-base`는 약 400MB입니다. 첫 실행 시 다운로드에 시간이 걸립니다.
    Colab에서는 보통 1~2분 정도 소요됩니다.

!!! tip "용량/속도가 부담이면 경량 대안"
    Colab 무료 티어나 저사양 환경에서는 MS MARCO 기반 MiniLM 리랭커가 실용적입니다.

    ```python
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")  # ~80MB
    ```

    정확도는 `bge-reranker-base`보다 약간 낮지만 한국어에서도 준수하며, **다운로드가 5배 이상 빠르고** GPU 없이도 수십 ms 단위로 응답합니다. 수업 첫 실행이 지연된다면 이 대안으로 바꿔 시연하세요.

### Re-ranking 테스트

```python
# 테스트
question = "야간에 어떤 과에서 진료를 받을 수 있나요?"

# 1단계: 하이브리드 검색 (후보 5개)
candidates = ensemble_retriever.invoke(question)[:5]
print(f"🔍 1단계 -- 후보 ({len(candidates)}개):")
for doc in candidates:
    print(f"  - {doc.page_content[:60]}...")

# 2단계: Re-ranking (상위 3개 선정)
reranked = rerank(question, candidates, top_k=3)
print(f"\n🏆 2단계 -- Re-rank 후 (상위 3개):")
for doc, score in reranked:
    print(f"  [{score:.4f}] {doc.page_content[:60]}...")
```

---

## 하이브리드 + Re-rank RAG 체인

검색부터 답변 생성까지 전체 파이프라인을 구축합니다.

```python
# ============================================================
# 3. 하이브리드 + Re-rank RAG 체인
# ============================================================
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

def hybrid_rerank_retriever(query: str) -> str:
    """하이브리드 검색 + Re-rank --> 문서 텍스트"""
    candidates = ensemble_retriever.invoke(query)
    if not candidates:
        return "(검색 결과 없음)"

    reranked = rerank(query, candidates, top_k=3)
    return "\n\n".join(doc.page_content for doc, score in reranked)

rag_prompt = ChatPromptTemplate.from_template("""다음 컨텍스트를 바탕으로 질문에 한국어로 답변하세요.
컨텍스트에 없는 내용은 "해당 정보가 없습니다"라고 답변하세요.

## 컨텍스트
{context}

## 질문
{question}

## 답변""")

final_rag_chain = (
    {"context": hybrid_rerank_retriever, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

answer = final_rag_chain.invoke("야간에 심장 문제가 생기면 어떻게 하나요?")
print(f"💬 {answer}")
```

### 추가 테스트

```python
# 다양한 질문으로 파이프라인 테스트
test_questions = [
    "심장내과 김철수 의사의 진료 시간은?",
    "입원하면 주차 요금이 얼마인가요?",
    "소아과에는 어떤 의사가 있나요?",
]

for q in test_questions:
    print(f"\n❓ {q}")
    answer = final_rag_chain.invoke(q)
    print(f"💬 {answer}")
    print("-" * 40)
```

---

## 전체 파이프라인 비교

각 단계별로 검색 품질이 어떻게 달라지는지 비교합니다:

```python
# ============================================================
# 파이프라인 단계별 비교
# ============================================================
question = "야간에 심장 문제가 생기면?"

# 1단계: 벡터만
vec_only = vector_retriever.invoke(question)
print("🔵 벡터만:")
for doc in vec_only:
    print(f"  - {doc.page_content[:50]}...")

# 2단계: BM25만
bm25_only = bm25_retriever.invoke(question)
print("\n🟢 BM25만:")
for doc in bm25_only:
    print(f"  - {doc.page_content[:50]}...")

# 3단계: 하이브리드
hybrid = ensemble_retriever.invoke(question)
print("\n🟡 하이브리드:")
for doc in hybrid:
    print(f"  - {doc.page_content[:50]}...")

# 4단계: 하이브리드 + Re-rank
reranked = rerank(question, hybrid, top_k=3)
print("\n🏆 하이브리드 + Re-rank:")
for doc, score in reranked:
    print(f"  [{score:.4f}] {doc.page_content[:50]}...")
```

!!! note "핵심 정리"
    파이프라인을 추가할수록 검색 품질이 향상됩니다:
    벡터만 < BM25만 < 하이브리드 < 하이브리드 + Re-rank
    하지만 각 단계가 추가되면 **처리 시간과 비용도 증가**합니다.
    프로젝트의 요구사항에 맞게 적절한 수준을 선택하세요.

---

## Weight 실험 -- 최적 비율 찾기

!!! example "실습 -- 최적 weight 찾기 실험"
    BM25와 벡터의 비율을 0.0 ~ 1.0까지 변경하면서 검색 결과를 비교합니다.

    질문 `"정형외과 척추 전문의"` 에 대해 BM25 가중치를 `[0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]` 으로 바꿔가며 `EnsembleRetriever` 의 Top-1 결과가 어떻게 달라지는지 표로 출력하세요.

    *힌트: 반복문 안에서 매번 새 `EnsembleRetriever(retrievers=[bm25_retriever, vector_retriever], weights=[bm25_w, 1.0 - bm25_w])` 를 만들고, `invoke(question)[0].page_content[:50]` 로 Top-1 미리보기를 뽑아 한 줄씩 정렬해 출력합니다.*

    **결과 기록표:**

    | BM25 | Vector | Top 1 결과 | 정확한가? |
    |---|---|---|---|
    | 0.0 | 1.0 | (벡터만) | |
    | 0.3 | 0.7 | | |
    | 0.4 | 0.6 | | |
    | 0.5 | 0.5 | | |
    | 0.7 | 0.3 | | |
    | 1.0 | 0.0 | (BM25만) | |

    **팁**: 고유명사가 많은 도메인(의료, 법률)은 BM25 비중을 높이고,
    의미 검색이 중요한 도메인(상담, FAQ)은 벡터 비중을 높이세요.

---

## 질문 유형별 최적 비율 정리

!!! tip "도메인별 권장 weight"
    | 질문 유형 | BM25 | Vector | 이유 |
    |---|---|---|---|
    | 고유명사 포함 ("김철수 의사") | 0.6~0.7 | 0.3~0.4 | 정확한 키워드 매칭 필요 |
    | 의미적 질문 ("호흡기 관련") | 0.2~0.3 | 0.7~0.8 | 유의어 검색 필요 |
    | 혼합 질문 ("내과 야간 진료") | 0.4 | 0.6 | 균형 잡힌 검색 |
    | 코드/약어 포함 ("ICD-J45") | 0.7~0.8 | 0.2~0.3 | 정확한 문자열 매칭 |

---

## 실습 과제

1. `ensemble_retriever`로 키워드 질문과 의미 질문을 각각 테스트하세요.
2. CrossEncoder `rerank` 함수로 검색 품질이 개선되는지 확인하세요.
3. weight 실험으로 본인 도메인에 최적인 비율을 찾으세요.

!!! question "생각해보기"
    - BM25 weight = 1.0 (벡터 없음)일 때와 0.0 (BM25 없음)일 때, 어떤 질문에서 차이가 큰가요?
    - Re-ranking은 항상 검색 품질을 개선하나요? 오히려 나빠지는 경우가 있을까요?
    - 하이브리드 검색 + Re-ranking은 Naive 검색 대비 얼마나 느린가요?

---

!!! note "핵심 정리"
    - **하이브리드 검색** = BM25(키워드 정밀) + 벡터(의미 재현율)의 장점 결합
    - **EnsembleRetriever**: `weights=[0.4, 0.6]`으로 비율 조정
    - **Re-ranking**: 1차 검색 후보를 CrossEncoder로 정밀 재정렬
    - **weight 실험**: 도메인에 따라 최적 비율이 다르므로 반드시 실험 필요
    - 전체 파이프라인: 하이브리드 검색 -> Re-ranking -> RAG 답변 생성
