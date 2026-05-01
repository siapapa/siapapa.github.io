# Colab 노트북 구현 계획 (notebooks_plan.md)

> **목적:** `team-coder`가 이 문서만 보고 `/home/totorokr/Assist 강의/notebooks/00_demo_agent.ipynb` ~ `19_ragas_eval.ipynb` 20종을 순서대로 구현할 수 있도록 하는 실행 계약서.
> **원천 자료(코드 리프트 대상):** `Lecture_Day1.md` ~ `Lecture_Day4.md` (code 블록 그대로 이식). `docs/dayN/*.md`는 정돈된 사본이므로 서사/설명에만 참조.
> **언어 규약:** 마크다운 셀 = 한국어, 코드 식별자/주석 = 영어. 노트북 제목·섹션 헤더·설명 문단은 한국어.
> **API 키 규약:** 전 노트북 `google.colab.userdata.get("OPENAI_API_KEY")`, `get("NEON_DSN")`, `get("LANGSMITH_KEY")` 만 사용. 하드코딩 금지.

---

## 0. 파일 소유권 맵 (File ownership map)

| 역할 | 소유 경로 | 권한 |
|---|---|---|
| `team-coder` | `/home/totorokr/Assist 강의/notebooks/*.ipynb` (20개) | 쓰기 전용(유일한 작성자) |
| `team-reviewer` | `notebooks/*.ipynb` | 읽기만. 검증 스크립트·메모는 `/home/totorokr/Assist 강의/review_output/`에 작성 가능 |
| 리드(본 에이전트) | `notebooks_plan.md` (이 문서) | 쓰기. 노트북 자체는 수정하지 않음 |
| **절대 건드리면 안 됨** | `Lecture_Day*.md`, `docs/**`, `PROJECT_BRIEF.md`, `CLAUDE.md`, `참고자료/**` | 읽기 전용 (소스 오브 트루스) |

충돌 방지 원칙: 모든 노트북의 소유자는 `team-coder` 1인이므로 파일 수준 충돌은 없음. 그러나 **재현성**을 위해 각 노트북은 원칙적으로 **자기완결(self-contained)** 이어야 한다. 즉 DB 연결·스키마 재수집은 매 노트북 상단에서 다시 수행(ChromaDB 퍼시스트 경로, Vanna 학습 자산은 예외적으로 이전 노트북 산출물 재사용 허용 — 아래 각 노트북 항목에서 명시).

---

## 1. 빌드 순서 권장 (Build order)

- **기본 순서: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 00**
- **00(demo_agent)은 맨 마지막에 작성**. 이유: 00은 17(`my_sql_agent`)을 단순화한 "완성품 미리보기"다. 17이 안정화되기 전에 00을 작성하면 두 노트북 사이에 로직이 다이버지(divergence)하고, 강의 첫 시간 데모가 실제 구현과 어긋날 위험이 크다. 17 완성 후 그 LangGraph 코드를 00에 축약 이식한다.
- **병렬 작성 가능한 세트: 없음.** 단일 코더가 순차로 작성한다. 다만 소스 레퍼런스가 겹치지 않는 그룹은 리뷰어가 이전 그룹을 검증하는 동안 다음 그룹 작성을 시작할 수 있다. 권장 리뷰 배치:
  1. **Batch A (Day 1 기초):** 01, 02, 03
  2. **Batch B (Day 1 RAG):** 04, 05, 06, 07
  3. **Batch C (Day 2):** 08, 09
  4. **Batch D (Day 3 전반):** 10, 11, 12, 13
  5. **Batch E (Day 3 후반):** 14, 15, 16, 17
  6. **Batch F (Day 4 + 데모):** 18, 19, 00
- **범위 경고(scope flag):** 20개 노트북 × 평균 25~30셀 = 약 500~600 셀 규모. 본 태스크가 단일 세션에서 완주 가능한지 team-coder가 Batch A 완료 시점에 속도를 재측정해 리드에게 보고해야 함. 리드는 필요 시 Day 1 노트북만 1차 납품하고 Day 2~4는 별도 세션으로 이월하는 옵션을 유지한다.

---

## 2. 리뷰어 검증 프로토콜 (모든 노트북 공통)

team-reviewer는 각 노트북에 대해 아래 5단계를 수행하고 결과를 `/home/totorokr/Assist 강의/review_output/{nn}_review.md`에 기록한다.

1. **JSON 유효성:** `python -c "import nbformat; nbformat.read(open('...'), as_version=4)"` 무오류.
2. **Python 구문:** `jupyter nbconvert --to script <nb>` 로 `.py` 추출 후 `python -m py_compile` 통과.
3. **하드코딩 시크릿 스캔:** `grep -E "sk-[A-Za-z0-9]{20,}|postgres(ql)?://[^$]*:[^@$]+@"` 에서 **0건** 이어야 함. API 키/DSN은 반드시 `userdata.get(...)` 형태여야 함.
4. **규약 준수:**
   - 첫 셀이 `%pip install` 혹은 `!pip install`로 시작
   - `google.colab.userdata` 또는 `getpass`로 키 로딩
   - 한국어 인트로 마크다운 셀 존재
   - 마지막 셀에 "다음 노트북에서는…" 포인터 마크다운 존재
   - 실습/연습 셀이 최소 1개 (주석 `# TODO:` 또는 마크다운 "### 실습 과제" 표식으로 식별)
5. **헤드리스 실행 가능 셀 부분 실행:** 아래 표의 "Executable without secrets" 열에 표시된 셀만 `jupyter nbconvert --to notebook --execute` 의 `--ExecutePreprocessor.allow_errors=True`로 실행 시도. 대부분 노트북은 OpenAI/Neon/LangSmith 키가 필수이므로 실제 실행은 인트로 셀(import/설명)에 한정됨을 전제로 한다.

불합격 항목 발견 시 리뷰어는 블로킹으로 코더에게 리포트하며, 코더는 해당 노트북을 재작성 후 재검증.

---

## 3. 공통 부트스트랩 템플릿 (모든 노트북 상단에 적용)

코더는 각 노트북 첫 2~3 셀을 아래 템플릿으로 통일한다(설치 패키지는 노트북별로 최소 집합만).

```python
# Cell: Install (code)
%pip install -q <notebook-specific packages>
```

```python
# Cell: Bootstrap (code)
import os
try:
    from google.colab import userdata
    os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
    os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
    # LangSmith key only for notebooks 18, 19
except ImportError:
    # Local fallback for reviewer / non-Colab
    from getpass import getpass
    for k in ("OPENAI_API_KEY", "NEON_DSN"):
        if k not in os.environ:
            os.environ[k] = getpass(f"{k}: ")
```

마크다운 셀 구조 공통:
1. 타이틀 `# NN. <주제>` + 부제 `> Day X · NH · 소요 약 50분`
2. `## 학습 목표` (불릿 2~3개)
3. 본문 개념 설명 셀들 사이사이
4. 맨 아래 `## 다음 노트북에서는…` 포인터

---

## 4. 노트북별 상세 계획

