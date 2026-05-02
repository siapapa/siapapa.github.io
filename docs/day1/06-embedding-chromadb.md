# 6H · 임베딩 + ChromaDB 영속화

## 학습목표

- 임베딩(벡터 변환)의 원리를 이해한다
- 코사인 유사도로 문장 간 유사성을 측정할 수 있다
- ChromaDB로 벡터를 영구 저장한다
- LlamaIndex와 ChromaDB를 연동할 수 있다

---

<div class="colab-link" data-notebook="05_embedding_chromadb"></div>

## 임베딩이란? — "단어의 좌표"

!!! tip "임베딩 = 텍스트를 지도 위의 좌표로 바꾸는 것"
    - "두통" -> 좌표 (3, 5)
    - "머리가 아파요" -> 좌표 (3.1, 4.9) ← 가까움! (의미가 비슷하니까)
    - "오늘 날씨" -> 좌표 (8, 1) ← 멀리 떨어져 있음 (의미가 다르니까)

### 텍스트 -> 벡터

임베딩(Embedding)은 텍스트를 **숫자 벡터**로 변환하는 과정입니다.

```
"환자가 두통을 호소합니다" → [0.12, -0.34, 0.56, 0.08, ..., -0.21]  (1536차원)
"머리가 아파요"           → [0.11, -0.32, 0.55, 0.09, ..., -0.20]  (1536차원)
"오늘 날씨가 좋습니다"     → [0.78, 0.45, -0.12, 0.33, ..., 0.67]  (1536차원)
```

- "두통을 호소"와 "머리가 아파요"는 벡터가 **가까움** -> 의미적으로 유사
- "오늘 날씨가 좋습니다"는 벡터가 **멀리 떨어져 있음** -> 의미적으로 다름

---

## 코사인 유사도 — "화살표 방향이 비슷한가?"

두 벡터의 유사도를 측정하는 가장 일반적인 방법입니다.

```
cos(A, B) = (A · B) / (||A|| x ||B||)

결과 범위: -1 ~ 1
  1에 가까움  = 매우 유사 (같은 방향)
  0에 가까움  = 관련 없음 (직각)
 -1에 가까움  = 반대 의미 (반대 방향)
```

- 두 벡터(화살표)의 방향이 같으면 유사도 = 1 (완전 같은 의미)
- 방향이 직각이면 유사도 = 0 (관련 없음)
- 방향이 반대면 유사도 = -1 (반대 의미)

---

## 실습 1 — 임베딩 직접 생성 + 유사도 계산

### 패키지 설치

??? success "정답 보기"

    ```python
    !pip install -q \
        llama-index llama-index-embeddings-openai llama-index-llms-openai \
        llama-index-vector-stores-chroma \
        chromadb \
        numpy matplotlib scikit-learn

    import os
    from google.colab import userdata
    os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
    ```

### 임베딩 함수 정의

??? success "정답 보기"

    ```python
    from openai import OpenAI
    import numpy as np

    client = OpenAI()

    def get_embedding(text: str) -> list[float]:
        """텍스트를 임베딩 벡터로 변환"""
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def cosine_similarity(a: list, b: list) -> float:
        """두 벡터의 코사인 유사도"""
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    ```

### 5개 문장 유사도 매트릭스 실험

??? success "정답 보기"

    ```python
    # 테스트 문장 5개
    sentences = [
        "환자가 심한 두통을 호소합니다",
        "머리가 깨질 듯이 아파요",
        "복부에 통증이 있습니다",
        "오늘 서울 날씨가 맑습니다",
        "내일 비가 올 예정입니다",
    ]

    # 임베딩 생성
    embeddings = [get_embedding(s) for s in sentences]

    print(f"임베딩 차원: {len(embeddings[0])}")
    print(f"\n📊 유사도 행렬:")
    print(f"{'':>5}", end="")
    for i in range(len(sentences)):
        print(f"  [{i}]", end="")
    print()

    for i in range(len(sentences)):
        print(f"[{i}]", end="")
        for j in range(len(sentences)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            print(f"  {sim:.2f}", end="")
        print(f"  ← {sentences[i][:20]}")
    ```

