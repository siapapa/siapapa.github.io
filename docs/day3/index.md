# Day 3 -- Vanna / LangChain / Advanced RAG / LangGraph (13~20H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API

---

## 학습 목표

- Vanna의 RAG 기반 Text-to-SQL 아키텍처를 이해하고 자가학습시킨다
- LangChain/LCEL로 체인을 조립하고 RAG 파이프라인을 구축한다
- HyDE, Multi-Query, 하이브리드 검색, Re-ranking 등 Advanced RAG 기법을 적용한다
- LangGraph로 조건 분기와 재시도가 가능한 SQL 에이전트를 빌드한다

---

## 8시간 타임라인

| 시간 | 주제 | 핵심 활동 |
|---|---|---|
| **13H** | Vanna 구조 | LlamaIndex vs Vanna 비교, 베이스라인 측정 |
| **14H** | Vanna 자가학습 | DDL/Documentation/SQL Pairs 학습, 정확도 비교 |
| **15H** | LangChain/LCEL 기초 | 파이프 연산자 체인, 구조화 출력 |
| **16H** | LCEL RAG 체인 | ChromaDB + RAG 체인 조립, 스트리밍 |
| **17H** | 쿼리 변환 | HyDE, Multi-Query, Decomposition |
| **18H** | 검색 고도화 | BM25+벡터 하이브리드, Re-ranking |
| **19H** | LangGraph 개념 | StateGraph, 조건부 분기, 루프 |
| **20H** | SQL 에이전트 빌드 | 4노드 그래프, 10개 질문 테스트 |

---

## 키워드 표

| 시간 | 핵심 키워드 |
|---|---|
| 13H | RAG 기반 Text-to-SQL, 학습 자산 3종 |
| 14H | DDL/Documentation/SQL Pairs 학습, 정확도 비교 |
| 15H | 파이프 연산자, invoke/stream/batch, 구조화 출력 |
| 16H | Retriever, Prompt, LLM, Parser |
| 17H | HyDE, Multi-Query, Decomposition |
| 18H | BM25+벡터 하이브리드, Re-ranking |
| 19H | StateGraph, Node, Edge, 조건부 분기 |
| 20H | 4노드 그래프, 재시도, 10개 질문 테스트 |

---

## 용어 사전 (비IT 수강생을 위한)

| 용어 | 쉬운 설명 |
|---|---|
| **파이프라인(Pipeline)** | 여러 단계가 순서대로 연결된 처리 과정. 공장의 "조립 라인"과 같음 |
| **프레임워크(Framework)** | 자주 쓰는 기능이 미리 만들어진 "도구 상자". 처음부터 만들 필요 없이 가져다 쓰면 됨 |
| **하이브리드(Hybrid)** | 두 가지를 섞는 것. 키워드 검색 + 의미 검색을 함께 사용 |
| **노드(Node)** | 그래프에서 하나의 "작업 단위". 네모 칸 하나 |
| **엣지(Edge)** | 노드와 노드를 잇는 "화살표". 작업 순서를 나타냄 |
| **상태 머신(State Machine)** | "현재 상태"에 따라 다음 행동이 달라지는 시스템. 자판기와 비슷 |

---

## 공통 부트스트랩

```python
# Day 3에 사용할 도구 설치
!pip install -q \
    vanna chromadb \
    langchain langchain-openai langchain-community langchain-chroma \
    langgraph \
    llama-index llama-index-llms-openai llama-index-embeddings-openai \
    sqlalchemy psycopg2-binary pandas tabulate \
    rank_bm25 sentence-transformers \
    openai sqlparse pydantic

import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text
engine = create_engine(os.environ["NEON_DSN"])
print("✅ 연결 성공!")
```

---

!!! note "핵심 정리"
    - Day 3는 8시간 동안 **Vanna -> LangChain -> Advanced RAG -> LangGraph**로 점진적 확장
    - 최종 목표: LangGraph 기반 SQL 분석 에이전트 빌드 (20H)
    - **과제 #3**: Day 4 시작 전까지 에이전트 v1 + 10개 질문 테스트 결과 제출
