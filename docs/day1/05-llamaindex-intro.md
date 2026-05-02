# 5H · LlamaIndex 파이프라인 개론

## 학습목표

- RAG(Retrieval-Augmented Generation)의 개념과 필요성을 설명할 수 있다
- LlamaIndex의 5단계 파이프라인을 이해한다
- `Settings` 객체를 통해 LLM과 임베딩 모델을 설정할 수 있다
- 문서 로딩, 청킹, 인덱싱, 질의를 수행할 수 있다

---

<div class="colab-link" data-notebook="04_llamaindex_intro"></div>

## RAG란? — "오픈북 시험"

!!! tip "RAG(Retrieval-Augmented Generation) = 오픈북 시험"
    - AI(LLM)은 학습 데이터에 없는 정보를 모릅니다 (회사 내부 데이터, 최신 정보)
    - RAG는 "관련 자료를 찾아서(Retrieval) AI에게 건네주는(Augmented) 방식"
    - AI는 건네받은 자료를 참고하여 답변을 생성(Generation)합니다

### LLM의 한계

LLM은 학습 데이터에 포함된 정보만 알고 있습니다:

- 회사 내부 데이터를 모름
- 최신 정보를 모름 (학습 시점 이후)
- 할루시네이션 (없는 정보를 만들어냄)

### RAG의 해결 방식

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  질문     │ →  │  검색     │ →  │ 컨텍스트  │ →  │  LLM     │
│ "매출은?" │    │ 관련문서   │    │ + 질문    │    │ 답변 생성 │
└──────────┘    │ 상위 K개  │    └──────────┘    └──────────┘
                └──────────┘
                  벡터 DB
```

### 동작 과정 예시

```
질문: "내과에 어떤 의사가 있나요?"
  ↓
[검색] 관련 문서 찾기 → "내과에는 김철수, 이영희, 신민아 전문의가..."
  ↓
[증강] 찾은 문서 + 질문을 AI에게 전달
  ↓
[생성] AI: "내과에는 심장내과 김철수, 호흡기내과 이영희, 소화기내과 신민아 전문의가 있습니다."
```

1. **Retrieval (검색)**: 질문과 관련된 문서를 벡터 DB에서 찾아옴
2. **Augmented (증강)**: 찾은 문서를 LLM 프롬프트에 추가
3. **Generation (생성)**: LLM이 제공된 컨텍스트 기반으로 답변 생성

---

## LlamaIndex 5단계 파이프라인

```
Documents  →  Nodes(Chunks)  →  Embeddings  →  Index  →  QueryEngine
 (원본 문서)    (청크 분할)      (벡터 변환)    (저장/검색)   (질의 응답)

  📄 PDF       📝 512자씩      🔢 [0.1,      🗄️ 벡터     ❓ "매출은?"
  📄 CSV        분할            0.3, ...]      DB에        💬 "답변..."
  📄 SQL                                       인덱싱
```

| 단계 | 역할 | LlamaIndex 클래스 |
|---|---|---|
| 1. Documents | 원본 문서 로딩 | `Document`, `SimpleDirectoryReader` |
| 2. Nodes | 작은 조각으로 분할 | `SentenceSplitter`, `TokenTextSplitter` |
| 3. Embeddings | 텍스트를 숫자 벡터로 변환 | `OpenAIEmbedding` |
| 4. Index | 벡터를 검색 가능하게 저장 | `VectorStoreIndex` |
| 5. QueryEngine | 질문을 받아 답변 생성 | `index.as_query_engine()` |

---

## 실습 — 병원 안내 RAG 만들기

### Step 0: 패키지 설치

```python
!pip install -q llama-index llama-index-llms-openai llama-index-embeddings-openai

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
```

### Step 1: Settings 객체 — 전역 설정

```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# 전역 LLM 설정 (모든 쿼리에서 사용)
Settings.llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0,          # 결정적 출력 (일관된 결과)
    max_tokens=1024,
)

# 전역 임베딩 모델 설정 (모든 인덱싱/검색에서 사용)
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # 빠르고 저렴
    # model="text-embedding-3-large",  # 더 정확하지만 비용 ↑
)