!!! note "핵심 정리"
    기대 결과 해석:

    - [0] "두통을 호소" vs [1] "머리가 아파요" → **높은 유사도** (0.8+)
    - [0] "두통" vs [2] "복부 통증" → **중간 유사도** (둘 다 의료, 하지만 부위가 다름)
    - [0] "두통" vs [3] "날씨" → **낮은 유사도** (완전히 다른 주제)
    - [3] "날씨가 맑다" vs [4] "비가 온다" → **중간 유사도** (둘 다 날씨 주제)

### 유사도 히트맵 시각화

??? success "정답 보기"

    ```python
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'

    # 유사도 행렬 계산
    n = len(sentences)
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            sim_matrix[i][j] = cosine_similarity(embeddings[i], embeddings[j])

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(sim_matrix, cmap='YlOrRd', vmin=0, vmax=1)
    plt.colorbar(im)

    labels = [s[:15] + "..." for s in sentences]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(range(n))
    ax.set_yticklabels(labels)

    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{sim_matrix[i][j]:.2f}", ha="center", va="center", fontsize=10)

    plt.title("Cosine Similarity Matrix")
    plt.tight_layout()
    plt.show()
    ```

---

## 임베딩 모델 비교

| 모델 | 차원 | 비용 | 특징 |
|---|---|---|---|
| `text-embedding-3-small` | 1,536 (축소 가능) | 저렴 ($0.02/1M tokens) | 빠르고 경제적. 대부분의 경우 충분 |
| `text-embedding-3-large` | 3,072 (축소 가능) | 보통 ($0.13/1M tokens) | 더 높은 정확도. 정밀 검색 필요 시 |
| `BAAI/bge-m3` | 1,024 | 무료 (HF) | 다국어(한국어 포함) 최신 오픈 임베딩. 권장 대안. |
| `jhgan/ko-sroberta-multitask` | 768 | 무료 (HF) | 한국어 SRoBERTa. 실재 확인된 한국어 특화 모델. |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | 무료 (HF) | 다국어, 경량(~100MB) |

!!! tip "어떤 모델을 선택할까?"
    - **프로토타입/학습**: `text-embedding-3-small` (빠르고 저렴)
    - **프로덕션 (정확도 중요)**: `text-embedding-3-large`
    - **비용 제한/오프라인**: `BAAI/bge-m3` 또는 `jhgan/ko-sroberta-multitask` (무료, 로컬 실행)

!!! warning "존재하지 않는 모델 이름 조심"
    과거 문서에서 자주 인용되는 `BAAI/bge-small-ko`는 **HuggingFace 허브에 실재하지 않는** 이름입니다. 오타로 퍼진 케이스로, 그대로 붙여 쓰면 `OSError: not found` 가 납니다. 한국어 특화를 원하면 **`jhgan/ko-sroberta-multitask`**(768차원), 다국어 포함 최신 임베딩을 원하면 **`BAAI/bge-m3`**(1,024차원)를 쓰세요.

### (실험) `dimensions` 파라미터로 벡터 축소

OpenAI 3세대 임베딩(`text-embedding-3-*`)은 **차원 축소**를 런타임에 선택할 수 있습니다. 대용량 저장 비용/속도와 정확도의 트레이드오프를 실험해보세요.

```python
from openai import OpenAI
client = OpenAI()

def embed(text: str, dim: int = 1536) -> list[float]:
    res = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
        dimensions=dim,          # 1536 → 512 → 256 으로 축소
    )
    return res.data[0].embedding

# 비교: 같은 문장을 1536 vs 256 차원으로 임베딩하여 유사도 저하를 관측
for d in (1536, 512, 256):
    v1 = embed("내과 의사가 몇 명인가요?", dim=d)
    v2 = embed("내과에서 일하는 의사 수는?", dim=d)
    print(f"dim={d}: cos={cosine_similarity(v1, v2):.4f}")
```