각 항목 공통 표기:
- **🎯 학습 목표:** Lecture_Day*.md의 "학습목표" 문구를 그대로 차용
- **📦 pip:** 첫 셀에 들어갈 패키지 목록 (최소집합)
- **🔑 secrets:** 부트스트랩에서 필요한 키 목록
- **🧩 Cell outline:** 순서대로. `[M]` = markdown, `[C]` = code. 숫자는 접근 셀 번호 추정.
- **📚 Source:** 원천 섹션 헤더(라인 번호 대신 헤더명으로 지정)
- **🔗 Inter-notebook deps:** 이전 노트북 산출물 의존 여부
- **🧪 Executable w/o secrets:** 리뷰어가 키 없이도 실행 가능한 셀 범위

---

### 📓 00. `00_demo_agent.ipynb` — OT & 전체 데모 (Day 1, 1H) ⚠️ **맨 마지막에 작성**

- **🎯 학습 목표:**
  - Agentic Analytics 개념과 기존 BI/Text-to-SQL의 차이를 체감한다.
  - 4일 후 학생이 완성할 에이전트의 최종 모습을 시연으로 확인한다.
  - Colab + Neon + OpenAI API 환경 셋업이 완료됨을 확인한다.
- **성격:** "from-scratch 실습"이 아니라 **완성품 시연 + 환경 점검**. 학생은 실행 버튼만 누른다. 셀 개수는 다른 노트북보다 적게(약 15셀) 유지.
- **📦 pip:** `psycopg2-binary sqlalchemy langgraph langchain langchain-openai openai pandas tabulate`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 15셀):**
  1. `[M]` 타이틀 + "4일 로드맵" + 역방향 학습 취지
  2. `[C]` %pip install
  3. `[C]` 부트스트랩 (userdata 로딩)
  4. `[C]` Neon 연결 테스트 — `SELECT version()` 출력
  5. `[M]` "이 에이전트가 하는 일" 다이어그램 설명 (LangGraph state flow)
  6. `[C]` 스키마 정보 수집 함수 (`get_schema_info`, `INFORMATION_SCHEMA` 조회)
  7. `[C]` LangGraph State 정의 + 보안 가드레일 함수
  8. `[C]` 노드 함수들: `generate_sql`, `execute_sql`, `validate`, `answer`
  9. `[C]` StateGraph 조립 + `compile()`
  10. `[C]` 그래프 시각화 (Mermaid 또는 `draw_mermaid_png`)
  11. `[M]` 시연 안내 ("다음 셀의 질문들을 하나씩 실행해 보세요")
  12. `[C]` 시연 질문 3개 순차 실행 (병원 DB 기준)
  13. `[M]` 실행 결과 해석 가이드
  14. `[M]` "4일 로드맵" (1~8H / 9~12H / 13~20H / 21~24H) 요약
  15. `[M]` "다음 노트북(`01_postgres_basics.ipynb`)에서는 이 에이전트의 가장 기초 블록인 SQL부터 하나씩 쌓아갑니다."
- **📚 Source:** `Lecture_Day1.md` 의 "1H · OT & Agentic Analytics 전체 데모" 전체 섹션 (특히 "핵심 코드 — `00_demo_agent.ipynb` (완성형 에이전트 시연)" 블록). 단 **17번 노트북의 로직을 축약해 이식**할 것 — 17과 00의 graph 구조·state schema·guardrail 문자열이 1:1로 일치해야 한다. 차이는 오직 "학습용 주석/출력이 00에서 더 친절함" 정도.
- **🔗 Inter-notebook deps:** 17과 논리적으로 쌍둥이. 실행 의존은 없음(각 노트북은 자기완결). 병원 DB 스키마가 DB에 존재한다는 가정은 있음 — 00은 강의 첫 시간이므로 Neon에 DDL이 이미 적재되어 있다는 전제를 마크다운에서 명시하고, 없으면 01을 먼저 실행하라고 안내.
- **🧪 Executable w/o secrets:** 셀 1(pip)만. 나머지는 모두 OpenAI + Neon 필요.

---

### 📓 01. `01_postgres_basics.ipynb` — PostgreSQL 기초 (Day 1, 2H)

- **🎯 학습 목표:**
  - Neon PostgreSQL 인스턴스에 Colab에서 접속할 수 있다.
  - `psycopg2`와 `SQLAlchemy`의 차이를 이해하고 상황에 맞게 사용한다.
  - `SELECT`/`WHERE`/`ORDER BY`/`LIMIT`/`EXPLAIN` 기본을 실행할 수 있다.
  - 병원 샘플 DB를 자신의 Neon 인스턴스에 적재한다.
- **📦 pip:** `psycopg2-binary sqlalchemy pandas tabulate`
- **🔑 secrets:** `OPENAI_API_KEY` (부트스트랩 공통, 이 노트북에서 사용은 안 함), `NEON_DSN`
- **🧩 Cell outline (약 30셀):**
  1. `[M]` 타이틀 + 학습목표
  2. `[C]` %pip install
  3. `[C]` 부트스트랩
  4. `[M]` "왜 PostgreSQL인가?" 짧은 배경
  5. `[C]` SQLAlchemy 엔진 생성 + `SELECT version()`
  6. `[C]` psycopg2 직접 접속 예제 (connection/cursor 패턴 1회 보여주기)
  7. `[M]` SQLAlchemy vs psycopg2 — 언제 무엇을 쓰나
  8. `[M]` 병원 DB 스키마 다이어그램 (텍스트 ERD)
  9. `[C]` 테이블 DDL 실행 (`CREATE TABLE patients…visits…doctors…diagnoses…departments`)
  10. `[C]` 시드 데이터 INSERT
  11. `[C]` 적재 검증 (`SELECT COUNT(*) FROM each`)
  12. `[M]` SELECT 기본 구조
  13~20. `[C]` 기본 SELECT 변형들: 전체 조회 / 컬럼 선택 / WHERE / 비교 연산자 / BETWEEN / IN / LIKE / IS NULL
  21. `[C]` ORDER BY + LIMIT
  22. `[C]` 별칭 + 계산 컬럼
  23. `[M]` EXPLAIN 개념
  24. `[C]` EXPLAIN 쿼리 실행 + 해석
  25. `[M]` 실행 계획 읽는 법 요약 박스
  26. `[M]` `## 실습 과제` (3문항: 나이 30대 환자 조회, 혈액형별 정렬, 이름에 '김'으로 시작하는 환자 등 Lecture_Day1.md "실습 과제"에서 복제)
  27. `[C]` 실습 템플릿 셀 (`# TODO:`)
  28. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "2H · PostgreSQL 기초 (Colab + Neon)" 전체 및 § "3. 병원 데이터베이스 생성" / § "4. 시드 데이터 삽입" 코드 블록. 참고로 같은 DDL을 03·04 등 이후 노트북에서도 필요 시 재실행할 수 있으나, 01이 **유일한 DDL/시드 적재 노트북**이며 이후 노트북은 "01을 먼저 실행했다는 전제"에서 `SELECT`만 수행하도록 한다.
