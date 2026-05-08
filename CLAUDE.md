# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This is **not a software codebase**. It is a working directory for preparing a 24-hour university course titled **"AI 기반 SQL 분석 에이전트 구축"** (AI-Driven SQL Analytics Agent), delivered as an Assist 집중강의 (modular intensive lecture) over 4 days.

The deliverables being produced here are **lecture materials**: a course design document, per-hour session plans, Google Colab notebooks for hands-on labs, and a project brief for students' final capstone.

## Directory layout

- `참고자료/` — source materials only; treat as **read-only reference**.
  - `AI 기반 SQL 분석 에이전트 구축 교육 과정.md` — **the authoritative syllabus** for this course. All lecture design must align with its 24H breakdown, 7:3 practice-to-theory ratio, and tool stack.
  - `현장에서 바로 써먹는 SQL with PostgreSQL.pdf.md` — primary textbook (김임용), used for the PostgreSQL/SQL portion of Day 1.
  - `붙임2. 국문 과목설명서.docx.md`, `붙임3. 영문 과목설명서.docx.md` — **previous-version** course descriptions. Reference only; do not treat as current spec.
  - `AI 기반 SQL 분석 강의 설계.md` — prior design notes.

New lecture materials (design docs, notebooks, project briefs) should be created at the repository root or in new top-level folders — **not** inside `참고자료/`.

## Course design constraints (load-bearing)

When producing or revising lecture materials, these constraints come from the user and must be preserved:

1. **24 hours split across 4 days**, following the syllabus H-block structure (1–8H, 9–12H, 13–20H, 21–24H). The user refers to these as 첫날 / 2번째 / 3번째 / 마지막 강의.
2. **Practice : theory = 7 : 3.** Each hour should be hands-on unless explicitly a concept intro.
3. **All hands-on uses Google Colab** so students can run labs from their own laptops without local installs. PostgreSQL access is via cloud Postgres (Neon or Supabase free tier) + `psycopg2`/`SQLAlchemy`; pgAdmin is demo-only.
4. **Tool stack is fixed by the syllabus:** PostgreSQL · LlamaIndex + ChromaDB · Vanna.ai · LangChain/LCEL · LangGraph · LangSmith · Ragas · Gradio. Do not substitute without asking.
5. **Final project track spans all 4 days:**
   - Day 1: brief the project + show a completed agent demo first (reverse-learning: students see the target before building pieces).
   - Day 2 start: students submit a **project proposal** (domain, schema draft, 10 NL questions, sample SQL).
   - Day 3 start: students submit **schema + seed data** deployed to their own Neon instance.
   - Day 4 start: students submit **agent v1** with a LangSmith trace link.
   - Day 4 end: 5–7 min final presentation with Ragas evaluation report.
6. **Shared dataset for in-class labs:** hospital / e-commerce PostgreSQL DBs, used consistently across all 4 days to minimize cognitive load. Students' *own* datasets are used only in the project track.
7. **Notebook numbering convention:** `00_demo_agent.ipynb` through `19_ragas_eval.ipynb`, in strict pedagogical order, so students can follow sequentially.

## Per-hour content (confirmed design)

Each hour = 50분 강의 + 10분 휴식 기준. 노트북 파일명은 앞서 고정한 번호 체계를 따른다.

### Day 1 (1~8H) — 개관 · SQL · RAG 파이프라인 + 프로젝트 브리핑
- **1H · OT & 전체 데모** — Agentic Analytics 개념, 전통 BI vs Text-to-SQL vs 에이전틱 비교, `00_demo_agent.ipynb`로 완성형 에이전트 시연(역방향 학습의 앵커), 4일 로드맵, Colab/Neon/API Key 셋업.
- **2H · PostgreSQL 기초** — Neon 인스턴스 생성, Colab에서 `psycopg2`/`SQLAlchemy` 접속, 샘플 DB(병원/이커머스) 임포트, `SELECT`/`WHERE`/`ORDER BY`/`LIMIT`, `EXPLAIN` 맛보기. 교재 1~3장.
- **3H · 집계·조인 실전** — `GROUP BY`/`HAVING`, `INNER`/`LEFT`/`SELF JOIN`, 서브쿼리, CTE, 윈도우 함수 입문. 교재 연습문제 병행.
- **4H · Schema Intelligence** — AI 가독성 스키마 원칙(네이밍, `COMMENT ON`, FK 명시), 정규화 vs LLM-친화적 비정규화 트레이드오프, ERD 간단 작성.
- **5H · LlamaIndex 개론** — Documents → Nodes → Index → Query Engine 파이프라인, Data Loader 생태계, `Settings` 객체, PDF/CSV/SQL 로더, SentenceSplitter, 메타데이터 부여.
- **6H · 임베딩 + ChromaDB** — 임베딩/코사인 유사도 개념, OpenAI/HF 임베딩 모델, Chroma 영속 저장, Top-K 검색 실습.
- **7H · Text-to-SQL 맛보기** — `SQLDatabase` 래퍼, `NLSQLTableQueryEngine` 최소 예제, 스키마 프롬프팅이 왜 중요한지 체감(Day 2 예고편).
- **8H · 최종 프로젝트 브리핑** — `PROJECT_BRIEF.md` 배포, 과제 #1(제안서) 기준·평가 루브릭 설명, 도메인 선정 Q&A.

