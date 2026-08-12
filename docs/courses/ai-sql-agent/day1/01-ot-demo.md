# 1H · OT & Agentic Analytics 전체 데모

## 학습목표
- "에이전틱 분석"이 기존 방식과 어떻게 다른지 설명할 수 있다
- 4일간 만들 최종 산출물의 전체 모습을 미리 체험한다
- Colab + Neon + OpenAI 환경을 설정한다

!!! tip "🧭 이 시간을 이렇게 읽으세요 (비개발자용)"
    - **한 줄 핵심**: 4일간 만들 최종 결과물(에이전트)을 **미리 한 번 구경** 하고, 환경을 준비하는 오리엔테이션 시간입니다.
    - **꼭 이해**: AI 에이전트는 SQL을 단번에 짜지 않고 **"생성 → 실행 → 검증 → 재시도"** 를 반복한다는 것 — 이 흐름 하나만 가져가면 됩니다.
    - **지금은 몰라도 OK**: 데모 코드의 `TypedDict`, `StateGraph`, 노드 함수들. 강사가 보여주는 시연 코드는 **구경만** 하셔도 됩니다 — Day 3 19~20H에 본인 손으로 같은 구조를 만들게 됩니다.
    - **막히면**: 모르는 단어는 [용어 사전](../appendix/glossary.md) 으로, 강의 따라가는 마음가짐은 [비개발자 학습 가이드](../beginners-guide.md) 로.

<div class="colab-link" data-notebook="00_demo_agent"></div>

## 쉬운 비유로 이해하기 — 데이터 분석의 3세대

우리가 식당에서 주문하는 방식에 비유해 봅시다:

| 세대 | 방식 | 식당 비유 | 한계 |
|---|---|---|---|
| **1세대: BI 대시보드** | 분석가가 미리 만들어 둔 보고서 | 정해진 세트 메뉴만 가능 | 새로운 질문은 불가 |
| **2세대: Text-to-SQL** | 자연어로 질문 → SQL 1회 변환 | 메뉴판 보고 단품 주문 | 복잡한 요리는 실패 |
| **3세대: Agentic Analytics** | AI가 계획-실행-검증-재시도 | 셰프에게 "맛있는 거 해주세요" | 우리가 4일간 만들 것! |

### 왜 "에이전트"인가?

**Text-to-SQL의 한계 (2세대)**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

Text-to-SQL: SQL 1회 생성 → 실행 → 끝
  ❌ 잘못된 SQL을 감지하지 못함
  ❌ 복잡한 질문을 분해하지 못함
  ❌ 결과가 이상해도 재시도하지 않음
```

**에이전트의 접근 (3세대)**
```
사용자: "지난 분기 매출 상위 5개 제품의 전년 대비 성장률은?"

에이전트:
  1단계: 질문 분석 → "매출 상위 5개" + "전년 대비 성장률"로 분해
  2단계: SQL 생성 → 첫 번째 쿼리 작성
  3단계: SQL 실행 → 결과 확인
  4단계: 검증 → "행이 0개? 날짜 조건을 수정하자" → SQL 재작성
  5단계: 재실행 → 성공 → 자연어 답변 생성