- **🔗 Inter-notebook deps:** 없음(DB는 빈 Neon). 01이 이후 전체 Day 1/Day 2 노트북(02~09)의 데이터 적재 선행 조건. 반드시 마크다운에 "이 노트북을 먼저 실행한 뒤 다른 노트북을 열어 주세요"라고 명기.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 02. `02_sql_aggregation_join.ipynb` — 집계·조인·CTE·윈도우 함수 (Day 1, 3H)

- **🎯 학습 목표:**
  - `GROUP BY` / `HAVING` 으로 집계 쿼리를 작성한다.
  - `INNER` / `LEFT` / `SELF JOIN` 을 목적에 맞게 선택한다.
  - 서브쿼리 vs CTE의 가독성 차이를 이해한다.
  - 윈도우 함수 (`ROW_NUMBER`, `RANK`, `LAG`, `SUM OVER`)로 그룹 내 연산을 수행한다.
- **📦 pip:** `psycopg2-binary sqlalchemy pandas tabulate`
- **🔑 secrets:** `NEON_DSN`
- **🧩 Cell outline (약 28셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 집계 함수와 GROUP BY 개념
  5~8. `[C]` GROUP BY 예제 4종 (진료과별 의사 수 / 월별 방문 / 혈액형 분포 / HAVING)
  9. `[M]` JOIN 개념 — Venn 도식 텍스트
  10~13. `[C]` INNER / LEFT / LEFT+NULL / SELF JOIN
  14. `[M]` 서브쿼리 패턴
  15~17. `[C]` WHERE 서브쿼리 / FROM 서브쿼리 / EXISTS
  18. `[M]` CTE — `WITH` 구문 개요
  19~20. `[C]` 중첩 쿼리 vs CTE 리팩터링 예제 (before/after)
  21. `[M]` 윈도우 함수 개념 (PARTITION BY, 행을 줄이지 않음)
  22~26. `[C]` ROW_NUMBER / RANK vs DENSE_RANK / LAG·LEAD / SUM OVER
  27. `[M]` 실습 과제 (Lecture_Day1.md § "3H 실습 과제" 복제, 3문항)
  28. `[C]` 실습 TODO 템플릿
  29. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "3H · 집계·조인·CTE·윈도우 함수"
- **🔗 Inter-notebook deps:** 01에서 적재된 병원 DB 필요.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 03. `03_schema_intelligence.ipynb` — Schema Intelligence (Day 1, 4H)

- **🎯 학습 목표:**
  - LLM이 읽는 스키마 프롬프트(`table_info`)의 실제 모습을 확인한다.
  - `COMMENT ON TABLE/COLUMN`과 FK 명시로 AI 친화적 스키마를 만든다.
  - 정규화 vs LLM 친화적 비정규화(뷰)의 트레이드오프를 이해한다.
  - Mermaid ERD를 작성한다.
- **📦 pip:** `psycopg2-binary sqlalchemy llama-index llama-index-llms-openai llama-index-embeddings-openai pandas`
- **🔑 secrets:** `NEON_DSN`, `OPENAI_API_KEY` (LlamaIndex `SQLDatabase` 호출 때문)
- **🧩 Cell outline (약 22셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` "LLM은 스키마를 어떻게 읽는가"
  5. `[C]` LlamaIndex `SQLDatabase`로 `table_info` 추출 & 출력
  6. `[M]` 좋은 네이밍 원칙 체크리스트
  7. `[C]` `COMMENT ON TABLE`, `COMMENT ON COLUMN` 일괄 부여 스크립트
  8. `[C]` `COMMENT` 후 `table_info` 재추출 — before/after 비교 출력
  9. `[M]` FK 명시와 ON DELETE 정책 짧은 설명
  10. `[C]` 누락된 FK 추가 `ALTER TABLE` (필요 시)
  11. `[M]` 정규화 vs LLM-친화 비정규화
  12. `[C]` 뷰 생성 (예: `v_visit_summary` — 환자명·의사명·진단명을 조인한 와이드 뷰)
  13. `[C]` 뷰로 간단 조회
  14. `[M]` Mermaid ERD 작성 가이드
  15. `[M]` Mermaid 코드 블록 (참조용 ERD)
  16~17. `[M]`/`[C]` 실습 과제: 학생이 `COMMENT`를 하나 추가하고 `table_info`가 바뀌는지 확인
  18. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "4H · Schema Intelligence — AI가 읽기 좋은 스키마"
- **🔗 Inter-notebook deps:** 01에서 적재된 병원 DB. 이 노트북에서 추가한 COMMENT는 06, 08에서 `NLSQLTableQueryEngine`이 이를 참조하므로 Day 1/Day 2 내내 유지된다고 마크다운에서 명기.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 04. `04_llamaindex_intro.ipynb` — LlamaIndex 파이프라인 개론 (Day 1, 5H)

- **🎯 학습 목표:**
  - LlamaIndex의 Document → Node → Index → Query Engine 파이프라인을 이해한다.
  - `Settings` 전역 설정 방식을 사용한다.
  - SentenceSplitter / TokenTextSplitter 청킹 전략을 비교한다.
  - VectorStoreIndex로 기본 RAG 쿼리를 수행한다.
- **📦 pip:** `llama-index llama-index-llms-openai llama-index-embeddings-openai openai`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 20셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` RAG 개념도 + 파이프라인 단계
  5. `[C]` `Settings.llm` / `Settings.embed_model` 전역 설정
  6. `[M]` Document 로딩 방식 소개
  7. `[C]` 텍스트에서 직접 `Document` 생성 (병원 관련 짧은 문서 5~8개)
  8. `[M]` 청킹 — Node 개념
  9. `[C]` SentenceSplitter 예제
  10. `[C]` TokenTextSplitter 예제 (비교)
  11. `[M]` 인덱싱 및 Query Engine
  12. `[C]` `VectorStoreIndex.from_documents(...)`
  13. `[C]` `as_query_engine()` + 질의 2~3건
  14. `[C]` 추가 질의 (source_nodes 출력)
  15. `[M]` Retriever만 사용(생성 없이 검색)
  16. `[C]` `as_retriever(similarity_top_k=3)`
  17. `[M]` 실습 과제
  18. `[C]` TODO 셀
  19. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "5H · LlamaIndex 파이프라인 개론" (특히 "핵심 코드 — `04_llamaindex_intro.ipynb`" 블록)
- **🔗 Inter-notebook deps:** 없음. DB 미사용, 인메모리 인덱스.
- **🧪 Executable w/o secrets:** 셀 1~2만 (임베딩 호출이 모두 OpenAI 키 필요).

---

### 📓 05. `05_embedding_chromadb.ipynb` — 임베딩 + ChromaDB 영속화 (Day 1, 6H)

- **🎯 학습 목표:**
  - 임베딩 벡터와 코사인 유사도 개념을 수치적으로 체감한다.
  - ChromaDB에 문서를 영속화하고 Top-K 검색한다.
  - LlamaIndex + ChromaDB 통합으로 영속 인덱스를 만든다.
- **📦 pip:** `chromadb llama-index llama-index-vector-stores-chroma llama-index-embeddings-openai llama-index-llms-openai openai numpy matplotlib`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 22셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 임베딩 이론 + 코사인 유사도
  5. `[C]` OpenAI 임베딩 직접 호출 → 벡터 일부 출력
  6. `[C]` 코사인 유사도 계산 + 유사도 매트릭스 히트맵 (matplotlib)
  7. `[M]` ChromaDB 소개
  8. `[C]` `chromadb.PersistentClient(path="./chroma_db")` + 컬렉션 생성
  9. `[C]` 병원 문서 upsert (ids/documents/metadatas)
  10. `[C]` 기본 `collection.query(...)` Top-K 검색
  11. `[C]` 메타데이터 `where` 필터 검색
  12. `[M]` LlamaIndex + ChromaDB 통합
  13. `[C]` `ChromaVectorStore` 래핑 + `VectorStoreIndex.from_documents(..., storage_context)`
  14. `[C]` Query Engine 질의
  15. `[M]` 영속성 확인
  16. `[C]` 새 `PersistentClient`로 재접속 → 문서 수 확인
  17. `[M]` 임베딩 모델 비교 표 (small/large/bge-small-ko/multilingual)
  18. `[M]` 실습 과제
  19. `[C]` TODO
  20. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "6H · 임베딩 + ChromaDB 영속화" — 핵심 코드 전체.
- **🔗 Inter-notebook deps:** 13번(LCEL RAG 체인) 노트북이 이 `./chroma_db` 디렉토리를 **재사용하지 않는다** (13은 langchain-chroma를 쓰고 자체 컬렉션 생성). 따라서 05의 `./chroma_db`는 05 내부 확인용이며, 이후 노트북은 독립적으로 chroma 디렉토리를 만든다. 마크다운에 "이 디렉토리는 이 노트북 전용입니다"라고 명기.
- **🧪 Executable w/o secrets:** 셀 1~2만. (임베딩 호출부터 OpenAI 키 필요)

---

### 📓 06. `06_text_to_sql.ipynb` — Text-to-SQL 맛보기 (Day 1, 7H)

- **🎯 학습 목표:**
  - `SQLDatabase` 래퍼와 `NLSQLTableQueryEngine` 기본 사용법을 익힌다.
  - `table_info`가 프롬프트로 들어가는 흐름을 확인한다.
  - 08(심화)로 가는 "왜 기본 설정만으론 부족한가?"의 동기를 체감한다.
- **📦 pip:** `llama-index llama-index-llms-openai llama-index-embeddings-openai sqlalchemy psycopg2-binary pandas`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 18셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` Text-to-SQL 작동 원리 도식
  5. `[C]` `SQLDatabase` 생성 (`include_tables=["patients","doctors","visits","diagnoses","departments"]`)
  6. `[C]` 연결된 테이블 목록 출력
  7. `[C]` `NLSQLTableQueryEngine` 생성
  8. `[C]` 기본 질의 3개 (성공 사례) — "진료과별 의사 수", "김환자의 방문 이력", "지난 달 방문 건수"
  9. `[M]` 생성 SQL 확인 방법
  10. `[C]` `response.metadata["sql_query"]` 출력
  11. `[M]` `table_info`가 얼마나 단순한지 보기
  12. `[C]` `sql_db.get_table_info(["patients"])` 출력
  13. `[M]` 기본 설정의 한계 — "모호한 질문은 실패함" 예시
  14. `[C]` 모호한 질문 2개 (실패/엉뚱한 답) — 의도적으로 나쁜 결과를 보여줌
  15. `[M]` "다음 노트북(08)에서 이걸 어떻게 개선할지" 티징
  16. `[M]` 실습 과제
  17. `[C]` TODO
  18. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day1.md` § "7H · Text-to-SQL 맛보기" — 전체 코드 및 설명.
- **🔗 Inter-notebook deps:** 01 병원 DB 필요. 03에서 부여한 COMMENT가 있으면 `table_info` 품질이 좋아짐(마크다운에 언급). 없어도 동작.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 07. `07_project_briefing.ipynb` — 프로젝트 브리핑 (Day 1, 8H)

- **🎯 학습 목표:**
  - 최종 프로젝트의 4단계 마일스톤을 이해한다.
  - 본인 도메인을 선정하고 제안서 템플릿을 채울 준비를 한다.
  - 과제 제출·평가 루브릭을 숙지한다.
- **성격:** **이 노트북은 코드가 거의 없다.** 대부분 마크다운 + 체크리스트. 코드는 "제안서 제출 확인용 간단한 스키마 자동 검증기"(Day 2 9H 코드)를 선택적으로 포함.
- **📦 pip:** `sqlalchemy psycopg2-binary pandas` (검증기용, 최소)
- **🔑 secrets:** `NEON_DSN` (선택 — 본인 DB 검증 시)
- **🧩 Cell outline (약 15셀, 대부분 마크다운):**
  1. `[M]` 타이틀 + "최종 프로젝트 브리핑" 개요
  2. `[M]` 기술 스택 표 (PROJECT_BRIEF.md § "기술 스택(고정)" 복제)
  3. `[M]` 4단계 마일스톤 표
  4. `[M]` 과제 #1 제안서 양식 전체 (PROJECT_BRIEF.md § "과제 #1" 복제)
  5. `[M]` 스키마 설계 원칙
  6. `[M]` 질문 10개 난이도 분포 가이드
  7. `[M]` 평가 루브릭 요약
  8. `[M]` 발표 가이드(5~7분)
  9. `[M]` FAQ
  10. `[M]` "선택: 본인 제안 스키마 자동 검증기"
  11. `[C]` 설치(최소) + 부트스트랩
  12. `[C]` 스키마 체커 함수(테이블명 snake_case, PK/FK, COMMENT 여부 체크 — Lecture_Day2.md § "핵심 코드 — 스키마 자동 검증 도구" 이식)
  13. `[C]` 사용 예시 (본인 DSN 입력 시)
  14. `[M]` 제출 방법 & 다음 노트북 포인터 ("다음 시간에는 여러분의 제안서를 피어리뷰합니다")
- **📚 Source:** `PROJECT_BRIEF.md` 전문 요약 + `Lecture_Day2.md` § "9H · 제안서 피어리뷰" 중 "핵심 코드 — 스키마 자동 검증 도구" 섹션.
- **🔗 Inter-notebook deps:** 없음.
- **🧪 Executable w/o secrets:** 전체 마크다운 셀 + 검증기 임포트 셀까지 가능. DSN 필요한 셀 제외.

---

### 📓 08. `08_text_to_sql_advanced.ipynb` — Text-to-SQL 심화 (Day 2, 10H)

- **🎯 학습 목표:**
  - `NLSQLTableQueryEngine`의 내부 프롬프트를 검사한다.
  - `context_str_prefix` / 커스텀 프롬프트 / Few-shot 예제로 정확도를 올린다.
  - `ObjectIndex`로 관련 테이블을 자동 선택한다.
  - Before/After 실험으로 프롬프트 튜닝의 효과를 측정한다.
- **📦 pip:** `llama-index llama-index-llms-openai llama-index-embeddings-openai sqlalchemy psycopg2-binary pandas`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 25셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` "왜 기본 설정으로는 부족한가?"
  5. `[C]` 내부 프롬프트 추적 — `query_engine.get_prompts()` 출력
  6. `[C]` 기본 text_to_sql_prompt 텍스트 전체 출력
  7. `[M]` 전략 1 — 컨텍스트 문자열 주입
  8. `[C]` `context_str_prefix=...` 로 도메인 규칙 주입
  9. `[M]` 전략 2 — 커스텀 프롬프트 + Few-shot
  10. `[C]` `PromptTemplate` 재정의 + Few-shot 3개
  11. `[M]` Before/After 실험
  12. `[C]` 같은 질문 10개를 기본 / 튜닝 엔진에 동시 실행 → 정답률 비교 DataFrame
  13. `[C]` 특정 질문의 SQL 나란히 비교 출력
  14. `[M]` 전략 3 — ObjectIndex로 테이블 자동 선택
  15. `[C]` `SQLTableSchema` + 자연어 설명
  16. `[C]` `ObjectIndex.from_objects(...)` 구성
  17. `[C]` `SQLTableRetrieverQueryEngine` 생성 + 질의
  18. `[C]` 검증: "진단" 질문에 `diagnoses` 테이블이 자동 선택되었는지 확인
  19. `[M]` 프롬프트 실험 워크시트 — 같은 모호한 질문에 프롬프트 A/B/C
  20. `[C]` 프롬프트 A/B/C 정의 + 실행
  21. `[M]` 결과 해석 + 규칙 팁
  22. `[M]` 실습 과제
  23. `[C]` TODO
  24. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day2.md` § "10H · NLSQLTableQueryEngine 심화" 전체.
- **🔗 Inter-notebook deps:** 01의 병원 DB, 03의 COMMENT 권장.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 09. `09_gradio_chatbot.ipynb` — 멀티턴 상담사 + Gradio UI (Day 2, 11~12H)

- **🎯 학습 목표:**
  - 멀티턴 대화에서 맥락을 누적하고 참조하는 상담사를 구현한다.
  - SQL 보안 가드레일(`SELECT`만 허용, DML/DDL 차단)을 적용한다.
  - Gradio `ChatInterface`로 Colab에서 공개 URL 챗봇을 배포한다.
- **노트:** 11H(상담사 설계)와 12H(Gradio) 통합. 적재량 많음.
- **📦 pip:** `llama-index llama-index-llms-openai llama-index-embeddings-openai sqlalchemy psycopg2-binary pandas gradio sqlparse`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 30셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 멀티턴 대화의 도전 (맥락 누적, 참조 해결)
  5. `[C]` SQL 보안 가드레일 함수 (`validate_sql`) — SELECT만 허용, 세미콜론, 주석, 위험 키워드 차단
  6. `[C]` 가드레일 테스트 (정상 쿼리 / 위험 쿼리 2종)
  7. `[M]` 스키마 + 대화 히스토리를 프롬프트에 누적
  8. `[C]` `HospitalCounselor` 클래스 — 상태, 히스토리, 쿼리 메서드
  9. `[C]` 스키마 정보 수집 유틸
  10. `[C]` 4턴 대화 테스트 (턴 3에서 "방금 그 의사가 담당한 환자는?" 같은 참조 질문 포함)
  11. `[M]` 에러 복구 — 재시도 로직
  12. `[C]` SQL 실패 시 에러 메시지와 함께 재생성 루프 (최대 2회)
  13. `[C]` 재시도 테스트
  14. `[M]` Gradio 최소 예제
  15. `[C]` Echo Bot ChatInterface (`share=True`)
  16. `[M]` 병원 DB 상담사 + Gradio 통합
  17. `[C]` 상담사 래퍼 함수 (history → answer) 정의
  18. `[C]` `gr.ChatInterface(fn=respond, ...)` + `launch(share=True)`
  19. `[M]` 세션 상태 관리
  20. `[C]` `gr.State`로 멀티턴 메모리 유지
  21. `[M]` 커스텀 CSS / 예시 질문 버튼 / 에러 토스트 (선택적 기능)
  22. `[C]` 고급 UI 예제 (예시 질문 버튼)
  23. `[M]` 교차 체험 안내 — 공개 URL 공유
  24. `[M]` 과제 #2 안내 — 본인 스키마+시드 Neon 배포
  25. `[C]` Faker 등 시드 생성 도우미 (선택)
  26. `[M]` 실습 과제
  27. `[C]` TODO
  28. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day2.md` § "11H · 병원 DB 멀티턴 상담사 설계" + § "12H · Gradio in Colab 데모".
- **🔗 Inter-notebook deps:** 01 병원 DB. Gradio `launch(share=True)`는 Colab에서만 제대로 동작(로컬 리뷰에서 `share` 비활성 가능) — 리뷰어용 주석 "in Colab, use share=True; locally, use share=False" 마크다운에 포함.
- **🧪 Executable w/o secrets:** 셀 1~2, 가드레일 함수 정의 셀(키 없이 구문 확인만) 가능. 실행은 OpenAI/Neon 필요.

---

### 📓 10. `10_vanna_intro.ipynb` — Vanna.ai 구조 (Day 3, 13H)

- **🎯 학습 목표:**
  - Vanna.ai의 RAG 기반 Text-to-SQL 아키텍처를 이해한다.
  - LlamaIndex Text-to-SQL과 Vanna의 차이를 비교한다.
  - 학습 자산 3종(DDL / Documentation / SQL Pairs)의 역할을 설명한다.
  - **학습 없이 베이스라인 질문** 동작을 확인한다.
- **📦 pip:** `"vanna[chromadb,openai,postgres]" chromadb openai sqlalchemy psycopg2-binary`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 15셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` Vanna vs LlamaIndex Text-to-SQL 비교 표
  5. `[C]` 커스텀 Vanna 클래스: `class MyVanna(ChromaDB_VectorStore, OpenAI_Chat): ...`
  6. `[C]` `vn = MyVanna(config={"api_key": ..., "model": "gpt-4o-mini", "path": "./vanna_chroma"})`
  7. `[C]` Neon 연결: `vn.connect_to_postgres(...)`
  8. `[M]` 학습 없이 질문 — 베이스라인
  9. `[C]` `vn.ask("진료과별 의사 수는?")` — 결과와 생성 SQL 확인
  10. `[C]` 모호한 질문 예제 (의도적으로 부정확한 답)
  11. `[M]` 현재 학습 자산 확인
  12. `[C]` `vn.get_training_data()` — DataFrame 출력 (비어있음)
  13. `[M]` "다음 노트북(11)에서 학습시켜 정확도를 끌어올립니다"
  14. `[M]` 실습 과제
  15. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "13H · Vanna.ai 구조"
- **🔗 Inter-notebook deps:** 01 병원 DB. **Vanna 학습 Chroma 경로 `./vanna_chroma`는 11번 노트북과 공유**. 그러나 같은 Colab 세션이 보장되지 않으므로, 11에서 전부 재학습하는 것을 기본으로 하되 10에서 생성된 컬렉션이 남아 있으면 이어서 쓸 수 있다고 마크다운에 명기.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 11. `11_vanna_training.ipynb` — Vanna 자가학습 (Day 3, 14H)

- **🎯 학습 목표:**
  - DDL / Documentation / SQL Pairs 3종 학습 자산을 Vanna에 주입한다.
  - 학습 전후 정확도를 비교한다.
  - In-Chat Training으로 오답을 교정한다.
  - 본인 프로젝트 DB에 Vanna를 적용할 수 있다.
- **📦 pip:** 10과 동일
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 20셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 학습 자산 3종 개요
  5. `[C]` Vanna 인스턴스 재생성 (10과 동일) — self-contained
  6. `[C]` DDL 학습: `vn.train(ddl=...)` 개별 테이블 5개
  7. `[C]` 학습 결과 확인 `get_training_data()`
  8. `[M]` Documentation — 비즈니스 용어집
  9. `[C]` `vn.train(documentation="응급실은 department_id=5이며 24시간 운영됩니다.")` 등 5~7건
  10. `[M]` SQL Pairs — 질문/정답 쌍
  11. `[C]` `vn.train(question="...", sql="...")` 5~10쌍
  12. `[M]` 학습 전후 정확도 비교
  13. `[C]` 테스트 질문 10개 일괄 실행 → 정확도 DataFrame
  14. `[M]` In-Chat Training — 오답 교정
  15. `[C]` 실패 질문 1~2개에 수동 정답 SQL 입력 후 `vn.train(question=..., sql=...)`
  16. `[C]` 재실행 → 정답 여부 확인
  17. `[M]` 본인 프로젝트 DB 적용 가이드 (DSN 교체 / DDL 덤프 획득 방법)
  18. `[C]` 학생용 TODO 템플릿 (`# MY_PROJECT_DSN = ...`)
  19. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "14H · Vanna 자가학습 실습"
- **🔗 Inter-notebook deps:** 10의 `./vanna_chroma` 재사용 가능(선택). 기본은 self-contained 재학습.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 12. `12_langchain_lcel.ipynb` — LangChain & LCEL 기초 (Day 3, 15H)

- **🎯 학습 목표:**
  - `PromptTemplate | Model | OutputParser` 파이프 연산자 체인을 이해한다.
  - `invoke` / `stream` / `batch` 3가지 실행 모드를 구분한다.
  - `RunnablePassthrough` / `RunnableLambda` / `RunnableParallel`을 활용한다.
  - `with_structured_output`으로 Pydantic 구조화 출력을 받는다.
- **📦 pip:** `langchain langchain-openai pydantic`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 22셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` LCEL 개요
  5. `[C]` 기본 체인: `prompt | ChatOpenAI | StrOutputParser`
  6. `[C]` `chain.invoke({...})`
  7. `[M]` 실행 모드 비교
  8. `[C]` `stream` (for chunk in chain.stream(...))
  9. `[C]` `batch` (여러 입력 동시)
  10. `[M]` 다양한 PromptTemplate
  11. `[C]` `ChatPromptTemplate.from_messages([...])` (system/human)
  12. `[M]` Runnable 유틸
  13. `[C]` `RunnablePassthrough.assign(...)`
  14. `[C]` `RunnableLambda(...)` 커스텀 변환
  15. `[C]` `RunnableParallel({...})` 병렬 실행
  16. `[M]` 구조화 출력
  17. `[C]` Pydantic BaseModel 정의
  18. `[C]` `llm.with_structured_output(Model)` 체인
  19. `[M]` JsonOutputParser 대안
  20. `[C]` JsonOutputParser 예제
  21. `[M]` 실습 과제
  22. `[C]` TODO
  23. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "15H · LangChain & LCEL 기초"
- **🔗 Inter-notebook deps:** 없음. DB 미사용.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 13. `13_lcel_rag_chain.ipynb` — LCEL RAG 체인 (Day 3, 16H)

- **🎯 학습 목표:**
  - ChromaDB + LangChain으로 RAG 체인을 LCEL로 조립한다.
  - 스트리밍 출력과 Fallback 로직을 적용한다.
  - 대화 히스토리를 RAG 체인에 통합한다.
- **📦 pip:** `langchain langchain-openai langchain-community langchain-chroma chromadb pydantic`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 22셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` LCEL RAG 개요
  5. `[C]` `Chroma` 벡터스토어 생성 (`./lc_chroma`) + 병원 문서 add_texts
  6. `[C]` Retriever 생성 `vs.as_retriever(search_kwargs={"k": 3})`
  7. `[M]` RAG 체인 조립
  8. `[C]` `format_docs` 함수 + RAG 체인 `{context: retriever|format_docs, question: RunnablePassthrough()} | prompt | llm | parser`
  9. `[C]` 테스트 질의 2건
  10. `[M]` 스트리밍
  11. `[C]` `for chunk in chain.stream(...)` 출력
  12. `[M]` Fallback
  13. `[C]` 고가 모델 → 저가 모델 `with_fallbacks([...])`
  14. `[M]` 대화 히스토리 통합 RAG
  15. `[C]` `RunnableWithMessageHistory` 또는 수동 히스토리 관리 체인
  16. `[C]` 멀티턴 테스트 (3턴)
  17. `[M]` 실습 과제
  18. `[C]` TODO
  19. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "16H · LCEL RAG 체인"
- **🔗 Inter-notebook deps:** 없음. 자체 Chroma 디렉토리 사용.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 14. `14_advanced_rag_query.ipynb` — Advanced RAG: 쿼리 변환 (Day 3, 17H)

- **🎯 학습 목표:**
  - HyDE(가상 문서 생성)로 검색 정확도를 높인다.
  - Multi-Query Retriever로 질문을 여러 관점으로 변형한다.
  - Query Decomposition으로 복잡 질문을 하위 질문으로 분해한다.
  - 세 기법을 동일 질문셋에 적용해 결과를 비교한다.
- **📦 pip:** `langchain langchain-openai langchain-community langchain-chroma chromadb`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 22셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[C]` Chroma 벡터스토어 재구축 (13과 독립, `./rag_chroma`)
  5. `[M]` HyDE 개념
  6. `[C]` 가상 문서 생성 프롬프트 + LCEL 체인
  7. `[C]` 가상 문서로 검색 vs 원문 검색 비교
  8. `[M]` Multi-Query Retriever
  9. `[C]` `MultiQueryRetriever.from_llm(...)` + 로깅
  10. `[C]` 생성된 서브 질문 확인
  11. `[M]` Query Decomposition
  12. `[C]` Decomposition 프롬프트 + 체인 (리스트 반환)
  13. `[C]` 각 하위 질문 검색 → 중복 제거
  14. `[M]` 세 기법 비교 실험
  15. `[C]` 동일 질문 5개 × 3기법 → 결과 DataFrame
  16. `[M]` 해석 가이드
  17. `[M]` 실습 과제
  18. `[C]` TODO
  19. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "17H · Advanced RAG — 쿼리 변환"
- **🔗 Inter-notebook deps:** 없음.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 15. `15_advanced_rag_retrieval.ipynb` — Advanced RAG: 검색 고도화 (Day 3, 18H)

- **🎯 학습 목표:**
  - BM25 + 벡터 하이브리드 검색을 구현한다.
  - CrossEncoder 기반 Re-ranking으로 상위 결과를 정제한다.
  - 하이브리드 + Re-rank RAG 체인을 LCEL로 조립한다.
- **📦 pip:** `langchain langchain-openai langchain-community langchain-chroma chromadb rank_bm25 sentence-transformers`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 18셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[C]` 벡터스토어 재구축 (14와 독립 또는 같은 경로 명시)
  5. `[M]` BM25 vs 벡터 검색
  6. `[C]` `BM25Retriever.from_texts(...)`
  7. `[C]` 벡터 Retriever
  8. `[C]` `EnsembleRetriever(weights=[0.4, 0.6])`
  9. `[C]` 비교 테스트 (동일 질문 3개로 bm25 / vector / ensemble 결과)
  10. `[M]` Re-ranking 이론
  11. `[C]` `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` 로드 (첫 실행 시 모델 다운로드)
  12. `[C]` 2단계: ensemble로 5개 후보 → crossencoder로 3개 재랭킹
  13. `[M]` 하이브리드 + Re-rank RAG 체인
  14. `[C]` 최종 체인 구성 + 질의
  15. `[M]` weight 실험
  16. `[C]` BM25 비중을 0.2 / 0.4 / 0.6 / 0.8 로 바꿔 결과 변화 관찰
  17. `[M]` 실습 과제
  18. `[C]` TODO
  19. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "18H · Advanced RAG — 검색 고도화"
- **🔗 Inter-notebook deps:** 없음. CrossEncoder 모델은 첫 실행 시 HF 허브에서 다운로드됨 (Colab은 OK).
- **🧪 Executable w/o secrets:** 셀 1~2만. CrossEncoder 로드 셀은 키 없이도 실행 가능하나 느려서 리뷰 실행은 스킵 권장.

---

### 📓 16. `16_langgraph_concept.ipynb` — LangGraph 개념 (Day 3, 19H)

- **🎯 학습 목표:**
  - `StateGraph` / Node / Edge / 조건부 분기 개념을 이해한다.
  - 루프(재시도) 패턴을 구현한다.
  - 그래프를 시각화하고 `stream`으로 실행 과정을 추적한다.
- **📦 pip:** `langgraph langchain langchain-openai`
- **🔑 secrets:** `OPENAI_API_KEY`
- **🧩 Cell outline (약 18셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` "왜 그래프인가?" — Chain vs Graph
  5. `[M]` 최소 예제 개념도
  6. `[C]` `State = TypedDict(...)` 정의
  7. `[C]` 노드 함수 2~3개
  8. `[C]` `StateGraph` 조립 + `compile()`
  9. `[C]` `graph.invoke({...})`
  10. `[M]` 그래프 시각화
  11. `[C]` `graph.get_graph().draw_mermaid_png()` (Colab 출력)
  12. `[M]` 조건부 분기 + 루프
  13. `[C]` 재시도 루프 예제 (랜덤 실패 시 최대 3회 재시도)
  14. `[C]` 분기 그래프 시각화
  15. `[M]` 실행 추적
  16. `[C]` `for state in graph.stream(...)` — 노드 순서 출력
  17. `[M]` 실습 과제
  18. `[C]` TODO
  19. `[M]` 다음 노트북 포인터 ("다음 노트북에서 이 개념을 SQL 에이전트로 조립합니다")
- **📚 Source:** `Lecture_Day3.md` § "19H · LangGraph 개념"
- **🔗 Inter-notebook deps:** 없음.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 17. `17_my_sql_agent.ipynb` — SQL 에이전트 빌드 (Day 3, 20H) ⭐ **00의 원본**

- **🎯 학습 목표:**
  - 상태 스키마(`AgentState`)를 설계한다.
  - SQL 생성 → 실행 → 검증 → 답변 4노드를 구현한다.
  - 검증 실패 시 재생성으로 분기하는 루프를 만든다.
  - 본인 프로젝트에 그대로 적용 가능한 템플릿을 완성한다.
- **📦 pip:** `langgraph langchain langchain-openai sqlalchemy psycopg2-binary sqlparse pandas tabulate`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 28셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 아키텍처 다이어그램 (state → gen → exec → validate → (ok) answer | (fail) gen)
  5. `[C]` 스키마 수집 함수
  6. `[C]` `AgentState` TypedDict
  7. `[M]` 보안 가드레일
  8. `[C]` `is_safe_sql(sql)` 함수
  9. `[M]` 노드 1 — SQL 생성
  10. `[C]` `generate_sql(state)` + 프롬프트
  11. `[M]` 노드 2 — SQL 실행
  12. `[C]` `execute_sql(state)` + 에러 캡처
  13. `[M]` 노드 3 — 검증
  14. `[C]` `validate(state)` — 결과 존재/에러 체크
  15. `[M]` 노드 4 — 답변 생성
  16. `[C]` `answer(state)` — 결과 → 자연어
  17. `[M]` 분기 함수
  18. `[C]` `should_retry(state)` → "retry" | "answer" | END (retry 최대 2회)
  19. `[M]` 그래프 조립
  20. `[C]` StateGraph + conditional_edges + compile
  21. `[C]` 그래프 시각화
  22. `[M]` 에이전트 실행
  23. `[C]` 단일 질문 실행 + state trace 출력
  24. `[M]` 10개 질문 일괄 테스트
  25. `[C]` 10개 질문 루프 + 결과 DataFrame (question, sql, answer, success)
  26. `[M]` 본인 프로젝트 적용 가이드 (DSN 교체 / 질문 교체)
  27. `[C]` `# MY_PROJECT_DSN = ...` TODO
  28. `[M]` 과제 #3 안내 (Day 4 시작까지 v1 + LangSmith trace URL 제출)
  29. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day3.md` § "20H · SQL 에이전트 빌드 (본인 프로젝트)"
- **🔗 Inter-notebook deps:** 01 병원 DB. **00과 로직이 동일해야 함** — 00을 마지막에 쓰기로 정한 이유.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

### 📓 18. `18_langsmith_tracing.ipynb` — LangSmith 트레이싱 (Day 4, 21H)

- **🎯 학습 목표:**
  - LangSmith 환경변수를 설정하고 프로젝트를 만든다.
  - 17번 에이전트를 재구성해 모든 실행을 LangSmith에 기록한다.
  - 토큰 사용량 / 지연 / 비용을 API로 분석한다.
  - 평가용 Dataset을 프로그램적으로 생성한다.
  - 실행 결과에 Feedback(정답/오답 태깅)을 부여한다.
- **📦 pip:** `langgraph langchain langchain-openai langsmith sqlalchemy psycopg2-binary pandas matplotlib sqlparse`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`, `LANGSMITH_KEY` (신규)
- **🧩 Cell outline (약 25셀):**
  1~3. 타이틀/설치/부트스트랩 (LangSmith 환경변수 포함: `LANGCHAIN_TRACING_V2="true"`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT="sql-agent-final"`)
  4. `[M]` 왜 모니터링인가
  5. `[C]` LangSmith Client 생성 + 프로젝트 리스트 확인
  6. `[M]` Day 3 에이전트 재구성
  7~14. `[C]` 17번 에이전트 코드를 압축 이식 (스키마/State/가드레일/4노드/그래프)
  15. `[M]` 10개 질문 실행
  16. `[C]` 질문 루프 실행 → 모든 실행이 자동으로 LangSmith에 기록됨
  17. `[C]` 실행 요약 DataFrame
  18. `[M]` LangSmith API로 트레이스 분석
  19. `[C]` `client.list_runs(project_name=..., execution_order=1, limit=20)` → DataFrame (토큰/지연/비용)
  20. `[M]` 시각화
  21. `[C]` 질문별 토큰 사용량 막대 차트
  22. `[C]` 지연 시간 차트
  23. `[M]` 평가용 Dataset 생성
  24. `[C]` `client.create_dataset(...)` + `create_examples(...)` (10문항 + ground truth)
  25. `[M]` Feedback 부여
  26. `[C]` 최근 실행에 `create_feedback(..., key="correctness", score=1)` 태깅
  27. `[M]` 실습 과제 — 본인 에이전트 실행에 LangSmith 연결
  28. `[M]` 다음 노트북 포인터
- **📚 Source:** `Lecture_Day4.md` § "21H · LangSmith 트레이싱"
- **🔗 Inter-notebook deps:** 17 에이전트 코드와 중복되나 self-contained(재이식). LangSmith 계정 필요 — 강의 첫 시간에 학생에게 무료 가입 안내했다는 전제.
- **🧪 Executable w/o secrets:** 셀 1~2만. LangSmith API 호출은 모두 키 필요.

---

### 📓 19. `19_ragas_eval.ipynb` — Ragas 정량 평가 (Day 4, 22H)

- **🎯 학습 목표:**
  - Ragas의 Faithfulness / Answer Relevancy / Context Precision·Recall 메트릭을 이해한다.
  - 에이전트 실행 결과를 Ragas 입력 형식으로 변환한다.
  - 평가를 실행하고 질문별 상세 분석 + 4-패널 시각화 + 레이더 차트를 만든다.
  - 낮은 점수의 원인을 진단하고 프롬프트 튜닝 후 Before/After를 비교한다.
- **📦 pip:** `ragas datasets langchain langchain-openai sqlalchemy psycopg2-binary pandas matplotlib langgraph sqlparse`
- **🔑 secrets:** `OPENAI_API_KEY`, `NEON_DSN`
- **🧩 Cell outline (약 25셀):**
  1~3. 타이틀/설치/부트스트랩
  4. `[M]` 왜 정량 평가 — Faithfulness / Relevancy / Context P·R
  5. `[C]` 18에서 실행한 results를 재생성(또는 저장된 results 로드) — 셀프컨테인을 위해 에이전트를 다시 실행
  6. `[C]` Ragas 입력 딕셔너리 구성 (`question`, `answer`, `contexts`, `ground_truth`)
  7. `[C]` `datasets.Dataset.from_dict(...)` 변환
  8. `[M]` Ragas 평가 실행
  9. `[C]` `evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])`
  10. `[C]` 전체 점수 출력
  11. `[M]` 질문별 분석
  12. `[C]` 결과 DataFrame 변환 + 정렬
  13. `[M]` 4-패널 차트
  14. `[C]` matplotlib subplot으로 metric별 막대 차트 4개
  15. `[M]` 레이더 차트
  16. `[C]` 레이더 차트 (전체 요약)
  17. `[M]` 낮은 점수 원인 진단
  18. `[C]` 각 메트릭 최저 질문 3건 추출 + SQL/답변/컨텍스트 비교
  19. `[M]` 튜닝 → 재평가
  20. `[C]` answer 노드 프롬프트 개선 (v2)
  21. `[C]` v2 실행 + Ragas 재평가
  22. `[C]` Before/After 점수 비교 DataFrame
  23. `[M]` Before/After 비교 차트
  24. `[C]` 막대 차트 (v1 vs v2)
  25. `[M]` 실습 과제 — 본인 에이전트에 적용
  26. `[M]` 다음 노트북 포인터 (23H 튜닝 / 24H 발표 — 노트북 없음)
- **📚 Source:** `Lecture_Day4.md` § "22H · Ragas 정량 평가"
- **🔗 Inter-notebook deps:** 17·18 에이전트 코드와 중복되나 self-contained. Ragas `evaluate`는 OpenAI 호출을 내부에서 많이 함 → 비용 경고 마크다운에 표시.
- **🧪 Executable w/o secrets:** 셀 1~2만.

---

## 5. 범위 우려 사항 (Scope flags)

- **총 작업량:** 20 노트북 × 평균 22셀 ≈ **440 셀**. 한 셀당 Lecture_Day*.md에서 코드를 이식하고 한국어 마크다운을 다듬는 데 평균 2~3분으로 보면 순수 작성만 **14~22시간**. 리뷰·재작업 포함 시 배로 늘어남. 단일 세션 완주는 비현실적.
- **권장 분할 납품:**
  - **Phase 1:** 01~07 (Day 1 기초, 7종). 강의가 Day 1만 먼저 나가도 1~8H 진행 가능.
  - **Phase 2:** 08~09 (Day 2, 2종). 
  - **Phase 3:** 10~17 (Day 3, 8종).
  - **Phase 4:** 18, 19, 00 (Day 4 + 데모, 3종). 00은 17을 복제·축약하는 작업이므로 마지막 Phase에서 가장 수월.
- **중복 코드:** 17 / 18 / 19 는 LangGraph SQL 에이전트 코어를 3번 반복 이식. 이는 "각 노트북 self-contained" 규약을 따른 결과이며, 코더는 17에서 확정한 코드 스니펫을 사본처럼 재사용하되 18에는 LangSmith 트레이싱 환경변수 한 줄, 19에는 Ragas 수집용 `contexts` 추가만 덧붙인다.
- **ChromaDB 경로 충돌:** 05(`./chroma_db`), 10~11(`./vanna_chroma`), 13(`./lc_chroma`), 14~15(`./rag_chroma` 등)는 모두 서로 다른 디렉토리를 사용해 한 Colab 세션에서도 간섭이 없어야 한다. 코더는 각 노트북 첫 chroma 셀에서 경로를 명시적으로 박아두고, 다른 노트북 경로를 공유하지 않는다.

---

## 6. 핸드오프 체크리스트 (팀 리드 → 코더)

코더가 작업 시작 전 이 체크리스트를 완료 확인:
- [ ] `/home/totorokr/Assist 강의/notebooks/` 디렉토리 존재 확인 (이미 생성됨)
- [ ] `Lecture_Day1.md` ~ `Lecture_Day4.md` 읽기 접근 확인
- [ ] `PROJECT_BRIEF.md` 읽기 접근 확인
- [ ] 각 노트북은 `nbformat v4` JSON으로 작성 (`nbformat.v4.new_notebook()`을 파이썬으로 만들고 `json.dump` 하거나, `jupytext` 없이 수동 JSON 작성)
- [ ] 절대 `참고자료/` 아래 파일을 수정/삭제하지 않는다
- [ ] 작성한 노트북 파일명은 정확히 `NN_topic.ipynb` (appendix/notebook-numbering.md 표 그대로)
- [ ] Batch A(01~03) 완료 시 리드에게 진행 보고 → 스피드/품질 점검 후 Batch B 진행