!!! tip "`dimensions`를 언제 줄일까?"
    - 저장소/메모리 비용이 큰 대량 벡터(수백만 건) → 512 또는 256 실험 가치 있음.
    - 256 이하부터는 한국어 구분력이 눈에 띄게 떨어집니다.
    - 차원을 줄이면 임베딩 인덱스는 **반드시 새로 만들어야** 합니다 (차원이 맞지 않으면 Chroma가 `dimensionality mismatch` 에러 발생).

---

## 2D 시각화 개념 — t-SNE

임베딩 벡터는 1,536차원이라 직접 시각화가 불가능합니다.
**t-SNE**(t-Distributed Stochastic Neighbor Embedding)를 사용하면
1,536차원을 2차원으로 축소하여 시각화할 수 있습니다.

```
원래: 1536차원 공간
  "두통"     = [0.12, -0.34, 0.56, ..., -0.21]  (1536개 숫자)
  "머리아파" = [0.11, -0.32, 0.55, ..., -0.20]

t-SNE 축소 후: 2차원 공간
  "두통"     = (3.2, 5.1)    ← 가까이 모여있음
  "머리아파" = (3.5, 4.8)    ← 의미가 비슷하니까!
  "날씨"     = (8.1, 1.3)    ← 멀리 떨어져있음
```

핵심 원리: **원래 고차원에서 가까운 점들은 2차원으로 축소해도 가까이 배치**됩니다.
이를 통해 비슷한 의미의 단어/문장이 시각적으로 클러스터를 형성하는 것을 관찰할 수 있습니다.

---

## 실습 2 — ChromaDB 연동

!!! tip "왜 ChromaDB가 필요한가?"
    5H에서 만든 인덱스는 Colab을 닫으면 사라집니다 (인메모리).
    ChromaDB를 사용하면 벡터를 **영구 저장**할 수 있습니다.

    - 인메모리: 빠르지만 휘발성 (세션 종료 시 소멸)
    - ChromaDB: 디스크에 저장되어 영속성 보장

### ChromaDB 저장소 생성

??? success "정답 보기"

    ```python
    import chromadb

    # PersistentClient: 데이터가 디스크에 저장됨
    chroma_client = chromadb.PersistentClient(path="./chroma_db")

    # 컬렉션 생성 (또는 기존 컬렉션 로드)
    collection = chroma_client.get_or_create_collection(
        name="hospital_docs",
        metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
    )

    print(f"✅ ChromaDB 컬렉션 생성: {collection.name}")
    print(f"   기존 문서 수: {collection.count()}")
    ```

### 문서 추가

??? success "정답 보기"

    ```python
    # 병원 문서들을 ChromaDB에 직접 저장
    documents = [
        "서울중앙병원 내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기) 전문의가 있습니다.",
        "외과는 박민수(일반외과), 정수진(흉부외과), 권혁준(혈관외과)이 근무합니다.",
        "진료 시간은 평일 09:00-18:00, 토요일 09:00-13:00입니다.",
        "응급실은 24시간 운영되며, 야간 당직의가 상주합니다.",
        "입원 병실은 1인실(25만원/일), 2인실(15만원/일), 4인실(8만원/일)입니다.",
        "외래 환자 주차는 3시간 무료이며, 이후 30분당 1,000원입니다.",
        "진단서 발급은 1층 제증명 창구에서 가능하며, 소요 시간은 약 30분입니다.",
        "소아과에는 최동현, 강미래, 문서영 전문의가 소아청소년 질환을 진료합니다.",
    ]

    metadatas = [
        {"section": "내과", "doc_type": "department"},
        {"section": "외과", "doc_type": "department"},
        {"section": "진료시간", "doc_type": "guide"},
        {"section": "응급실", "doc_type": "guide"},
        {"section": "입원", "doc_type": "guide"},
        {"section": "주차", "doc_type": "guide"},
        {"section": "제증명", "doc_type": "guide"},
        {"section": "소아과", "doc_type": "department"},
    ]

    # Upsert (있으면 업데이트, 없으면 추가)
    collection.upsert(
        ids=[f"doc_{i}" for i in range(len(documents))],
        documents=documents,
        metadatas=metadatas,
    )

    print(f"✅ {len(documents)}개 문서 저장 완료 (총 {collection.count()}개)")
    ```

