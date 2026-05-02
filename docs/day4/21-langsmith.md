# 21H · LangSmith 트레이싱

## 학습목표

- LangSmith의 역할(LLM 애플리케이션 관측 가능성)을 설명할 수 있다
- Run/Trace 구조를 이해하고, 에이전트 실행을 트레이싱할 수 있다
- 토큰 사용량, 지연 시간, 비용을 분석할 수 있다
- 평가용 Dataset을 프로그래밍 방식으로 생성할 수 있다

---

<div class="colab-link" data-notebook="18_langsmith_tracing"></div>

## 왜 모니터링이 필요한가?

!!! tip "LangSmith = AI 앱의 "진료 기록부""
    전통 소프트웨어는 로그만 보면 디버깅이 가능하지만, LLM 애플리케이션은 프롬프트, 컨텍스트, 모델 파라미터가 모두 결합되어 비결정적 출력을 만듭니다. LangSmith는 이 모든 것을 **한 곳에서 추적**할 수 있게 해주는 관측 도구입니다.

### 전통 소프트웨어 vs LLM 애플리케이션

| | 전통 소프트웨어 | AI(LLM) 앱 |
|---|---|---|
| 출력 | 항상 같은 결과 (결정적) | 매번 다른 결과 (비결정적) |
| 버그 | 재현 가능 | 재현 어려움 |
| 디버깅 | 로그 확인 | 프롬프트+컨텍스트+모델 모두 확인 필요 |
| 테스트 | 단위 테스트 | **정량 평가 프레임워크** 필요 |

→ AI 앱은 "무엇이 왜 잘못됐는지" 추적하기 어려움 → **관측 가능성(Observability)**이 핵심 → LangSmith가 해결!

---

## Run/Trace 구조

LangSmith에서 모든 에이전트 실행은 **Trace**로 기록되고, 각 단계는 **Run**으로 세분됩니다.

```
Trace (전체 에이전트 실행 1건)
├── Run: generate_sql (AI 호출)
│   ├── 입력: {question: "환자 수?", schema: "..."}
│   ├── 출력: "SELECT COUNT(*) FROM patients"
│   ├── 토큰: 450 (in) + 12 (out) = 462
│   ├── 시간: 1.2초
│   └── 비용: $0.0003
├── Run: run_sql (SQL 실행)
│   ├── 입력: "SELECT COUNT(*) FROM patients"
│   ├── 출력: "30"
│   └── 시간: 0.3초
├── Run: validate (검증)
│   └── 결과: 에러 없음
└── Run: answer (AI 호출)
    ├── 입력: {result: "30", question: "..."}
    ├── 출력: "현재 등록된 환자는 30명입니다."
    ├── 토큰: 280 (in) + 25 (out) = 305
    └── 비용: $0.0002
```

!!! tip "LangSmith UI 화면 구성"
    LangSmith 웹 대시보드는 크게 4가지 화면으로 구성됩니다:

    **1. Trace 목록 (Projects 탭)**
    전체 실행 목록이 시간순으로 나열됩니다. 성공/실패 필터, 기간 필터, Feedback 점수 필터를 사용해 원하는 실행만 골라볼 수 있습니다. 각 행에는 실행 시간, 총 토큰, 지연 시간이 표시됩니다.

    **2. Trace 상세 (개별 Trace 클릭)**
    하나의 Trace를 클릭하면 각 노드의 입출력, 토큰 수, 지연 시간, 비용이 상세하게 표시됩니다. 프롬프트 전문과 LLM 응답 전문을 그대로 볼 수 있어 디버깅에 핵심적입니다.

    **3. Run Tree (트리 뷰)**
    부모-자식 관계로 실행 흐름을 시각화합니다. 어떤 노드가 어떤 순서로 실행되었는지, 재시도가 몇 번 발생했는지를 한눈에 파악할 수 있습니다. 각 Run의 시간 비율이 바 형태로 표시되어 병목을 바로 찾을 수 있습니다.

    **4. Analytics (통계 탭)**
    전체 프로젝트의 총 토큰 사용량, 평균 지연 시간, 비용 추이를 시계열 그래프로 보여줍니다. 일별/주별 추이를 확인하여 비용 관리와 성능 모니터링에 활용합니다.

