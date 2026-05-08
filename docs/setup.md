# 사전 준비 — 환경 설정 가이드

이 페이지에서는 4일간의 실습에 필요한 모든 환경을 준비합니다.

!!! tip "비개발자라면 — 먼저 이 두 페이지부터"
    - **[비개발자 학습 가이드](beginners-guide.md)** — 24H 강의를 어떻게 읽고 따라가야 하는지 마음가짐과 신호 해석법.
    - **[용어 사전](appendix/glossary.md)** — API·DSN·임베딩·LCEL 등 강의 전반의 용어를 비유와 함께 정리한 한 페이지.

    이 페이지에서 처음 보는 단어(예: DSN, Connection String, SSL, Secrets)는 용어 사전에 모두 정리되어 있습니다.

## Neon PostgreSQL 가입 가이드

Neon은 클라우드 기반 PostgreSQL 서비스로, 무료 플랜으로 실습에 충분합니다.

### Step 1: 가입

1. 브라우저에서 `neon.tech` 접속
2. "Sign Up" 클릭
3. Google 계정 또는 GitHub으로 가입

### Step 2: 프로젝트 생성

1. 로그인 후 "New Project" 클릭
2. 프로젝트 이름: `sql-agent-course`
3. Region: `Asia Pacific (Singapore)` 선택
4. "Create Project" 클릭

### Step 3: Connection String 복사

1. 프로젝트 대시보드에서 **Connection String** 확인
2. 형식: `postgresql://user:pass@host/dbname?sslmode=require`
3. 이 문자열을 메모장에 복사해 둡니다

!!! warning "주의"
    반드시 `?sslmode=require`가 포함되어야 합니다! 누락 시 연결이 실패합니다.

---

## OpenAI API Key 발급

1. `platform.openai.com` 접속 후 로그인
2. 좌측 메뉴 "API keys" 클릭
3. "Create new secret key" 클릭
4. 키 이름 입력 (예: `sql-agent-course`)
5. 생성된 키(`sk-...`)를 복사해 메모장에 저장

!!! warning "주의"
    API 키는 생성 시 한 번만 표시됩니다. 반드시 복사해 두세요. 분실 시 새로 발급해야 합니다.

!!! tip "비용이 부담된다면 — 무료 LLM 경로"
    OpenAI 무료 크레딧이 소진되었거나 결제 수단이 없는 경우, **Colab에서 Ollama(Qwen3) 를 띄우거나 Groq 무료 Tier** 로 강의를 그대로 따라갈 수 있습니다. 노트북당 LLM 초기화 1~2줄만 바꾸면 됩니다. → [부록 · 무료 LLM · Ollama (Qwen3)](appendix/free-llm-ollama.md)

---

## LangSmith API Key 발급 (선택 · Day 4용)

LangSmith는 LangChain·LangGraph 실행을 자동 트레이싱·평가해 주는 관측 도구입니다. **Day 4 21H 트레이싱 실습**에서 사용합니다. 무료(Developer) 플랜이면 강의 분량을 모두 커버합니다.

1. 브라우저에서 `smith.langchain.com` 접속 후 가입(Google/GitHub OK)
2. 좌측 하단 ⚙️ **Settings** → **API Keys** 메뉴로 이동
3. **"Create API Key"** 클릭 → 키 이름(예: `sql-agent-course`) 입력 → **Personal Access Token** 선택
4. 생성된 키(`lsv2_pt_...`)를 복사해 메모장에 저장

!!! tip "팁"
    부트스트랩 코드는 `LANGSMITH_API_KEY`가 등록돼 있으면 `LANGSMITH_TRACING=true` 와 `LANGSMITH_PROJECT=sql-agent-class` 를 자동으로 켭니다. Day 1~3에는 키가 없어도 실습이 정상 작동합니다.

---

## Cohere API Key 발급 (선택 · Day 3 18H용)

Cohere는 검색 결과를 의미 기반으로 재정렬하는 **Re-rank** API를 제공합니다. **Day 3 18H Advanced RAG 검색 고도화**에서 BM25+벡터 하이브리드 결과를 Cohere Re-rank로 정밀화하는 실습에 사용합니다. 무료 Trial Key로 강의 분량은 충분합니다.

1. 브라우저에서 `dashboard.cohere.com` 접속 후 가입
2. 좌측 메뉴 **API Keys** 클릭
3. 기본 제공되는 **Trial Key**를 복사하거나 **"+ New Trial Key"** 로 새로 발급
4. 생성된 키를 메모장에 저장