print(f"✅ LLM: {Settings.llm.model}")
print(f"✅ Embedding: {Settings.embed_model.model_name}")
```

!!! note "핵심 정리"
    `Settings` 객체는 LlamaIndex 전역 설정입니다.

    - `Settings.llm` : 답변 생성에 사용할 LLM 모델
    - `Settings.embed_model` : 문서 임베딩에 사용할 모델
    - 한 번 설정하면 이후 모든 인덱싱/질의에서 자동 적용됩니다

### Step 2: Document 로딩 — 병원 안내 문서 4종

```python
from llama_index.core import Document

# 병원 관련 문서를 직접 생성 (실습용)
hospital_docs = [
    Document(
        text="""
        서울중앙병원 진료 안내
        
        진료 시간: 평일 09:00-18:00, 토요일 09:00-13:00
        점심 시간: 12:30-13:30
        응급실: 24시간 운영
        
        외래 진료 예약은 전화(02-1234-5678) 또는 온라인으로 가능합니다.
        초진 환자는 신분증을 지참해 주세요.
        """,
        metadata={"source": "hospital_guide", "section": "진료안내", "doc_type": "guide"}
    ),
    Document(
        text="""
        진료과 소개
        
        내과: 심장, 호흡기, 소화기 질환을 전문으로 합니다. 김철수, 이영희, 신민아 전문의가 진료합니다.
        외과: 일반외과, 흉부외과, 혈관외과를 운영합니다. 박민수, 정수진, 권혁준 전문의가 근무합니다.
        소아과: 소아청소년과와 신생아과로 구성되어 있으며, 최동현, 강미래, 문서영 전문의가 있습니다.
        정형외과: 척추, 관절 질환을 전문으로 하며, 윤성호, 한지은 전문의가 진료합니다.
        """,
        metadata={"source": "hospital_guide", "section": "진료과소개", "doc_type": "guide"}
    ),
    Document(
        text="""
        입원 안내
        
        입원 절차:
        1. 담당 의사의 입원 결정
        2. 원무과에서 입원 수속 (보험증, 신분증 필요)
        3. 병동 배정 및 입실
        
        병실 종류:
        - 1인실: 250,000원/일
        - 2인실: 150,000원/일  
        - 4인실: 80,000원/일
        - 다인실: 건강보험 적용
        
        면회 시간: 매일 18:00-20:00
        """,
        metadata={"source": "hospital_guide", "section": "입원안내", "doc_type": "guide"}
    ),
    Document(
        text="""
        자주 묻는 질문 (FAQ)
        
        Q: 진료비 수납은 어떻게 하나요?
        A: 진료 후 1층 수납 창구 또는 무인 수납기를 이용해 주세요. 카드, 현금, 계좌이체 가능합니다.
        
        Q: 진단서 발급은 어떻게 하나요?
        A: 1층 제증명 창구에서 신청하실 수 있습니다. 신분증 지참 필수이며, 발급 소요 시간은 약 30분입니다.
        
        Q: 주차 요금은 얼마인가요?
        A: 외래 환자 3시간 무료, 이후 30분당 1,000원입니다. 입원 환자 보호자는 1일 5,000원입니다.
        """,
        metadata={"source": "hospital_guide", "section": "FAQ", "doc_type": "faq"}
    ),
]

print(f"✅ 로드된 문서 수: {len(hospital_docs)}")
for doc in hospital_docs:
    print(f"  - [{doc.metadata['section']}] {doc.text[:50].strip()}...")
```

### Step 3: 청킹 — 문서를 작은 조각(Node)으로 분할

!!! tip "왜 청킹이 필요한가? — 교과서 통째로 vs 페이지 몇 장"
    시험 문제를 풀 때 **교과서 전체를 통째로 들고 찾는 것**과 **필요한 페이지 몇 장만 뽑아서 보는 것** 중 어느 쪽이 빠르고 정확할까요?
    - **검색 정밀도**: 문서 전체를 한 덩어리로 넣으면 "관련 있음/없음"만 판단 → 긴 문서는 무조건 상위에 올라감. 쪼개면 "어느 부분이 관련 있는지"까지 판단 가능.
    - **컨텍스트 윈도우 제약**: LLM은 한 번에 넣을 수 있는 텍스트 길이(토큰 수)가 제한됨. 교과서 10권을 통째로 넣을 수는 없음.
    - **비용·지연**: 프롬프트가 길어질수록 비용↑·응답 속도↓. 질문에 꼭 필요한 조각만 넣는 게 경제적.
    → 그래서 문서를 **검색 단위(노드)**로 잘라 저장하고, 질문과 가장 가까운 조각만 뽑아 LLM에 넣는 것이 RAG의 핵심 아이디어입니다.

```python
from llama_index.core.node_parser import SentenceSplitter

