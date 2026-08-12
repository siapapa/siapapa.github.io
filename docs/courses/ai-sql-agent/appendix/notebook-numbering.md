# 노트북 번호 체계

이 강의에서 사용하는 Google Colab 노트북은 `00`번부터 `19`번까지 순서대로 번호가 매겨져 있습니다. 수강생은 이 순서대로 실습을 진행합니다.

---

## 노트북 파일명 및 대응 시간

| 번호 | 파일명 | 시간 | Day | 주제 |
|---|---|---|---|---|
| 00 | `00_demo_agent.ipynb` | 1H | Day 1 | OT & 전체 데모 |
| 01 | `01_postgres_basics.ipynb` | 2H | Day 1 | PostgreSQL 기초 |
| 02 | `02_sql_aggregation_join.ipynb` | 3H | Day 1 | 집계 & 조인 |
| 03 | `03_schema_intelligence.ipynb` | 4H | Day 1 | Schema Intelligence |
| 04 | `04_llamaindex_intro.ipynb` | 5H | Day 1 | LlamaIndex 개론 |
| 05 | `05_embedding_chromadb.ipynb` | 6H | Day 1 | 임베딩 + ChromaDB |
| 06 | `06_text_to_sql.ipynb` | 7H | Day 1 | Text-to-SQL 맛보기 |
| 07 | `07_project_briefing.ipynb` | 8H | Day 1 | 프로젝트 브리핑 |
| 08 | `08_text_to_sql_advanced.ipynb` | 10H | Day 2 | Text-to-SQL 심화 |
| 09 | `09_gradio_chatbot.ipynb` | 11~12H | Day 2 | Gradio 챗봇 UI |
| 10 | `10_vanna_intro.ipynb` | 13H | Day 3 | Vanna.ai 구조 |
| 11 | `11_vanna_training.ipynb` | 14H | Day 3 | Vanna 자가학습 |
| 12 | `12_langchain_lcel.ipynb` | 15H | Day 3 | LangChain & LCEL |
| 13 | `13_lcel_rag_chain.ipynb` | 16H | Day 3 | LCEL RAG 체인 |
| 14 | `14_advanced_rag_query.ipynb` | 17H | Day 3 | Advanced RAG 쿼리 변환 |
| 15 | `15_advanced_rag_retrieval.ipynb` | 18H | Day 3 | Advanced RAG 검색 고도화 |
| 16 | `16_langgraph_concept.ipynb` | 19H | Day 3 | LangGraph 개념 |
| 17 | `17_my_sql_agent.ipynb` | 20H | Day 3 | SQL 에이전트 빌드 |
| 18 | `18_langsmith_tracing.ipynb` | 21H | Day 4 | LangSmith 트레이싱 |
| 19 | `19_ragas_eval.ipynb` | 22H | Day 4 | Ragas 정량 평가 |

---

## 번호 체계 규칙

!!! tip "팁"
    번호는 **교육 순서**(pedagogical order)를 따릅니다. 수강생이 00번부터 19번까지 순서대로 실행하면 자연스럽게 학습이 진행됩니다.

- **00~07**: Day 1 — 기초 (SQL, RAG, Text-to-SQL)
- **08~09**: Day 2 — Text-to-SQL 심화 + Gradio UI
- **10~17**: Day 3 — Vanna, LangChain, Advanced RAG, LangGraph
- **18~19**: Day 4 — 평가 & 모니터링

!!! note "핵심 정리"
    - 노트북 번호 `00`~`19`는 24시간 강의의 교육 순서에 1:1 대응합니다
    - 9H(제안서 피어리뷰)와 23~24H(튜닝/발표)는 별도 노트북 없이 진행합니다
    - 파일명은 `번호_주제.ipynb` 형식으로 통일되어 있습니다