!!! note "키가 없을 때"
    Day 3 18H 실습은 Cohere 키가 없으면 자동으로 **`sentence-transformers` 기반 CrossEncoder Re-rank** 로 폴백합니다. 키가 없어도 실습 진행 자체는 가능합니다.

---

## Google Colab 설정

1. 브라우저에서 `colab.research.google.com` 접속
2. Google 계정으로 로그인
3. "새 노트" 클릭하여 빈 노트북 생성
4. 상단 메뉴 "런타임 > 런타임 유형 변경"에서 Python 3 확인

---

## Colab Secrets 등록법

API 키와 DB 접속 정보를 안전하게 저장하는 방법입니다.

1. Colab 왼쪽 사이드바의 **🔑 아이콘(Secrets)** 클릭
2. "Add a new secret" 클릭
3. 다음 키들을 등록합니다 (필수 2개 + 선택 2개):

| 이름 | 값 | 사용 시점 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI에서 복사한 API 키 (`sk-...`) | 필수 · Day 1~4 전체 |
| `NEON_DSN` | Neon에서 복사한 Connection String | 필수 · Day 1~4 전체 |
| `LANGSMITH_API_KEY` | LangSmith에서 복사한 키 (`lsv2_pt_...`) | 선택 · Day 4 21H |
| `COHERE_API_KEY` | Cohere에서 복사한 Trial Key | 선택 · Day 3 18H |

4. 각 키의 **"Notebook access"** 토글을 **ON**으로 설정

!!! tip "팁"
    Secrets에 저장하면 코드에 키를 직접 쓰지 않아도 됩니다. 노트북을 공유할 때 키가 노출되지 않아 안전합니다.

---

## 라이브러리 버전 핀

4일 강의 전 기간 동안 **같은 버전**으로 실행되도록 다음 목록을 `requirements.txt` 또는 각 Day 첫 셀에 고정합니다. 2026-04 기준 검증된 조합입니다.

```text
gradio==4.44.1
langsmith>=0.1.70,<0.2
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.20
llama-index>=0.10.50,<0.12
llama-index-vector-stores-chroma
ragas>=0.1.17,<0.2
vanna>=0.6.0
sentence-transformers>=2.7.0
psycopg2-binary
sqlalchemy>=2.0
tabulate
matplotlib
chromadb
openai>=1.30
pandas
```

!!! warning "버전 핀이 꼭 필요한 이유"
    - Gradio 5.x에서 `ChatInterface`의 `retry_btn` / `undo_btn` / `clear_btn` / `bubble_full_width` 파라미터가 제거됐습니다 → **Day 2 12H 실습이 `TypeError`** 로 중단됩니다.
    - `langsmith` 구버전은 `list_runs(is_root=...)` 를 지원하지 않습니다.
    - Ragas 0.2+ 는 필드명이 `ground_truth→reference`, `contexts→retrieved_contexts` 로 바뀝니다.

---

## 공통 부트스트랩 코드 { #bootstrap-common }

모든 실습 노트북의 **첫 번째 셀**에 아래 코드를 복사하여 실행하세요. Day 별로 필요한 추가 패키지는 각 Day 문서에 별도 안내됩니다.

```python
# ============================================================
# 📦 패키지 설치 (Colab 환경) — 버전 핀으로 재현성 확보
# ============================================================
!pip install -q \
    psycopg2-binary "sqlalchemy>=2.0" \
    "llama-index>=0.10.50,<0.12" llama-index-embeddings-openai llama-index-llms-openai \
    llama-index-vector-stores-chroma chromadb \
    "openai>=1.30" \
    tabulate pandas matplotlib

# ============================================================
# 🔑 환경변수 설정 — Colab / 로컬 모두 지원
# ============================================================
import os

try:
    from google.colab import userdata
    # Colab Secrets에서 키를 읽어 환경변수로 승격 (이미 있으면 덮어쓰지 않음)
    for key in ("OPENAI_API_KEY", "NEON_DSN", "LANGSMITH_API_KEY", "COHERE_API_KEY"):
        val = userdata.get(key)
        if val:
            os.environ.setdefault(key, val)
except ImportError:
    # 로컬 환경에서는 .env 등 다른 방식으로 이미 설정돼 있다고 가정
    pass

# LangSmith (옵션) — 키가 있으면 자동 트레이싱 ON
if os.environ.get("LANGSMITH_API_KEY"):
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "sql-agent-class")

# ============================================================
# 🔌 Neon 엔진 — 실습용 / 에이전트용 분리
# ============================================================
from sqlalchemy import create_engine, text

# 실습(테이블 생성·INSERT 포함)용 — read-write
engine = create_engine(
    os.environ["NEON_DSN"],   # 반드시 ?sslmode=require 포함
    pool_pre_ping=True,
    pool_recycle=300,
)

# 에이전트(생성된 SQL 실행)용 — 세션을 read-only 로 강제
#   LLM이 만든 DROP/DELETE/UPDATE가 어떤 정규식도 통과해도 DB 레벨에서 차단됩니다
agent_engine = create_engine(
    os.environ["NEON_DSN"],
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"options": "-c default_transaction_read_only=on"},
)

# 연결 확인
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()")).fetchone()
    print(f"✅ PostgreSQL 연결 성공: {result[0][:50]}...")
```