# SentenceSplitter: 문장 경계를 존중하면서 청킹
splitter = SentenceSplitter(
    chunk_size=256,        # 청크 최대 크기 (토큰 기준)
    chunk_overlap=30,      # 청크 간 겹침 (문맥 연결성 유지)
)

nodes = splitter.get_nodes_from_documents(hospital_docs)

print(f"✅ 생성된 노드(청크) 수: {len(nodes)}")
print(f"\n{'='*50}")
for i, node in enumerate(nodes):
    print(f"\n--- 노드 {i+1} ---")
    print(f"  텍스트: {node.text[:100].strip()}...")
    print(f"  메타데이터: {node.metadata}")
    print(f"  길이: {len(node.text)} 자")
```

!!! tip "chunk_size와 chunk_overlap의 역할"
    - **chunk_size** (256): 한 조각의 최대 크기 (토큰 수)
      - 작으면: 정밀한 검색, 하지만 문맥이 끊길 수 있음
      - 크면: 문맥 유지, 하지만 검색 정밀도 하락
    - **chunk_overlap** (30): 인접 조각 간 겹치는 부분
      - 문장이 조각 경계에서 잘리는 것을 방지
      - 보통 chunk_size의 10~15%로 설정

### 청킹 전략 비교: SentenceSplitter vs TokenTextSplitter

```python
from llama_index.core.node_parser import TokenTextSplitter

# TokenTextSplitter: 토큰 단위로 정확히 분할 (문장 경계 무시)
token_splitter = TokenTextSplitter(chunk_size=256, chunk_overlap=30)
token_nodes = token_splitter.get_nodes_from_documents(hospital_docs)

print(f"\n📊 청킹 전략 비교:")
print(f"  SentenceSplitter: {len(nodes)}개 노드")
print(f"  TokenTextSplitter: {len(token_nodes)}개 노드")
```

| 전략 | 특징 | 장점 | 단점 |
|---|---|---|---|
| SentenceSplitter | 문장 경계 존중 | 문장이 중간에 잘리지 않음 | 청크 크기가 불균일할 수 있음 |
| TokenTextSplitter | 토큰 단위로 정확히 자름 | 균일한 청크 크기 | 문장이 중간에 잘릴 수 있음 |

### Step 4: 인덱싱 — VectorStoreIndex

```python
from llama_index.core import VectorStoreIndex

# 문서를 임베딩 → 인메모리 벡터 인덱스에 저장
index = VectorStoreIndex.from_documents(
    hospital_docs,
    transformations=[splitter],  # 청킹 전략 지정
    show_progress=True,
)

print("✅ 인덱싱 완료!")
```

### Step 5: 질의 — Query Engine

```python
# Query Engine 생성
query_engine = index.as_query_engine(
    similarity_top_k=3,     # 상위 3개 관련 문서 검색
)

# 질의
response = query_engine.query("내과에는 어떤 의사가 있나요?")
print(f"💬 답변: {response.response}")
print(f"\n📚 참조한 소스:")
for node in response.source_nodes:
    print(f"  - [{node.metadata.get('section', '?')}] score={node.score:.3f}")
    print(f"    {node.text[:80].strip()}...")
```

### 추가 질의 테스트 (4개)

```python
# 다양한 질문으로 RAG 테스트
questions = [
    "내과에는 어떤 의사가 있나요?",
    "입원 1인실 비용은 얼마인가요?",
    "주차 요금에 대해 알려주세요.",
    "응급실은 언제 이용할 수 있나요?",
]

for q in questions:
    resp = query_engine.query(q)
    print(f"\n❓ {q}")
    print(f"💬 {resp.response}")
    print(f"   (참조 {len(resp.source_nodes)}개, 최고 유사도: {resp.source_nodes[0].score:.3f})")