```

### 에이전트의 4가지 핵심 요소

```
┌─────────────────────────────────────────────┐
│               AI 에이전트                      │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │  State   │  │  Tools   │                 │
│  │ (기억력)  │  │ (도구함)  │                 │
│  │ 대화 이력 │  │ SQL 실행  │                 │
│  │ 현재 SQL  │  │ 검색 엔진 │                 │
│  └──────────┘  └──────────┘                 │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │ Planning │  │Validation│                 │
│  │ (계획력)  │  │ (검증력)  │                 │
│  │ 질문 분해 │  │ 결과 확인 │                 │
│  │ 단계 수립 │  │ 재시도    │                 │
│  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────┘
```

1. **State (기억력)** — 이전 대화, 현재 작업 상태를 기억
2. **Tools (도구함)** — SQL 실행, 벡터 검색, AI 호출 등 사용 가능한 도구
3. **Planning (계획력)** — 복잡한 질문을 단계별로 분해
4. **Validation (검증력)** — 결과 확인, 오류 시 재시도

### 4일 학습 여정

```
┌──────────┬──────────────────────────────────────────────┐
│  Day 1   │ SQL 기초 + RAG 파이프라인 + 프로젝트 브리핑   │
│ (1~8H)   │ 🎯 "재료 준비" — DB, 검색, Text-to-SQL 기초  │
├──────────┼──────────────────────────────────────────────┤
│  Day 2   │ Text-to-SQL 심화 + 상담사 에이전트            │
│ (9~12H)  │ 🎯 "조리 시작" — 프롬프트 튜닝, Gradio UI    │
├──────────┼──────────────────────────────────────────────┤
│  Day 3   │ Vanna + LangChain + LangGraph 에이전트       │
│ (13~20H) │ 🎯 "완성" — 본인 프로젝트 에이전트 빌드      │
├──────────┼──────────────────────────────────────────────┤
│  Day 4   │ LangSmith + Ragas 평가 + 최종 발표           │
│ (21~24H) │ 🎯 "검증 & 발표" — 정량 평가, 라이브 데모    │
└──────────┴──────────────────────────────────────────────┘
```

## 실습 — 완성형 에이전트 데모 시연 (강사 진행)

!!! warning "⚠️ 복붙 금지 — 구경만 하세요"
    이 섹션 코드는 **강사가 실행하는 것을 구경만** 하는 시연용입니다.
    `TypedDict`, `StateGraph`, 프롬프트 엔지니어링, 가드레일 등 뒤에서 차근차근 배웁니다.
    **지금 이해하지 못해도 괜찮습니다** — Day 3 19~20H에서 본인 손으로 같은 구조를 만들게 됩니다.

!!! tip "한 줄 비유로 친해지기"
    - **LangGraph** = "에이전트가 어떤 순서로 일할지"를 **그림(흐름도)으로 그리는 도구**. 신호등처럼 상태에 따라 다음 단계를 고릅니다.
    - **StateGraph** = 그 흐름도의 설계도. "질문 → SQL 생성 → 실행 → (에러면 재시도) → 답변" 같은 길을 그립니다.
    - **TypedDict** = 에이전트가 머릿속에 적어두는 **메모지 양식**(질문·SQL·결과·에러 칸).

    이 비유만 기억하고 코드는 흐름만 따라가세요. 세부 구현은 Day 3에서 파고듭니다.

LangGraph라는 프레임워크로 SQL 분석 에이전트를 만듭니다. 질문을 받으면 SQL을 생성하고, 실행하고, 검증하고, 자연어로 답변합니다.

```python
# ============================================================
# 🎯 완성형 SQL 분석 에이전트 데모
# ============================================================
!pip install -q langchain langchain-openai langgraph sqlalchemy psycopg2-binary tabulate

import os, re
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")

from sqlalchemy import create_engine, text, inspect
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

engine = create_engine(os.environ["NEON_DSN"])
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- 상태 정의: 에이전트가 기억할 정보 ---
class AgentState(TypedDict):
    question: str     # 사용자 질문
    sql: str          # 생성된 SQL
    result: str       # 실행 결과
    error: str        # 에러 메시지
    answer: str       # 최종 답변
    attempts: int     # 재시도 횟수

# --- (생략: 스키마 수집 + 노드 함수들은 강사 시연용) ---
# 4일 후에 여러분이 직접 구현합니다!
```

```python
# 시연 질문 예시
# ask("현재 등록된 환자 수는 몇 명인가요?")
# ask("진료과별 의사 수를 보여주세요.")
# ask("지난 3개월간 가장 많이 방문한 환자 Top 5는?")
```

## 실습 — 환경 셋업 (직접 따라하기)

### Step 1: Google Colab 접속

1. 브라우저에서 `colab.research.google.com` 접속
2. Google 계정으로 로그인
3. "새 노트" 클릭하여 빈 노트북 생성

### Step 2: Neon PostgreSQL 가입

1. `neon.tech` 접속 → "Sign Up" 클릭
2. Google 계정 또는 GitHub으로 가입
3. "New Project" → 프로젝트 이름: `sql-agent-course`
4. Region: `Asia Pacific (Singapore)` 선택
5. 생성 완료 후 **Connection String** 복사
   - 형식: `postgresql://user:pass@host/dbname?sslmode=require`

!!! warning "주의"
    반드시 `?sslmode=require`가 포함되어야 합니다!

### Step 3: Colab Secrets 등록

1. Colab 왼쪽 사이드바의 🔑 아이콘(Secrets) 클릭
2. "Add a new secret" 클릭
3. 두 개의 키 등록:
   - 이름: `OPENAI_API_KEY` → 값: OpenAI API 키 붙여넣기
   - 이름: `NEON_DSN` → 값: Neon Connection String 붙여넣기
4. 각 키의 "Notebook access" 토글을 **ON**으로 설정

### Step 4: 부트스트랩 실행

- 공통 부트스트랩 코드를 복사 → 첫 번째 셀에 붙여넣기 → 실행(▶)
- `✅ PostgreSQL 연결 성공:` 메시지가 나오면 성공!

### 실습 체크리스트

- [ ] Colab 노트북 생성 완료
- [ ] Neon 인스턴스 생성 + DSN 복사 완료
- [ ] Colab Secrets에 2개 키 등록 완료
- [ ] 부트스트랩 실행 → 연결 성공 확인

!!! note "핵심 정리"
    - **에이전틱 분석** = AI가 계획→실행→검증→재시도를 자율적으로 수행
    - 4일 후 여러분은 **본인 도메인**의 SQL 분석 에이전트를 만들어 발표합니다
    - 오늘은 "재료 준비" — SQL, 검색, Text-to-SQL의 기초를 배웁니다