!!! warning "주의"
    자주 발생하는 오류: "연결 실패" → Neon DSN 끝에 `?sslmode=require`가 빠진 경우가 많습니다.

!!! tip "왜 엔진을 두 개로 분리하나요?"
    - `engine`: 학생이 DDL·INSERT 실습할 때 사용 (권한 넓음).
    - `agent_engine`: 에이전트가 만든 SQL을 실행할 때만 사용 (세션이 read-only 라 UPDATE/DELETE 실행 자체가 실패).

    정규식 블랙리스트만 쓰면 `WITH x AS (DELETE ... RETURNING *) SELECT * FROM x` 같은 data-modifying CTE 를 못 막습니다. **read-only 세션이 진짜 방어선**입니다. 정규식 가드는 "보조 방어선(defense-in-depth)" 으로만 쓰세요.

---

## Matplotlib 한글 폰트 설정

차트의 한글 라벨이 □ 박스로 깨지지 않도록 NanumGothic 을 설치·등록합니다.

!!! tip "관련 노트북은 이미 자동 처리됩니다"
    matplotlib 을 사용하는 노트북(`05_embedding_chromadb`, `18_langsmith_tracing`, `19_ragas_eval`)은 `%pip install` 직후 셀에서 **이 셋업을 자동으로 실행** 합니다. 수강생이 따로 추가할 필요 없음. 셀 재실행도 안전(이미 설치돼 있으면 즉시 통과).

본인 프로젝트 노트북에서 matplotlib 한글 차트를 그릴 때는 다음 코드를 첫 셀 근처에 추가하세요. apt 설치 + matplotlib 폰트 매니저 등록까지 한 번에 해결합니다.

```python
import subprocess
subprocess.run(["apt-get", "install", "-y", "fonts-nanum"], check=False, capture_output=True)
subprocess.run(["fc-cache", "-fv"],                          check=False, capture_output=True)

import matplotlib.pyplot as plt
from matplotlib import font_manager
for p in font_manager.findSystemFonts():
    if "Nanum" in p:
        font_manager.fontManager.addfont(p)

plt.rcParams["font.family"]        = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 부호 깨짐 방지
```

!!! note "왜 `addfont()` 까지 호출하나요?"
    `apt-get` 만으로는 matplotlib 의 폰트 캐시가 새 폰트를 인식하지 못해 **런타임 재시작 없이는 적용이 안 되는** 경우가 있습니다. `font_manager.fontManager.addfont(...)` 로 직접 등록하면 그 자리에서 즉시 활성화됩니다.

---

## 연결 확인 방법

부트스트랩 코드를 실행한 후 아래 메시지가 출력되면 성공입니다:

```
✅ PostgreSQL 연결 성공: PostgreSQL 16.x ...
```

### 문제 해결 체크리스트

| 증상 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError` | 패키지 미설치 | `!pip install` 셀을 다시 실행 |
| `연결 실패` | DSN 오류 | Neon 대시보드에서 Connection String 재확인 |
| `sslmode` 오류 | DSN 끝에 `?sslmode=require` 누락 | DSN 수정 후 Secrets 업데이트 |
| `API key` 오류 | OpenAI 키 오류 | Secrets에서 키 값 재확인 |
| `Notebook access` 오류 | Secrets 토글 OFF | 각 키의 토글을 ON으로 변경 |

!!! note "핵심 정리"
    - Neon 가입 → 프로젝트 생성 → Connection String 복사
    - OpenAI API Key 발급 → 복사
    - (선택) LangSmith API Key 발급 — Day 4 21H 트레이싱용
    - (선택) Cohere API Key 발급 — Day 3 18H Re-rank용 (없으면 CrossEncoder로 폴백)
    - Colab Secrets에 `OPENAI_API_KEY`·`NEON_DSN` (필수) + `LANGSMITH_API_KEY`·`COHERE_API_KEY` (선택) 등록
    - 부트스트랩 코드 실행 → `✅ PostgreSQL 연결 성공` 확인
    - 이 과정은 매 실습 시작 시 반복합니다
