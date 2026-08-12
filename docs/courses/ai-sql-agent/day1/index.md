# Day 1 — 개관 · SQL · RAG 파이프라인 + 프로젝트 브리핑 (1~8H)

!!! info "수업 형식"
    각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%
    **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API
    **준비물**: 노트북(크롬 브라우저), 이메일 계정(Google/Neon/OpenAI)

## 학습 목표 요약

Day 1은 4일간의 프로젝트를 위한 **"재료 준비"** 단계입니다.

1. **SQL 기초부터 중급까지** — SELECT, JOIN, CTE, 윈도우 함수로 데이터 조회
2. **AI 친화적 스키마 설계** — COMMENT ON, FK 명시, 리포팅 뷰
3. **RAG 파이프라인 구축** — LlamaIndex로 문서 로딩 → 임베딩 → 검색
4. **Text-to-SQL 체험** — 자연어 질문을 SQL로 자동 변환
5. **프로젝트 시작** — 본인 도메인 선정 및 제안서 작성

## 타임라인

| 시간 | 주제 | 핵심 키워드 | 페이지 |
|:---:|---|---|---|
| **1H** | OT & 전체 데모 | Agentic Analytics, 환경 셋업 | [01-ot-demo](01-ot-demo.md) |
| **2H** | PostgreSQL 기초 | SELECT, WHERE, ORDER BY, LIMIT | [02-postgres-basics](02-postgres-basics.md) |
| **3H** | 집계 · 조인 · CTE | GROUP BY, JOIN, 윈도우 함수 | [03-sql-advanced](03-sql-advanced.md) |
| **4H** | Schema Intelligence | COMMENT ON, FK, 리포팅 뷰, ERD | [04-schema-intelligence](04-schema-intelligence.md) |
| **5H** | LlamaIndex 개론 | RAG, Documents → Index → Query | [05-llamaindex-intro](05-llamaindex-intro.md) |
| **6H** | 임베딩 + ChromaDB | 벡터, 코사인 유사도, 영속 저장 | [06-embedding-chromadb](06-embedding-chromadb.md) |
| **7H** | Text-to-SQL | NLSQLTableQueryEngine | [07-text-to-sql](07-text-to-sql.md) |
| **8H** | 프로젝트 브리핑 | 과제 #1: 제안서 작성 | [08-project-briefing](08-project-briefing.md) |

## 핵심 키워드 정리

| 키워드 | 의미 |
|---|---|
| **Agentic Analytics** | AI가 계획-실행-검증-재시도를 자율적으로 수행하는 데이터 분석 |
| **PostgreSQL** | AI 연동에 최적화된 오픈소스 관계형 데이터베이스 |
| **COMMENT ON** | 테이블/컬럼에 설명을 다는 PostgreSQL 명령 (AI 가독성 핵심) |
| **RAG** | Retrieval-Augmented Generation. 관련 자료를 검색하여 AI에게 제공하는 방식 |
| **LlamaIndex** | RAG 파이프라인을 쉽게 구축할 수 있는 프레임워크 |
| **임베딩** | 텍스트를 숫자 벡터(좌표)로 변환하는 기술 |
| **ChromaDB** | 벡터를 영구 저장하는 벡터 데이터베이스 |
| **Text-to-SQL** | 자연어 질문을 SQL로 자동 변환하는 기술 |

!!! note "핵심 정리"
    Day 1은 **재료 준비** 단계입니다. SQL로 데이터를 다루고, RAG로 검색하고, Text-to-SQL로 자연어 질의를 체험합니다. 이 모든 것이 Day 2~4에서 만들 **SQL 분석 에이전트**의 구성 요소가 됩니다.