### ChromaDB 검색

??? success "정답 보기"

    ```python
    # 유사도 검색
    results = collection.query(
        query_texts=["내과 의사가 누구인가요?"],
        n_results=3,
    )

    print("🔍 검색: '내과 의사가 누구인가요?'\n")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        similarity = 1 - dist  # ChromaDB는 distance를 반환 → similarity로 변환
        print(f"  [{i+1}] 유사도={similarity:.3f} | 섹션={meta['section']}")
        print(f"      {doc}")
    ```

### 메타데이터 필터링 검색

??? success "정답 보기"

    ```python
    # doc_type이 "department"인 문서만 검색
    results_filtered = collection.query(
        query_texts=["의사 정보를 알려주세요"],
        n_results=5,
        where={"doc_type": "department"},  # department 타입만 검색
    )

    print("\n🔍 필터 검색: doc_type='department'\n")
    for doc, meta in zip(results_filtered["documents"][0], results_filtered["metadatas"][0]):
        print(f"  [{meta['section']}] {doc}")
    ```

---

## 실습 3 — LlamaIndex + ChromaDB 연동

LlamaIndex의 VectorStoreIndex와 ChromaDB를 연결하면
LlamaIndex의 편리한 Query Engine + ChromaDB의 영속 저장을 함께 활용할 수 있습니다.

??? success "정답 보기"

    ```python
    from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI

    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    # ChromaDB 컬렉션을 LlamaIndex 벡터스토어로 래핑
    chroma_collection = chroma_client.get_or_create_collection("hospital_llamaindex")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # LlamaIndex 문서 → ChromaDB에 인덱싱
    li_docs = [
        Document(text=doc, metadata=meta)
        for doc, meta in zip(documents, metadatas)
    ]

    index = VectorStoreIndex.from_documents(
        li_docs,
        storage_context=storage_context,
        show_progress=True,
    )

    print(f"✅ LlamaIndex + ChromaDB 인덱싱 완료!")
    ```

### 질의 테스트

??? success "정답 보기"

    ```python
    # Query Engine으로 질의
    query_engine = index.as_query_engine(similarity_top_k=3)

    response = query_engine.query("응급실 이용 가능한 시간은?")
    print(f"💬 답변: {response.response}")
    print(f"\n📚 참조:")
    for node in response.source_nodes:
        print(f"  - score={node.score:.3f}: {node.text[:60]}...")
    ```

### Top-K 검색 실습

??? success "정답 보기"

    ```python
    # Top-K 값에 따른 결과 비교
    for k in [1, 3, 5]:
        qe = index.as_query_engine(similarity_top_k=k)
        resp = qe.query("주차 요금이 어떻게 되나요?")
        print(f"\n--- similarity_top_k={k} ---")
        print(f"💬 답변: {resp.response}")
        print(f"   참조 문서 수: {len(resp.source_nodes)}")
    ```

### 영속성 확인

??? success "정답 보기"

    ```python
    # 세션 재시작 후에도 데이터 유지 확인
    chroma_client2 = chromadb.PersistentClient(path="./chroma_db")
    collection2 = chroma_client2.get_collection("hospital_docs")

    print(f"✅ 재접속 후 문서 수: {collection2.count()}")
    # → 세션이 끊겨도 ./chroma_db 폴더에 데이터가 남아있음!
    ```