### Day 2 (9~12H) — 제안서 회수 + Text-to-SQL 상담사
- **9H · 제안서 피어리뷰** — 과제 #1 제출, 3인 1조 피어리뷰 10분 + 강사 피드백. 스키마·질문 난이도 분포 점검.
- **10H · NLSQLTableQueryEngine 심화** — 내부 프롬프트 추적, `table_info` 주입, 테이블 선택 전략, 오답 사례 분석 및 프롬프트 튜닝.
- **11H · 병원 DB 상담사 설계** — 요구사항 정의, 멀티턴 상태 관리, 컨텍스트 누적, 금칙어·쿼리 범위 가드레일.
- **12H · Gradio in Colab** — `ChatInterface`, `share=True`로 공개 URL, 세션 메모리, 에러 핸들링, 수강생 간 앱 교차 체험. 과제 #2(스키마+시드) 안내.

### Day 3 (13~20H) — Vanna · LangChain · Advanced RAG · LangGraph + 프로젝트 빌드
- **13H · Vanna.ai 구조** — RAG 기반 Text-to-SQL 작동 원리, 학습 자산 3종(DDL / Documentation / SQL Pairs), Vanna 내부 검색 흐름.
- **14H · Vanna 자가학습** — DDL 주입, 비즈니스 용어집 문서화, In-Chat Training으로 오답→정답 피드백 루프. **본인 프로젝트 DB로 실습**.
- **15H · LangChain & LCEL 기초** — `PromptTemplate`, Model I/O, `OutputParser`, `|` 연산자 체인, `Runnable` 인터페이스.
- **16H · LCEL RAG 체인** — RAG 체인 조립, Pydantic 구조화 출력, 스트리밍/배치, 에러 fallback.
- **17H · Advanced RAG — 쿼리 변환** — HyDE(가상문서 생성), Multi-Query, Query Decomposition 비교 실습.
- **18H · Advanced RAG — 검색 고도화** — BM25+벡터 하이브리드, CrossEncoder/Cohere Re-rank, Parent-Child 청킹.
- **19H · LangGraph 개념** — `StateGraph`, Node/Edge, 조건부 분기, 루프/재시도, ReAct 에이전트 개관.
- **20H · SQL 에이전트 빌드** — 상태 스키마 설계 → SQL 생성 노드 → 실행 노드 → 검증/재생성 분기 → 답변 노드. **본인 프로젝트에 바로 적용**. 과제 #3(에이전트 v1) 착수.

### Day 4 (21~24H) — 평가·모니터링 + 최종 발표
- **21H · LangSmith 트레이싱** — 프로젝트 설정, Run/Trace 구조, 토큰·지연·비용 가시화, 평가용 데이터셋 구축. 본인 에이전트에 즉시 연결.
- **22H · Ragas 정량 평가** — Faithfulness, Answer Relevancy, Context Precision/Recall 메트릭 설명 및 리포트 작성. 결과 기반 프롬프트/검색 튜닝.
- **23H · 최종 튜닝 & 리허설** — 개인 작업 + 강사 1:1 피드백, 발표 슬라이드 3장 준비(문제/아키텍처/평가결과).
- **24H · 최종 발표 & 수료** — 1인 5~7분, 라이브 데모 + Ragas 리포트 공유, 상호 피드백, 수료.

## Language

All student-facing materials (slides, notebook markdown, project brief, assessment rubrics) are in **Korean**. Code identifiers and comments stay in English. Internal design docs may mix both.

## Progress log