```

!!! tip "similarity_top_k가 결과에 미치는 영향"
    `similarity_top_k`는 검색 시 가져올 문서 조각의 수입니다.

    - **top_k=1**: 가장 관련 높은 1개만 → 정밀하지만 정보 누락 가능
    - **top_k=3**: 상위 3개 → 균형잡힌 선택 (기본 권장)
    - **top_k=5**: 상위 5개 → 풍부한 컨텍스트, 하지만 노이즈 증가 + 토큰 비용 증가

    질문이 여러 문서에 걸친 정보를 필요로 하면 top_k를 높이세요.
    단답형 질문이면 top_k=1~2로 충분합니다.

---

## Retriever — 검색만 수행 (LLM 호출 없이)

Query Engine은 "검색 + LLM 답변 생성"을 한번에 수행합니다.
Retriever는 **검색만** 수행하여 어떤 문서가 검색되는지 확인할 수 있습니다.

```python
# Retriever: LLM 호출 없이 검색만
retriever = index.as_retriever(similarity_top_k=3)

nodes_found = retriever.retrieve("외래 진료 시간이 어떻게 되나요?")

print(f"🔍 검색 결과 ({len(nodes_found)}개):")
for i, node in enumerate(nodes_found):
    print(f"\n--- 결과 {i+1} (유사도: {node.score:.4f}) ---")
    print(f"  섹션: {node.metadata.get('section', '?')}")
    print(f"  내용: {node.text[:200].strip()}")
```

!!! note "핵심 정리"
    - **Query Engine** = 검색 + LLM 답변 생성 (최종 사용자용)
    - **Retriever** = 검색만 (디버깅/분석용)

    RAG 시스템을 개발할 때는 Retriever로 먼저 "올바른 문서가 검색되는지" 확인한 후,
    Query Engine으로 최종 답변 품질을 검증하는 것이 좋습니다.

---

## 실습

!!! example "실습 — chunk_size 비교 실험"
    `chunk_size`를 128, 256, 512로 바꿔서 각각의 노드 수와 검색 결과를 비교해보세요.

    _힌트: `for size in [128, 256, 512]:` 루프 안에서 매번 `SentenceSplitter`와 `VectorStoreIndex`를 새로 만들고, 같은 질문("입원 1인실 비용은?")으로 `query_engine.query()`를 호출해 노드 수와 답변을 출력하세요._

    **관찰 포인트:**

    - chunk_size가 작을수록 노드 수가 많아지고 검색이 정밀해집니다
    - chunk_size가 너무 작으면 문맥이 끊겨서 답변 품질이 떨어질 수 있습니다
    - 최적의 chunk_size는 문서 특성과 질문 유형에 따라 다릅니다

!!! example "실습 — 새 문서 추가 후 재인덱싱"
    "비급여 항목 안내" 문서를 추가하고 인덱스를 재구성해보세요.

    문서에 들어갈 내용 예시:

    - 일반 건강검진: 150,000원
    - 종합 건강검진: 500,000원
    - MRI 촬영: 400,000원~800,000원 (부위별 상이)
    - CT 촬영: 200,000원~400,000원
    - 도수치료: 1회 80,000원

    _힌트: 새 `Document(text=..., metadata={"section": "비급여안내", ...})`를 만들어 `hospital_docs + [new_doc]`로 합친 뒤, `VectorStoreIndex.from_documents(...)`로 재인덱싱하고 "MRI 비용은 얼마인가요?"로 질의하세요._

!!! question "생각해보기"
    1. 병원 안내 문서 대신 본인 프로젝트의 도메인 문서를 로딩한다면 어떤 문서를 넣겠습니까?
    2. chunk_size를 너무 크게 잡으면 어떤 문제가 생길까요? 너무 작으면?
    3. 메타데이터(`section`, `doc_type`)를 활용하면 검색을 어떻게 개선할 수 있을까요?

---

## 핵심 정리

!!! note "핵심 정리"
    - **RAG** = AI에게 참고 자료를 건네주는 방식 ("오픈북 시험")
    - **5단계**: 문서 로딩 → 청킹 → 임베딩 → 인덱싱 → 질의
    - **Settings**: `Settings.llm`과 `Settings.embed_model`로 전역 설정
    - **SentenceSplitter**: 문장 경계를 존중하는 청킹 전략
    - **VectorStoreIndex**: 벡터 인덱스 생성 + 질의 엔진 제공
    - **Retriever**: LLM 없이 검색만 수행하여 디버깅에 활용
    - LlamaIndex가 이 전체 과정을 쉽게 구현하게 해줌
    - 이 시간에는 인메모리 인덱스 → 6H에서 ChromaDB로 영속화