---

## 추가 실습

!!! example "실습 — 의료 용어 유사도 실험"
    의료 도메인에서 유사한 표현들의 임베딩 유사도를 실험해보세요.

    테스트할 용어 6개:

    - "고혈압", "혈압이 높다"
    - "두통", "머리가 아프다"
    - "당뇨병", "혈당이 높다"

    _힌트: 위 6개 용어를 리스트로 만들고 각각 `get_embedding(t)`로 임베딩한 뒤, 이중 for 루프(`i, j with i<j`)로 모든 쌍에 대해 `cosine_similarity()`를 출력하세요._

    **관찰 포인트:**

    - "고혈압" vs "혈압이 높다" → 높은 유사도 (같은 의미, 다른 표현)
    - "고혈압" vs "두통" → 중간 유사도 (고혈압의 증상으로 두통이 올 수 있음)
    - "고혈압" vs "당뇨병" → 중간 유사도 (둘 다 만성질환)
    - 이런 의미적 유사성을 AI가 자동으로 파악하는 것이 임베딩의 핵심입니다

!!! tip "Embedding 캐싱으로 비용 절약"
    같은 텍스트를 반복 임베딩하면 API 비용이 낭비됩니다.
    캐싱 전략으로 비용을 크게 줄일 수 있습니다.

    **방법 1: 딕셔너리 캐시 (간단)**

    ```python
    embedding_cache = {}

    def get_embedding_cached(text: str) -> list[float]:
        if text not in embedding_cache:
            embedding_cache[text] = get_embedding(text)
        return embedding_cache[text]
    ```

    **방법 2: ChromaDB 자체가 캐시 역할**

    - ChromaDB에 문서를 저장하면 임베딩도 함께 저장됩니다
    - 같은 문서를 다시 인덱싱할 필요가 없습니다
    - `upsert`를 사용하면 변경된 문서만 업데이트됩니다

    **방법 3: 파일 기반 캐시 (세션 간 유지)**

    ```python
    import json

    CACHE_FILE = "embedding_cache.json"

    def save_cache():
        with open(CACHE_FILE, 'w') as f:
            json.dump(embedding_cache, f)

    def load_cache():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    ```

    **비용 참고**: `text-embedding-3-small`은 1M 토큰당 약 $0.02입니다.
    병원 문서 8개는 약 500토큰이므로 비용은 미미하지만,
    대량 문서(수천~수만 건)를 처리할 때는 캐싱이 필수입니다.

!!! question "생각해보기"
    1. 한국어와 영어의 임베딩 유사도 차이가 있을까요? "headache"와 "두통"의 유사도를 실험해보세요.
    2. ChromaDB 외에 다른 벡터 DB(Pinecone, Weaviate, Milvus)는 어떤 특징이 있을까요?
    3. 임베딩 모델을 바꾸면 기존 ChromaDB 데이터를 그대로 쓸 수 있을까요? (정답: 아닙니다. 모델이 다르면 벡터 공간이 달라지므로 재인덱싱 필요)

---

## 핵심 정리

!!! note "핵심 정리"
    - **임베딩** = 텍스트를 숫자 벡터(좌표)로 변환하는 것
    - **코사인 유사도** = 두 벡터의 방향이 비슷하면 의미가 비슷
    - **ChromaDB** = 벡터를 영구 저장하는 "보관함" (PersistentClient)
    - **LlamaIndex + ChromaDB** = 편리한 Query Engine + 영속 저장
    - **Top-K**: 검색 시 가져올 문서 수. 보통 3~5가 적절
    - **임베딩 캐싱**: 같은 텍스트 반복 임베딩 방지로 비용 절약
    - 다음 시간(7H)에서 이 파이프라인을 Text-to-SQL에 연결합니다