### LangSmith UI에서 볼 수 있는 것 요약

| 화면 | 정보 |
|---|---|
| **Trace 목록** | 전체 실행 목록, 성공/실패 필터, 시간순 정렬 |
| **Trace 상세** | 각 노드의 입출력, 토큰, 지연, 비용 |
| **Run Tree** | 부모-자식 관계로 실행 흐름 시각화 |
| **Feedback** | 성공/실패 태깅, 점수 부여 |
| **Datasets** | 평가용 입력-기대출력 쌍 관리 |
| **Analytics** | 전체 통계 -- 총 토큰, 평균 지연, 비용 추이 |

!!! warning "무료 플랜 월 5,000 트레이스 제한"
    LangSmith 개인 무료 플랜은 **월 5,000 트레이스**까지 사용할 수 있습니다. 수업 중 실습으로는 충분하지만, 프로덕션 환경에서는 유료 플랜을 고려해야 합니다. 트레이스 수가 한도에 가까워지면 LangSmith 대시보드의 Usage 탭에서 확인할 수 있습니다. 또한 LangSmith 서버에 실행 데이터가 저장되므로, 민감한 의료 데이터 등을 다룰 때는 개인정보 마스킹에 주의하세요.

---

## 실습 1 -- LangSmith 환경변수 설정

### 부트스트랩

_힌트: `pip install`로 langgraph/langchain/langsmith/ragas 등 의존성 설치 후, `google.colab.userdata`에서 `OPENAI_API_KEY`/`NEON_DSN`/LangSmith 키를 읽어 `os.environ`에 주입하고 `sqlalchemy.create_engine`으로 Neon 연결을 만드세요._

!!! warning "env var 이름에 주의"
    `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` 는 **deprecated**.
    최신 `langsmith` SDK(0.1.70+)는 `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` 를 읽습니다. 두 이름은 당분간 호환되지만 새 프로젝트는 `LANGSMITH_*` 를 기본으로 쓰세요.

### LangSmith 환경변수 확인