### ✅ 완료
- **`CLAUDE.md`** — 저장소 목적, 설계 제약, 시간별 주요 내용 정리.
- **`Lecture.md` (v0.1 초안)** — 24H 전 과정 강의자료 초안. 각 시간별 학습목표·핵심 개념·실습 코드 스니펫·과제 연결 포함. 사전 준비, Day 1~4 본문, 부록(리포 구조/트러블슈팅/참고자료) 구성. 슬라이드화 및 Colab 노트북 분할을 전제로 작성됨.
- **`PROJECT_BRIEF.md`** — Day 1 8H 배포용 최종 프로젝트 브리핑. 4단계 마일스톤·제안서 양식·스키마 설계 원칙·평가 루브릭·발표 가이드·FAQ·템플릿 포함.
- **`Lecture_Day1.md`** — Day 1 (1~8H) 상세 강의자료. 시간별 학습목표·이론 설명·완전한 실행 코드·실습 과제·강사 노트. 병원 DB DDL+시드 데이터 포함.
- **`Lecture_Day2.md`** — Day 2 (9~12H) 상세 강의자료. 피어리뷰·NLSQLTableQueryEngine 심화·멀티턴 상담사·Gradio UI.
- **`Lecture_Day3.md`** — Day 3 (13~20H) 상세 강의자료. Vanna·LangChain/LCEL·Advanced RAG·LangGraph SQL 에이전트 빌드.
- **`Lecture_Day4.md`** — Day 4 (21~24H) 상세 강의자료. LangSmith 트레이싱·Ragas 정량 평가·최종 발표·수료.
- **`docs/appendix/free-llm-ollama.md` + `notebooks/99_free_llm_ollama.ipynb`** — OpenAI 비용 부담 완화용 부록. Colab에서 Ollama(Qwen3) 띄우기 / Groq 무료 Tier / LlamaIndex·LangChain·Vanna LLM 초기화 교체 레시피. mkdocs nav · `setup.md` · `colab-links.js` 등록 완료.

### 🔜 다음 작업 후보 (우선순위 미정, 사용자 확인 필요)
1. **Colab 노트북 실제 구현** — `Lecture_Day*.md`의 코드를 실행 가능한 `.ipynb`로 분할 제작. 번호 체계 `00_demo_agent.ipynb` ~ `19_ragas_eval.ipynb`.
2. ~~**`PROJECT_BRIEF.md`**~~ — ✅ 완료.
3. **샘플 데이터셋 분리** — `data/hospital.sql`, `data/ecommerce.sql` 별도 파일 분리. (현재 Day 1 강의자료 내에 DDL+시드 포함되어 있으나, 독립 파일로도 제공 필요).
4. **슬라이드 자료** — `Lecture_Day*.md`를 Marp/Reveal.js로 변환하는 작업. 사용자가 요청하기 전에는 착수 금지.
5. **`rubric.md`** — 과제 3건 + 최종 발표 세부 채점 기준 분리 문서화.

### 작업 이력 (대화 순)
1. 사용자가 `참고자료/` 내 syllabus·이전 과목설명서를 제시, 강의 설계 요청.
2. 1차 설계안 — 24H를 4블록(1–8H/9–12H/13–20H/21–24H)으로 분할, 일자별·시간별 구성.
3. 교재 『현장에서 바로 써먹는 SQL with PostgreSQL』이 Day 1 PostgreSQL 파트 주교재로 확정.
4. 제약 추가 — 전 실습 Colab 기반, 4일 프로젝트 트랙(Day1 브리핑 → Day2 제안서 → Day3 v1 → Day4 발표), 첫 시간 완성품 시연(역방향 학습).
5. `CLAUDE.md` 생성 → 시간별 내용 추가.
6. `Lecture.md` v0.1 초안 생성.
7. `PROJECT_BRIEF.md` 작성 — 프로젝트 개요, 4단계 마일스톤, 제안서 양식, 평가 루브릭, 발표 가이드, FAQ, 템플릿.
8. `Lecture_Day1~4.md` 상세 강의자료 작성 — 24H 전 시간에 대해 이론 설명·완전한 실행 코드·실습 과제·강사 노트 포함. `Lecture.md` 초안 대비 3~4배 분량으로 확장.

## Working style for this repo

- There is no build, test, or lint. "Running" a notebook means opening it in Colab.
- Before proposing structural changes to the course design, re-read `참고자료/AI 기반 SQL 분석 에이전트 구축 교육 과정.md` — it is the source of truth the user anchors on.
- The user iterates on design first, then asks for artifacts. Do not start producing notebooks until the design for that day is confirmed.