_힌트: `LANGSMITH_TRACING="true"`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` 세 환경변수가 잘 잡혔는지 `os.environ.get(...)`로 확인하세요._

!!! note "핵심 정리"
    환경변수 3개만 설정하면 LangSmith 트레이싱이 **자동으로** 활성화됩니다:

    - `LANGSMITH_TRACING` = `"true"` -- 트레이싱 ON
    - `LANGSMITH_API_KEY` = LangSmith API 키
    - `LANGSMITH_PROJECT` = 프로젝트 이름 (트레이스 그룹)

### LangSmith Client 생성 + 프로젝트 확인

_힌트: `from langsmith import Client`로 클라이언트를 생성하고, 현재 `LANGSMITH_PROJECT` 값을 출력해 확인하세요._

---

## 실습 2 -- Day 3 에이전트 재구성 + 트레이싱

Day 3에서 만든 SQL 에이전트를 다시 구성합니다. 환경변수 설정만으로 모든 실행이 자동으로 LangSmith에 기록됩니다.

### 스키마 수집 함수

_힌트: `sqlalchemy.inspect`로 컬럼·FK를 가져와 `CREATE TABLE` 문자열을 만들고, `information_schema.columns` + `col_description`으로 COMMENT를 붙이는 `collect_schema(engine, tables)`를 작성하세요._

### AgentState + 가드레일

_힌트: `TypedDict`로 `question/sql/sql_result/error/answer/attempts` 필드를 가진 `AgentState`를 정의하고, 정규식으로 DDL/DML(`DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE`) 키워드를 차단하는 `sanitize_sql`을 만드세요._

### 노드 함수들

_힌트: Day 3과 동일하게 `generate_sql` (프롬프트→LLM→파싱), `run_sql` (`sanitize_sql`+`pd.read_sql`), `validate`, `answer` (결과 요약 프롬프트), `should_retry` (조건부 분기) 5개 노드를 작성하세요._

### 그래프 조립

_힌트: `StateGraph(AgentState)`로 4개 노드를 추가하고 `generate_sql → run_sql → validate`로 엣지를 연결, `validate`에 `should_retry` 조건부 엣지를 걸어 `compile()` 하세요._

---

## 실습 3 -- 10개 질문 실행 + 트레이스 확인

모든 실행이 LangSmith에 자동으로 기록됩니다. 실행 후 LangSmith UI에서 트레이스를 확인하세요.

_힌트: 10개 질문 리스트를 순회하며 `agent.invoke({"question": q, "attempts": 0})`를 호출하고, question/status/attempts/sql/answer/sql_result를 `results` 리스트에 모은 뒤 정답률을 출력하세요._

---

## 실습 4 -- LangSmith API로 트레이스 분석

### 토큰/비용/지연 분석

_힌트: `Client().list_runs(project_name=..., is_root=True, limit=10)`로 root run을 가져오고, 각 run의 `total_tokens`/`extra["runtime"]["token_usage"]`에서 토큰을 방어적으로 추출하여 토큰·지연(`end_time-start_time`)·비용을 DataFrame으로 정리하세요._

!!! note "핵심 정리"
    `list_runs()`의 `is_root=True` 옵션은 **root run만** 가져옵니다 (`langsmith>=0.1.70`). 이는 하위 노드 Run이 아닌, 에이전트 전체 실행 단위의 Trace를 의미합니다. 개별 노드의 세부 정보는 LangSmith UI의 Run Tree에서 확인하거나, `is_root` 를 생략하여 모든 Run을 가져올 수 있습니다.

!!! warning "토큰/비용이 0으로만 찍힌다면"
    최신 SDK에서 `run.total_tokens` / `run.prompt_tokens` 등 최상위 속성은 많은 경우 `None` 입니다. 위 `_token_usage()` 처럼 `run.extra["runtime"]["token_usage"]` 로 폴백하거나, LangSmith UI의 **Analytics** 탭에서 프로젝트 단위 집계로 확인하는 편이 더 안정적입니다.

### 시각화 -- 질문별 토큰/지연 2-패널 차트

_힌트: `matplotlib`의 `subplots(1, 2)`와 `barh`로 좌측에 토큰, 우측에 지연 시간을 가로 막대 차트로 그리고 `savefig`로 PNG 저장하세요._

!!! example "실습 -- 가장 느린 질문의 트레이스 열어 병목 찾기"
    1. 위 차트에서 **지연 시간이 가장 긴 질문**을 확인합니다.
    2. LangSmith UI (https://smith.langchain.com/) 에 접속합니다.
    3. 프로젝트 `sql-agent-final`을 클릭합니다.
    4. 해당 질문의 Trace를 클릭하여 **Run Tree**를 엽니다.
    5. 각 노드(generate_sql, run_sql, validate, answer)의 소요 시간을 비교합니다.
    6. **병목 노드**를 찾으세요:
        - `generate_sql`이 느리면: 프롬프트가 너무 길거나, 스키마 정보가 과다한 것
        - `run_sql`이 느리면: SQL 쿼리가 비효율적이거나, 데이터베이스 인덱스 부족
        - `answer`가 느리면: 결과 데이터가 너무 많아 요약에 시간이 걸린 것
        - **재시도(retry)**가 발생했다면: generate_sql이 여러 번 호출된 것이 원인
    7. 병목 원인과 개선 아이디어를 메모하세요 -- 발표에서 활용할 수 있습니다.

---

## 실습 5 -- 평가용 Dataset 생성

LangSmith Dataset은 질문(input)과 기대 답변(output)의 쌍입니다. 22H Ragas 평가에서 ground truth로 사용됩니다.

_힌트: `ls.create_dataset(dataset_name=...)`으로 데이터셋을 만들고, 질문/정답 쌍 10개를 `ls.create_example(inputs=..., outputs=..., dataset_id=...)`로 등록하세요. 동명 데이터셋이 있으면 `read_dataset` + `delete_dataset`으로 먼저 정리하면 됩니다._

!!! tip "Dataset 활용 팁"
    Dataset은 단순히 저장만 하는 것이 아닙니다. LangSmith UI에서:

    - **Datasets 탭**에서 생성한 데이터셋을 확인할 수 있습니다.
    - 각 Example을 클릭하면 입력(질문)과 기대 출력(ground truth)을 편집할 수 있습니다.
    - **Evaluator**를 연결하면 에이전트를 Dataset 전체에 대해 자동으로 평가할 수 있습니다.
    - 본인 프로젝트에서는 **본인 도메인의 질문 10개**로 Dataset을 만드세요.

---

## 실습 6 -- Feedback 태깅

실행 결과에 정답/오답 태그를 붙여 LangSmith에서 필터링하고 분석할 수 있습니다.

_힌트: `list_runs(is_root=True)`는 최신→과거 역순이므로 `start_time`으로 정렬하거나 질문 문자열로 매칭한 뒤, 각 run에 `ls.create_feedback(run_id=..., key="correctness", score=1.0 또는 0.0, comment=...)`로 정답/오답 태그를 부여하세요._

!!! tip "Feedback 활용법"
    Feedback을 부여하면 LangSmith UI에서 강력한 필터링이 가능합니다:

    - **Feedback 탭**에서 `correctness` 키로 필터링
    - `score=0` (실패)만 골라서 원인 분석
    - 시간대별 성공률 추이 확인
    - 특정 질문 유형별 성공률 비교

    프로덕션 환경에서는 사용자 피드백(좋아요/싫어요)을 `create_feedback`으로 기록하여 지속적인 품질 모니터링에 활용합니다.

---

## 실습 과제

!!! example "실습"
    1. **본인 에이전트에 LangSmith 트레이싱을 연결**하고 10개 질문을 실행하세요.
    2. LangSmith UI에서 **가장 느린 질문의 트레이스를 열어 병목 노드를 찾으세요**.
        - 어떤 노드가 가장 오래 걸렸나요?
        - 재시도(retry)가 발생했나요?
    3. **평가용 Dataset을 본인 질문 10개로 생성**하세요.
    4. (도전) Feedback으로 정답/오답을 태깅하고, LangSmith UI에서 실패 케이스만 필터링해보세요.

!!! question "생각해보기"
    - LangSmith 트레이싱 없이 에이전트를 디버깅하려면 어떻게 해야 할까요? print 문을 곳곳에 넣는 방법과 비교하면 어떤 장점이 있나요?
    - 토큰 사용량이 가장 많은 질문과 가장 적은 질문의 차이는 무엇인가요? 어떤 유형의 질문이 토큰을 많이 소비하나요?
    - 프로덕션 환경에서 LangSmith를 사용할 때, 민감한 데이터(환자 정보 등)를 어떻게 처리해야 할까요?

---

!!! note "핵심 정리"
    - **LangSmith** = LLM 앱의 관측 도구. 환경변수 3줄 설정으로 자동 트레이싱
    - **Run/Trace 구조**로 각 노드의 입출력, 토큰, 지연, 비용을 상세히 확인
    - `list_runs()` API로 프로그래밍 방식으로 트레이스 데이터 분석 가능
    - **matplotlib 시각화**로 질문별 토큰/지연 패턴을 한눈에 파악
    - **Dataset** = 평가용 질문+정답 모음 -- 22H Ragas에서 ground truth로 사용
    - **Feedback** = 실행 결과에 태그를 부여하여 성공/실패 필터링 및 품질 추적
